defmodule ChatF1.Agents.ClientTest do
  @moduledoc """
  Integration tests for the agent HTTP client using Bypass to replay recorded
  NDJSON fixtures.  Covers: happy path, cache-hit, error event, connection
  refused (UPSTREAM_UNAVAILABLE).

  These tests enforce the STREAMING_PROTOCOL.md contract on the gateway side.
  """

  use ExUnit.Case, async: true

  alias ChatF1.Agents.Client

  setup do
    bypass = Bypass.open()
    Application.put_env(:chat_f1, :agent_url, "http://localhost:#{bypass.port}")
    Application.put_env(:chat_f1, :internal_api_token, "test-bypass-token")
    {:ok, bypass: bypass}
  end

  # ─── Happy path ───────────────────────────────────────────────────────────────

  test "happy path: aggregates NDJSON stream into content + sources", %{bypass: bypass} do
    ndjson = """
    {"event":"node_started","node":"analyze_query"}
    {"event":"node_started","node":"route"}
    {"event":"node_started","node":"rank_context"}
    {"event":"sources","items":[{"kind":"vector","title":"Monaco 2026","url":null,"snippet":"Verstappen won.","score":0.85}]}
    {"event":"node_started","node":"generate"}
    {"event":"token","text":"Max "}
    {"event":"token","text":"Verstappen "}
    {"event":"token","text":"won."}
    {"event":"node_started","node":"format_response"}
    {"event":"complete","content":"Max Verstappen won.","cached":false,"usage":null}
    """

    Bypass.expect_once(bypass, "POST", "/internal/chat", fn conn ->
      conn
      |> Plug.Conn.put_resp_content_type("application/x-ndjson")
      |> Plug.Conn.send_resp(200, ndjson)
    end)

    assert {:ok, result} = Client.chat("Who won?", [], "req-001")
    assert result.content == "Max Verstappen won."
    assert result.cached == false
    assert length(result.sources) == 1
    assert hd(result.sources).kind == "vector"
    assert hd(result.sources).title == "Monaco 2026"
    assert is_integer(result.latency_ms)
  end

  # ─── Cache hit ────────────────────────────────────────────────────────────────

  test "cache hit: zero token events; complete with cached: true", %{bypass: bypass} do
    ndjson = """
    {"event":"node_started","node":"analyze_query"}
    {"event":"node_started","node":"route"}
    {"event":"node_started","node":"rank_context"}
    {"event":"sources","items":[{"kind":"web","title":"F1 News","url":"https://example.com","snippet":"Race report","score":0.9}]}
    {"event":"node_started","node":"generate"}
    {"event":"node_started","node":"format_response"}
    {"event":"complete","content":"Verstappen wins from pole.","cached":true,"usage":null}
    """

    Bypass.expect_once(bypass, "POST", "/internal/chat", fn conn ->
      conn
      |> Plug.Conn.put_resp_content_type("application/x-ndjson")
      |> Plug.Conn.send_resp(200, ndjson)
    end)

    assert {:ok, result} = Client.chat("Who won?", [], "req-002")
    assert result.cached == true
    assert result.content == "Verstappen wins from pole."
  end

  # ─── Error event ─────────────────────────────────────────────────────────────

  test "error event: returns agent_error tuple", %{bypass: bypass} do
    ndjson =
      ~s|{"event":"error","code":"internal","message":"Pipeline failed.","retryable":true}\n|

    Bypass.expect_once(bypass, "POST", "/internal/chat", fn conn ->
      conn
      |> Plug.Conn.put_resp_content_type("application/x-ndjson")
      |> Plug.Conn.send_resp(200, ndjson)
    end)

    assert {:error, {:agent_error, "internal", "Pipeline failed."}} =
             Client.chat("Who won?", [], "req-003")
  end

  # ─── Validation error event ───────────────────────────────────────────────────

  test "validation error from agent: returns agent_error with validation code", %{bypass: bypass} do
    ndjson =
      ~s|{"event":"error","code":"validation","message":"Message rejected by prompt-injection guard.","retryable":false}\n|

    Bypass.expect_once(bypass, "POST", "/internal/chat", fn conn ->
      conn
      |> Plug.Conn.put_resp_content_type("application/x-ndjson")
      |> Plug.Conn.send_resp(200, ndjson)
    end)

    assert {:error, {:agent_error, "validation", _}} = Client.chat("inject", [], "req-004")
  end

  # ─── Connection refused ───────────────────────────────────────────────────────

  test "connection refused returns upstream_unavailable", %{bypass: bypass} do
    Bypass.down(bypass)

    assert {:error, :upstream_unavailable} = Client.chat("Who won?", [], "req-005")

    Bypass.up(bypass)
  end

  # ─── HTTP 401 ─────────────────────────────────────────────────────────────────

  test "401 from agent returns upstream_unavailable", %{bypass: bypass} do
    Bypass.expect_once(bypass, "POST", "/internal/chat", fn conn ->
      Plug.Conn.send_resp(conn, 401, "Unauthorized")
    end)

    assert {:error, :upstream_unavailable} = Client.chat("Who won?", [], "req-006")
  end
end
