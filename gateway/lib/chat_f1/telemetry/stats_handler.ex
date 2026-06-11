defmodule ChatF1.Telemetry.StatsHandler do
  @moduledoc """
  Telemetry handler that aggregates TTFT and tokens-per-second into an ETS
  ring buffer for the public `systemStats` GraphQL query.

  ## Events handled

  * `[:chatf1, :agent, :first_token]` — records TTFT in ms.
  * `[:chatf1, :agent, :stream, :stop]` — records tokens/s.

  ## ETS table

  `:chatf1_stats` is an ETS table (type `:set`, public) created by the
  `Application` supervisor.  It stores:

  * `{:last_standings_sync_at, DateTime.t()}` — written by `JolpicaSync`.
  * `{:first_token_ring, [integer()]}` — ring buffer of last 100 TTFT values.
  * `{:tokens_per_second_ring, [float()]}` — ring buffer of last 100 tps values.

  ## p95 computation

  `p95_first_token_ms/0` fetches the ring, sorts, and returns the 95th
  percentile.  With 100 values this is position 95.  Returns `nil` if empty.
  """

  require Logger

  @table :chatf1_stats
  @ring_size 100

  # ─── Attach / detach ──────────────────────────────────────────────────────────

  @doc "Attaches telemetry handlers and ensures the ETS table exists."
  def attach do
    ensure_table()

    :telemetry.attach_many(
      "chatf1-stats-handler",
      [
        [:chatf1, :agent, :first_token],
        [:chatf1, :agent, :stream, :stop]
      ],
      &__MODULE__.handle_event/4,
      nil
    )
  end

  @doc "Detaches the telemetry handlers (called in tests for cleanup)."
  def detach do
    :telemetry.detach("chatf1-stats-handler")
  end

  # ─── Handler ──────────────────────────────────────────────────────────────────

  @doc false
  def handle_event([:chatf1, :agent, :first_token], %{latency_ms: ms}, _meta, _config) do
    push_ring(:first_token_ring, ms)
  end

  def handle_event([:chatf1, :agent, :stream, :stop], measurements, _meta, _config) do
    tokens_per_s = Map.get(measurements, :tokens_per_second)

    if is_number(tokens_per_s) do
      push_ring(:tokens_per_second_ring, tokens_per_s)
    end
  end

  def handle_event(_event, _measurements, _meta, _config), do: :ok

  # ─── Public read helpers ──────────────────────────────────────────────────────

  @doc "Returns the p95 first-token latency in ms, or nil."
  @spec p95_first_token_ms() :: integer() | nil
  def p95_first_token_ms do
    case read_ring(:first_token_ring) do
      [] ->
        nil

      values ->
        sorted = Enum.sort(values)
        n = length(sorted)
        idx = max(ceil(n * 0.95) - 1, 0)
        Enum.at(sorted, idx)
    end
  end

  @doc "Returns the mean tokens/second from recent streams, or nil."
  @spec tokens_per_second() :: float() | nil
  def tokens_per_second do
    case read_ring(:tokens_per_second_ring) do
      [] -> nil
      values -> Enum.sum(values) / length(values)
    end
  end

  @doc "Returns the last standings sync timestamp, or nil."
  @spec last_standings_sync_at() :: DateTime.t() | nil
  def last_standings_sync_at do
    case :ets.lookup(@table, :last_standings_sync_at) do
      [{_, dt}] -> dt
      [] -> nil
    end
  end

  # ─── Private helpers ──────────────────────────────────────────────────────────

  defp ensure_table do
    if :ets.whereis(@table) == :undefined do
      :ets.new(@table, [:named_table, :public, :set, {:write_concurrency, true}])
    end
  end

  defp push_ring(key, value) do
    current = read_ring(key)
    trimmed = Enum.take(current, @ring_size - 1)
    :ets.insert(@table, {key, [value | trimmed]})
  end

  defp read_ring(key) do
    case :ets.lookup(@table, key) do
      [{_, values}] -> values
      [] -> []
    end
  end
end
