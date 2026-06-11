defmodule ChatF1.Workers.IngestNews do
  @moduledoc """
  Oban worker: nightly Tavily news ingestion trigger.

  1. Pre-warms the agent by polling `GET /internal/health` for up to 90 s
     (Render cold-start tolerance).
  2. Posts `POST /internal/ingest` with `{"source": "news"}` to kick off
     the agent-side news ingestion pipeline.
  3. Tolerates agent down: logs at `:info`, returns `:ok` (no retry storm).

  ## Schedule

  Runs nightly at 01:00 UTC.
  """

  use Oban.Worker,
    queue: :default,
    unique: [period: 23 * 60 * 60],
    max_attempts: 3

  require Logger

  @health_path "/internal/health"
  @ingest_path "/internal/ingest"
  @warm_timeout_s 90
  @poll_interval_ms 5_000
  @recv_timeout 30_000

  @impl Oban.Worker
  def perform(%Oban.Job{args: args}) do
    source = Map.get(args, "source", "news")
    agent_url = Application.get_env(:chat_f1, :agent_url, "")
    token = Application.get_env(:chat_f1, :internal_api_token, "")

    if agent_url == "" do
      Logger.info("[IngestNews] agent_url not configured — skipping")
      :ok
    else
      Logger.info("[IngestNews] pre-warming agent for ingest source=#{source}")

      case wait_for_agent(agent_url, token) do
        :ready ->
          trigger_ingest(agent_url, token, source)

        :timeout ->
          Logger.info("[IngestNews] agent did not become ready in #{@warm_timeout_s}s — skipping")
          :ok
      end
    end
  end

  defp wait_for_agent(agent_url, token) do
    deadline = System.monotonic_time(:millisecond) + @warm_timeout_s * 1_000
    do_wait(agent_url, token, deadline)
  end

  defp do_wait(agent_url, token, deadline) do
    now = System.monotonic_time(:millisecond)

    if now >= deadline do
      :timeout
    else
      case probe_health(agent_url, token) do
        :ok ->
          :ready

        :error ->
          Process.sleep(@poll_interval_ms)
          do_wait(agent_url, token, deadline)
      end
    end
  end

  defp probe_health(agent_url, token) do
    case Req.get(
           agent_url <> @health_path,
           headers: [{"authorization", "Bearer #{token}"}],
           connect_options: [timeout: 5_000],
           receive_timeout: 8_000,
           # No retries — the warm-loop handles its own retry cadence.
           retry: false
         ) do
      {:ok, %Req.Response{status: 200}} -> :ok
      _ -> :error
    end
  end

  defp trigger_ingest(agent_url, token, source) do
    Logger.info("[IngestNews] triggering ingest source=#{source}")

    case Req.post(
           agent_url <> @ingest_path,
           json: %{source: source},
           headers: [{"authorization", "Bearer #{token}"}],
           receive_timeout: @recv_timeout
         ) do
      {:ok, %Req.Response{status: status}} when status in 200..299 ->
        Logger.info("[IngestNews] ingest accepted (status #{status})")
        :ok

      {:ok, %Req.Response{status: status}} ->
        Logger.warning("[IngestNews] ingest rejected with status #{status}")
        {:error, {:http_status, status}}

      {:error, exception} ->
        Logger.info("[IngestNews] ingest request failed: #{Exception.message(exception)}")
        :ok
    end
  end
end
