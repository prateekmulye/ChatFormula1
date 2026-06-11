defmodule ChatF1.Conversations.MessageFeedback do
  @moduledoc "Ecto schema for viewer feedback on an assistant message."

  use Ecto.Schema
  import Ecto.Changeset

  alias ChatF1.Conversations.Message

  @type t :: %__MODULE__{}

  schema "message_feedback" do
    belongs_to :message, Message
    field :viewer_id, :string
    field :helpful, :boolean

    timestamps(type: :utc_datetime)
  end

  @spec changeset(t(), map()) :: Ecto.Changeset.t()
  def changeset(feedback, attrs) do
    feedback
    |> cast(attrs, [:message_id, :viewer_id, :helpful])
    |> validate_required([:message_id, :viewer_id, :helpful])
    |> unique_constraint([:message_id, :viewer_id],
      name: :message_feedback_message_id_viewer_id_index,
      message: "Feedback already submitted for this message"
    )
  end
end
