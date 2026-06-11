defmodule ChatF1Web.HealthController do
  @moduledoc """
  Health probe endpoints for Fly.io monitoring and portfolio build probes.

  ## /up

  Lightweight liveness probe — always 200 if the app is running.

  ## /healthz

  Detailed readiness probe used by the portfolio CI build-probe.
  Returns JSON with **stable keys** (do not rename without updating build config):

      {"status": "ok" | "degraded", "agent": "ready" | "degraded" | "down", "mode": "live" | "degraded" | "showcase"}

  HTTP 200 when `status == "ok"`, HTTP 503 when `status == "degraded"`.
  """

  use ChatF1Web, :controller

  alias ChatF1.Agents.Breaker
  alias ChatF1.Budget

  @doc "Lightweight liveness probe — returns 200 if the app is running."
  def up(conn, _params) do
    send_resp(conn, 200, "")
  end

  @doc """
  Detailed health check — verifies DB connectivity, surfaces agent readiness
  and current ServiceMode.

  Keys are stable (portfolio build-probe reads them):
  * `status` — "ok" | "degraded"
  * `agent`  — "ready" | "degraded" | "down"
  * `mode`   — "live" | "degraded" | "showcase"
  """
  def healthz(conn, _params) do
    db_ok =
      try do
        ChatF1.Repo.query!("SELECT 1")
        true
      rescue
        _ -> false
      end

    breaker_state = safe_breaker_state()
    mode = safe_mode()

    agent_status =
      case breaker_state do
        :closed -> "ready"
        :half_open -> "degraded"
        :open -> "down"
      end

    overall_status = if db_ok, do: "ok", else: "degraded"
    http_status = if db_ok, do: 200, else: 503

    body =
      Jason.encode!(%{
        status: overall_status,
        agent: agent_status,
        mode: Atom.to_string(mode)
      })

    conn
    |> put_resp_content_type("application/json")
    |> send_resp(http_status, body)
  end

  defp safe_breaker_state do
    try do
      Breaker.state()
    rescue
      _ -> :open
    end
  end

  defp safe_mode do
    try do
      Budget.mode()
    rescue
      _ -> :live
    end
  end
end
