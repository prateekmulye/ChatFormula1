defmodule ChatF1.Conversations.StreamRunner do
  @moduledoc """
  Supervised streaming HTTP task that consumes the agent's NDJSON stream.

  One `StreamRunner` runs per active assistant message, started under
  `ChatF1.StreamTaskSupervisor` (a `Task.Supervisor`) by `Conversation.Server`
  via `Task.Supervisor.async_nolink/3`.  The owning `Conversation.Server`
  monitors the task via `Process.monitor/1` so an unexpected crash is caught
  and translated into a stream error event — other conversations are
  unaffected.

  ## NDJSON line buffering

  Req/Finch delivers the response body in arbitrary chunks.  A JSON object
  may span multiple chunks, or multiple objects may arrive in one chunk.
  `StreamRunner` keeps a partial-line carry-over buffer:

  1. Append the chunk to `carry`.
  2. Split on `\n`.
  3. All but the last element are complete lines — decode and cast to the
     `Conversation.Server`.
  4. The last element is the new `carry` (empty string if the chunk ended
     with `\n`).

  ## Cold-start / backoff

  The agent runs on Render's free tier and may take 30–60 s to cold-start.
  On connection refused or `recv_timeout`:

  1. Emit a gateway-synthesized `NodeTransition{WARMING_UP}` so the UI
     shows the pit-radio animation instead of a dead spinner.
  2. Retry with exponential backoff: 2 s, 4 s, 8 s.
  3. Give up after total elapsed time exceeds `@max_retry_ms` (45 s).
  4. On final failure, cast `:stream_error` to the owning server.

  ## Telemetry

  * `:telemetry.span([:chatf1, :agent, :stream], ...)` wraps the entire call.
  * The first `token` event emits `[:chatf1, :agent, :first_token]` with
    `%{ttft_ms: <elapsed since stream open>}` (TTFT measurement).
  """

  require Logger

  @connect_timeout 5_000
  @recv_timeout 60_000
  @max_retry_ms 45_000
  @initial_backoff_ms 2_000

  @doc """
  Entry point called by `Task.Supervisor.async_nolink/3`.

  Checks the circuit breaker, builds the agent request payload, and starts
  streaming.  On cold-start errors, emits WARMING_UP and retries with
  exponential backoff.
  """
  @spec run(integer(), binary()) :: :ok
  def run(conversation_id, assistant_message_id) do
    case ChatF1.Agents.Breaker.check() do
      {:error, :upstream_unavailable} ->
        Logger.warning("[StreamRunner #{assistant_message_id}] breaker open — short-circuit")

        ChatF1.Conversations.Server.handle_stream_error(
          conversation_id,
          assistant_message_id,
          :upstream_unavailable
        )

        :ok

      {:ok, :proceed} ->
        do_stream(conversation_id, assistant_message_id, 0)
    end
  end

  defp do_stream(conversation_id, assistant_message_id, attempt) do
    start_ms = System.monotonic_time(:millisecond)

    :telemetry.span(
      [:chatf1, :agent, :stream],
      %{message_id: assistant_message_id, conversation_id: conversation_id},
      fn ->
        result = attempt_stream(conversation_id, assistant_message_id, attempt, start_ms)
        {result, %{attempt: attempt}}
      end
    )
  end

  defp attempt_stream(conversation_id, assistant_message_id, attempt, start_ms) do
    agent_url = Application.fetch_env!(:chat_f1, :agent_url)
    token = Application.fetch_env!(:chat_f1, :internal_api_token)

    payload = build_payload(conversation_id, assistant_message_id)

    # State for the streaming reducer.
    reducer_state = %{
      carry: "",
      first_token_emitted?: false,
      stream_start_ms: start_ms,
      conversation_id: conversation_id,
      assistant_message_id: assistant_message_id
    }

    result =
      Req.post(
        agent_url <> "/internal/chat",
        json: payload,
        headers: [{"authorization", "Bearer #{token}"}],
        connect_options: [timeout: @connect_timeout],
        receive_timeout: @recv_timeout,
        into: fn chunk, {req, resp} ->
          new_state = process_chunk(chunk, resp.private[:reducer_state] || reducer_state)
          {:cont, {req, put_in(resp.private[:reducer_state], new_state)}}
        end
      )

    case result do
      {:ok, _resp} ->
        ChatF1.Agents.Breaker.record_success()
        :ok

      {:error, exception} ->
        handle_stream_failure(
          conversation_id,
          assistant_message_id,
          attempt,
          start_ms,
          exception
        )
    end
  end

  defp handle_stream_failure(
         conversation_id,
         assistant_message_id,
         attempt,
         start_ms,
         exception
       ) do
    elapsed_ms = System.monotonic_time(:millisecond) - start_ms
    error_msg = Exception.message(exception)

    Logger.warning(
      "[StreamRunner #{assistant_message_id}] attempt #{attempt + 1} failed: #{error_msg}"
    )

    if cold_start_error?(exception) and elapsed_ms < @max_retry_ms do
      backoff_ms = min(@initial_backoff_ms * :math.pow(2, attempt) |> round(), 10_000)
      remaining_ms = @max_retry_ms - elapsed_ms

      if backoff_ms < remaining_ms do
        # Emit WARMING_UP on first retry.
        if attempt == 0 do
          emit_warming_up(conversation_id, assistant_message_id)
        end

        Logger.info(
          "[StreamRunner #{assistant_message_id}] cold-start detected, retrying in #{backoff_ms}ms"
        )

        Process.sleep(backoff_ms)
        attempt_stream(conversation_id, assistant_message_id, attempt + 1, start_ms)
      else
        final_failure(conversation_id, assistant_message_id, :upstream_unavailable)
      end
    else
      ChatF1.Agents.Breaker.record_failure()
      final_failure(conversation_id, assistant_message_id, :upstream_unavailable)
    end
  end

  defp final_failure(conversation_id, assistant_message_id, reason) do
    ChatF1.Conversations.Server.handle_stream_error(
      conversation_id,
      assistant_message_id,
      reason
    )

    :error
  end

  # ─── Chunk processing ─────────────────────────────────────────────────────────

  defp process_chunk(chunk, state) when is_binary(chunk) do
    full = state.carry <> chunk
    lines = String.split(full, "\n")

    # All elements except the last are complete lines.
    # The last element is the carry-over (may be empty if chunk ended with \n).
    {complete_lines, [new_carry]} = Enum.split(lines, length(lines) - 1)

    new_state =
      Enum.reduce(complete_lines, state, fn line, acc ->
        process_line(String.trim(line), acc)
      end)

    %{new_state | carry: new_carry}
  end

  defp process_chunk(_other, state), do: state

  defp process_line("", state), do: state

  defp process_line(line, state) do
    case Jason.decode(line) do
      {:ok, event} ->
        handle_decoded_event(event, state)

      {:error, reason} ->
        Logger.debug("[StreamRunner] JSON decode failed: #{inspect(reason)} — line: #{line}")
        state
    end
  end

  defp handle_decoded_event(%{"event" => "token"} = event, state) do
    state =
      if not state.first_token_emitted? do
        ttft_ms = System.monotonic_time(:millisecond) - state.stream_start_ms

        :telemetry.execute(
          [:chatf1, :agent, :first_token],
          %{ttft_ms: ttft_ms},
          %{
            message_id: state.assistant_message_id,
            conversation_id: state.conversation_id
          }
        )

        %{state | first_token_emitted?: true}
      else
        state
      end

    ChatF1.Conversations.Server.handle_agent_event(state.conversation_id, event)
    state
  end

  defp handle_decoded_event(event, state) do
    ChatF1.Conversations.Server.handle_agent_event(state.conversation_id, event)
    state
  end

  # ─── Helpers ──────────────────────────────────────────────────────────────────

  defp build_payload(conversation_id, _assistant_message_id) do
    messages = ChatF1.Conversations.list_messages(conversation_id)
    history_window = Enum.take(messages, -11)

    {history, current_message} = split_history(history_window)

    %{
      message: current_message,
      history: history,
      request_id: Ecto.UUID.generate()
    }
  end

  defp split_history([]) do
    {[], ""}
  end

  defp split_history(messages) do
    # The last user message before the assistant placeholder is the current input.
    # History is everything before it.
    messages_excl_placeholder =
      Enum.reject(messages, fn m -> m.status == :pending end)

    case Enum.reverse(messages_excl_placeholder) do
      [last | rest] when last.role == :user ->
        history =
          rest
          |> Enum.reverse()
          |> Enum.map(fn m -> %{role: to_string(m.role), content: m.content} end)

        {history, last.content}

      _ ->
        {[], ""}
    end
  end

  defp cold_start_error?(%Mint.TransportError{reason: :econnrefused}), do: true
  defp cold_start_error?(%Req.TransportError{reason: :econnrefused}), do: true
  defp cold_start_error?(%Req.TransportError{}), do: true
  defp cold_start_error?(%Mint.TransportError{reason: :timeout}), do: true

  defp cold_start_error?(exception) do
    message = Exception.message(exception)
    String.contains?(message, "econnrefused") or String.contains?(message, "connection refused")
  end

  defp emit_warming_up(conversation_id, assistant_message_id) do
    ChatF1.Conversations.Server.handle_agent_event(conversation_id, %{
      "event" => "node_started",
      "node" => "warming_up"
    })

    _ = assistant_message_id
  end
end
