defmodule ChatF1.Repo.Migrations.CreateMessageFeedback do
  use Ecto.Migration

  def change do
    create table(:message_feedback) do
      add :message_id, references(:messages, on_delete: :delete_all), null: false
      # Viewer-scoped: the same viewer_id string used in conversations.
      add :viewer_id, :string, null: false
      add :helpful, :boolean, null: false

      timestamps(type: :utc_datetime)
    end

    # Idempotency: one feedback row per (viewer, message) pair.
    create unique_index(:message_feedback, [:message_id, :viewer_id])

    # Fast lookup by message for aggregation.
    create index(:message_feedback, [:message_id])
  end
end
