defmodule ChatF1.Repo.Migrations.CreateConversations do
  use Ecto.Migration

  def change do
    create table(:conversations) do
      add :viewer_id, :string, null: false
      add :title, :string

      timestamps(type: :utc_datetime)
    end

    create index(:conversations, [:viewer_id])
  end
end
