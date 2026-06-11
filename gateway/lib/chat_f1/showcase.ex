defmodule ChatF1.Showcase do
  @moduledoc """
  Context for SHOWCASE cached answers.

  ## Nearest-match lookup

  When the budget is exhausted or the breaker is open, `begin_stream` routes
  to this context.  We first try an exact match on the question text; if none
  exists, we use PostgreSQL trigram similarity (`pg_trgm`) to find the nearest
  pre-generated answer above a 0.3 similarity threshold.

  If no match exceeds the threshold, we return `{:error, :no_match}` — the
  Conversation.Server then publishes a polite `AgentError{BUDGET_EXHAUSTED}`.
  """

  import Ecto.Query

  alias ChatF1.Repo
  alias ChatF1.Showcase.Answer

  @trgm_threshold 0.3

  # ─── Demo questions ────────────────────────────────────────────────────────────

  @doc """
  Returns the list of question strings seeded in `showcase_answers`.
  These are the chips wired to the `demoQuestions` GraphQL query.
  """
  @spec demo_questions() :: [String.t()]
  def demo_questions do
    Answer
    |> order_by([a], a.id)
    |> select([a], a.question)
    |> Repo.all()
  end

  # ─── Lookup ────────────────────────────────────────────────────────────────────

  @doc """
  Finds the best cached answer for `question`.

  1. Exact match (case-insensitive).
  2. Trigram similarity >= 0.3 (pg_trgm).
  3. Returns `{:error, :no_match}` if nothing qualifies.
  """
  @spec find_nearest(String.t()) :: {:ok, Answer.t()} | {:error, :no_match}
  def find_nearest(question) when is_binary(question) do
    case exact_match(question) do
      %Answer{} = answer ->
        {:ok, answer}

      nil ->
        case nearest_trgm(question) do
          %Answer{} = answer -> {:ok, answer}
          nil -> {:error, :no_match}
        end
    end
  end

  # ─── Upsert (used by WarmShowcaseCache worker) ─────────────────────────────────

  @doc """
  Upserts a cached answer.  If the question already exists, all answer fields
  are updated.  Returns `{:ok, answer}`.
  """
  @spec upsert_answer(map()) :: {:ok, Answer.t()} | {:error, Ecto.Changeset.t()}
  def upsert_answer(attrs) do
    %Answer{}
    |> Answer.changeset(attrs)
    |> Repo.insert(
      on_conflict:
        {:replace,
         [
           :content,
           :sources,
           :node_trace,
           :token_timing_histogram,
           :token_batches,
           :generated_at,
           :updated_at
         ]},
      conflict_target: :question,
      returning: true
    )
  end

  @doc "Returns all `Answer` records."
  @spec list_answers() :: [Answer.t()]
  def list_answers do
    Repo.all(Answer)
  end

  # ─── Private helpers ──────────────────────────────────────────────────────────

  defp exact_match(question) do
    Answer
    |> where([a], fragment("lower(?)", a.question) == ^String.downcase(question))
    |> Repo.one()
  end

  defp nearest_trgm(question) do
    Answer
    |> where(
      [a],
      fragment("similarity(?, ?) >= ?", a.question, ^question, @trgm_threshold)
    )
    |> order_by([a], desc: fragment("similarity(?, ?)", a.question, ^question))
    |> limit(1)
    |> Repo.one()
  end
end
