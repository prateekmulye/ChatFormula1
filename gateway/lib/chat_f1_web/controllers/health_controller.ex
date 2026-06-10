defmodule ChatF1Web.HealthController do
  @moduledoc "Health probe endpoints for Fly.io and monitoring tools."

  use ChatF1Web, :controller

  @doc "Lightweight liveness probe — returns 200 if the app is running."
  def up(conn, _params) do
    send_resp(conn, 200, "")
  end

  @doc "Detailed health check — verifies DB connectivity."
  def healthz(conn, _params) do
    db_ok =
      try do
        ChatF1.Repo.query!("SELECT 1")
        true
      rescue
        _ -> false
      end

    status = if db_ok, do: 200, else: 503
    body = Jason.encode!(%{status: if(db_ok, do: "ok", else: "degraded"), db: db_ok})

    conn
    |> put_resp_content_type("application/json")
    |> send_resp(status, body)
  end
end
