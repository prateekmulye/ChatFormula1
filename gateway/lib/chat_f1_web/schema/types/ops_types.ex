defmodule ChatF1Web.Schema.Types.OpsTypes do
  @moduledoc """
  Absinthe type definitions for Phase 5 ops/admin types.

  Covers:
  * `SystemStats` — public pit-wall panel (only telemetry-fed numbers).
  * `IngestSource` enum + `IngestJob` — for the `triggerIngest` mutation.
  """

  use Absinthe.Schema.Notation

  @desc """
  Real-time BEAM + system statistics.  All fields are telemetry-fed — no
  invented numbers.  Nullable fields return nil when no data is available yet
  (e.g. p95FirstTokenMs before any stream has completed).
  """
  object :system_stats do
    @desc "Number of active Conversation.Server GenServers."
    field :active_conversations, non_null(:integer)

    @desc "Total BEAM process count (VM-level)."
    field :beam_process_count, non_null(:integer)

    @desc "Seconds since the gateway started."
    field :uptime_seconds, non_null(:integer)

    @desc "p95 first-token latency in ms (nil until at least 1 stream completes)."
    field :p95_first_token_ms, :integer

    @desc "Mean tokens/second from recent streams (nil until at least 1 stream completes)."
    field :tokens_per_second, :float

    @desc "Oban jobs completed in the last 24 hours."
    field :oban_jobs_completed_24h, non_null(:integer)

    @desc "When the standings data was last synced from Jolpica/Ergast. Nil if never."
    field :last_standings_sync_at, :datetime

    @desc "LLM spend in USD today."
    field :llm_spend_today_usd, non_null(:float)

    @desc "Remaining daily LLM budget in USD."
    field :daily_budget_remaining_usd, non_null(:float)
  end

  @desc "Allowlisted ingest sources for the triggerIngest mutation."
  enum :ingest_source do
    @desc "Tavily news ingestion (nightly Oban job)."
    value(:news)

    @desc "Historical F1 data ingestion."
    value(:historical)

    @desc "Race calendar sync."
    value(:calendar)
  end

  @desc "Result of enqueuing an ingest job."
  object :ingest_job do
    field :id, non_null(:id)
    field :state, non_null(:string)
    field :queued_at, non_null(:datetime)
  end
end
