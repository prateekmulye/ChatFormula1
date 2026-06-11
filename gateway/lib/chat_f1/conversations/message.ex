defmodule ChatF1.Conversations.Message do
  @moduledoc "Ecto schema for a single message in a conversation."

  use Ecto.Schema
  import Ecto.Changeset

  alias ChatF1.Conversations.Conversation

  @type t :: %__MODULE__{}

  # Roles mirror the MessageRole GraphQL enum (lowercase atoms in Ecto).
  @roles [:user, :assistant]
  # Status lifecycle: pending → streaming → complete | failed
  @statuses [:pending, :streaming, :complete, :failed]

  schema "messages" do
    belongs_to :conversation, Conversation

    field :role, Ecto.Enum, values: @roles
    field :content, :string, default: ""
    field :status, Ecto.Enum, values: @statuses, default: :pending
    field :intent, :string
    # JSON array of source objects: [{kind, title, url, snippet, score}]
    field :sources, {:array, :map}, default: []
    field :cached, :boolean, default: false
    field :latency_ms, :integer

    timestamps(type: :utc_datetime)
  end

  # Base changeset: casts all permitted fields and validates conversation_id.
  # Role is NOT required here because specialized changesets set it via put_change
  # after calling this function — validating it before put_change would always fail.
  @spec changeset(t(), map()) :: Ecto.Changeset.t()
  def changeset(message, attrs) do
    message
    |> cast(attrs, [
      :conversation_id,
      :role,
      :content,
      :status,
      :intent,
      :cached,
      :latency_ms
    ])
    |> cast_sources(attrs)
    |> validate_required([:conversation_id])
    |> validate_inclusion(:role, @roles)
    |> validate_inclusion(:status, @statuses)
  end

  @spec user_changeset(t(), map()) :: Ecto.Changeset.t()
  def user_changeset(message, attrs) do
    message
    |> changeset(attrs)
    |> put_change(:role, :user)
    |> put_change(:status, :complete)
    |> validate_required([:role])
    |> validate_content()
  end

  @spec assistant_placeholder_changeset(t(), map()) :: Ecto.Changeset.t()
  def assistant_placeholder_changeset(message, attrs) do
    message
    |> changeset(attrs)
    |> put_change(:role, :assistant)
    |> put_change(:status, :pending)
    |> put_change(:content, "")
    |> validate_required([:role])
  end

  # Sources can be an atom-keyed map (from GenServer normalize_sources) or a list.
  # Coerce to list of string-keyed maps for the {:array, :map} column.
  defp cast_sources(changeset, attrs) do
    sources = Map.get(attrs, :sources) || Map.get(attrs, "sources")

    normalized =
      case sources do
        nil ->
          nil

        [] ->
          []

        [%{} | _] = list ->
          Enum.map(list, fn s ->
            %{
              "kind" => to_string(s[:kind] || s["kind"] || "vector"),
              "title" => s[:title] || s["title"] || "",
              "url" => s[:url] || s["url"],
              "snippet" => s[:snippet] || s["snippet"],
              "score" => s[:score] || s["score"]
            }
          end)

        _ ->
          nil
      end

    if is_nil(normalized) do
      changeset
    else
      put_change(changeset, :sources, normalized)
    end
  end

  # Content validation for user messages: length, control chars, repeated chars.
  # This mirrors the transport-level validation spec (ARCHITECTURE.md §2).
  defp validate_content(changeset) do
    changeset
    |> validate_required([:content])
    |> validate_length(:content, min: 1, max: 2000)
    |> validate_change(:content, &validate_no_control_chars/2)
    |> validate_change(:content, &validate_no_excessive_repetition/2)
  end

  defp validate_no_control_chars(:content, content) do
    stripped = String.replace(content, ~r/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/, "")

    if stripped == content do
      []
    else
      [content: "must not contain control characters"]
    end
  end

  # Guard: more than 30 consecutive identical characters is almost always abuse.
  defp validate_no_excessive_repetition(:content, content) do
    if Regex.match?(~r/(.)\1{29,}/, content) do
      [content: "contains excessive character repetition"]
    else
      []
    end
  end
end
