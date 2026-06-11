defmodule ChatF1.Showcase.Replayer do
  @moduledoc """
  Replays a cached SHOWCASE answer through the *identical* publish path used by
  live streaming — so the frontend never receives a different event shape.

  ## Replay sequence

  1. `NodeTransition{REPLAYING_CACHE}` — tells the UI this is a cache replay.
  2. One `TokenDelta` per entry in `answer.token_batches`, each paced by the
     corresponding delay in `answer.token_timing_histogram` via
     `Process.send_after`.
  3. `SourcesResolved` — same sources as the original answer.
  4. `MessageCompleted{cached: true}` — persisted to Postgres with `cached: true`.

  ## Honesty guarantee (ARCHITECTURE risk #12)

  * `MessageCompleted.cached` is always `true`.
  * `NodeTransition.node` is always `REPLAYING_CACHE`.
  * The frontend must surface these fields (phase 6 UI wires the badge).
  * Neither value is ever overridden — this is structurally enforced by running
    through the same `Conversation.Server` publish path with no workarounds.

  ## Fallback (no match in SHOWCASE)

  If `ChatF1.Showcase.find_nearest/1` returns `{:error, :no_match}`, the caller
  publishes a `AgentError{BUDGET_EXHAUSTED, retryable: false}` directly and
  marks the message `:failed`.  This module is not invoked in that path.
  """

  require Logger

  alias ChatF1.Conversations
  alias ChatF1.Repo
  alias ChatF1.Showcase.Answer

  # Default delay between batches if the histogram has no timing for this index.
  @default_delay_ms 40

  @doc """
  Runs the replay for `assistant_message_id` using `answer`.

  Called from `Conversation.Server` via `Task.Supervisor.async_nolink` (same
  as the live StreamRunner) so the server's `:DOWN` monitor handles crashes.
  Casts events into the server's mailbox using `handle_agent_event/2`.
  """
  @spec run(integer(), binary(), Answer.t()) :: :ok
  def run(conversation_id, assistant_message_id, %Answer{} = answer) do
    Logger.debug("[Replayer #{conversation_id}] starting replay for msg #{assistant_message_id}")

    alias ChatF1.Conversations.Server, as: ConvServer

    # 1. NodeTransition: REPLAYING_CACHE
    ConvServer.handle_agent_event(conversation_id, %{
      "event" => "node_started",
      "node" => "replaying_cache"
    })

    # 2. Token batches paced by histogram
    batches = answer.token_batches
    histogram = answer.token_timing_histogram

    batches
    |> Enum.with_index()
    |> Enum.each(fn {batch_text, idx} ->
      delay = Enum.at(histogram, idx, @default_delay_ms)
      Process.sleep(max(delay, 0))

      ConvServer.handle_agent_event(conversation_id, %{
        "event" => "token",
        "text" => batch_text
      })
    end)

    # 3. SourcesResolved
    if answer.sources != [] do
      sources = Enum.map(answer.sources, &normalize_source/1)

      ConvServer.handle_agent_event(conversation_id, %{
        "event" => "sources",
        "items" => sources
      })
    end

    # 4. Complete — persisted with cached: true
    ConvServer.handle_agent_event(conversation_id, %{
      "event" => "complete",
      "content" => answer.content,
      "cached" => true,
      "usage" => nil
    })

    # Persist sources onto the message row (Phase 4 handoff debt).
    persist_sources(assistant_message_id, answer.sources)

    Logger.debug("[Replayer #{conversation_id}] replay complete for msg #{assistant_message_id}")
    :ok
  end

  # ─── Private helpers ──────────────────────────────────────────────────────────

  defp normalize_source(source) when is_map(source) do
    %{
      "kind" => source["kind"] || source[:kind] || "vector",
      "title" => source["title"] || source[:title] || "",
      "url" => source["url"] || source[:url],
      "snippet" => source["snippet"] || source[:snippet],
      "score" => source["score"] || source[:score]
    }
  end

  defp persist_sources(assistant_message_id, sources) when is_list(sources) and sources != [] do
    msg_id_int =
      case assistant_message_id do
        id when is_integer(id) -> id
        id when is_binary(id) -> String.to_integer(id)
      end

    case Repo.get(Conversations.Message, msg_id_int) do
      nil ->
        :ok

      message ->
        Conversations.update_assistant_message(message, %{sources: sources})
    end
  end

  defp persist_sources(_assistant_message_id, _sources), do: :ok
end
