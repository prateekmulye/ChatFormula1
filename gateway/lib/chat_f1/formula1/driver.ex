defmodule ChatF1.Formula1.Driver do
  @moduledoc "Ecto schema for an F1 driver."

  use Ecto.Schema
  import Ecto.Changeset

  alias ChatF1.Formula1.{Constructor, RaceResult}

  @type t :: %__MODULE__{}

  schema "drivers" do
    field :code, :string
    field :number, :integer
    field :full_name, :string
    field :nationality, :string

    belongs_to :constructor, Constructor

    has_many :race_results, RaceResult

    timestamps(type: :utc_datetime)
  end

  @spec changeset(t(), map()) :: Ecto.Changeset.t()
  def changeset(driver, attrs) do
    driver
    |> cast(attrs, [:code, :number, :full_name, :nationality, :constructor_id])
    |> validate_required([:code, :full_name, :nationality, :constructor_id])
    |> unique_constraint(:code)
    |> validate_length(:code, min: 2, max: 5)
    |> validate_number(:number, greater_than: 0)
  end
end
