defmodule ChatF1Web.Schema.Resolvers.OpsResolvers do
  @moduledoc """
  Resolver functions for Phase 5 ops queries and mutations:
  * `systemStats` — BEAM telemetry pit-wall panel.
  * `demoQuestions` — SHOWCASE demo question chips.
  * `triggerIngest` — enqueues an IngestNews Oban job (API-key gated).
  """

  require Logger

  import Ecto.Query

  alias ChatF1.Budget
  alias ChatF1.Showcase
  alias ChatF1.Telemetry.StatsHandler
  alias ChatF1.Workers.IngestNews

  # ─── systemStats ──────────────────────────────────────────────────────────────

  @doc "Resolves the `systemStats` query — only telemetry-fed numbers."
  def system_stats(_parent, _args, _context) do
    {:ok, build_system_stats()}
  end

  defp build_system_stats do
    active_conversations = Registry.count(ChatF1.ConvRegistry)
    process_count = :erlang.system_info(:process_count)

    # Uptime in seconds since application started.
    uptime_seconds =
      :erlang.statistics(:wall_clock)
      |> elem(0)
      |> div(1_000)

    p95 = StatsHandler.p95_first_token_ms()
    tps = StatsHandler.tokens_per_second()
    last_sync = StatsHandler.last_standings_sync_at()

    oban_completed_24h = count_oban_completed_24h()

    {spend, budget} =
      try do
        {:ok, s, b} = Budget.today_spend()
        {Decimal.to_float(s), Decimal.to_float(b)}
      rescue
        _ -> {0.0, 2.0}
      end

    remaining = max(budget - spend, 0.0)

    %{
      active_conversations: active_conversations,
      beam_process_count: process_count,
      uptime_seconds: uptime_seconds,
      p95_first_token_ms: p95,
      tokens_per_second: tps,
      oban_jobs_completed_24h: oban_completed_24h,
      last_standings_sync_at: last_sync,
      llm_spend_today_usd: spend,
      daily_budget_remaining_usd: remaining
    }
  end

  defp count_oban_completed_24h do
    cutoff = DateTime.add(DateTime.utc_now(), -24 * 60 * 60, :second)

    try do
      ChatF1.Repo.aggregate(
        from(j in Oban.Job,
          where: j.state == "completed" and j.completed_at >= ^cutoff
        ),
        :count
      )
    rescue
      _ -> 0
    end
  end

  # ─── demoQuestions ────────────────────────────────────────────────────────────

  @doc "Returns the question strings from seeded showcase_answers."
  def demo_questions(_parent, _args, _context) do
    {:ok, Showcase.demo_questions()}
  end

  # ─── triggerIngest ────────────────────────────────────────────────────────────

  @doc """
  Enqueues an `IngestNews` Oban job for the given source.
  API-key scope `admin:ingest` is enforced by `ApiKeyScope` middleware
  before this resolver runs.
  """
  def trigger_ingest(_parent, %{source: source}, _context) do
    worker_args = %{"source" => Atom.to_string(source)}

    case IngestNews.new(worker_args) |> Oban.insert() do
      {:ok, job} ->
        {:ok,
         %{
           id: to_string(job.id),
           state: job.state,
           queued_at: job.inserted_at
         }}

      {:error, changeset} ->
        Logger.error("[OpsResolvers] triggerIngest insert failed: #{inspect(changeset)}")
        {:error, %{message: "Failed to enqueue ingest job", extensions: %{code: "INTERNAL"}}}
    end
  end
end
