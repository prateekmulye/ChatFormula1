defmodule ChatF1.Workers.PruneConversations do
  @moduledoc """
  Oban worker: daily TTL pruning of conversations older than 7 days.

  Deletes conversations (and their messages via ON DELETE CASCADE) that were
  inserted more than `@ttl_days` days ago.  This keeps the Postgres free tier
  healthy and prevents the `conversations` table growing without bound.

  ## Schedule

  Runs daily at 03:00 UTC.

  ## Idempotency

  Unique by worker within a 23-hour window — safe to re-enqueue manually.
  """

  use Oban.Worker,
    queue: :default,
    unique: [period: 23 * 60 * 60],
    max_attempts: 5

  require Logger

  import Ecto.Query

  alias ChatF1.Conversations.Conversation
  alias ChatF1.Repo

  @ttl_days 7

  @impl Oban.Worker
  def perform(_job) do
    cutoff = DateTime.add(DateTime.utc_now(), -@ttl_days * 24 * 60 * 60, :second)

    {count, _} =
      Repo.delete_all(
        from c in Conversation,
          where: c.inserted_at < ^cutoff
      )

    Logger.info("[PruneConversations] pruned #{count} conversations older than #{@ttl_days} days")
    :ok
  end
end
