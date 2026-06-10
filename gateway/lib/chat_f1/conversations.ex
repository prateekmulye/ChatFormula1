defmodule ChatF1.Conversations do
  @moduledoc """
  Context for conversation and message persistence.

  ## Viewer scoping

  Every conversation is owned by a `viewer_id` derived from the signed
  `Phoenix.Token`.  All queries that return conversations assert
  `c.viewer_id == ^viewer_id` — a viewer cannot retrieve another viewer's
  conversations regardless of ID knowledge.  This resolves the IDOR present in
  v1 (`GET /api/chat/sessions`).

  ## sendMessage lifecycle

  `send_message/3` atomically:
  1. Inserts the user `Message` (status `:complete`).
  2. Inserts an assistant `Message` placeholder (status `:pending`).
  3. Calls the agent, aggregates the NDJSON stream.
  4. Updates the assistant message (status `:complete` or `:failed`).

  Steps 1–2 run inside `Ecto.Multi`; the caller owns the agent call so partial
  failure (agent down) marks the placeholder `:failed` rather than leaving an
  orphaned `:pending` row.
  """

  import Ecto.Query

  alias ChatF1.Conversations.{Conversation, Message}
  alias ChatF1.Repo

  # ─── Conversations ───────────────────────────────────────────────────────────

  @spec list_conversations(String.t()) :: [Conversation.t()]
  def list_conversations(viewer_id) do
    Conversation
    |> where([c], c.viewer_id == ^viewer_id)
    |> order_by([c], desc: c.inserted_at)
    |> Repo.all()
  end

  @spec get_conversation(String.t(), String.t()) :: Conversation.t() | nil
  def get_conversation(id, viewer_id) do
    Conversation
    |> where([c], c.id == ^id and c.viewer_id == ^viewer_id)
    |> Repo.one()
  end

  @spec create_conversation(String.t()) :: {:ok, Conversation.t()} | {:error, Ecto.Changeset.t()}
  def create_conversation(viewer_id) do
    %Conversation{}
    |> Conversation.changeset(%{viewer_id: viewer_id})
    |> Repo.insert()
  end

  @spec delete_conversation(String.t(), String.t()) ::
          {:ok, Conversation.t()} | {:error, :not_found}
  def delete_conversation(id, viewer_id) do
    case get_conversation(id, viewer_id) do
      nil -> {:error, :not_found}
      conversation -> Repo.delete(conversation) |> then(&{:ok, &1}) |> elem(1) |> wrap_ok()
    end
  end

  defp wrap_ok(%Conversation{} = c), do: {:ok, c}
  defp wrap_ok({:ok, c}), do: {:ok, c}

  # ─── Messages ────────────────────────────────────────────────────────────────

  @spec list_messages(integer()) :: [Message.t()]
  def list_messages(conversation_id) do
    Message
    |> where([m], m.conversation_id == ^conversation_id)
    |> order_by([m], asc: m.id)
    |> Repo.all()
  end

  @doc """
  Atomically inserts a user message and an assistant placeholder.

  Returns `{:ok, %{user_message: Message.t(), assistant_message: Message.t()}}` or
  `{:error, step, changeset, _changes}`.

  This is the transactional core of `sendMessage`: the entire insert is
  committed before any agent call is made.  If the agent call fails later,
  the placeholder is updated to `:failed` — there is no silent data loss.
  """
  @spec insert_message_pair(integer(), String.t()) ::
          {:ok, %{user_message: Message.t(), assistant_message: Message.t()}}
          | {:error, atom(), Ecto.Changeset.t(), map()}
  def insert_message_pair(conversation_id, content) do
    Ecto.Multi.new()
    |> Ecto.Multi.insert(:user_message, fn _ ->
      Message.user_changeset(%Message{}, %{
        conversation_id: conversation_id,
        content: content
      })
    end)
    |> Ecto.Multi.insert(:assistant_message, fn _ ->
      Message.assistant_placeholder_changeset(%Message{}, %{
        conversation_id: conversation_id
      })
    end)
    |> Repo.transaction()
  end

  @doc """
  Updates an assistant message after the agent call completes.

  Called by the `sendMessage` resolver after the NDJSON stream is fully
  aggregated.  On success: status `:complete`, content filled.
  On agent failure: status `:failed`, content is the error summary.
  """
  @spec update_assistant_message(Message.t(), map()) ::
          {:ok, Message.t()} | {:error, Ecto.Changeset.t()}
  def update_assistant_message(%Message{} = message, attrs) do
    message
    |> Message.changeset(attrs)
    |> Repo.update()
  end

  @spec get_message!(integer()) :: Message.t()
  def get_message!(id), do: Repo.get!(Message, id)
end
