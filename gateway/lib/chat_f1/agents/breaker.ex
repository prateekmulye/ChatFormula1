defmodule ChatF1.Agents.Breaker do
  @moduledoc """
  Circuit breaker GenServer guarding the Python inference agent.

  ## Why a circuit breaker?

  The agent runs on Render's free tier, which sleeps after 15 minutes of
  inactivity and takes 30–60 s to cold-start.  Without a breaker:

  * Every stream attempt during a cold-start would hang until timeout, tying
    up a BEAM process and a Finch connection slot.
  * Cascading timeouts could flood the agent with duplicate requests once it
    wakes, making recovery slower.

  With a breaker, after `@failure_threshold` consecutive stream failures:
  1. The breaker opens — new `begin_stream` calls return
     `{:error, :upstream_unavailable}` immediately (< 1 ms, no HTTP).
  2. After `@open_timeout_ms`, it moves to `:half_open` and fires a single
     health probe to `GET /internal/health`.
  3. If the probe succeeds → `:closed`; if it fails → back to `:open`.

  ## State transitions

  ```
  :closed --[N failures]--> :open --[timeout]--> :half_open
     ^                                                 |
     |                                          [probe ok]
     +--[probe ok]------------------------------------>|
                                               [probe fail]
                             :open <--[timeout]--------+
  ```

  ## Integration with Absinthe subscriptions

  On every state transition the breaker publishes to
  `Absinthe.Subscription.publish/3` on the `systemHealthChanged` topic so
  the React UI can flip LIVE/DEGRADED badges in real time without polling.

  ## Telemetry

  Emits `[:chatf1, :breaker, :transition]` with metadata
  `%{from: state, to: state}` on every state change.
  """

  use GenServer

  require Logger

  alias ChatF1.Agents.BreakerState

  @failure_threshold 3
  # 30 seconds
  @open_timeout_ms 30_000
  @probe_path "/internal/health"
  @connect_timeout 5_000
  @recv_timeout 8_000

  @type state_name :: :closed | :open | :half_open

  # ─── Public API ──────────────────────────────────────────────────────────────

  @spec start_link(keyword()) :: GenServer.on_start()
  def start_link(opts \\ []) do
    GenServer.start_link(__MODULE__, opts, name: __MODULE__)
  end

  @doc """
  Returns the current breaker state atom: `:closed`, `:open`, or `:half_open`.
  """
  @spec state() :: state_name()
  def state do
    GenServer.call(__MODULE__, :state)
  end

  @doc """
  Called by `StreamRunner` when a stream completes successfully.
  Resets the consecutive-failure counter (closes the breaker if half-open).
  """
  @spec record_success() :: :ok
  def record_success do
    GenServer.cast(__MODULE__, :record_success)
  end

  @doc """
  Called by `StreamRunner` (via `:DOWN` monitor) when a stream fails.
  After `@failure_threshold` consecutive failures, the breaker opens.
  """
  @spec record_failure() :: :ok
  def record_failure do
    GenServer.cast(__MODULE__, :record_failure)
  end

  @doc """
  Checks whether the breaker is closed.

  Returns `{:ok, :proceed}` when the request should go through (`:closed` or
  `:half_open`), or `{:error, :upstream_unavailable}` when `:open`.
  """
  @spec check() :: {:ok, :proceed} | {:error, :upstream_unavailable}
  def check do
    GenServer.call(__MODULE__, :check)
  end

  @doc """
  Returns the full `SystemHealth` map for the `systemHealth` GraphQL query.
  """
  @spec system_health() :: BreakerState.system_health()
  def system_health do
    GenServer.call(__MODULE__, :system_health)
  end

  # ─── GenServer callbacks ─────────────────────────────────────────────────────

  @impl true
  def init(_opts) do
    state = %{
      breaker: :closed,
      consecutive_failures: 0,
      last_transition_at: nil
    }

    {:ok, state}
  end

  @impl true
  def handle_call(:state, _from, state) do
    {:reply, state.breaker, state}
  end

  @impl true
  def handle_call(:check, _from, %{breaker: :open} = state) do
    {:reply, {:error, :upstream_unavailable}, state}
  end

  def handle_call(:check, _from, state) do
    {:reply, {:ok, :proceed}, state}
  end

  @impl true
  def handle_call(:system_health, _from, state) do
    health = build_system_health(state)
    {:reply, health, state}
  end

  @impl true
  def handle_cast(:record_success, state) do
    new_state = handle_success(state)
    {:noreply, new_state}
  end

  @impl true
  def handle_cast(:record_failure, state) do
    new_state = handle_failure(state)
    {:noreply, new_state}
  end

  @impl true
  def handle_info(:probe, state) do
    new_state = run_probe(state)
    {:noreply, new_state}
  end

  # ─── Private helpers ─────────────────────────────────────────────────────────

  defp handle_success(%{breaker: :half_open} = state) do
    transition(state, :closed)
  end

  defp handle_success(state) do
    %{state | consecutive_failures: 0}
  end

  defp handle_failure(%{breaker: :open} = state), do: state

  defp handle_failure(%{consecutive_failures: n} = state)
       when n + 1 >= @failure_threshold do
    new_state = transition(state, :open)
    schedule_probe()
    new_state
  end

  defp handle_failure(state) do
    %{state | consecutive_failures: state.consecutive_failures + 1}
  end

  defp run_probe(state) do
    agent_url = Application.fetch_env!(:chat_f1, :agent_url)
    token = Application.fetch_env!(:chat_f1, :internal_api_token)

    result =
      Req.get(
        agent_url <> @probe_path,
        headers: [{"authorization", "Bearer #{token}"}],
        connect_options: [timeout: @connect_timeout],
        receive_timeout: @recv_timeout
      )

    case result do
      {:ok, %Req.Response{status: 200}} ->
        Logger.info("[Breaker] health probe succeeded — transitioning to :closed")
        transition(state, :closed)

      other ->
        Logger.warning("[Breaker] health probe failed: #{inspect(other)} — re-opening")
        new_state = transition(state, :open)
        schedule_probe()
        new_state
    end
  end

  defp transition(%{breaker: from} = state, to) do
    :telemetry.execute(
      [:chatf1, :breaker, :transition],
      %{count: 1},
      %{from: from, to: to}
    )

    Logger.info("[Breaker] #{from} → #{to}")

    new_state = %{state | breaker: to, consecutive_failures: 0, last_transition_at: now()}

    # Publish to Absinthe subscription topic so the UI updates in real time.
    # Guarded with try/rescue because in test mode with server: false the
    # endpoint's PubSub registry is not started and publish would raise.
    Task.start(fn ->
      health = build_system_health(new_state)

      try do
        Absinthe.Subscription.publish(
          ChatF1Web.Endpoint,
          health,
          system_health_changed: "system_health"
        )
      rescue
        ArgumentError -> :ok
      end
    end)

    new_state
  end

  defp schedule_probe do
    Process.send_after(self(), :probe, @open_timeout_ms)
  end

  defp now, do: System.monotonic_time(:millisecond)

  defp build_system_health(%{breaker: breaker}) do
    agent_service =
      case breaker do
        :closed -> :healthy
        :half_open -> :degraded
        :open -> :down
      end

    mode =
      case breaker do
        :closed -> :live
        _ -> :degraded
      end

    %{
      mode: mode,
      gateway: :healthy,
      agent_service: agent_service,
      database: :healthy,
      breaker_state: breaker
    }
  end
end

defmodule ChatF1.Agents.BreakerState do
  @moduledoc "Type alias for the SystemHealth map returned by Breaker."

  @type system_health :: %{
          mode: :live | :degraded | :showcase,
          gateway: :healthy | :degraded | :down,
          agent_service: :healthy | :degraded | :down,
          database: :healthy | :degraded | :down,
          breaker_state: :closed | :open | :half_open
        }
end
