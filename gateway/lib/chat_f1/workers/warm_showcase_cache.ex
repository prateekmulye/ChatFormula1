defmodule ChatF1.Workers.WarmShowcaseCache do
  @moduledoc """
  Oban worker: pre-generates SHOWCASE cached answers for all `demoQuestions`
  entries when budget and breaker allow.

  ## What it does

  For each question in `ChatF1.Showcase.demo_questions/0`:

  1. Checks budget + breaker — skips silently if already in SHOWCASE mode.
  2. Sends the question to the agent via `ChatF1.Agents.Client.chat/3`.
  3. Splits the response content into batches and records inter-batch timings
     (simulated at 40 ms intervals since the aggregated client doesn't expose
     real stream timing — future improvement: use the streaming runner directly).
  4. Upserts the cached answer via `ChatF1.Showcase.upsert_answer/1`.

  ## Schedule

  Runs nightly at 04:00 UTC (after JolpicaSync at 02:00).

  ## Degrade silently

  If the agent is down or over budget, the existing cached answer remains.
  Missing answers are never surfaced as errors.
  """

  use Oban.Worker,
    queue: :default,
    unique: [period: 23 * 60 * 60],
    max_attempts: 3

  require Logger

  alias ChatF1.Agents.Client, as: AgentClient
  alias ChatF1.Budget
  alias ChatF1.Showcase

  # Simulated inter-batch delay when real histogram is unavailable.
  @simulated_batch_delay_ms 40
  # Split content into ~80-char batches to simulate realistic token streams.
  @batch_size 80

  @impl Oban.Worker
  def perform(_job) do
    questions = Showcase.demo_questions()

    if questions == [] do
      Logger.info("[WarmShowcaseCache] no demo questions seeded — skipping")
      :ok
    else
      Logger.info("[WarmShowcaseCache] warming #{length(questions)} showcase answers")

      results =
        Enum.map(questions, fn question ->
          warm_one(question)
        end)

      successes = Enum.count(results, &(&1 == :ok))
      Logger.info("[WarmShowcaseCache] #{successes}/#{length(questions)} answers warmed")
      :ok
    end
  end

  defp warm_one(question) do
    # Skip if we're already in SHOWCASE mode (budget exhausted) —
    # calling the agent would fail anyway.
    case Budget.mode() do
      :showcase ->
        Logger.info("[WarmShowcaseCache] in SHOWCASE mode — skipping '#{String.slice(question, 0, 40)}'")
        :ok

      _ ->
        request_id = "warm-#{:crypto.hash(:sha256, question) |> Base.encode16(case: :lower) |> String.slice(0, 8)}"

        case AgentClient.chat(question, [], request_id) do
          {:ok, %{content: content, sources: sources}} ->
            batches = split_into_batches(content, @batch_size)
            histogram = List.duplicate(@simulated_batch_delay_ms, length(batches))

            Showcase.upsert_answer(%{
              question: question,
              content: content,
              sources: sources,
              node_trace: [],
              token_timing_histogram: histogram,
              token_batches: batches,
              generated_at: DateTime.utc_now()
            })
            |> case do
              {:ok, _} ->
                Logger.debug("[WarmShowcaseCache] warmed: #{String.slice(question, 0, 40)}")
                :ok

              {:error, cs} ->
                Logger.warning("[WarmShowcaseCache] upsert failed: #{inspect(cs)}")
                :error
            end

          {:error, reason} ->
            Logger.info("[WarmShowcaseCache] agent error for '#{String.slice(question, 0, 40)}': #{inspect(reason)}")
            :ok
        end
    end
  end

  defp split_into_batches(content, size) when is_binary(content) and size > 0 do
    content
    |> String.graphemes()
    |> Enum.chunk_every(size)
    |> Enum.map(&Enum.join/1)
  end
end
