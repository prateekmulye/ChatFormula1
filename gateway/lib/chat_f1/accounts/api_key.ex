defmodule ChatF1.Accounts.ApiKey do
  @moduledoc """
  Ecto schema for `f1s_`-prefixed API keys.

  ## Key format

  Raw key: `f1s_<32 random bytes as base16>` (65 chars total).
  Stored: only the SHA-256 hex hash of the full raw key string.
  Shown: the raw key is returned *once* at creation via `mix chat_f1.gen_api_key`.

  ## Scopes

  `scopes` is a Postgres `text[]` array.  Supported scopes:

  * `admin:ingest`    — allows `triggerIngest` mutation
  * `admin:dashboard` — allows `/dev/dashboard` and `GET /metrics`

  The middleware checks `scope in key.scopes` (exact match; no wildcards in Phase 5).
  """

  use Ecto.Schema
  import Ecto.Changeset

  @type t :: %__MODULE__{}

  @key_prefix "f1s_"
  # 32 random bytes → 64 hex chars
  @raw_bytes 32

  schema "api_keys" do
    field :prefix, :string
    field :key_hash, :string
    field :label, :string, default: ""
    field :scopes, {:array, :string}, default: []
    field :revoked_at, :utc_datetime

    timestamps(type: :utc_datetime)
  end

  @spec changeset(t(), map()) :: Ecto.Changeset.t()
  def changeset(key, attrs) do
    key
    |> cast(attrs, [:prefix, :key_hash, :label, :scopes, :revoked_at])
    |> validate_required([:prefix, :key_hash])
    |> validate_format(:prefix, ~r/^f1s_/)
    |> unique_constraint(:key_hash)
  end

  @doc """
  Generates a new raw API key and returns `{raw_key, changeset}`.

  The raw key is NOT stored — only the SHA-256 hash.
  Call `Repo.insert(changeset)` to persist.
  """
  @spec generate(String.t(), [String.t()]) :: {String.t(), Ecto.Changeset.t()}
  def generate(label \\ "", scopes \\ []) do
    random_bytes = :crypto.strong_rand_bytes(@raw_bytes)
    hex_suffix = Base.encode16(random_bytes, case: :lower)
    raw_key = @key_prefix <> hex_suffix

    key_hash = hash_key(raw_key)

    changeset =
      changeset(%__MODULE__{}, %{
        prefix: @key_prefix,
        key_hash: key_hash,
        label: label,
        scopes: scopes
      })

    {raw_key, changeset}
  end

  @doc """
  Verifies `raw_key` against the stored hash.
  Returns `true` if the key's SHA-256 hash matches `stored_hash`.
  """
  @spec verify(String.t(), String.t()) :: boolean()
  def verify(raw_key, stored_hash) do
    candidate_hash = hash_key(raw_key)
    Plug.Crypto.secure_compare(candidate_hash, stored_hash)
  end

  @doc "SHA-256 hex digest of the raw key string."
  @spec hash_key(String.t()) :: String.t()
  def hash_key(raw_key) do
    :crypto.hash(:sha256, raw_key) |> Base.encode16(case: :lower)
  end
end
