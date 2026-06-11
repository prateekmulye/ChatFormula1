defmodule ChatF1.Showcase.Answer do
  @moduledoc """
  Ecto schema for a pre-generated SHOWCASE cached answer.

  Each row stores a canonical question, the full answer content, retrieval
  sources, the node transition trace, and a token-timing histogram used by
  `ChatF1.Showcase.Replayer` to pace the replay stream.

  ## token_timing_histogram

  An array of inter-batch delay values in milliseconds, recorded during the
  original `WarmShowcaseCache` generation pass.  The replayer walks this array
  `Process.send_after(self(), :next_batch, delay_ms)` to reproduce the original
  pacing — so the replay feels live, not instant.

  ## token_batches

  The pre-baked text for each `TokenDelta` batch, in order.  Combined with
  `token_timing_histogram` (one timing per batch), the replayer emits
  timer-paced `TokenDelta` events with honest delays.
  """

  use Ecto.Schema
  import Ecto.Changeset

  @type t :: %__MODULE__{}

  schema "showcase_answers" do
    field :question, :string
    field :content, :string
    field :sources, {:array, :map}, default: []
    field :node_trace, {:array, :map}, default: []
    field :token_timing_histogram, {:array, :integer}, default: []
    field :token_batches, {:array, :string}, default: []
    field :generated_at, :utc_datetime

    timestamps(type: :utc_datetime)
  end

  @spec changeset(t(), map()) :: Ecto.Changeset.t()
  def changeset(answer, attrs) do
    answer
    |> cast(attrs, [
      :question,
      :content,
      :sources,
      :node_trace,
      :token_timing_histogram,
      :token_batches,
      :generated_at
    ])
    |> validate_required([:question, :content])
    |> validate_length(:question, min: 1, max: 2000)
    |> unique_constraint(:question)
  end
end
