defmodule ChatF1.Accounts do
  @moduledoc """
  Viewer identity via signed `Phoenix.Token`.

  ## Design

  ChatFormula1 does not have user accounts in Phase 2.  Every browser session
  gets an **anonymous viewer token** — a signed, opaque string that the gateway
  uses to scope conversations and rate-limit requests.

  Tokens are signed with the endpoint's `secret_key_base` plus a dedicated
  salt (`chatf1_viewer_v1`).  The payload is just the `viewer_id` — a random
  UUID minted once and stored in the client cookie/`Authorization` header.

  ### Why Phoenix.Token instead of JWT?

  * `Phoenix.Token` is part of the standard library — zero extra deps.
  * The gateway is the only verifier, so compact opaque tokens suffice.
  * Max-age enforcement happens in `verify_viewer_token/1` — tokens expire
    after 30 days, forcing a re-mint on the next visit.

  ### Security properties

  * Tokens are HMAC-SHA-256 signed; forgery requires the `secret_key_base`.
  * The raw token is never logged.
  * Cross-viewer access: every Conversations query asserts `viewer_id == ^id`.
    A valid token for viewer A cannot retrieve viewer B's conversations.
  """

  @salt Application.compile_env!(:chat_f1, :viewer_token_salt)
  @max_age Application.compile_env!(:chat_f1, :viewer_token_max_age)

  @type viewer_id :: String.t()

  @doc """
  Mints a new viewer token for the given UUID viewer_id.

  The token is suitable for storage in a client cookie or HTTP header.
  """
  @spec mint_viewer_token(viewer_id()) :: String.t()
  def mint_viewer_token(viewer_id) do
    Phoenix.Token.sign(ChatF1Web.Endpoint, @salt, viewer_id)
  end

  @doc """
  Verifies a viewer token and returns `{:ok, viewer_id}` or `{:error, reason}`.

  Reasons: `:expired` | `:invalid` | `:missing`
  """
  @spec verify_viewer_token(String.t() | nil) :: {:ok, viewer_id()} | {:error, atom()}
  def verify_viewer_token(nil), do: {:error, :missing}

  def verify_viewer_token(token) do
    Phoenix.Token.verify(ChatF1Web.Endpoint, @salt, token, max_age: @max_age)
  end

  @doc """
  Generates a new random viewer_id (UUID v4).
  """
  @spec new_viewer_id() :: viewer_id()
  def new_viewer_id, do: Ecto.UUID.generate()
end
