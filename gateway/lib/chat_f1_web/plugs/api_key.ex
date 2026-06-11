defmodule ChatF1Web.Plugs.ApiKey do
  @moduledoc """
  Plug that authenticates requests using an `x-api-key` header.

  Looks up the key via `ChatF1.Accounts.ApiKeys.verify_key/1`.  If valid and
  unrevoked, assigns `conn.assigns.api_key` and — when `scope` is specified —
  checks that the key has the required scope.

  Usage in the router:

      plug ChatF1Web.Plugs.ApiKey, scope: "admin:dashboard"

  Without a `scope` option, any valid unrevoked key is accepted.
  """

  import Plug.Conn

  alias ChatF1.Accounts.ApiKeys

  @behaviour Plug

  @impl Plug
  def init(opts), do: opts

  @impl Plug
  def call(conn, opts) do
    required_scope = Keyword.get(opts, :scope)
    raw_key = get_req_header(conn, "x-api-key") |> List.first()

    case ApiKeys.verify_key(raw_key) do
      {:ok, api_key} ->
        if required_scope && not ApiKeys.has_scope?(api_key, required_scope) do
          conn
          |> put_resp_content_type("application/json")
          |> send_resp(403, Jason.encode!(%{error: "Insufficient scope"}))
          |> halt()
        else
          assign(conn, :api_key, api_key)
        end

      {:error, :invalid} ->
        conn
        |> put_resp_content_type("application/json")
        |> send_resp(401, Jason.encode!(%{error: "Invalid or missing API key"}))
        |> halt()
    end
  end
end
