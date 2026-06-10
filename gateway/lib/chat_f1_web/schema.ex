defmodule ChatF1Web.Schema do
  @moduledoc """
  Absinthe root schema for the ChatFormula1 GraphQL API.

  ## Middleware stack (per field, in order)

  1. `ViewerAuth` — asserts `context.viewer_id` is set.
  2. `RateLimit` — enforces ETS token-bucket limits on mutations.
  3. `Absinthe.Middleware.MapGet` (built-in) — resolves struct fields.
  4. Field-specific resolver.
  5. `ErrorHandler` — normalizes all errors into `{code, message}` shape.

  ## Query limits

  * **Max depth: 7** — prevents infinite nesting on the Driver→results→race→results path.
  * **Max complexity: 200** — each field costs 1; lists multiply by expected size (10).
    A typical standings query (20 drivers + constructor + results) costs ~60.
    A pathological `drivers { results { race { results { driver { ... } } } } }` query
    is blocked before execution.

  ## Dataloader

  The Dataloader Ecto source batches all association lookups.  It is initialized
  in `context/1` (called once per operation) and passed to the resolution
  context so Absinthe's middleware extracts it automatically.
  """

  use Absinthe.Schema

  alias ChatF1Web.Schema.DataloaderSource
  alias ChatF1Web.Schema.Middleware.{ErrorHandler, RateLimit, ViewerAuth}
  alias ChatF1Web.Schema.Resolvers.{ConversationResolvers, F1Resolvers}

  import_types(Absinthe.Type.Custom)
  import_types(ChatF1Web.Schema.Types.F1Types)
  import_types(ChatF1Web.Schema.Types.ConversationTypes)

  # ─── Dataloader context ──────────────────────────────────────────────────────

  def context(ctx) do
    loader =
      Dataloader.new()
      |> Dataloader.add_source(ChatF1.Formula1, DataloaderSource.data())

    Map.put(ctx, :loader, loader)
  end

  def plugins do
    [Absinthe.Middleware.Dataloader] ++ Absinthe.Plugin.defaults()
  end

  # ─── Middleware stack ────────────────────────────────────────────────────────

  # Applied to every field.  Per-field resolvers run between RateLimit and
  # ErrorHandler.
  def middleware(middleware, _field, _object) do
    [ViewerAuth, RateLimit] ++ middleware ++ [ErrorHandler]
  end

  # ─── Queries ─────────────────────────────────────────────────────────────────

  query do
    @desc "List all drivers, optionally filtered by season."
    field :drivers, list_of(non_null(:driver)) do
      arg(:season, :integer)

      complexity(fn args, child_complexity ->
        ((args[:season] && 10) || 20) * child_complexity
      end)

      resolve(&F1Resolvers.list_drivers/3)
    end

    @desc "Look up a driver by three-letter code (e.g. 'VER')."
    field :driver, :driver do
      arg(:code, non_null(:string))
      resolve(&F1Resolvers.get_driver/3)
    end

    @desc "List races for a season."
    field :races, non_null(list_of(non_null(:race))) do
      arg(:season, non_null(:integer))
      complexity(fn _args, child_complexity -> 24 * child_complexity end)
      resolve(&F1Resolvers.list_races/3)
    end

    @desc "The next upcoming race (used for homepage countdown)."
    field :next_race, :race do
      resolve(&F1Resolvers.next_race/3)
    end

    @desc "Championship standings for a season. Single aggregating query — N+1 free."
    field :standings, non_null(list_of(non_null(:standing_row))) do
      arg(:season, non_null(:integer))
      complexity(fn _args, child_complexity -> 20 * child_complexity end)
      resolve(&F1Resolvers.standings/3)
    end

    @desc "Fetch a conversation by ID. Returns null if not found or not owned by viewer."
    field :conversation, :conversation do
      arg(:id, non_null(:id))
      resolve(&ConversationResolvers.get_conversation/3)
    end

    @desc "List all conversations for the current viewer."
    field :conversations, non_null(list_of(non_null(:conversation))) do
      resolve(&ConversationResolvers.list_conversations/3)
    end

    @desc "Current rate-limit status for the viewer."
    field :rate_limit_status, non_null(:rate_limit_status) do
      resolve(&ConversationResolvers.rate_limit_status/3)
    end
  end

  # ─── Mutations ────────────────────────────────────────────────────────────────

  mutation do
    @desc "Create a new conversation for the current viewer."
    field :start_conversation, non_null(:conversation) do
      resolve(&ConversationResolvers.start_conversation/3)
    end

    @desc """
    Send a message in a conversation.

    Phase 2: synchronous — blocks until the agent responds and returns the
    completed assistant message.  Phase 3 upgrades this to async with a
    subscription-based streaming response.

    Input validation: 1–2000 chars, no control characters, no excessive
    character repetition.
    """
    field :send_message, non_null(:send_message_payload) do
      arg(:conversation_id, non_null(:id))
      arg(:content, non_null(:string))

      resolve(&ConversationResolvers.send_message/3)
    end

    @desc "Delete a conversation owned by the viewer."
    field :delete_conversation, non_null(:boolean) do
      arg(:id, non_null(:id))
      resolve(&ConversationResolvers.delete_conversation/3)
    end
  end
end
