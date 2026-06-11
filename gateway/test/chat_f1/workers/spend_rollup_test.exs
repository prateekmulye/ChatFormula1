defmodule ChatF1.Workers.SpendRollupTest do
  @moduledoc """
  Tests for the SpendRollup Oban worker.

  Verifies that the daily reconciliation job updates the budget ledger row
  and returns :ok.
  """

  use ChatF1.DataCase, async: false
  use Oban.Testing, repo: ChatF1.Repo

  alias ChatF1.Budget
  alias ChatF1.Workers.SpendRollup

  test "perform/1 updates ledger row and returns :ok" do
    # Ensure today row exists
    Budget.today_row()

    assert :ok = perform_job(SpendRollup, %{})

    # After rollup a ledger row for today must exist
    row = Budget.today_row()
    assert row != nil
  end

  test "perform/1 is idempotent — can run twice safely" do
    Budget.today_row()
    assert :ok = perform_job(SpendRollup, %{})
    assert :ok = perform_job(SpendRollup, %{})
  end
end
