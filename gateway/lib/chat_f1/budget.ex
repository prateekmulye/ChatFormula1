defmodule ChatF1.Budget do
  @moduledoc """
  Daily LLM spend ledger.

  ## Design

  One Postgres row per UTC calendar date (`budget_ledger.date`).  The row is
  created with `spent_usd = 0` on first access and incremented atomically via
  a PostgreSQL `UPDATE … SET spent_usd = spent_usd + $1 RETURNING *` — no
  read-modify-write race condition.

  ## ServiceMode

  `mode/0` is the **single source of truth** for `ServiceMode`:

  * `:live` — budget not exhausted **and** breaker closed.
  * `:showcase` — budget exhausted **or** breaker open (SHOWCASE wins; never
    shows :live while budget is gone, even if breaker is closed).
  * `:degraded` — breaker is `:half_open` and budget not exhausted.

  Composition rule: SHOWCASE > DEGRADED > LIVE.

  ## Concurrency

  The atomic SQL `UPDATE … SET spent_usd = spent_usd + delta` means concurrent
  `decrement/1` calls from different Conversation.Server processes are safe with
  no application-level locking.  `ensure_today_row/0` uses `on_conflict: :nothing`
  to avoid duplicate-row races.
  """

  import Ecto.Query

  alias ChatF1.Agents.Breaker
  alias ChatF1.Budget.LedgerRow
  alias ChatF1.Repo

  # ─── ServiceMode ─────────────────────────────────────────────────────────────

  @doc """
  Returns the current `ServiceMode` atom: `:live`, `:degraded`, or `:showcase`.

  Composition: SHOWCASE > DEGRADED > LIVE.
  Called by resolvers, SHOWCASE replayer, and systemHealth.
  """
  @spec mode() :: :live | :degraded | :showcase
  def mode do
    breaker_state = Breaker.state()
    today = today_row()

    budget_exhausted =
      today != nil and Decimal.compare(today.spent_usd, today.budget_usd) != :lt

    cond do
      budget_exhausted -> :showcase
      breaker_state == :open -> :showcase
      breaker_state == :half_open -> :degraded
      true -> :live
    end
  end

  # ─── Read helpers ─────────────────────────────────────────────────────────────

  @doc """
  Returns today's `LedgerRow` (or `nil` if no row yet).
  Creates the row if absent via `ensure_today_row/0`.
  """
  @spec today_row() :: LedgerRow.t() | nil
  def today_row do
    today = Date.utc_today()
    Repo.get(LedgerRow, today) || ensure_today_row()
  end

  @doc """
  Returns `{:ok, spend_usd, budget_usd}` for today, creating the row if needed.
  """
  @spec today_spend() :: {:ok, Decimal.t(), Decimal.t()}
  def today_spend do
    row = today_row()
    {:ok, row.spent_usd, row.budget_usd}
  end

  # ─── Write helpers ────────────────────────────────────────────────────────────

  @doc """
  Atomically increments today's `spent_usd` by `cost_usd`.

  Creates the row if it doesn't exist yet.  Returns `{:ok, updated_row}`.

  Called by `Conversation.Server` inside the `complete` event handler, wrapped
  in the same `Ecto.Multi` transaction that updates the message status.
  """
  @spec decrement(float() | Decimal.t()) :: {:ok, LedgerRow.t()} | {:error, term()}
  def decrement(cost_usd) when is_float(cost_usd) do
    decrement(Decimal.from_float(cost_usd))
  end

  def decrement(%Decimal{} = cost_usd) do
    today = Date.utc_today()
    _row = ensure_today_row()

    {count, rows} =
      Repo.update_all(
        from(r in LedgerRow,
          where: r.date == ^today,
          select: r
        ),
        inc: [spent_usd: cost_usd]
      )

    if count == 1 do
      {:ok, hd(rows)}
    else
      {:error, :ledger_row_missing}
    end
  end

  @doc """
  Upserts today's budget row with the summed spend from agent usage.

  Called by the `SpendRollup` Oban worker (daily) to reconcile any drift.
  """
  @spec set_spent(Date.t(), Decimal.t()) :: {:ok, LedgerRow.t()} | {:error, term()}
  def set_spent(%Date{} = date, %Decimal{} = spent) do
    default_budget = default_budget_usd()

    %LedgerRow{}
    |> LedgerRow.changeset(%{date: date, spent_usd: spent, budget_usd: default_budget})
    |> Repo.insert(
      on_conflict: {:replace, [:spent_usd, :updated_at]},
      conflict_target: :date,
      returning: true
    )
  end

  # ─── Private helpers ──────────────────────────────────────────────────────────

  # Creates today's row with spent_usd = 0 if absent.
  # on_conflict: :nothing is safe because we always read the existing row on
  # the next Repo.get after the no-op insert — there is no TOCTOU here.
  @spec ensure_today_row() :: LedgerRow.t()
  defp ensure_today_row do
    today = Date.utc_today()
    budget = default_budget_usd()

    Repo.insert!(
      %LedgerRow{date: today, spent_usd: Decimal.new(0), budget_usd: budget},
      on_conflict: :nothing,
      conflict_target: :date
    )

    Repo.get!(LedgerRow, today)
  end

  @spec default_budget_usd() :: Decimal.t()
  defp default_budget_usd do
    System.get_env("DAILY_LLM_BUDGET_USD", "2.00")
    |> Decimal.new()
  end
end
