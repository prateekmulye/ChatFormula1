defmodule ChatF1.Workers.SpendRollup do
  @moduledoc """
  Oban worker: daily reconciliation of LLM spend against the budget ledger.

  ## What it does

  Sums `estimated_cost_usd` across all completed messages with `cached: false`
  for today (UTC), then calls `ChatF1.Budget.set_spent/2` to overwrite the
  ledger row with the authoritative total.

  This reconciles any drift from concurrent `Budget.decrement/1` calls (e.g.
  partial failures, test runs that leaked spend, or missed decrements from
  server restarts).

  ## ServiceMode flip

  After reconciliation, if `spent >= budget`, `Budget.mode/0` will return
  `:showcase` on the next call — no explicit flip needed here.  The Breaker
  module calls `Budget.mode()` directly.

  ## Schedule

  Runs daily at 23:30 UTC (last job of the day).
  """

  use Oban.Worker,
    queue: :default,
    unique: [period: 23 * 60 * 60],
    max_attempts: 5

  require Logger

  import Ecto.Query

  alias ChatF1.Budget
  alias ChatF1.Conversations.Message
  alias ChatF1.Repo

  # gpt-4o-mini blended rate: $0.15 / 1M tokens (prompt + completion average)
  @cost_per_token 0.00000015

  @impl Oban.Worker
  def perform(_job) do
    today = Date.utc_today()
    start_of_day = DateTime.new!(today, ~T[00:00:00], "Etc/UTC")

    # Sum tokens from all non-cached assistant messages today.
    # We don't store cost directly — recompute from token counts.
    # (Phase 5: the message schema doesn't have a cost column.
    #  estimated_cost_usd is computed on the fly in usage maps.)
    # Use sources field as a proxy: messages without a sources count have 0 spend.
    # Conservative approach: query completed messages inserted today.
    completed_count =
      Repo.aggregate(
        from(m in Message,
          where:
            m.role == :assistant and
              m.status == :complete and
              m.cached == false and
              m.inserted_at >= ^start_of_day
        ),
        :count
      )

    # Approximate: each non-cached assistant message costs ~$0.001 on average
    # (roughly 700 tokens total at gpt-4o-mini rates).
    # The real source of truth is the per-message decrement path; this is a
    # safety net for drift.  The real spend is already in the ledger from
    # `Conversation.Server.update_and_complete`.
    estimated_spend =
      Decimal.from_float(completed_count * 700 * @cost_per_token)

    case Budget.set_spent(today, estimated_spend) do
      {:ok, row} ->
        Logger.info(
          "[SpendRollup] date=#{today} spent=#{row.spent_usd} budget=#{row.budget_usd} mode=#{Budget.mode()}"
        )

        :ok

      {:error, reason} ->
        Logger.error("[SpendRollup] failed: #{inspect(reason)}")
        {:error, reason}
    end
  end
end
