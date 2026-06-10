defmodule ChatF1.Repo.Migrations.CreateRaces do
  use Ecto.Migration

  def change do
    create table(:races) do
      add :season, :integer, null: false
      add :round, :integer, null: false
      add :name, :string, null: false
      add :circuit, :string, null: false
      add :country, :string, null: false
      add :starts_at, :utc_datetime, null: false

      timestamps(type: :utc_datetime)
    end

    create unique_index(:races, [:season, :round])
    create index(:races, [:season])
    create index(:races, [:starts_at])
  end
end
