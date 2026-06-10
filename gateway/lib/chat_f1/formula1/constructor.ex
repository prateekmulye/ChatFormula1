defmodule ChatF1.Formula1.Constructor do
  @moduledoc "Ecto schema for an F1 constructor (team)."

  use Ecto.Schema
  import Ecto.Changeset

  alias ChatF1.Formula1.Driver

  @type t :: %__MODULE__{}

  schema "constructors" do
    field :name, :string
    field :nationality, :string
    # Points are computed from race_results; this field caches the seed-time
    # snapshot and is refreshed by the nightly Jolpica sync (Phase 5).
    field :points, :float, default: 0.0

    has_many :drivers, Driver

    timestamps(type: :utc_datetime)
  end

  @spec changeset(t(), map()) :: Ecto.Changeset.t()
  def changeset(constructor, attrs) do
    constructor
    |> cast(attrs, [:name, :nationality, :points])
    |> validate_required([:name])
    |> unique_constraint(:name)
    |> validate_number(:points, greater_than_or_equal_to: 0)
  end
end
