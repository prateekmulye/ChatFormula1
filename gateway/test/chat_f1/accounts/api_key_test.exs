defmodule ChatF1.Accounts.ApiKeyTest do
  @moduledoc """
  Tests for ApiKey schema + generate/verify, and the ApiKeys context
  (verify_key lookup, has_scope?, revoke_key).
  """

  use ChatF1.DataCase, async: true

  alias ChatF1.Accounts.ApiKey
  alias ChatF1.Accounts.ApiKeys

  # ─── Key generation ───────────────────────────────────────────────────────────

  test "generate/2 returns a raw key with f1s_ prefix and a valid changeset" do
    {raw_key, changeset} = ApiKey.generate("test-label", ["admin:ingest"])
    assert String.starts_with?(raw_key, "f1s_")
    # 4 prefix chars + 64 hex chars
    assert String.length(raw_key) == 68
    assert changeset.valid?
  end

  test "generate/2 stores SHA-256 hash, not raw key" do
    {raw_key, changeset} = ApiKey.generate("test", [])
    hash = Ecto.Changeset.get_change(changeset, :key_hash)
    assert hash != raw_key
    assert String.length(hash) == 64
  end

  test "generate/2 two calls produce different keys" do
    {k1, _} = ApiKey.generate()
    {k2, _} = ApiKey.generate()
    refute k1 == k2
  end

  # ─── hash_key ─────────────────────────────────────────────────────────────────

  test "hash_key/1 is deterministic" do
    h1 = ApiKey.hash_key("f1s_abc")
    h2 = ApiKey.hash_key("f1s_abc")
    assert h1 == h2
  end

  test "hash_key/1 produces 64-char hex string" do
    assert String.length(ApiKey.hash_key("anything")) == 64
  end

  # ─── verify/2 ────────────────────────────────────────────────────────────────

  test "verify/2 returns true for matching key" do
    raw = "f1s_testkey"
    hash = ApiKey.hash_key(raw)
    assert ApiKey.verify(raw, hash)
  end

  test "verify/2 returns false for wrong key" do
    hash = ApiKey.hash_key("f1s_realkey")
    refute ApiKey.verify("f1s_wrongkey", hash)
  end

  # ─── verify_key/1 (context, requires DB) ─────────────────────────────────────

  test "verify_key/1 returns {:ok, key} for valid non-revoked key" do
    {raw_key, changeset} = ApiKey.generate("lookup-test", ["admin:ingest"])
    {:ok, _stored} = Repo.insert(changeset)

    assert {:ok, key} = ApiKeys.verify_key(raw_key)
    assert key.label == "lookup-test"
    assert "admin:ingest" in key.scopes
  end

  test "verify_key/1 returns {:error, :invalid} for unknown key" do
    assert {:error, :invalid} = ApiKeys.verify_key("f1s_doesnotexist")
  end

  test "verify_key/1 returns {:error, :invalid} for nil" do
    assert {:error, :invalid} = ApiKeys.verify_key(nil)
  end

  test "verify_key/1 returns {:error, :invalid} for revoked key" do
    {raw_key, changeset} = ApiKey.generate("revoke-test", [])
    {:ok, stored} = Repo.insert(changeset)

    {:ok, _} = ApiKeys.revoke_key(stored.id)
    assert {:error, :invalid} = ApiKeys.verify_key(raw_key)
  end

  # ─── has_scope? ──────────────────────────────────────────────────────────────

  test "has_scope?/2 returns true when scope present" do
    {_, changeset} = ApiKey.generate("scoped", ["admin:ingest", "admin:dashboard"])
    {:ok, key} = Repo.insert(changeset)
    assert ApiKeys.has_scope?(key, "admin:ingest")
    assert ApiKeys.has_scope?(key, "admin:dashboard")
  end

  test "has_scope?/2 returns false when scope absent" do
    {_, changeset} = ApiKey.generate("no-scope", [])
    {:ok, key} = Repo.insert(changeset)
    refute ApiKeys.has_scope?(key, "admin:ingest")
  end

  # ─── revoke_key/1 ────────────────────────────────────────────────────────────

  test "revoke_key/1 sets revoked_at" do
    {_, changeset} = ApiKey.generate("to-revoke", [])
    {:ok, stored} = Repo.insert(changeset)

    {:ok, revoked} = ApiKeys.revoke_key(stored.id)
    assert revoked.revoked_at != nil
  end

  test "revoke_key/1 returns {:error, :not_found} for missing id" do
    assert {:error, :not_found} = ApiKeys.revoke_key(0)
  end
end
