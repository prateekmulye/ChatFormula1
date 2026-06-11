defmodule ChatF1.Agents.BreakerTest do
  @moduledoc """
  Tests for the circuit breaker GenServer.

  Each test starts an isolated GenServer instance (not the application
  singleton at `ChatF1.Agents.Breaker`) to avoid cross-test state leakage.
  """

  use ExUnit.Case, async: true

  alias ChatF1.Agents.Breaker

  # Start a fresh, isolated Breaker process for each test. The probe URL is
  # pinned to a dead local port so a fired probe NEVER hits the global
  # :agent_url — async client tests point that at their own Bypass instances.
  defp start_breaker do
    {:ok, pid} = GenServer.start(Breaker, agent_url: "http://127.0.0.1:1")
    on_exit(fn -> if Process.alive?(pid), do: GenServer.stop(pid, :normal) end)
    pid
  end

  defp state(pid), do: GenServer.call(pid, :state)
  defp check(pid), do: GenServer.call(pid, :check)
  defp health(pid), do: GenServer.call(pid, :system_health)
  defp failure(pid), do: GenServer.cast(pid, :record_failure)
  defp success(pid), do: GenServer.cast(pid, :record_success)

  # Drain the mailbox so casts are processed before the next call.
  defp sync(pid), do: state(pid)

  # ─── Initial state ────────────────────────────────────────────────────────────

  test "breaker starts in :closed state" do
    pid = start_breaker()
    assert state(pid) == :closed
  end

  test "check returns :proceed when closed" do
    pid = start_breaker()
    assert check(pid) == {:ok, :proceed}
  end

  # ─── Failure accumulation ────────────────────────────────────────────────────

  test "two failures below threshold keep breaker closed" do
    pid = start_breaker()

    failure(pid)
    failure(pid)
    sync(pid)

    assert state(pid) == :closed
    assert check(pid) == {:ok, :proceed}
  end

  test "three consecutive failures open the breaker" do
    pid = start_breaker()

    failure(pid)
    failure(pid)
    failure(pid)
    sync(pid)

    assert state(pid) == :open
    assert check(pid) == {:error, :upstream_unavailable}
  end

  test "success resets failure counter" do
    pid = start_breaker()

    failure(pid)
    failure(pid)
    success(pid)
    # Two more failures — counter was reset so should not open (threshold is 3)
    failure(pid)
    failure(pid)
    sync(pid)

    assert state(pid) == :closed
  end

  # ─── Open state ──────────────────────────────────────────────────────────────

  test "check returns :upstream_unavailable when open" do
    pid = start_breaker()

    Enum.each(1..3, fn _ -> failure(pid) end)
    sync(pid)

    assert check(pid) == {:error, :upstream_unavailable}
  end

  test "additional failures when open do not change state" do
    pid = start_breaker()

    Enum.each(1..3, fn _ -> failure(pid) end)
    sync(pid)

    failure(pid)
    failure(pid)
    sync(pid)

    assert state(pid) == :open
  end

  # ─── Open state ignores success (only probe can close) ────────────────────────

  test "success cast while open does NOT close the breaker" do
    pid = start_breaker()

    # Open the breaker
    Enum.each(1..3, fn _ -> failure(pid) end)
    sync(pid)
    assert state(pid) == :open

    # Success while open — breaker stays open (probe must succeed to close it)
    success(pid)
    sync(pid)

    assert state(pid) == :open
  end

  # ─── System health ────────────────────────────────────────────────────────────

  test "system_health returns :live mode when closed" do
    pid = start_breaker()
    h = health(pid)

    assert h.mode == :live
    assert h.breaker_state == :closed
    assert h.gateway == :healthy
    assert h.agent_service == :healthy
  end

  test "system_health returns :showcase + :down when open (Phase 5: SHOWCASE wins)" do
    # Per ARCHITECTURE §3: ServiceMode SHOWCASE = budget spent OR agent down (breaker open).
    # Breaker open → mode is :showcase so the UI activates cached-replay path.
    pid = start_breaker()

    Enum.each(1..3, fn _ -> failure(pid) end)
    sync(pid)

    h = health(pid)
    assert h.mode == :showcase
    assert h.breaker_state == :open
    assert h.agent_service == :down
  end

  # ─── Telemetry ───────────────────────────────────────────────────────────────

  test "emits [:chatf1, :breaker, :transition] on failure threshold" do
    pid = start_breaker()
    test_pid = self()
    ref = make_ref()

    :telemetry.attach(
      "breaker-transition-test-#{inspect(ref)}",
      [:chatf1, :breaker, :transition],
      fn _event, _measurements, metadata, _ ->
        send(test_pid, {:telemetry, ref, metadata})
      end,
      nil
    )

    on_exit(fn -> :telemetry.detach("breaker-transition-test-#{inspect(ref)}") end)

    Enum.each(1..3, fn _ -> failure(pid) end)
    sync(pid)

    assert_receive {:telemetry, ^ref, %{from: :closed, to: :open}}, 1000
  end

  test "probe passes through :half_open before deciding" do
    pid = start_breaker()
    test_pid = self()
    ref = make_ref()

    :telemetry.attach(
      "breaker-half-open-test-#{inspect(ref)}",
      [:chatf1, :breaker, :transition],
      fn _event, _measurements, metadata, _ ->
        send(test_pid, {:telemetry, ref, metadata})
      end,
      nil
    )

    on_exit(fn -> :telemetry.detach("breaker-half-open-test-#{inspect(ref)}") end)

    Enum.each(1..3, fn _ -> failure(pid) end)
    sync(pid)
    assert_receive {:telemetry, ^ref, %{from: :closed, to: :open}}, 1000

    # Fire the scheduled probe immediately. Nothing listens on the test
    # agent_url, so the trial fails: open -> half_open -> open.
    send(pid, :probe)

    assert_receive {:telemetry, ^ref, %{from: :open, to: :half_open}}, 2000
    assert_receive {:telemetry, ^ref, %{from: :half_open, to: :open}}, 10_000
    assert state(pid) == :open
  end
end
