defmodule ChatF1.Workers.TitleGen do
  @moduledoc """
  Oban worker: generates a one-line conversation title after the first exchange
  completes.

  Proxies a short prompt through `ChatF1.Agents.Client` asking the agent to
  summarise the conversation in ≤10 words.  On agent error or timeout the job
  silently degrades — a missing title is not user-visible.

  ## Enqueue timing

  Enqueued by `Conversation.Server` after the first `MessageCompleted` event
  for a given conversation (only when title is nil).

  ## Degrade silently

  Any error from the agent is logged at `:info` level and returns `:ok` so
  Oban does NOT retry (a missing title is not worth three retries).
  """

  use Oban.Worker,
    queue: :default,
    unique: [fields: [:args], period: :infinity, states: [:available, :scheduled, :executing]],
    max_attempts: 2

  require Logger

  import Ecto.Query

  alias ChatF1.Agents.Client, as: AgentClient
  alias ChatF1.Conversations.{Conversation, Message}
  alias ChatF1.Repo

  @impl Oban.Worker
  def perform(%Oban.Job{args: %{"conversation_id" => conv_id}}) do
    # Idempotency: skip if title already set.
    conversation = Repo.get(Conversation, conv_id)

    if is_nil(conversation) or not is_nil(conversation.title) do
      :ok
    else
      generate_and_persist_title(conversation)
    end
  end

  defp generate_and_persist_title(conversation) do
    # Fetch first user message as context.
    first_user_msg =
      Repo.one(
        from m in Message,
          where: m.conversation_id == ^conversation.id and m.role == :user,
          order_by: [asc: m.id],
          limit: 1
      )

    if is_nil(first_user_msg) do
      :ok
    else
      prompt =
        "Summarise this question in 8 words or fewer (no punctuation): #{first_user_msg.content}"

      request_id = "title-gen-#{conversation.id}"

      case AgentClient.chat(prompt, [], request_id) do
        {:ok, %{content: content}} when is_binary(content) and content != "" ->
          title = content |> String.trim() |> String.slice(0, 100)

          conversation
          |> Conversation.changeset(%{title: title})
          |> Repo.update()
          |> case do
            {:ok, _} -> :ok
            {:error, cs} -> Logger.info("[TitleGen] update failed: #{inspect(cs)}"); :ok
          end

        other ->
          Logger.info("[TitleGen] agent returned #{inspect(other)} — skipping title")
          :ok
      end
    end
  end
end
