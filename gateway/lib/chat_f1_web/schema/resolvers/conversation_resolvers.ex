defmodule ChatF1Web.Schema.Resolvers.ConversationResolvers do
  @moduledoc """
  Resolver functions for conversation queries, mutations, and subscriptions.

  ## Phase 3 sendMessage semantics

  `sendMessage` is now **async**:

  1. Validates conversation ownership (IDOR guard).
  2. Validates input (changeset-level: length, control chars, repetition).
  3. `Ecto.Multi` inserts user message + assistant placeholder atomically.
  4. Ensures the `Conversation.Server` is running (`ensure_started/1`).
  5. Calls `Conversation.Server.begin_stream/2` — kicks off `StreamRunner`
     under `Task.Supervisor`.
  6. Returns `{userMessage, assistantMessageId}` in < 50 ms (no LLM work).

  The caller then subscribes to `agentStream(messageId: <id>)` to receive
  streaming events.

  ## IDOR prevention

  Every resolver that returns conversation data passes `viewer_id` from the
  Absinthe context into `Conversations.get_conversation/2`.  The context
  module adds `WHERE viewer_id = $1` to every query.
  """

  require Logger

  import Ecto.Query, only: []

  alias ChatF1.Agents.Breaker
  alias ChatF1.Conversations
  alias ChatF1.Conversations.MessageFeedback
  alias ChatF1.Conversations.Server, as: ConvServer
  alias ChatF1.RateLimit.Server, as: RateLimitServer
  alias ChatF1.Repo

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

  @doc "Resolves the `systemHealth` query — current gateway + agent health."
  def system_health(_parent, _args, _context) do
    health = Breaker.system_health()
    {:ok, health}
  end

  # ── Mutations ────────────────────────────────────────────────────────────────

  @doc """
  `startConversation` — creates a new conversation for the viewer.
  """
  def start_conversation(_parent, _args, %{context: %{viewer_id: viewer_id}}) do
    Conversations.create_conversation(viewer_id)
  end

  @doc """
  `sendMessage` — Phase 3 async implementation.

  Persists the message pair and immediately kicks off the streaming pipeline.
  Returns `{userMessage, assistantMessageId}` in < 50 ms.

  The caller subscribes to `agentStream(messageId: <assistantMessageId>)` for
  events.  This resolver no longer blocks on the LLM call.
  """
  def send_message(_parent, %{conversation_id: conv_id, content: content}, %{
        context: %{viewer_id: viewer_id}
      }) do
    with {:conv, %{} = conversation} <-
           {:conv, Conversations.get_conversation(conv_id, viewer_id)},
         {:multi, {:ok, %{user_message: user_msg, assistant_message: asst_msg}}} <-
           {:multi, Conversations.insert_message_pair(conversation.id, content)},
         {:server, {:ok, _pid}} <-
           {:server, ConvServer.ensure_started(conversation.id)},
         {:stream, :ok} <-
           {:stream, ConvServer.begin_stream(conversation.id, to_string(asst_msg.id))} do
      {:ok,
       %{
         user_message: user_msg,
         assistant_message_id: to_string(asst_msg.id)
       }}
    else
      {:conv, nil} ->
        {:error, %{message: "Conversation not found", extensions: %{code: "NOT_FOUND"}}}

      {:multi, {:error, step, changeset, _changes}} ->
        Logger.error("sendMessage multi failed at #{step}: #{inspect(changeset)}")
        {:error, %{message: "Validation failed", extensions: %{code: "VALIDATION"}}}

      {:server, {:error, reason}} ->
        Logger.error("sendMessage failed to start ConvServer: #{inspect(reason)}")

        {:error,
         %{message: "Upstream service unavailable", extensions: %{code: "UPSTREAM_UNAVAILABLE"}}}

      {:stream, {:error, reason}} ->
        Logger.error("sendMessage failed to begin stream: #{inspect(reason)}")

        {:error,
         %{message: "Upstream service unavailable", extensions: %{code: "UPSTREAM_UNAVAILABLE"}}}
    end
  end

  @doc "`deleteConversation` — removes a conversation owned by the viewer."
  def delete_conversation(_parent, %{id: id}, %{context: %{viewer_id: viewer_id}}) do
    case Conversations.delete_conversation(id, viewer_id) do
      {:ok, _} -> {:ok, true}
      {:error, :not_found} -> {:error, :not_found}
    end
  end

  @doc """
  `submitFeedback` — records thumbs-up/down on an assistant message.

  Idempotent per viewer+message: if feedback already exists, updates the
  `helpful` value.  Returns `true` on success.
  """
  def submit_feedback(_parent, %{message_id: message_id, helpful: helpful}, %{
        context: %{viewer_id: viewer_id}
      }) do
    msg_id_int =
      case Integer.parse(to_string(message_id)) do
        {n, ""} -> n
        _ -> nil
      end

    if is_nil(msg_id_int) do
      {:error, %{message: "Invalid message ID", extensions: %{code: "VALIDATION"}}}
    else
      # Upsert: insert or update on conflict.
      result =
        Repo.insert(
          %MessageFeedback{}
          |> MessageFeedback.changeset(%{
            message_id: msg_id_int,
            viewer_id: viewer_id,
            helpful: helpful
          }),
          on_conflict: {:replace, [:helpful, :updated_at]},
          conflict_target: [:message_id, :viewer_id]
        )

      case result do
        {:ok, _} ->
          {:ok, true}

        {:error, cs} ->
          Logger.error("submitFeedback failed: #{inspect(cs)}")
          {:error, %{message: "Failed to submit feedback", extensions: %{code: "INTERNAL"}}}
      end
    end
  end

  def submit_feedback(_parent, _args, _context) do
    {:error, %{message: "Viewer token required", extensions: %{code: "UNAUTHORIZED"}}}
  end
end
