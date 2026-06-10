defmodule ChatF1Web.Schema.Resolvers.ConversationResolvers do
  @moduledoc """
  Resolver functions for conversation queries and mutations.

  ## IDOR prevention

  Every resolver that returns conversation data passes `viewer_id` from the
  Absinthe context into `Conversations.get_conversation/2`.  The context
  module adds `WHERE viewer_id = $1` to every query, so a valid token for
  viewer A cannot retrieve viewer B's data.
  """

  require Logger

  alias ChatF1.Agents.Client, as: AgentClient
  alias ChatF1.Conversations
  alias ChatF1.RateLimit.Server, as: RateLimitServer

  # ── Queries ──────────────────────────────────────────────────────────────────

  @doc "Resolves the `conversation` query — scoped to the viewer."
  def get_conversation(_parent, %{id: id}, %{context: %{viewer_id: viewer_id}}) do
    case Conversations.get_conversation(id, viewer_id) do
      nil -> {:ok, nil}
      conversation -> {:ok, conversation}
    end
  end

  @doc "Resolves the `conversations` query — returns only the viewer's own list."
  def list_conversations(_parent, _args, %{context: %{viewer_id: viewer_id}}) do
    {:ok, Conversations.list_conversations(viewer_id)}
  end

  @doc "Resolves the `rateLimitStatus` query for the current viewer."
  def rate_limit_status(_parent, _args, %{context: %{viewer_token: token}})
      when is_binary(token) do
    key = :crypto.hash(:sha256, token) |> Base.encode16(case: :lower)
    status = RateLimitServer.status(key)
    {:ok, status}
  end

  def rate_limit_status(_parent, _args, _context) do
    {:error, :internal}
  end

  # ── Mutations ────────────────────────────────────────────────────────────────

  @doc """
  `startConversation` — creates a new conversation for the viewer.
  """
  def start_conversation(_parent, _args, %{context: %{viewer_id: viewer_id}}) do
    Conversations.create_conversation(viewer_id)
  end

  @doc """
  `sendMessage` — the synchronous Phase 2 implementation.

  1. Validates the conversation belongs to the viewer (IDOR guard).
  2. Validates the input content (changeset-level).
  3. Atomically inserts user message + assistant placeholder (Ecto.Multi).
  4. Calls the agent with a last-10 history window.
  5. Updates the assistant placeholder with the aggregated result.
  6. Returns `{userMessage, assistantMessageId}`.

  On agent failure the placeholder is marked `:failed` and a normalized
  UPSTREAM_UNAVAILABLE error is returned.  The two DB rows always exist.
  """
  def send_message(_parent, %{conversation_id: conv_id, content: content}, %{
        context: %{viewer_id: viewer_id}
      }) do
    with {:conv, %{} = conversation} <-
           {:conv, Conversations.get_conversation(conv_id, viewer_id)},
         {:multi, {:ok, %{user_message: user_msg, assistant_message: asst_msg}}} <-
           {:multi, Conversations.insert_message_pair(conversation.id, content)} do
      # Build the last-10 turns history window for the agent.
      # We include the new user message in the history.
      history =
        conversation.id
        |> Conversations.list_messages()
        |> Enum.take(-10)
        |> Enum.map(fn m ->
          %{role: to_string(m.role), content: m.content}
        end)

      request_id = Ecto.UUID.generate()

      start_ms = System.monotonic_time(:millisecond)

      result =
        :telemetry.span(
          [:chatf1, :agent, :stream],
          %{request_id: request_id},
          fn ->
            r = AgentClient.chat(content, history, request_id)
            {r, %{cached: match?({:ok, %{cached: true}}, r)}}
          end
        )

      elapsed_ms = System.monotonic_time(:millisecond) - start_ms

      case result do
        {:ok, agent_result} ->
          sources = encode_sources(agent_result.sources)

          {:ok, updated_msg} =
            Conversations.update_assistant_message(asst_msg, %{
              content: agent_result.content,
              status: :complete,
              sources: sources,
              cached: agent_result.cached,
              latency_ms: elapsed_ms,
              intent: agent_result.intent
            })

          {:ok,
           %{
             user_message: user_msg,
             assistant_message_id: updated_msg.id
           }}

        {:error, {:agent_error, code, _message}} when code in ["validation"] ->
          mark_failed(asst_msg, "Input rejected by agent validation.")
          {:error, %{message: "Message rejected by agent", extensions: %{code: "VALIDATION"}}}

        {:error, _} ->
          mark_failed(asst_msg, "Agent service unavailable.")

          {:error,
           %{
             message: "Upstream service unavailable",
             extensions: %{code: "UPSTREAM_UNAVAILABLE"}
           }}
      end
    else
      {:conv, nil} ->
        {:error, %{message: "Conversation not found", extensions: %{code: "NOT_FOUND"}}}

      {:multi, {:error, step, changeset, _changes}} ->
        Logger.error("sendMessage multi failed at #{step}: #{inspect(changeset)}")

        {:error, %{message: "Validation failed", extensions: %{code: "VALIDATION"}}}
    end
  end

  @doc "`deleteConversation` — removes a conversation owned by the viewer."
  def delete_conversation(_parent, %{id: id}, %{context: %{viewer_id: viewer_id}}) do
    case Conversations.delete_conversation(id, viewer_id) do
      {:ok, _} -> {:ok, true}
      {:error, :not_found} -> {:error, :not_found}
    end
  end

  # ─── Private helpers ─────────────────────────────────────────────────────────

  defp mark_failed(message, error_content) do
    Conversations.update_assistant_message(message, %{
      status: :failed,
      content: error_content
    })
  end

  # Encode source list as a map for the JSONB column.
  # Schema stores sources as %{"items" => [...]} to keep a versioned envelope.
  defp encode_sources(sources) when is_list(sources) do
    %{"items" => Enum.map(sources, &Map.from_struct/1)}
  rescue
    _ -> %{"items" => []}
  end

  defp encode_sources(_), do: %{"items" => []}
end
