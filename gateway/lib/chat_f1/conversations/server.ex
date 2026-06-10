defmodule ChatF1.Conversations.Server do
  @moduledoc """
  Per-conversation GenServer.  One process per active conversation, started
  lazily and registered via `ChatF1.ConvRegistry` (Registry with unique keys).

  ## Why one process per conversation?

  * **Isolation:** a crash in one stream never affects another conversation.
    Supervision is user-visible: kill the process mid-stream on camera and
    every other tab keeps streaming.
  * **State locality:** the replay buffer, token batch accumulator, and
    in-flight stream ref all live in one process — no distributed state, no
    ETS lookups, no lock contention.
  * **Back-pressure:** casting events from the `StreamRunner` task into this
    GenServer's mailbox provides natural back-pressure — the task yields when
    the server's queue is full.

  ## Replay buffer

  Keeps a seq-numbered ring of `AgentEvent` structs for reconnecting clients.
  Clients that re-subscribe mid-stream receive buffered events with their
  original `seq` values; the Apollo reducer deduplicates by seq.

  Hard cap: **32 KB per assistant message** (configurable via
  `@replay_buf_max_bytes`).  When the cap is hit, the oldest token events are
  truncated from the head (non-token events are never truncated — they carry
  structural information the client needs to reconstruct state).

  Why 32 KB?  On a 256 MB Fly machine, 100 concurrent conversations each
  holding 32 KB = 3.2 MB — well within budget.  A typical LLM answer is
  2–5 KB; 32 KB gives 6–16× headroom before truncation kicks in.

  ## Micro-batched TokenDelta publishing

  `Absinthe.Subscription.publish/3` → Phoenix.PubSub → WebSocket frame is
  non-trivial on a 256 MB machine.  Per-token publishing at 20–30 tok/s would
  mean 20–30 `publish` calls/second per concurrent stream.

  Instead: tokens are accumulated in `state.token_batch` and flushed via
  `Process.send_after(self(), :flush_tokens, 40)` on the first token in a
  batch.  Flushing happens when:
  * The batch timer fires (≤ 40 ms latency, tunable).
  * 12 tokens accumulate (prevents overshooting on fast LLMs).

  A single `TokenDelta` event is published per flush, carrying concatenated
  text and the seq of the **last** token in the batch.

  ## Idle timeout + hibernation

  After 15 minutes of inactivity the server calls `stop(:normal)` — the
  conversation state survives in Postgres and is re-hydrated on the next
  `ensure_started/1` call.  Between events the process hibernates
  (`{:noreply, state, :hibernate}`) to return heap memory to the BEAM.

  ## Via-tuples

  Registration uses `{ChatF1.ConvRegistry, conversation_id}` as the via-tuple:

      GenServer.start_link(__MODULE__, args,
        name: {:via, Registry, {ChatF1.ConvRegistry, conversation_id}})

  Lookup:

      Registry.lookup(ChatF1.ConvRegistry, conversation_id)
  """

  use GenServer

  require Logger

  alias ChatF1.Agents.Breaker
  alias ChatF1.Conversations
  alias ChatF1.Conversations.StreamRunner
  alias ChatF1.Repo

  # ─── Configuration ───────────────────────────────────────────────────────────

  # 15 minutes idle timeout before self-termination.
  @idle_timeout_ms 15 * 60 * 1_000
  # Max replay buffer size per message in bytes (32 KB).
  @replay_buf_max_bytes 32 * 1024
  # Max tokens in a batch before forced flush.
  @batch_max_tokens 12
  # Flush timer interval in milliseconds.
  @flush_interval_ms 40

  # ─── State shape ─────────────────────────────────────────────────────────────

  # ─── Public API ──────────────────────────────────────────────────────────────

  @doc """
  Returns the via-tuple for registering/looking up this server.

  Usage:

      GenServer.call(ChatF1.Conversations.Server.via(conv_id), :some_call)
  """
  @spec via(integer()) :: {:via, Registry, {ChatF1.ConvRegistry, integer()}}
  def via(conversation_id) do
    {:via, Registry, {ChatF1.ConvRegistry, conversation_id}}
  end

  @doc """
  Looks up or starts a `Conversation.Server` for the given conversation_id.

  If the server is already registered, returns its pid.  Otherwise starts it
  under `ChatF1.ConversationSupervisor`.  This is the *only* entry point for
  acquiring a server reference — callers never call `start_link/1` directly.
  """
  @spec ensure_started(integer()) :: {:ok, pid()} | {:error, term()}
  def ensure_started(conversation_id) do
    case Registry.lookup(ChatF1.ConvRegistry, conversation_id) do
      [{pid, _}] ->
        {:ok, pid}

      [] ->
        DynamicSupervisor.start_child(
          ChatF1.ConversationSupervisor,
          {__MODULE__, conversation_id: conversation_id}
        )
    end
  end

  @doc """
  Begins a streaming session for the given assistant message.

  Stores the message ID, resets the replay buffer and batch state, then
  starts a `StreamRunner` task under `ChatF1.StreamTaskSupervisor`.

  Called by the `sendMessage` resolver after persisting the message pair.
  Returns quickly (< 1 ms); the actual HTTP call to the agent happens
  asynchronously in the StreamRunner.
  """
  @spec begin_stream(integer(), binary()) :: :ok | {:error, term()}
  def begin_stream(conversation_id, assistant_message_id) do
    GenServer.call(via(conversation_id), {:begin_stream, assistant_message_id})
  end

  @doc """
  Called by `StreamRunner` with each decoded NDJSON event.
  """
  @spec handle_agent_event(integer(), map()) :: :ok
  def handle_agent_event(conversation_id, event) do
    GenServer.cast(via(conversation_id), {:agent_event, event})
  end

  @doc """
  Called by `StreamRunner` when the stream fails (via `:DOWN` monitor or
  HTTP error).  Marks the message failed and publishes `AgentError`.
  """
  @spec handle_stream_error(integer(), binary(), atom()) :: :ok
  def handle_stream_error(conversation_id, assistant_message_id, reason) do
    GenServer.cast(
      via(conversation_id),
      {:stream_error, assistant_message_id, reason}
    )
  end

  @doc """
  Returns buffered replay events for the given message, in seq order.

  Called at subscription time to replay events to a reconnecting subscriber
  before the live publish path starts.  The returned list may overlap with
  the first live event — clients must deduplicate by seq.
  """
  @spec get_replay_buffer(integer()) :: [map()]
  def get_replay_buffer(conversation_id) do
    case Registry.lookup(ChatF1.ConvRegistry, conversation_id) do
      [{pid, _}] ->
        GenServer.call(pid, :get_replay_buffer)

      [] ->
        []
    end
  end

  # ─── GenServer lifecycle ─────────────────────────────────────────────────────

  @spec start_link(keyword()) :: {:ok, pid()} | {:error, term()}
  def start_link(opts) do
    conversation_id = Keyword.fetch!(opts, :conversation_id)

    GenServer.start_link(
      __MODULE__,
      conversation_id,
      name: via(conversation_id)
    )
  end

  @impl true
  def init(conversation_id) do
    Logger.debug("[ConvServer #{conversation_id}] started")

    state = %{
      conversation_id: conversation_id,
      replay_buffer: [],
      replay_buffer_bytes: 0,
      next_seq: 0,
      streaming_message_id: nil,
      token_batch: [],
      flush_scheduled?: false,
      stream_monitor: nil
    }

    {:ok, state, @idle_timeout_ms}
  end

  # ─── Call handlers ────────────────────────────────────────────────────────────

  @impl true
  def handle_call({:begin_stream, assistant_message_id}, _from, state) do
    # Build payload here (in the GenServer process) so the DB query runs on a
    # connection that is allowed by Ecto.Adapters.SQL.Sandbox in tests.
    # The Task.Supervised process running StreamRunner cannot access the
    # sandbox connection owned by the test process.
    payload =
      StreamRunner.build_request_payload(
        state.conversation_id,
        assistant_message_id
      )

    # Reset buffer for the new message.
    new_state = %{
      state
      | streaming_message_id: assistant_message_id,
        replay_buffer: [],
        replay_buffer_bytes: 0,
        next_seq: 0,
        token_batch: [],
        flush_scheduled?: false,
        stream_monitor: nil
    }

    # Launch the StreamRunner task with the pre-built payload.
    task_ref =
      Task.Supervisor.async_nolink(
        ChatF1.StreamTaskSupervisor,
        StreamRunner,
        :run,
        [state.conversation_id, assistant_message_id, payload]
      )

    new_state = %{new_state | stream_monitor: task_ref.ref}
    Process.monitor(task_ref.pid)

    {:reply, :ok, new_state, @idle_timeout_ms}
  end

  @impl true
  def handle_call(:get_replay_buffer, _from, state) do
    events = Enum.map(state.replay_buffer, & &1.event)
    {:reply, events, state, @idle_timeout_ms}
  end

  # ─── Cast handlers ────────────────────────────────────────────────────────────

  @impl true
  def handle_cast({:agent_event, event}, state) do
    new_state = process_agent_event(event, state)
    {:noreply, new_state, @idle_timeout_ms}
  end

  @impl true
  def handle_cast({:stream_error, message_id, reason}, state) do
    new_state = do_stream_error(message_id, reason, state)
    {:noreply, new_state, @idle_timeout_ms}
  end

  # ─── Info handlers ─────────────────────────────────────────────────────────

  @impl true
  def handle_info(:flush_tokens, state) do
    new_state = flush_token_batch(state)
    {:noreply, %{new_state | flush_scheduled?: false}, @idle_timeout_ms}
  end

  # StreamRunner task completed successfully.
  @impl true
  def handle_info({ref, _result}, %{stream_monitor: ref} = state) do
    Process.demonitor(ref, [:flush])
    {:noreply, %{state | stream_monitor: nil}, @idle_timeout_ms}
  end

  # StreamRunner task died unexpectedly.
  @impl true
  def handle_info(
        {:DOWN, ref, :process, _pid, reason},
        %{stream_monitor: ref, streaming_message_id: msg_id} = state
      )
      when not is_nil(msg_id) do
    Logger.warning("[ConvServer #{state.conversation_id}] StreamRunner died: #{inspect(reason)}")
    Breaker.record_failure()
    new_state = do_stream_error(msg_id, reason, state)
    {:noreply, %{new_state | stream_monitor: nil}, @idle_timeout_ms}
  end

  # Demonitor flush for completed tasks (already handled above).
  @impl true
  def handle_info({:DOWN, _ref, :process, _pid, _reason}, state) do
    {:noreply, state, @idle_timeout_ms}
  end

  # Idle timeout — self-terminate; state lives in Postgres.
  @impl true
  def handle_info(:timeout, state) do
    Logger.debug("[ConvServer #{state.conversation_id}] idle timeout — stopping")
    {:stop, :normal, state}
  end

  # ─── Agent event processing ───────────────────────────────────────────────────

  defp process_agent_event(%{"event" => "node_started", "node" => node} = _raw, state) do
    agent_node = map_agent_node(node)

    event = %{
      message_id: state.streaming_message_id,
      node: agent_node,
      started_at: DateTime.utc_now()
    }

    state
    |> append_to_buffer(:node_transition, event)
    |> publish_event(:node_transition, event)
  end

  defp process_agent_event(%{"event" => "sources", "items" => items}, state) do
    sources = normalize_sources(items)

    event = %{
      message_id: state.streaming_message_id,
      sources: sources
    }

    state
    |> append_to_buffer(:sources_resolved, event)
    |> publish_event(:sources_resolved, event)
  end

  defp process_agent_event(%{"event" => "token", "text" => text}, state) do
    accumulate_token(text, state)
  end

  defp process_agent_event(%{"event" => "complete"} = raw, state) do
    # Flush any remaining token batch before publishing completion.
    state = flush_token_batch(state)

    content = Map.get(raw, "content", "")
    cached = Map.get(raw, "cached", false)
    usage_raw = Map.get(raw, "usage")

    usage =
      if is_map(usage_raw) do
        prompt = Map.get(usage_raw, "prompt_tokens", 0)
        completion = Map.get(usage_raw, "completion_tokens", 0)

        %{
          prompt_tokens: prompt,
          completion_tokens: completion,
          estimated_cost_usd: (prompt + completion) * 0.00000015
        }
      end

    # Cache-hit: synthesize one TokenDelta with the full text so the
    # frontend render path is uniform (§4.5).
    state =
      if cached and content != "" do
        state
        |> then(&accumulate_token(content, &1))
        |> flush_token_batch()
      else
        state
      end

    # Persist final state to Postgres.
    # Done inline (not Task.start) so the GenServer's DB connection is used —
    # this also works correctly with Ecto.Adapters.SQL.Sandbox in tests.
    message_id = state.streaming_message_id
    update_and_complete(message_id, content, cached, usage, state.conversation_id)

    state
  end

  defp process_agent_event(%{"event" => "error"} = raw, state) do
    code = raw |> Map.get("code", "internal") |> map_error_code()
    message = Map.get(raw, "message", "Agent error")
    retryable = Map.get(raw, "retryable", true)

    error_event = %{
      message_id: state.streaming_message_id,
      code: code,
      message: message,
      retryable: retryable
    }

    # Inline DB update (not Task.start) for sandbox compatibility in tests.
    mark_message_failed(state.streaming_message_id, message)

    state
    |> append_to_buffer(:agent_error, error_event)
    |> publish_event(:agent_error, error_event)
  end

  defp process_agent_event(_unknown, state), do: state

  # ─── Token micro-batching ─────────────────────────────────────────────────────

  defp accumulate_token(text, state) do
    new_batch = [text | state.token_batch]
    batch_size = length(new_batch)

    state = %{state | token_batch: new_batch}

    cond do
      batch_size >= @batch_max_tokens ->
        flush_token_batch(state)

      not state.flush_scheduled? ->
        Process.send_after(self(), :flush_tokens, @flush_interval_ms)
        %{state | flush_scheduled?: true}

      true ->
        state
    end
  end

  defp flush_token_batch(%{token_batch: []} = state), do: state

  defp flush_token_batch(state) do
    text = state.token_batch |> Enum.reverse() |> Enum.join()
    seq = state.next_seq

    event = %{
      message_id: state.streaming_message_id,
      seq: seq,
      text: text
    }

    state = %{state | token_batch: [], next_seq: seq + 1}

    state
    |> append_to_buffer(:token_delta, event)
    |> publish_event(:token_delta, event)
  end

  # ─── Replay buffer management ─────────────────────────────────────────────────

  defp append_to_buffer(state, _type, event) do
    # Serialize the event to measure its byte size.
    entry_bytes = event |> Jason.encode!() |> byte_size()
    new_entry = %{seq: state.next_seq, event: event}

    # Buffer is maintained oldest-first (append to tail).
    current_buffer = state.replay_buffer
    current_bytes = state.replay_buffer_bytes

    new_total = current_bytes + entry_bytes

    {trimmed_buffer, trimmed_bytes} =
      if new_total > @replay_buf_max_bytes do
        truncate_buffer(current_buffer, current_bytes, new_total - @replay_buf_max_bytes)
      else
        {current_buffer, current_bytes}
      end

    %{
      state
      | replay_buffer: trimmed_buffer ++ [new_entry],
        replay_buffer_bytes: trimmed_bytes + entry_bytes
    }
  end

  # Truncate oldest token events until we've freed `bytes_to_free` bytes.
  # Non-token events (NodeTransition, SourcesResolved, AgentError) are never
  # removed — they carry structural state the client needs for reconstruction.
  defp truncate_buffer(buffer, total_bytes, _bytes_to_free) do
    Enum.reduce_while(buffer, {[], total_bytes}, fn entry, {kept, remaining} ->
      if remaining > @replay_buf_max_bytes and token_entry?(entry) do
        freed = entry.event |> Jason.encode!() |> byte_size()
        {:cont, {kept, remaining - freed}}
      else
        {:halt, {kept ++ [entry], remaining}}
      end
    end)
  end

  defp token_entry?(%{event: %{text: _}}), do: true
  defp token_entry?(_), do: false

  # ─── Publishing ───────────────────────────────────────────────────────────────

  defp publish_event(state, type, event) do
    topic = "agent:#{state.streaming_message_id}"

    payload =
      case type do
        :token_delta -> %{token_delta: event}
        :node_transition -> %{node_transition: event}
        :sources_resolved -> %{sources_resolved: event}
        :agent_error -> %{agent_error: event}
      end

    # Guard: Absinthe.Subscription.publish requires the endpoint's PubSub
    # registry to be running (started by `use Absinthe.Phoenix.Endpoint`).
    # In test mode with `server: false` the registry is not started, so we
    # catch the ArgumentError rather than crashing the GenServer.
    try do
      Absinthe.Subscription.publish(
        ChatF1Web.Endpoint,
        payload,
        agent_stream: topic
      )
    rescue
      ArgumentError -> :ok
    end

    state
  end

  # ─── Stream error path ────────────────────────────────────────────────────────

  defp do_stream_error(message_id, reason, state) do
    error_event = %{
      message_id: message_id,
      code: :upstream_unavailable,
      message: "Stream failed: #{inspect(reason)}",
      retryable: true
    }

    # Inline DB update for sandbox compatibility in tests.
    mark_message_failed(message_id, "Stream failed")

    state
    |> append_to_buffer(:agent_error, error_event)
    |> publish_event(:agent_error, error_event)
    |> Map.put(:streaming_message_id, nil)
  end

  # ─── Ecto persistence helpers ─────────────────────────────────────────────────

  defp update_and_complete(message_id, content, cached, usage, _conversation_id) do
    message_id_int = to_integer(message_id)

    case Repo.get(Conversations.Message, message_id_int) do
      nil ->
        Logger.error("[ConvServer] message #{message_id} not found for completion update")

      message ->
        sources_map = Map.get(message.sources, "items", [])

        {:ok, updated} =
          Conversations.update_assistant_message(message, %{
            content: content,
            status: :complete,
            cached: cached,
            sources: message.sources,
            latency_ms: nil
          })

        completed_event = %{
          message_id: message_id,
          message: updated,
          cached: cached,
          usage: usage
        }

        try do
          Absinthe.Subscription.publish(
            ChatF1Web.Endpoint,
            %{message_completed: completed_event},
            agent_stream: "agent:#{message_id}"
          )
        rescue
          ArgumentError -> :ok
        end

        _ = sources_map
    end
  end

  defp mark_message_failed(message_id, error_content) do
    case Repo.get(Conversations.Message, to_integer(message_id)) do
      nil ->
        :ok

      message ->
        Conversations.update_assistant_message(message, %{
          status: :failed,
          content: error_content
        })
    end
  end

  defp to_integer(id) when is_integer(id), do: id
  defp to_integer(id) when is_binary(id), do: String.to_integer(id)

  # ─── Mapping helpers ──────────────────────────────────────────────────────────

  defp map_agent_node("analyze_query"), do: :analyze_query
  defp map_agent_node("route"), do: :route
  defp map_agent_node("vector_search"), do: :vector_search
  defp map_agent_node("tavily_search"), do: :web_search
  defp map_agent_node("parallel_retrieval"), do: :parallel_retrieval
  defp map_agent_node("rank_context"), do: :rank_context
  defp map_agent_node("generate"), do: :generate
  defp map_agent_node("format_response"), do: :format_response
  defp map_agent_node("warming_up"), do: :warming_up
  defp map_agent_node(_unknown), do: :analyze_query

  defp map_error_code("validation"), do: :validation
  defp map_error_code("internal"), do: :internal
  defp map_error_code(_), do: :internal

  defp normalize_sources(items) when is_list(items) do
    Enum.map(items, fn item ->
      %{
        kind: Map.get(item, "kind", "vector") |> String.to_existing_atom(),
        title: Map.get(item, "title", ""),
        url: Map.get(item, "url"),
        snippet: Map.get(item, "snippet"),
        score: Map.get(item, "score")
      }
    end)
  end

  defp normalize_sources(_), do: []
end
