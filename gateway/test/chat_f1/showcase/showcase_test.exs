defmodule ChatF1.ShowcaseTest do
  @moduledoc """
  Tests for Showcase context: upsert_answer, demo_questions, and find_nearest
  (exact + trigram fallback + no-match).
  """

  use ChatF1.DataCase, async: true

  alias ChatF1.Showcase

  # Helper to insert a showcase answer directly.
  defp insert_answer(question, content \\ "some answer") do
    {:ok, answer} =
      Showcase.upsert_answer(%{
        question: question,
        content: content,
        sources: [],
        node_trace: [],
        token_timing_histogram: [100, 50, 30],
        token_batches: ["Hello", " world"],
        generated_at: DateTime.utc_now()
      })

    answer
  end

  # ─── upsert_answer ────────────────────────────────────────────────────────────

  test "upsert_answer/1 inserts a new answer" do
    {:ok, answer} =
      Showcase.upsert_answer(%{
        question: "Who is the fastest F1 driver?",
        content: "It depends on the era.",
        sources: [],
        node_trace: [],
        token_timing_histogram: [],
        token_batches: [],
        generated_at: DateTime.utc_now()
      })

    assert answer.id != nil
    assert answer.question == "Who is the fastest F1 driver?"
  end

  test "upsert_answer/1 updates content on conflict" do
    insert_answer("What is DRS?", "Drag Reduction System v1")

    {:ok, updated} =
      Showcase.upsert_answer(%{
        question: "What is DRS?",
        content: "Drag Reduction System v2",
        sources: [],
        node_trace: [],
        token_timing_histogram: [],
        token_batches: [],
        generated_at: DateTime.utc_now()
      })

    assert updated.content == "Drag Reduction System v2"
  end

  # ─── demo_questions ──────────────────────────────────────────────────────────

  test "demo_questions/0 returns list of question strings" do
    insert_answer("Q1")
    insert_answer("Q2")
    questions = Showcase.demo_questions()
    assert is_list(questions)
    assert "Q1" in questions
    assert "Q2" in questions
  end

  # ─── find_nearest: exact match ────────────────────────────────────────────────

  test "find_nearest/1 returns exact match (case-insensitive)" do
    insert_answer("Who won the 2023 F1 championship?", "Verstappen")
    {:ok, answer} = Showcase.find_nearest("WHO WON THE 2023 F1 CHAMPIONSHIP?")
    assert answer.content == "Verstappen"
  end

  test "find_nearest/1 returns exact match (exact case)" do
    insert_answer("Who won Monaco 2024?", "Leclerc")
    {:ok, answer} = Showcase.find_nearest("Who won Monaco 2024?")
    assert answer.content == "Leclerc"
  end

  # ─── find_nearest: trigram fallback ──────────────────────────────────────────

  test "find_nearest/1 returns trigram match for similar question" do
    insert_answer("Who is the fastest F1 driver in 2024?", "Verstappen arguably")
    # Slightly different phrasing — should hit trgm path (similarity > 0.3)
    {:ok, answer} = Showcase.find_nearest("Who was fastest F1 driver in 2024?")
    assert answer.content == "Verstappen arguably"
  end

  # ─── find_nearest: no match ──────────────────────────────────────────────────

  test "find_nearest/1 returns {:error, :no_match} for unrelated question" do
    # No answers in this sandbox; completely unrelated question.
    assert {:error, :no_match} = Showcase.find_nearest("What is the meaning of life?")
  end

  test "find_nearest/1 returns {:error, :no_match} when only low-similarity entries exist" do
    insert_answer("Ferrari pit stop time", "2.5 seconds")
    # This is unrelated to the inserted question — should be below 0.3 threshold.
    assert {:error, :no_match} = Showcase.find_nearest("What is the weather in Tokyo?")
  end
end
