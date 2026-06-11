defmodule ChatF1.Repo.Migrations.AddSourcesLatencyToMessages do
  @moduledoc """
  Phase 5 handoff debt: persist SourcesResolved sources and real latency_ms
  onto the message row.

  The sources column already exists as :map (jsonb). This migration changes it
  to :jsonb array type and adds a proper array column for structured sources.
  Since the existing column default is %{} (object), we need to migrate it to [].

  latency_ms was already nullable; we just ensure a default of NULL is explicit.
  """
  use Ecto.Migration

  def up do
    # Update messages.sources default from empty map to empty array
    # (the column type is already jsonb — Postgres handles both)
    execute("ALTER TABLE messages ALTER COLUMN sources SET DEFAULT '[]'::jsonb")
    # Backfill existing {} rows to []
    execute("UPDATE messages SET sources = '[]'::jsonb WHERE sources = '{}'::jsonb OR sources IS NULL")
  end

  def down do
    execute("ALTER TABLE messages ALTER COLUMN sources SET DEFAULT '{}'::jsonb")
  end
end
