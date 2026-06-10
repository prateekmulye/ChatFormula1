defmodule ChatF1.RateLimitTest do
  @moduledoc """
  Unit tests for the hand-rolled ETS dual-window token-bucket rate limiter.
  Tests cover: allow path, per-minute limit, per-hour limit, window resets,
  and concurrent key isolation.
  """

  use ExUnit.Case, async: false

  alias ChatF1.RateLimit.Server

  # Use a unique key per test to avoid cross-test state leakage.
  defp unique_key, do: "test_key_#{System.unique_integer([:positive, :monotonic])}"

  describe "check_and_consume/1" do
    test "allows requests within the per-minute limit" do
      key = unique_key()
      # Default per-minute limit is 20 in test config; send 5 — all should pass
      results = Enum.map(1..5, fn _ -> Server.check_and_consume(key) end)
      assert Enum.all?(results, &(&1 == :allow))
    end

    test "denies requests exceeding per-minute limit" do
      # Override per-minute to 3 for this test by using Application.put_env
      # We can't easily change runtime config per-test, so we use a key that
      # has already been consumed to its limit by manual ETS manipulation.
      table = ChatF1.RateLimit.Bucket
      key = unique_key()
      pm = Application.get_env(:chat_f1, :rate_limit)[:per_minute] || 20

      # Exhaust the minute window by direct ETS write
      now_ms = System.monotonic_time(:millisecond)
      :ets.insert(table, {key, pm, now_ms, 0, now_ms})

      result = Server.check_and_consume(key)
      assert {:deny, {:retry_after_seconds, t}} = result
      assert t > 0
    end

    test "denies requests exceeding per-hour limit" do
      table = ChatF1.RateLimit.Bucket
      key = unique_key()
      ph = Application.get_env(:chat_f1, :rate_limit)[:per_hour] || 200

      now_ms = System.monotonic_time(:millisecond)
      # minute window is fine (0), hour window is exhausted
      :ets.insert(table, {key, 0, now_ms, ph, now_ms})

      result = Server.check_and_consume(key)
      assert {:deny, {:retry_after_seconds, t}} = result
      assert t > 0
    end

    test "resets minute window after 60 seconds (simulated)" do
      table = ChatF1.RateLimit.Bucket
      key = unique_key()
      pm = Application.get_env(:chat_f1, :rate_limit)[:per_minute] || 20

      # Set the minute window start to 61 seconds ago — it should reset
      now_ms = System.monotonic_time(:millisecond)
      old_mws = now_ms - 61_000
      :ets.insert(table, {key, pm, old_mws, 0, now_ms})

      # Now the minute window is expired; should allow
      assert Server.check_and_consume(key) == :allow
    end

    test "different keys are isolated" do
      key1 = unique_key()
      key2 = unique_key()

      table = ChatF1.RateLimit.Bucket
      pm = Application.get_env(:chat_f1, :rate_limit)[:per_minute] || 20
      now_ms = System.monotonic_time(:millisecond)
      :ets.insert(table, {key1, pm, now_ms, 0, now_ms})

      # key1 is exhausted; key2 should still be allowed
      assert {:deny, _} = Server.check_and_consume(key1)
      assert :allow = Server.check_and_consume(key2)
    end
  end

  describe "status/1" do
    test "returns status with correct limit fields" do
      key = unique_key()
      status = Server.status(key)

      assert is_integer(status.limit_per_minute)
      assert is_integer(status.limit_per_hour)
      assert is_integer(status.remaining_minute)
      assert is_integer(status.remaining_hour)
      assert %DateTime{} = status.resets_at
    end

    test "remaining decreases after check_and_consume" do
      key = unique_key()
      before = Server.status(key)
      Server.check_and_consume(key)
      after_call = Server.status(key)

      assert after_call.remaining_minute == before.remaining_minute - 1
    end
  end
end
