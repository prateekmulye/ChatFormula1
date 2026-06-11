defmodule ChatF1.Repo.Migrations.CreateBudgetLedger do
  use Ecto.Migration

  def change do
    create table(:budget_ledger, primary_key: false) do
      add :date, :date, primary_key: true, null: false
      add :spent_usd, :decimal, precision: 12, scale: 6, null: false, default: 0
      add :budget_usd, :decimal, precision: 12, scale: 6, null: false, default: 2.00

      timestamps(type: :utc_datetime, updated_at: :updated_at, inserted_at: :inserted_at)
    end

    # Index on date for efficient daily lookups (already PK but explicit for clarity)
    # No extra index needed — date IS the primary key.
  end
end
