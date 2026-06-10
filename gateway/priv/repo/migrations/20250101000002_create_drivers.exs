defmodule ChatF1.Repo.Migrations.CreateDrivers do
  use Ecto.Migration

  def change do
    create table(:drivers) do
      add :code, :string, null: false, size: 5
      add :number, :integer
      add :full_name, :string, null: false
      add :nationality, :string, null: false
      add :constructor_id, references(:constructors, on_delete: :restrict), null: false

      timestamps(type: :utc_datetime)
    end

    create unique_index(:drivers, [:code])
    create index(:drivers, [:constructor_id])
  end
end
