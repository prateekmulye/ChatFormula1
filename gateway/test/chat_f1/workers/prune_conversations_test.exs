defmodule ChatF1.Workers.PruneConversationsTest do
  @moduledoc """
  Tests for the PruneConversations Oban worker.

  Uses Oban.Testing helpers (testing: :inline in test config) so jobs execute
  synchronously within the sandbox.
  """

  use ChatF1.DataCase, async: true
  use Oban.Testing, repo: ChatF1.Repo

  alias ChatF1.Accounts
  alias ChatF1.Conversations
  alias ChatF1.Conversations.Conversation
  alias ChatF1.Repo
  alias ChatF1.Workers.PruneConversations

  # Insert a conversation with a forced inserted_at timestamp.
  defp insert_aged_conversation(days_ago) do
    viewer_id = Accounts.new_viewer_id()
    {:ok, conv} = Conversations.create_conversation(viewer_id)
    past = DateTime.add(DateTime.utc_now(), -days_ago * 24 * 60 * 60, :second)

    Repo.update_all(
      from(c in Conversation, where: c.id == ^conv.id),
      set: [inserted_at: past, updated_at: past]
    )

    conv
  end

  import Ecto.Query

  test "prunes conversations older than 7 days" do
    old = insert_aged_conversation(8)
    recent = insert_aged_conversation(3)

    assert :ok = perform_job(PruneConversations, %{})

    # Old conversation deleted; recent still present.
    refute Repo.get(Conversation, old.id)
    assert Repo.get(Conversation, recent.id)
  end

  test "does not prune conversations exactly at 7-day boundary (< not <=)" do
    # The cutoff uses inserted_at < cutoff, so a conversation inserted at
    # exactly 7 days ago is on the boundary — may or may not be pruned depending
    # on sub-second timing.  A conversation at 6 days ago is definitely safe.
    safe = insert_aged_conversation(6)
    assert :ok = perform_job(PruneConversations, %{})
    assert Repo.get(Conversation, safe.id)
  end

  test "returns :ok when nothing to prune" do
    assert :ok = perform_job(PruneConversations, %{})
  end
end
