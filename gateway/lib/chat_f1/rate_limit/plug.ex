defmodule ChatF1.RateLimit.Plug do
  @moduledoc """
  Plug-level rate limiting for non-GraphQL HTTP endpoints.

  For GraphQL operations, rate limiting is applied by
  `ChatF1Web.Schema.Middleware.RateLimit` in the Absinthe middleware stack.
  This plug covers direct HTTP access (e.g., health checks from external
  monitors that might be abused).

  Returns 429 with a `Retry-After` header on denial.
  """

  @behaviour Plug

  import Plug.Conn

  alias ChatF1.RateLimit.Server

  @impl Plug
  def init(opts), do: opts

  @impl Plug
  def call(conn, _opts) do
    key = viewer_key(conn)

    case Server.check_and_consume(key) do
      :allow ->
        conn

      {:deny, {:retry_after_seconds, t}} ->
        conn
        |> put_resp_header("retry-after", to_string(t))
        |> put_resp_content_type("application/json")
        |> send_resp(429, Jason.encode!(%{error: "rate_limited", retry_after: t}))
        |> halt()
    end
  end

  # Prefer viewer token (from Authorization header); fall back to remote IP.
  defp viewer_key(conn) do
    case get_req_header(conn, "authorization") do
      ["Bearer " <> token] ->
        # Hash the token so it's not stored raw in ETS.
        :crypto.hash(:sha256, token) |> Base.encode16(case: :lower)

      _ ->
        conn.remote_ip |> :inet.ntoa() |> to_string()
    end
  end
end
