defmodule ChatF1.Formula1.RaceResult do
  @moduledoc "Ecto schema for a single driver's result in one race."

  use Ecto.Schema
  import Ecto.Changeset

  alias ChatF1.Formula1.{Driver, Race}

  @type t :: %__MODULE__{}

  schema "race_results" do
    belongs_to :driver, Driver
    belongs_to :race, Race

    field :grid_position, :integer
    field :finish_position, :integer
    field :points, :float, default: 0.0
    # Computed from finish_position (1, 2, or 3)
    field :podium, :boolean, default: false

    timestamps(type: :utc_datetime)
  end

  @spec changeset(t(), map()) :: Ecto.Changeset.t()
  def changeset(result, attrs) do
    result
    |> cast(attrs, [:driver_id, :race_id, :grid_position, :finish_position, :points, :podium])
    |> validate_required([:driver_id, :race_id, :points])
    |> unique_constraint([:driver_id, :race_id])
    |> validate_number(:points, greater_than_or_equal_to: 0)
    |> put_podium()
  end

  defp put_podium(changeset) do
    case get_field(changeset, :finish_position) do
      pos when is_integer(pos) and pos in 1..3 -> put_change(changeset, :podium, true)
      _ -> changeset
    end
  end
end
