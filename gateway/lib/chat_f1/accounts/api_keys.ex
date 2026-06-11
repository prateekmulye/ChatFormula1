defmodule ChatF1.Accounts.ApiKeys do
  @moduledoc """
  Context for API key management.

  Lookups use the SHA-256 hash of the raw key, so the plaintext never touches
  the database after creation.
  """

  import Ecto.Query

  alias ChatF1.Accounts.ApiKey
  alias ChatF1.Repo

  @doc """
  Looks up a valid (non-revoked) API key by its raw value.
  Returns `{:ok, key}` or `{:error, :invalid}`.
  """
  @spec verify_key(String.t()) :: {:ok, ApiKey.t()} | {:error, :invalid}
  def verify_key(raw_key) when is_binary(raw_key) do
    hash = ApiKey.hash_key(raw_key)

    result =
      ApiKey
      |> where([k], k.key_hash == ^hash and is_nil(k.revoked_at))
      |> Repo.one()

    case result do
      nil -> {:error, :invalid}
      key -> {:ok, key}
    end
  end

  def verify_key(_), do: {:error, :invalid}

  @doc "Returns true if `key` has the given scope."
  @spec has_scope?(ApiKey.t(), String.t()) :: boolean()
  def has_scope?(%ApiKey{scopes: scopes}, scope), do: scope in scopes

  @doc "Lists all non-revoked keys (for admin view)."
  @spec list_active_keys() :: [ApiKey.t()]
  def list_active_keys do
    ApiKey
    |> where([k], is_nil(k.revoked_at))
    |> order_by([k], asc: k.inserted_at)
    |> Repo.all()
  end

  @doc "Revokes a key by ID."
  @spec revoke_key(integer()) :: {:ok, ApiKey.t()} | {:error, :not_found}
  def revoke_key(id) do
    case Repo.get(ApiKey, id) do
      nil ->
        {:error, :not_found}

      key ->
        key
        |> ApiKey.changeset(%{revoked_at: DateTime.utc_now()})
        |> Repo.update()
    end
  end
end
