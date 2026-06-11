# GraphQL API Tour

The gateway owns the entire public surface: queries, mutations, and
subscriptions, served by Absinthe at `/graphql` with GraphiQL mounted at
`/graphiql` (public in every environment, rate-limited like any other
client). The generated SDL lives at [`web/schema.graphql`](../web/schema.graphql)
— regenerate it with `make codegen-web`; web CI fails on drift.

Every operation below is copy-pasteable into GraphiQL
(`http://localhost:4000/graphiql` locally).

## Identity and limits

- **Viewer identity** is an anonymous signed `Phoenix.Token`. The
  `ChatF1Web.Plugs.ViewerToken` plug mints one per client; conversations
  are scoped to it (`WHERE viewer_id = $1` on every query — no global
  enumeration).
- **Rate limiting**: a hand-rolled ETS dual-window token bucket
  (per-minute burst + per-hour), applied as Absinthe middleware on every
  root query and mutation field. Check your own budget:

```graphql
query {
  rateLimitStatus {
    limitPerMinute
    remainingMinute
    limitPerHour
    remainingHour
    resetsAt
  }
}
```

- **Complexity budget: 400**, enforced with `analyze_complexity: true`
  on the Absinthe.Plug forwards. Scalars cost 1; list fields multiply
  their children by expected size (20 drivers, 24 races, 20 results per
  race). The full standings-page query costs 260 and passes; a
  pathological `drivers { results { race { results { … } } } }` nest
  multiplies to ~19,000 and is rejected before execution. Depth is
  bounded by these compounding multipliers, not a separate depth
  analyzer.
- **Input validation**: `sendMessage` content is 1–2000 chars, no
  control characters, no excessive character repetition — enforced in
  changesets before any LLM work.

## F1 structured data (zero LLM cost)

Drivers, constructors, races, results, and standings live in Postgres,
seeded from `data/` and refreshed nightly by the Jolpica/Ergast Oban
job. Associations are Dataloader-batched — the standings query below
issues a constant number of SQL queries regardless of row count, not
one per driver:

```graphql
query Standings {
  standings(season: 2025) {
    position
    points
    wins
    podiums
    driver {
      code
      fullName
      constructor {
        name
      }
    }
  }
}
```

```graphql
query NextRace {
  nextRace {
    name
    circuit
    country
    startsAt
  }
}
```

## Conversations and streaming

The chat flow is a three-step contract:

### 1. Start a conversation

```graphql
mutation {
  startConversation {
    id
    insertedAt
  }
}
```

### 2. Send a message — returns in <50 ms, no LLM work

```graphql
mutation Send($conversationId: ID!) {
  sendMessage(conversationId: $conversationId, content: "Who won the last race?") {
    userMessage {
      id
      content
    }
    assistantMessageId
  }
}
```

The resolver persists the user message and an assistant placeholder
(status `PENDING`) in one `Ecto.Multi`, kicks off the stream in a
supervised process, and returns. The answer arrives on the
subscription.

### 3. Subscribe to the stream

Subscriptions ride the standard `graphql-ws` sub-protocol
(`absinthe_graphql_ws`), so Apollo's stock `GraphQLWsLink` works. The
`connection_init` payload must carry the viewer token. The payload type
is the **`AgentEvent` union** — the schema's centerpiece:

```graphql
subscription AgentStream($messageId: ID!) {
  agentStream(messageId: $messageId) {
    __typename
    ... on TokenDelta {
      seq
      text
    }
    ... on NodeTransition {
      node
      startedAt
    }
    ... on SourcesResolved {
      sources {
        kind
        title
        url
        score
      }
    }
    ... on MessageCompleted {
      cached
      message {
        content
        latencyMs
      }
      usage {
        promptTokens
        completionTokens
        estimatedCostUsd
      }
    }
    ... on AgentError {
      code
      errorMessage: message
      retryable
    }
  }
}
```

What each member means:

| Member | Meaning |
|---|---|
| `TokenDelta` | One or more LLM tokens. Micro-batched by the gateway (40 ms / 12 tokens per publish). `seq` increases monotonically per message — clients deduplicate replay/live overlap by seq. |
| `NodeTransition` | A pipeline node started (`ANALYZE_QUERY` … `FORMAT_RESPONSE`, plus gateway-synthesized `WARMING_UP` and `REPLAYING_CACHE`). Drives the UI telemetry strip. |
| `SourcesResolved` | Retrieval finished — citation chips render before the answer completes. |
| `MessageCompleted` | Final state, including the hydrated `Message` for direct Apollo cache writes, the `cached` flag, and token usage. |
| `AgentError` | Normalized stream failure with an `ErrorCode` and a `retryable` hint. |

Notes that matter:

- **Authorization happens at subscribe time**: the viewer token must own
  the message's conversation, enforced in the subscription `config/2`
  callback — cross-viewer subscriptions are rejected before any event
  flows.
- **Reconnects replay**: the per-conversation GenServer keeps a
  seq-numbered buffer (32 KB cap per message). Re-subscribing clients
  receive buffered events before live ones; duplicates are dropped by
  the seq guard client-side.
- **`AgentError.message` vs `MessageCompleted.message`**: same field
  name, different types (`String!` vs `Message!`) — alias one of them in
  any document selecting both, as above.

### Health, ops, and SHOWCASE

```graphql
query {
  systemHealth {
    mode          # LIVE | DEGRADED | SHOWCASE
    agentService  # HEALTHY | DEGRADED | DOWN
    breakerState  # CLOSED | OPEN | HALF_OPEN
  }
  systemStats {
    activeConversations
    beamProcessCount
    p95FirstTokenMs    # null until at least one stream has completed
    tokensPerSecond
    llmSpendTodayUsd
    dailyBudgetRemainingUsd
  }
  demoQuestions
}
```

- `systemStats` is **telemetry-fed only**: nullable fields are null
  until real traffic produces data. Nothing is invented.
- `mode: SHOWCASE` means the daily LLM budget is spent or the breaker is
  open; answers to `demoQuestions` (and trigram-nearest matches) are
  token-replayed from cache through the identical publish path, with
  `NodeTransition { node: REPLAYING_CACHE }` and `cached: true` making
  the replay explicit.
- Breaker transitions push in real time:

```graphql
subscription {
  systemHealthChanged {
    mode
    breakerState
  }
}
```

## Errors

All errors normalize to `{code, message}` via the `ErrorHandler`
middleware. The `ErrorCode` enum:

| Code | Produced by | Meaning |
|---|---|---|
| `UPSTREAM_UNAVAILABLE` | gateway | Agent unreachable / breaker open |
| `RATE_LIMITED` | gateway | Token bucket exhausted; a `retry_after` extension says when to retry |
| `BUDGET_EXHAUSTED` | gateway | Daily LLM budget spent, no cached match |
| `VALIDATION` | gateway or agent | Input failed validation or the prompt-injection guard |
| `INTERNAL` | either | Unexpected failure mid-pipeline |

The agent's own NDJSON error vocabulary is narrower (`validation`,
`internal`); the transport-level codes are gateway-produced. See
[STREAMING_PROTOCOL.md](STREAMING_PROTOCOL.md) for that boundary.

## Admin surface

`triggerIngest(source: NEWS | HISTORICAL | CALENDAR)` enqueues an Oban
ingest job and requires an API key with scope `admin:ingest`
(`x-api-key` header; keys are `f1s_`-prefixed, SHA-256 at rest).
LiveDashboard (`/dev/dashboard`) and Prometheus metrics (`/metrics`)
sit behind the `admin:dashboard` scope.
