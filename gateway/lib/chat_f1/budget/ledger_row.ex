defmodule ChatF1.Budget.LedgerRow do
  @moduledoc """
  Ecto schema for a single daily budget ledger row.

  Primary key is the calendar date.  One row per UTC day; upserted by
  `ChatF1.Budget` on every spend-decrement call.
  """

  use Ecto.Schema
  import Ecto.Changeset

  @type t :: %__MODULE__{}

  @primary_key {:date, :date, autogenerate: false}
  @timestamps_opts [type: :utc_datetime]

  schema "budget_ledger" do
    field :spent_usd, :decimal, default: Decimal.new(0)
    field :budget_usd, :decimal, default: Decimal.new("2.00")

    timestamps()
  end

  @spec changeset(t(), map()) :: Ecto.Changeset.t()
  def changeset(row, attrs) do
    row
    |> cast(attrs, [:date, :spent_usd, :budget_usd])
    |> validate_required([:date, :budget_usd])
    |> validate_number(:spent_usd, greater_than_or_equal_to: 0)
    |> validate_number(:budget_usd, greater_than: 0)
  end
end
