defmodule ChatF1.BudgetTest do
  @moduledoc """
  Tests for the Budget daily-spend ledger.

  Covers row creation, atomic increment, set_spent upsert, and
  ServiceMode composition (live / degraded / showcase) via Budget.mode/0.

  Note: mode/0 calls Breaker.state(), which requires the singleton Breaker
  process running under the application supervision tree.
  """

  use ChatF1.DataCase, async: false

  alias ChatF1.Budget
  alias ChatF1.Budget.LedgerRow

  # ─── today_row / ensure idempotency ───────────────────────────────────────────

  test "today_row/0 creates a row on first call" do
    row = Budget.today_row()
    assert %LedgerRow{} = row
    assert row.date == Date.utc_today()
    assert Decimal.equal?(row.spent_usd, Decimal.new(0))
  end

  test "today_row/0 is idempotent — second call returns same row (date PK)" do
    # LedgerRow uses date as primary key (no integer :id).
    r1 = Budget.today_row()
    r2 = Budget.today_row()
    assert r1.date == r2.date
    assert Decimal.equal?(r1.spent_usd, r2.spent_usd)
  end

  # ─── decrement ────────────────────────────────────────────────────────────────

  test "decrement/1 atomically adds cost to spent_usd" do
    Budget.today_row()
    {:ok, row} = Budget.decrement(0.05)
    assert Decimal.equal?(row.spent_usd, Decimal.from_float(0.05))
  end

  test "decrement/1 accepts Decimal" do
    Budget.today_row()
    {:ok, row} = Budget.decrement(Decimal.new("0.10"))
    assert Decimal.equal?(row.spent_usd, Decimal.new("0.10"))
  end

  test "two sequential decrements accumulate correctly" do
    Budget.today_row()
    {:ok, _} = Budget.decrement(0.01)
    {:ok, row} = Budget.decrement(0.02)
    assert Decimal.equal?(row.spent_usd, Decimal.new("0.03"))
  end

  # ─── set_spent ────────────────────────────────────────────────────────────────

  test "set_spent/2 upserts spent on a new date" do
    future_date = Date.add(Date.utc_today(), 365)
    {:ok, row} = Budget.set_spent(future_date, Decimal.new("1.50"))
    assert row.date == future_date
    assert Decimal.equal?(row.spent_usd, Decimal.new("1.50"))
  end

  test "set_spent/2 overwrites existing spent" do
    today = Date.utc_today()
    Budget.today_row()
    {:ok, _} = Budget.decrement(0.05)
    {:ok, row} = Budget.set_spent(today, Decimal.new("0.99"))
    assert Decimal.equal?(row.spent_usd, Decimal.new("0.99"))
  end

  # ─── mode/0 — ServiceMode composition ─────────────────────────────────────────

  test "mode/0 returns :live when budget not exhausted and breaker closed" do
    # Ensure a today row with plenty of budget left (no spend yet).
    Budget.today_row()
    # Breaker should be :closed at app start; mode must be :live.
    assert Budget.mode() == :live
  end

  test "mode/0 returns :showcase when budget is exhausted" do
    # Exhaust budget by setting spent == budget.
    row = Budget.today_row()
    # Set spent equal to budget (exhausted).
    Budget.set_spent(Date.utc_today(), row.budget_usd)
    assert Budget.mode() == :showcase
  end
end
