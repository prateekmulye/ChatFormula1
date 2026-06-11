defmodule ChatF1Web.Schema do
  @moduledoc """
  Absinthe root schema for the ChatFormula1 GraphQL API.

  ## Middleware stack

  Root query/mutation fields (one rate-limit token per operation):

  1. `ViewerAuth` — asserts `context.viewer_id` is set.
  2. `RateLimit` — enforces ETS token-bucket limits, keyed by viewer token
     (IP fallback).
  3. Field-specific resolver.
  4. `ErrorHandler` — normalizes all errors into `{code, message}` shape.

  Nested object fields run only their own resolver + `ErrorHandler`.

  Subscription fields are NOT rate-limited per-event (that would be
  prohibitive); the subscription start is gated by viewer-token auth only.

  ## Query limits

  * **Max complexity: 400**, enforced via `analyze_complexity: true` on the
    Absinthe.Plug forwards in the router. Each field costs 1 by default;
    list fields multiply their children by expected size (20 drivers,
    24 races, 20 results per race, 2 drivers per constructor).
  * The full standings-page query costs 260. A pathological
    `drivers { results { race { results { driver { ... } } } } }` document
    multiplies to ~19,000 and is rejected before execution — nesting depth
    is bounded by the compounding list multipliers rather than a separate
    depth analyzer.

  ## Dataloader

  The Dataloader Ecto source batches all association lookups.  It is initialized
  in `context/1` (called once per operation) and passed to the resolution
  context so Absinthe's middleware extracts it automatically.

  ## Subscriptions (Phase 3)

  * `agentStream(messageId: ID!)` — per-message topic `agent:<message_id>`;
    delivers the `AgentEvent` union (TokenDelta | NodeTransition | ...).
    Subscription-time auth checks viewer token owns the message's conversation.
    On subscribe, buffered replay events are sent to the subscriber before
    the live publish path starts.

  * `systemHealthChanged` — delivered on every breaker state transition;
    lets the React UI flip LIVE/DEGRADED badges without polling.
  """

  use Absinthe.Schema

  alias ChatF1.Conversations.Server, as: ConvServer
  alias ChatF1Web.Schema.DataloaderSource
  alias ChatF1Web.Schema.Middleware.{ApiKeyScope, ErrorHandler, RateLimit, ViewerAuth}
  alias ChatF1Web.Schema.Resolvers.{ConversationResolvers, F1Resolvers, OpsResolvers}

  import_types(Absinthe.Type.Custom)
  import_types(ChatF1Web.Schema.Types.F1Types)
  import_types(ChatF1Web.Schema.Types.ConversationTypes)
  import_types(ChatF1Web.Schema.Types.AgentTypes)
  import_types(ChatF1Web.Schema.Types.OpsTypes)

  # ─── Dataloader context ──────────────────────────────────────────────────────

  def context(ctx) do
    loader =
      Dataloader.new()
      |> Dataloader.add_source(ChatF1.Formula1, DataloaderSource.data())

    # Propagate api_key from conn.assigns (set by ChatF1Web.Plugs.ApiKey) into
    # Absinthe context so the ApiKeyScope middleware can read it.
    api_key = Map.get(ctx, :api_key) || get_in(ctx, [:conn, Access.key(:assigns, %{}), :api_key])
    ctx |> Map.put(:loader, loader) |> Map.put(:api_key, api_key)
  end

  def plugins do
    [Absinthe.Middleware.Dataloader] ++ Absinthe.Plugin.defaults()
  end

  # ─── Middleware stack ────────────────────────────────────────────────────────

  def middleware(middleware, _field, %{identifier: id}) when id in [:query, :mutation] do
    [ViewerAuth, RateLimit] ++ middleware ++ [ErrorHandler]
  end

  def middleware(middleware, _field, _object) do
    middleware ++ [ErrorHandler]
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

    @desc "Current system health — gateway, agent, database, and circuit breaker state."
    field :system_health, non_null(:system_health) do
      resolve(&ConversationResolvers.system_health/3)
    end

    @desc """
    BEAM + system telemetry for the public pit-wall panel.
    Only telemetry-fed numbers — no theater (see ARCHITECTURE.md risk #12).
    """
    field :system_stats, non_null(:system_stats) do
      resolve(&OpsResolvers.system_stats/3)
    end

    @desc "Pre-warmed SHOWCASE question chips wired to cached answers."
    field :demo_questions, non_null(list_of(non_null(:string))) do
      resolve(&OpsResolvers.demo_questions/3)
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

    Phase 3: **async** — persists the message pair and immediately returns
    `{userMessage, assistantMessageId}` (< 50 ms, no LLM work).  The caller
    subscribes to `agentStream(messageId: <assistantMessageId>)` to receive
    streaming events.

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

    @desc """
    Submit thumbs-up/down feedback on an assistant message.
    Idempotent per viewer+message — re-submitting updates the existing row.
    """
    field :submit_feedback, non_null(:boolean) do
      arg(:message_id, non_null(:id))
      arg(:helpful, non_null(:boolean))
      resolve(&ConversationResolvers.submit_feedback/3)
    end

    @desc """
    Enqueues a news/data ingest Oban job.
    Requires API key with scope 'admin:ingest'.
    """
    field :trigger_ingest, non_null(:ingest_job) do
      arg(:source, non_null(:ingest_source))
      middleware(ApiKeyScope, scope: "admin:ingest")
      resolve(&OpsResolvers.trigger_ingest/3)
    end
  end

  # ─── Subscriptions ────────────────────────────────────────────────────────────

  subscription do
    @desc """
    Subscribe to streaming events for a single assistant message.

    Topic: `agent:<message_id>`.  The subscription delivers the `AgentEvent`
    union: TokenDelta batches, NodeTransition (pipeline telemetry), SourcesResolved
    (citation chips), MessageCompleted (final state), and AgentError.

    **Authorization:** the viewer token must own the message's conversation.
    Cross-viewer subscriptions are rejected at subscribe time with an
    `UNAUTHORIZED` error — this is enforced in the `config/2` callback below,
    not in the resolver.

    **Replay on reconnect:** buffered events (with original seq values) are
    sent to a re-subscribing client before the live publish path starts.
    The Apollo reducer deduplicates by seq.
    """
    field :agent_stream, :agent_event do
      arg(:message_id, non_null(:id))

      config(fn args, %{context: context} ->
        message_id = args.message_id
        viewer_id = Map.get(context, :viewer_id)

        # Authorization: verify the viewer owns this message's conversation.
        case authorize_subscription(message_id, viewer_id) do
          {:ok, conversation_id} ->
            # Replay buffered events before going live.
            replay_buffered_events(conversation_id, message_id, context)

            {:ok, topic: "agent:#{message_id}"}

          {:error, reason} ->
            {:error, reason}
        end
      end)

      resolve(fn payload, _args, _context ->
        # The payload arrives as %{token_delta: event} | %{node_transition: event} etc.
        # Unwrap to the concrete event map so Absinthe resolves the union type.
        {:ok, unwrap_payload(payload)}
      end)
    end

    @desc """
    Subscribe to circuit breaker state changes.

    Published on every breaker transition (closed → open → half_open → closed).
    Lets the React UI flip LIVE/DEGRADED service badges in real time.
    No message_id argument needed — this is a global gateway health topic.
    """
    field :system_health_changed, :system_health do
      config(fn _args, _context ->
        {:ok, topic: "system_health"}
      end)

      resolve(fn health, _args, _context ->
        {:ok, health}
      end)
    end
  end

  # ─── Subscription helpers ────────────────────────────────────────────────────

  defp authorize_subscription(message_id, viewer_id) when is_binary(viewer_id) do
    import Ecto.Query

    message_id_int =
      case Integer.parse(message_id) do
        {n, ""} -> n
        _ -> nil
      end

    if is_nil(message_id_int) do
      {:error, "Invalid message ID"}
    else
      query =
        from m in ChatF1.Conversations.Message,
          join: c in ChatF1.Conversations.Conversation,
          on: c.id == m.conversation_id,
          where: m.id == ^message_id_int and c.viewer_id == ^viewer_id,
          select: c.id

      case ChatF1.Repo.one(query) do
        nil -> {:error, "Unauthorized — message not found or not owned by viewer"}
        conversation_id -> {:ok, conversation_id}
      end
    end
  end

  defp authorize_subscription(_message_id, _viewer_id) do
    {:error, "Unauthorized — viewer token required"}
  end

  defp replay_buffered_events(conversation_id, message_id, _context) do
    # Fire-and-forget: replay buffered events to the (re)connecting
    # subscriber. Payloads come back from the server already in the wrapped
    # shape the live path publishes (%{token_delta: ...} etc.), so replayed
    # and live deliveries are indistinguishable to the resolver and the
    # client deduplicates overlap by seq.
    Task.start(fn ->
      # Absinthe registers the subscription only after config/2 returns; a
      # publish that races ahead of registration is silently dropped. The
      # short delay keeps the replay behind that registration. A client that
      # still misses events detects the seq gap and refetches the message —
      # the completed message always lives in Postgres.
      Process.sleep(50)

      conversation_id
      |> ConvServer.get_replay_buffer()
      |> Enum.each(fn payload ->
        Absinthe.Subscription.publish(
          ChatF1Web.Endpoint,
          payload,
          agent_stream: "agent:#{message_id}"
        )
      end)
    end)
  end

  defp unwrap_payload(%{token_delta: event}), do: event
  defp unwrap_payload(%{node_transition: event}), do: event
  defp unwrap_payload(%{sources_resolved: event}), do: event
  defp unwrap_payload(%{message_completed: event}), do: event
  defp unwrap_payload(%{agent_error: event}), do: event
  defp unwrap_payload(other), do: other
end
