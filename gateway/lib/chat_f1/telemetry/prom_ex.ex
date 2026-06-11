defmodule ChatF1.Telemetry.PromEx do
  @moduledoc """
  PromEx configuration for the ChatFormula1 gateway.

  Exports Prometheus-compatible metrics at `GET /metrics` (behind API-key
  auth in all envs).

  ## Plugins enabled

  * `PromEx.Plugins.Application` — BEAM/OTP application metrics.
  * `PromEx.Plugins.Beam` — VM memory, scheduler, process counts.
  * `PromEx.Plugins.Phoenix` — HTTP request durations and counts.
  * `PromEx.Plugins.Ecto` — query durations keyed by repo.
  * `PromEx.Plugins.Oban` — job counts/durations per queue and worker.

  Absinthe plugin is omitted — it does not exist as a first-party PromEx plugin;
  Absinthe telemetry is emitted as raw `:telemetry` events and covered by the
  Phoenix plugin's generic handler.

  ## Single-node note (ADR-000)

  All metrics are local to the single Fly machine.  No Prometheus remote-write
  or Grafana agent is required; optional Grafana Cloud free scrape is supported.
  """

  use PromEx, otp_app: :chat_f1

  @impl PromEx
  def plugins do
    base = [
      PromEx.Plugins.Application,
      PromEx.Plugins.Beam,
      {PromEx.Plugins.Phoenix, router: ChatF1Web.Router, endpoint: ChatF1Web.Endpoint}
    ]

    # Ecto and Oban plugins poll the DB — disable in test to avoid sandbox ownership
    # errors from the PromEx poller process (which is not in the sandbox).
    if Application.get_env(:chat_f1, :prom_ex_db_plugins, true) do
      base ++
        [
          {PromEx.Plugins.Ecto, repos: [ChatF1.Repo]},
          {PromEx.Plugins.Oban, queues: [:default], poll_rate: 5_000}
        ]
    else
      base
    end
  end

  @impl PromEx
  def dashboard_assigns do
    []
  end

  @impl PromEx
  def dashboards do
    []
  end
end
