defmodule ChatF1.Repo.Migrations.CreateRaceResults do
  use Ecto.Migration

  def change do
    create table(:race_results) do
      add :driver_id, references(:drivers, on_delete: :restrict), null: false
      add :race_id, references(:races, on_delete: :restrict), null: false
      add :grid_position, :integer
      add :finish_position, :integer
      add :points, :float, default: 0.0, null: false
      add :podium, :boolean, default: false, null: false

      timestamps(type: :utc_datetime)
    end

    create unique_index(:race_results, [:driver_id, :race_id])
    create index(:race_results, [:race_id])
    create index(:race_results, [:driver_id])
  end
end
