defmodule ChatF1Web.Schema.Types.AgentTypes do
  @moduledoc """
  Absinthe type definitions for the Phase 3 streaming protocol.

  ## AgentEvent union

  The `agentStream` subscription delivers a union of five event types, each
  carrying a `messageId` for client-side routing:

  | Type              | When                                                  |
  |-------------------|-------------------------------------------------------|
  | `TokenDelta`      | Batched token text (40 ms / 12 tokens micro-batch)    |
  | `NodeTransition`  | LangGraph pipeline node started (drives telemetry strip) |
  | `SourcesResolved` | RAG retrieval completed; cite chips can render early  |
  | `MessageCompleted`| Stream finished; final message + usage stats          |
  | `AgentError`      | Recoverable or terminal error with `ErrorCode`        |

  `WARMING_UP` is a gateway-synthesized `AgentNode` (not from the agent)
  emitted when the Render cold-start is detected (connection refused on
  first attempt).  The UI renders this as pit-radio chatter rather than a
  dead spinner — see `ChatF1.Conversations.StreamRunner` for the retry logic.

  ## SystemHealth / BreakerState

  Returned by the `systemHealth` query and pushed via `systemHealthChanged`
  subscription.  Phase 3 returns `LIVE` or `DEGRADED` for `mode` only.
  The `SHOWCASE` enum value exists so the SDL is final but is never set
  until Phase 5's budget-ledger and cached-answer replay are implemented.

  ## Why union over interface?

  Absinthe unions let each concrete type carry a completely different field
  set.  `TokenDelta` is tiny (seq + text); `MessageCompleted` carries the
  full hydrated `Message` and `TokenUsage`.  A single interface would bloat
  every event delivery with null fields — wasteful at the 40 ms cadence of
  a token stream on a 256 MB machine.
  """

  use Absinthe.Schema.Notation

  # ─── AgentNode enum ─────────────────────────────────────────────────────────

  @desc "LangGraph pipeline node or gateway-synthesized state transition."
  enum :agent_node do
    @desc "Gateway-synthesized: Render agent is cold-starting (designed UX, not an error)."
    value(:warming_up)

    @desc "LangGraph: analysing the query intent and routing decision."
    value(:analyze_query)

    @desc "LangGraph: routing between retrieval strategies."
    value(:route)

    @desc "LangGraph: Pinecone vector similarity search."
    value(:vector_search)

    @desc "LangGraph: Tavily web search."
    value(:web_search)

    @desc "LangGraph: both vector and web retrieval running concurrently."
    value(:parallel_retrieval)

    @desc "LangGraph: ContextScore multi-factor re-ranking of retrieved chunks."
    value(:rank_context)

    @desc "LangGraph: LLM generation (gpt-4o-mini)."
    value(:generate)

    @desc "LangGraph: formatting and safety check on the generated response."
    value(:format_response)

    @desc "SHOWCASE mode: token-replaying a cached answer (Phase 5 only)."
    value(:replaying_cache)
  end

  # ─── TokenUsage ─────────────────────────────────────────────────────────────

  @desc "Token-level usage statistics from the LLM provider."
  object :token_usage do
    field :prompt_tokens, non_null(:integer)
    field :completion_tokens, non_null(:integer)
    field :estimated_cost_usd, non_null(:float)
  end

  # ─── AgentEvent union members ────────────────────────────────────────────────

  @desc """
  One or more LLM tokens.  Delivery is micro-batched: the Conversation.Server
  accumulates tokens for 40 ms or 12 tokens (whichever comes first) before a
  single publish.  This amortises Absinthe.Subscription.publish overhead and
  PubSub frame cost on the 256 MB Fly machine.

  `seq` is a monotonically increasing integer scoped to the assistant message.
  Clients use it for idempotent-replay deduplication — on reconnect, replay
  from the Conversation.Server buffer overlaps with live events; duplicates
  are dropped by the seq guard in the Apollo reducer.
  """
  object :token_delta do
    field :message_id, non_null(:id)
    field :seq, non_null(:integer)
    field :text, non_null(:string)
  end

  @desc "A LangGraph pipeline node has started executing."
  object :node_transition do
    field :message_id, non_null(:id)
    field :node, non_null(:agent_node)
    field :started_at, non_null(:datetime)
  end

  @desc "Retrieval context has been resolved; citation chips can render before the answer finishes."
  object :sources_resolved do
    field :message_id, non_null(:id)
    field :sources, non_null(list_of(non_null(:source)))
  end

  @desc """
  The assistant message is complete.  The hydrated `message` is included so
  Apollo can write it directly to the normalized cache — no follow-up query
  needed.  On cache-hit paths the gateway synthesizes one TokenDelta before
  this event so the frontend render path is uniform.
  """
  object :message_completed do
    field :message_id, non_null(:id)
    field :message, non_null(:message)
    field :cached, non_null(:boolean)
    field :usage, :token_usage
  end

  @desc "Stream-level error.  `retryable: true` means the client may call sendMessage again."
  object :agent_error do
    field :message_id, non_null(:id)
    field :code, non_null(:error_code)
    field :message, non_null(:string)
    field :retryable, non_null(:boolean)
  end

  # ─── AgentEvent union ───────────────────────────────────────────────────────

  @desc """
  Union of all event types published on the `agentStream` subscription.
  Apollo resolves the concrete type via `__typename` (returned automatically
  by Absinthe).
  """
  union :agent_event do
    types([:token_delta, :node_transition, :sources_resolved, :message_completed, :agent_error])

    # Order matters: AgentError carries a :message key too (the error text),
    # so its distinctive {:code, :retryable} pair must match BEFORE the
    # %{message: _} clause — otherwise every error resolves as
    # MessageCompleted (found in Phase 4 browser integration).
    resolve_type(fn
      %{text: _}, _ -> :token_delta
      %{node: _}, _ -> :node_transition
      %{sources: _}, _ -> :sources_resolved
      %{code: _, retryable: _}, _ -> :agent_error
      %{message: _}, _ -> :message_completed
    end)
  end

  # ─── SystemHealth types ──────────────────────────────────────────────────────

  @desc "High-level service operating mode."
  enum :service_mode do
    @desc "Live LLM inference running normally."
    value(:live)

    @desc "Circuit breaker open or partial degradation; service still operational."
    value(:degraded)

    @desc "Budget exhausted or agent down; Phase 5 cached-replay path active."
    value(:showcase)
  end

  @desc "Health of an individual service component."
  enum :service_status do
    value(:healthy)
    value(:degraded)
    value(:down)
  end

  @desc "Circuit breaker state for the Python agent upstream."
  enum :breaker_state do
    @desc "Normal operation; requests pass through."
    value(:closed)

    @desc "Failures threshold exceeded; requests short-circuit with UPSTREAM_UNAVAILABLE."
    value(:open)

    @desc "Probe request allowed through to test recovery."
    value(:half_open)
  end

  @desc """
  Snapshot of gateway and upstream health.  Published on state transitions
  via the `systemHealthChanged` subscription.
  """
  object :system_health do
    field :mode, non_null(:service_mode)
    field :gateway, non_null(:service_status)
    field :agent_service, non_null(:service_status)
    field :database, non_null(:service_status)
    field :breaker_state, non_null(:breaker_state)
  end
end
