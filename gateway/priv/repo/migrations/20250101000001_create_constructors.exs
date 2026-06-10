defmodule ChatF1.Repo.Migrations.CreateConstructors do
  use Ecto.Migration

  def change do
    create table(:constructors) do
      add :name, :string, null: false
      add :nationality, :string
      add :points, :float, default: 0.0, null: false

      timestamps(type: :utc_datetime)
    end

    create unique_index(:constructors, [:name])
  end
end
