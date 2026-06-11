defmodule ChatF1.Repo.Migrations.CreateApiKeys do
  use Ecto.Migration

  def change do
    create table(:api_keys) do
      add :prefix, :string, null: false
      # SHA-256 hex of the raw key (32 bytes → 64 hex chars)
      add :key_hash, :string, null: false
      # Human-readable label for audit logs
      add :label, :string, null: false, default: ""
      # Array of scope strings, e.g. ["admin:ingest", "admin:dashboard"]
      add :scopes, {:array, :string}, null: false, default: []
      # Soft-revoke: non-nil means the key is disabled
      add :revoked_at, :utc_datetime

      timestamps(type: :utc_datetime)
    end

    # Unique index on the hash — prevents duplicate key registration.
    create unique_index(:api_keys, [:key_hash])

    # Fast lookup by prefix for the "list keys" admin view.
    create index(:api_keys, [:prefix])
  end
end
