defmodule ChatF1.Repo.Migrations.CreateShowcaseAnswers do
  use Ecto.Migration

  def change do
    # Requires pg_trgm extension for trigram similarity search.
    execute("CREATE EXTENSION IF NOT EXISTS pg_trgm", "DROP EXTENSION IF EXISTS pg_trgm")

    create table(:showcase_answers) do
      add :question, :text, null: false
      add :content, :text, null: false
      # [%{kind, title, url, snippet, score}]
      add :sources, :jsonb, null: false, default: "[]"
      # [%{node, started_at_ms}] — node transition trace
      add :node_trace, :jsonb, null: false, default: "[]"
      # Inter-batch delays in ms — paces the replay to match original stream timing
      add :token_timing_histogram, {:array, :integer}, null: false, default: []
      # Full pre-baked token batches for replay (each element = one TokenDelta text)
      add :token_batches, {:array, :text}, null: false, default: []
      # Tracks when this answer was last generated/refreshed
      add :generated_at, :utc_datetime

      timestamps(type: :utc_datetime)
    end

    # Unique index: one cached answer per canonical question text.
    create unique_index(:showcase_answers, [:question])

    # GIN trigram index: powers nearest-match query for unknown questions.
    execute(
      "CREATE INDEX showcase_answers_question_trgm_idx ON showcase_answers USING gin (question gin_trgm_ops)",
      "DROP INDEX IF EXISTS showcase_answers_question_trgm_idx"
    )
  end
end
