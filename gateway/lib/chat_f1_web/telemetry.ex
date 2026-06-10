defmodule ChatF1Web.Telemetry do
  @moduledoc """
  Telemetry supervisor: attaches handlers and runs a VM-metrics poller.

  Metrics are exported via Phoenix LiveDashboard in dev and will be scraped
  by PromEx in Phase 5.  The public `systemStats` GraphQL query surfaces a
  curated subset.

  Handlers cover:
  * Phoenix endpoint + router request metrics
  * Ecto query duration
  * Absinthe operation metrics (via Absinthe.Telemetry if available)
  * Custom ChatF1 events: `[:chatf1, :agent, :stream, :stop]`,
    `[:chatf1, :rate_limit, :allow]`, `[:chatf1, :rate_limit, :deny]`
  """

  use Supervisor
  import Telemetry.Metrics

  def start_link(arg) do
    Supervisor.start_link(__MODULE__, arg, name: __MODULE__)
  end

  @impl true
  def init(_arg) do
    children = [
      {Telemetry.Metrics.ConsoleReporter, metrics: metrics()},
      {:telemetry_poller,
       measurements: periodic_measurements(), period: 10_000, name: :chatf1_vm_poller}
    ]

    Supervisor.init(children, strategy: :one_for_one)
  end

  def metrics do
    [
      # ── Phoenix HTTP ─────────────────────────────────────────────────────────
      summary("phoenix.endpoint.start.system_time", unit: {:native, :millisecond}),
      summary("phoenix.endpoint.stop.duration", unit: {:native, :millisecond}),
      summary("phoenix.router_dispatch.stop.duration",
        tags: [:route],
        unit: {:native, :millisecond}
      ),

      # ── Ecto ─────────────────────────────────────────────────────────────────
      summary("chat_f1.repo.query.total_time",
        unit: {:native, :millisecond},
        description: "The sum of the other measurements"
      ),
      summary("chat_f1.repo.query.decode_time",
        unit: {:native, :millisecond},
        description: "Time spent decoding the data received from the database"
      ),
      summary("chat_f1.repo.query.query_time",
        unit: {:native, :millisecond},
        description: "Time spent executing the query"
      ),
      summary("chat_f1.repo.query.queue_time",
        unit: {:native, :millisecond},
        description: "Time spent waiting for a database connection"
      ),
      summary("chat_f1.repo.query.idle_time",
        unit: {:native, :millisecond},
        description: "Time the connection spent waiting before being checked out for the query"
      ),

      # ── Absinthe ─────────────────────────────────────────────────────────────
      summary("absinthe.execute.operation.stop.duration", unit: {:native, :millisecond}),
      summary("absinthe.resolve.field.stop.duration", unit: {:native, :millisecond}),

      # ── Agent stream ─────────────────────────────────────────────────────────
      summary("chatf1.agent.stream.stop.duration",
        unit: {:native, :millisecond},
        tags: [:cached]
      ),

      # ── Rate limiter ─────────────────────────────────────────────────────────
      counter("chatf1.rate_limit.allow.count"),
      counter("chatf1.rate_limit.deny.count"),

      # ── VM metrics ───────────────────────────────────────────────────────────
      last_value("vm.memory.total", unit: {:byte, :kilobyte}),
      last_value("vm.total_run_queue_lengths.total"),
      last_value("vm.total_run_queue_lengths.cpu"),
      last_value("vm.system_counts.process_count")
    ]
  end

  defp periodic_measurements do
    [
      {__MODULE__, :dispatch_vm_stats, []}
    ]
  end

  @doc false
  def dispatch_vm_stats do
    :telemetry.execute(
      [:vm, :memory],
      Map.new(:erlang.memory()),
      %{}
    )
  end
end
