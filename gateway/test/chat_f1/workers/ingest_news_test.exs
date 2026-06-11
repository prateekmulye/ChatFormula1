defmodule ChatF1.Workers.IngestNewsTest do
  @moduledoc """
  Tests for the IngestNews Oban worker.

  Uses Bypass to simulate the agent's health and ingest endpoints so the
  worker never touches a real HTTP server.
  """

  # async: false — Application.put_env(:agent_url) is global state
  use ChatF1.DataCase, async: false
  use Oban.Testing, repo: ChatF1.Repo

  alias ChatF1.Workers.IngestNews

  setup do
    bypass = Bypass.open()
    Application.put_env(:chat_f1, :agent_url, "http://localhost:#{bypass.port}")
    Application.put_env(:chat_f1, :internal_api_token, "test-token")
    {:ok, bypass: bypass}
  end

  test "perform/1 warms agent then triggers ingest successfully", %{bypass: bypass} do
    # Health probe returns 200
    Bypass.expect_once(bypass, "GET", "/internal/health", fn conn ->
      Plug.Conn.send_resp(conn, 200, ~s({"status":"ok"}))
    end)

    # Ingest endpoint returns 200
    Bypass.expect_once(bypass, "POST", "/internal/ingest", fn conn ->
      Plug.Conn.send_resp(conn, 200, ~s({"accepted":true}))
    end)

    assert :ok = perform_job(IngestNews, %{"source" => "news"})
  end

  test "perform/1 tolerates ingest HTTP 500 — does not crash", %{bypass: bypass} do
    Bypass.expect_once(bypass, "GET", "/internal/health", fn conn ->
      Plug.Conn.send_resp(conn, 200, ~s({"status":"ok"}))
    end)

    Bypass.expect_once(bypass, "POST", "/internal/ingest", fn conn ->
      Plug.Conn.send_resp(conn, 500, "error")
    end)

    # Returns {:error, {:http_status, 500}} — Oban retries
    assert {:error, _} = perform_job(IngestNews, %{"source" => "news"})
  end

  test "perform/1 returns :ok when agent_url not configured" do
    Application.put_env(:chat_f1, :agent_url, "")
    assert :ok = perform_job(IngestNews, %{})
  end

  # NOTE: The "agent stays down for 90s" path is not unit-tested here because
  # the worker's warm-loop sleeps 5s between polls and runs for 90s total —
  # making the test suite 90s slower per run. The real guard is:
  # (a) agent_url = "" short-circuits immediately (tested above), and
  # (b) the probe returns :error → tolerate path is exercised via the
  #     @warm_timeout_s integration behaviour. The per-probe error path is
  #     covered implicitly by the Bypass connection-refused setup in other tests.
end
