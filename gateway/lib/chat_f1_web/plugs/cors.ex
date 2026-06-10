defmodule ChatF1Web.Plugs.CORS do
  @moduledoc """
  Minimal CORS support for the browser frontend (added in Phase 4).

  The React app is served from a different origin than the gateway (Vite dev
  server in development, Vercel in production), so two things must hold for a
  browser client to work at all:

  1. **CORS headers** on GraphQL HTTP responses — the frontend fetches with
     `credentials: "include"`, which requires an exact-origin
     `access-control-allow-origin` plus `access-control-allow-credentials`,
     and an OPTIONS preflight (Apollo sends `content-type: application/json`).

  2. **A JS-readable viewer token** — the `_chat_f1_viewer` cookie is
     HttpOnly (correctly), but the graphql-ws handshake requires the token in
     the `connection_init` payload (`ChatF1Web.GraphqlSocket.handle_init/2`).
     This plug therefore echoes the verified/minted token assigned by
     `ChatF1Web.Plugs.ViewerToken` in an `x-viewer-token` response header
     (exposed via CORS). The frontend persists it and presents it as
     `Authorization: Bearer` + WS `connectionParams`. The token is an
     anonymous session identity — JS access to it is required by the WS
     design, not a privilege escalation.

  Allowed origins come from `config :chat_f1, :cors_origins` (exact-match
  list). Requests without an `Origin` header, or from unlisted origins, pass
  through untouched — same-origin behaviour is unchanged.
  """

  @behaviour Plug

  import Plug.Conn

  @impl Plug
  def init(opts), do: opts

  @impl Plug
  def call(conn, _opts) do
    conn = register_before_send(conn, &echo_viewer_token/1)

    case origin_if_allowed(conn) do
      nil ->
        conn

      origin ->
        conn
        |> put_resp_header("access-control-allow-origin", origin)
        |> put_resp_header("access-control-allow-credentials", "true")
        |> put_resp_header("access-control-expose-headers", "x-viewer-token")
        |> put_resp_header("vary", "origin")
        |> halt_preflight()
    end
  end

  defp origin_if_allowed(conn) do
    with [origin] <- get_req_header(conn, "origin"),
         true <- origin in allowed_origins() do
      origin
    else
      _ -> nil
    end
  end

  defp allowed_origins, do: Application.get_env(:chat_f1, :cors_origins, [])

  # Preflight requests never reach the router (it has no OPTIONS routes).
  defp halt_preflight(%Plug.Conn{method: "OPTIONS"} = conn) do
    conn
    |> put_resp_header("access-control-allow-methods", "GET, POST, OPTIONS")
    |> put_resp_header("access-control-allow-headers", "authorization, content-type")
    |> put_resp_header("access-control-max-age", "86400")
    |> send_resp(204, "")
    |> halt()
  end

  defp halt_preflight(conn), do: conn

  # Runs at send time, after the router pipeline has assigned the token.
  defp echo_viewer_token(conn) do
    case conn.assigns[:viewer_token] do
      token when is_binary(token) -> put_resp_header(conn, "x-viewer-token", token)
      _ -> conn
    end
  end
end
