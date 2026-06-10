defmodule ChatF1.Conversations.Conversation do
  @moduledoc "Ecto schema for a chat conversation owned by a viewer."

  use Ecto.Schema
  import Ecto.Changeset

  alias ChatF1.Conversations.Message

  @type t :: %__MODULE__{}

  schema "conversations" do
    field :viewer_id, :string
    field :title, :string

    has_many :messages, Message, preload_order: [asc: :id]

    timestamps(type: :utc_datetime)
  end

  @spec changeset(t(), map()) :: Ecto.Changeset.t()
  def changeset(conversation, attrs) do
    conversation
    |> cast(attrs, [:viewer_id, :title])
    |> validate_required([:viewer_id])
    |> validate_length(:title, max: 200)
  end
end
