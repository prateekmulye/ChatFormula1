defmodule ChatF1.RateLimit.Server do
  @moduledoc """
  GenServer that owns the ETS token-bucket rate-limiter table.

  ## Design (OTP Showcase §5 item 5)

  This is a **hand-rolled dual-window token bucket** — deliberately not Hammer.
  It demonstrates ETS ownership patterns and is the interview story.

  ### ETS table

  The table is `:public` so that the Plug and Absinthe middleware can `lookup`
  without a GenServer roundtrip (reads are hot-path).  Writes go through this
  GenServer to serialize `check_and_consume/1` atomically per key.

  Table name: `ChatF1.RateLimit.Bucket`
  Schema: `{key, minute_count, minute_window_start_ms, hour_count, hour_window_start_ms}`

  ### Dual-window semantics

  * **Per-minute burst window**: max N requests in any 60-second tumbling window.
  * **Per-hour sustained window**: max M requests in any 3600-second tumbling window.
  * Both windows must pass; the more restrictive one governs.
  * Windows are tumbling (not sliding) — simpler and sufficient for abuse prevention.
  * On limit hit: `:deny` with `{:retry_after_seconds, t}`.

  ### GC

  Expired entries (last touch > 2 hours ago) are pruned on a 60-second timer
  to bound ETS memory on a 256 MB Fly machine.  At 40 bytes/entry and a typical
  1000-viewer day, the table uses ~40 KB, well within budget.

  ### Telemetry

  Emits `[:chatf1, :rate_limit, :allow]` and `[:chatf1, :rate_limit, :deny]`
  with `%{viewer_key: key}` metadata on every decision.
  """

  use GenServer

  require Logger

  @table ChatF1.RateLimit.Bucket
  @gc_interval_ms 60_000

  # ─── Public API ──────────────────────────────────────────────────────────────

  @doc "Start the rate-limit server."
  @spec start_link(any()) :: GenServer.on_start()
  def start_link(_opts) do
    GenServer.start_link(__MODULE__, :ok, name: __MODULE__)
  end

  @doc """
  Checks the token bucket for `key` and consumes one token if allowed.

  Returns `:allow` or `{:deny, {:retry_after_seconds, non_neg_integer()}}`.

  This call is synchronous through the GenServer to guarantee atomicity.
  The hot path (allow) completes in a single ETS write, typically < 20 µs.
  """
  @spec check_and_consume(String.t()) ::
          :allow | {:deny, {:retry_after_seconds, non_neg_integer()}}
  def check_and_consume(key) do
    GenServer.call(__MODULE__, {:check_and_consume, key})
  end

  @doc """
  Returns the current rate-limit status for `key` without consuming a token.
  Used by the `rateLimitStatus` GraphQL query.
  """
  @spec status(String.t()) :: map()
  def status(key) do
    GenServer.call(__MODULE__, {:status, key})
  end

  # ─── GenServer callbacks ──────────────────────────────────────────────────────

  @impl GenServer
  def init(:ok) do
    :ets.new(@table, [:named_table, :set, :public, read_concurrency: true])
    schedule_gc()
    {:ok, %{per_minute: limit(:per_minute), per_hour: limit(:per_hour)}}
  end

  @impl GenServer
  def handle_call({:check_and_consume, key}, _from, %{per_minute: pm, per_hour: ph} = state) do
    now_ms = System.monotonic_time(:millisecond)
    result = do_check_and_consume(key, now_ms, pm, ph)
    {:reply, result, state}
  end

  def handle_call({:status, key}, _from, %{per_minute: pm, per_hour: ph} = state) do
    now_ms = System.monotonic_time(:millisecond)
    info = do_status(key, now_ms, pm, ph)
    {:reply, info, state}
  end

  @impl GenServer
  def handle_info(:gc, state) do
    now_ms = System.monotonic_time(:millisecond)
    evict_before = now_ms - 2 * 3_600_000

    # Select all entries whose hour-window start is older than 2 hours.
    # matchspec: {key, _mc, _mws, _hc, hour_window_start} where hws < evict_before
    match_spec = [{{:_, :_, :_, :_, :"$1"}, [{:<, :"$1", evict_before}], [true]}]
    deleted = :ets.select_delete(@table, match_spec)

    if deleted > 0, do: Logger.debug("RateLimit GC: evicted #{deleted} stale entries")

    schedule_gc()
    {:noreply, state}
  end

  # ─── Internal logic ──────────────────────────────────────────────────────────

  defp do_check_and_consume(key, now_ms, per_minute, per_hour) do
    minute_window_ms = 60_000
    hour_window_ms = 3_600_000

    {mc, mws, hc, hws} =
      case :ets.lookup(@table, key) do
        [{^key, mc, mws, hc, hws}] -> {mc, mws, hc, hws}
        [] -> {0, now_ms, 0, now_ms}
      end

    # Reset expired windows
    {mc2, mws2} =
      if now_ms - mws >= minute_window_ms, do: {0, now_ms}, else: {mc, mws}

    {hc2, hws2} =
      if now_ms - hws >= hour_window_ms, do: {0, now_ms}, else: {hc, hws}

    cond do
      mc2 >= per_minute ->
        retry_after = div(minute_window_ms - (now_ms - mws2), 1000) + 1
        :telemetry.execute([:chatf1, :rate_limit, :deny], %{count: 1}, %{key: key})
        {:deny, {:retry_after_seconds, max(retry_after, 1)}}

      hc2 >= per_hour ->
        retry_after = div(hour_window_ms - (now_ms - hws2), 1000) + 1
        :telemetry.execute([:chatf1, :rate_limit, :deny], %{count: 1}, %{key: key})
        {:deny, {:retry_after_seconds, max(retry_after, 1)}}

      true ->
        :ets.insert(@table, {key, mc2 + 1, mws2, hc2 + 1, hws2})
        :telemetry.execute([:chatf1, :rate_limit, :allow], %{count: 1}, %{key: key})
        :allow
    end
  end

  defp do_status(key, now_ms, per_minute, per_hour) do
    minute_window_ms = 60_000

    {mc, mws, hc, _hws} =
      case :ets.lookup(@table, key) do
        [{^key, mc, mws, hc, hws}] -> {mc, mws, hc, hws}
        [] -> {0, now_ms, 0, now_ms}
      end

    # Remaining counts (clamp to 0)
    remaining_minute = max(per_minute - mc, 0)
    remaining_hour = max(per_hour - hc, 0)

    # The minute window's reset time governs the displayed resets_at.
    minute_resets_in = max(minute_window_ms - (now_ms - mws), 0)
    resets_at = DateTime.add(DateTime.utc_now(), div(minute_resets_in, 1000), :second)

    %{
      limit_per_minute: per_minute,
      remaining_minute: remaining_minute,
      limit_per_hour: per_hour,
      remaining_hour: remaining_hour,
      resets_at: resets_at
    }
  end

  defp schedule_gc, do: Process.send_after(self(), :gc, @gc_interval_ms)

  defp limit(key) do
    :chat_f1
    |> Application.get_env(:rate_limit, [])
    |> Keyword.get(key, default_limit(key))
  end

  defp default_limit(:per_minute), do: 20
  defp default_limit(:per_hour), do: 200
end
