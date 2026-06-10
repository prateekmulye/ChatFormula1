defmodule ChatF1.Formula1.Race do
  @moduledoc "Ecto schema for an F1 race event."

  use Ecto.Schema
  import Ecto.Changeset

  alias ChatF1.Formula1.RaceResult

  @type t :: %__MODULE__{}

  schema "races" do
    field :season, :integer
    field :round, :integer
    field :name, :string
    field :circuit, :string
    field :country, :string
    field :starts_at, :utc_datetime

    has_many :race_results, RaceResult

    timestamps(type: :utc_datetime)
  end

  @spec changeset(t(), map()) :: Ecto.Changeset.t()
  def changeset(race, attrs) do
    race
    |> cast(attrs, [:season, :round, :name, :circuit, :country, :starts_at])
    |> validate_required([:season, :round, :name, :circuit, :country, :starts_at])
    |> unique_constraint([:season, :round])
    |> validate_number(:season, greater_than: 2000)
    |> validate_number(:round, greater_than: 0)
  end
end
