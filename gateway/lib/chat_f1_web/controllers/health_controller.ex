defmodule ChatF1Web.HealthController do
  @moduledoc """
  Health probe endpoints for Fly.io monitoring and portfolio build probes.

  ## /up

  Lightweight liveness probe — always 200 if the app is running. Also the
  wake-on-paint target (ARCHITECTURE §2): the frontend's first paint fires
  `GET /up`, and this controller forwards a fire-and-forget health probe to
  the agent so Render's 30–60 s cold start burns while the visitor is still
  reading the hero copy.

  ## /healthz

  Detailed readiness probe used by the portfolio CI build-probe.
  Returns JSON with **stable keys** (do not rename without updating build config):

      {"status": "ok" | "degraded", "agent": "ready" | "degraded" | "down", "mode": "live" | "degraded" | "showcase"}

  HTTP 200 when `status == "ok"`, HTTP 503 when `status == "degraded"`.
  """

  use ChatF1Web, :controller

  alias ChatF1.Agents.Breaker
  alias ChatF1.Budget

  @doc """
  Lightweight liveness probe — returns 200 if the app is running.

  Side effect: fires an async warm ping at the agent (wake-on-paint).
  The response never waits on it.
  """
  def up(conn, _params) do
    warm_agent()
    send_resp(conn, 200, "")
  end

  # Fire-and-forget agent warm ping. The HTTP request itself is what makes
  # Render start a sleeping machine; the response (or any error) is
  # irrelevant, so failures are swallowed. receive_timeout rides out the
  # full cold start so the connection that triggered the wake stays open.
  defp warm_agent do
    Task.start(fn ->
      agent_url = Application.fetch_env!(:chat_f1, :agent_url)
      token = Application.fetch_env!(:chat_f1, :internal_api_token)

      Req.get(
        agent_url <> "/internal/health",
        headers: [{"authorization", "Bearer #{token}"}],
        connect_options: [timeout: 5_000],
        receive_timeout: 65_000,
        retry: false
      )
    end)
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
    Breaker.state()
  rescue
    _ -> :open
  end

  defp safe_mode do
    Budget.mode()
  rescue
    _ -> :live
  end
end
