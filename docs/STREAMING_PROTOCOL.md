# NDJSON Streaming Protocol

**The frozen interface between `agent/` and `gateway/`.** Both sides pin
contract tests against this document: the agent asserts exact event
sequences (`agent/tests/test_streaming_contract.py`), and the Phase 3
gateway replays a recorded stream against its parser via Bypass. Changes
here are breaking changes — bump deliberately, never drift.

## Transport

```
POST /internal/chat
Authorization: Bearer <INTERNAL_API_TOKEN>
Content-Type: application/json
```

The response is a chunked `application/x-ndjson` stream: **one JSON object
per line**, UTF-8, `\n` terminated. The HTTP status is `200` once the
stream opens; failures after that point are reported in-band via the
`error` event.

HTTP-level failures (before any event):

| Status | Meaning |
|---|---|
| `401` | Missing or invalid bearer token |
| `422` | Malformed request body |
| `503` | `INTERNAL_API_TOKEN` not configured on the agent (fails closed) |

## Request body

```json
{
  "message": "Who won the last race?",
  "history": [
    {"role": "user", "content": "Hi"},
    {"role": "assistant", "content": "Hello! Ask me about F1."}
  ],
  "request_id": "9f4c1c2e-demo"
}
```

- `message` — the current user message (required, non-empty).
- `history` — prior turns, **oldest first**. The agent is fully stateless;
  the gateway owns the conversation and sends a last-10-messages window.
- `request_id` — correlation ID; echoed into the agent's structured logs.

## Events

| Event | Shape | Emitted |
|---|---|---|
| `node_started` | `{"event":"node_started","node":"<name>"}` | When a pipeline node begins (drives the UI telemetry strip) |
| `sources` | `{"event":"sources","items":[Source,...]}` | Once, after context ranking — **before** any token |
| `token` | `{"event":"token","text":"<chunk>"}` | Per generation-LLM chunk; only the `generation`-tagged model streams (analysis JSON never leaks) |
| `complete` | `{"event":"complete","content":"<full text>","cached":bool,"usage":Usage\|null}` | Exactly once, last event of a successful stream |
| `error` | `{"event":"error","code":"<code>","message":"<text>","retryable":bool}` | Exactly once, terminating a failed stream |

**Source** items:

```json
{"kind": "vector" | "web", "title": "...", "url": "https://..." | null,
 "snippet": "...", "score": 0.852}
```

**Usage** (`null` when the provider reports none, e.g. cache hits):

```json
{"prompt_tokens": 1024, "completion_tokens": 96, "total_tokens": 1120}
```

**`node` values** (gateway maps these to the `AgentNode` GraphQL enum):
`analyze_query`, `route`, `vector_search`, `tavily_search`,
`parallel_retrieval`, `rank_context`, `generate`, `format_response`.
Which retrieval nodes appear depends on routing: `parallel_retrieval`
(both sources), `vector_search` or `tavily_search` (one source), or none
(off-topic / direct generation).

## Ordering guarantees

1. The first event is always `node_started` for `analyze_query` (unless
   the guard rejects the input — see error semantics).
2. `sources` is emitted at most once, after `rank_context` and **before
   the first `token`** — citation chips can render before the answer.
3. All `token` events occur between `node_started:generate` and
   `node_started:format_response`, in generation order; concatenating
   their `text` fields reproduces `complete.content` exactly (when no
   degradation warning was prepended by `format_response`).
4. The final event is exactly one `complete` **or** one `error` — never
   both, never neither.

## Cache-hit semantics

An LLM-cache hit **legally emits zero `token` events** and a single
`complete` with `"cached": true`. This is explicit in the contract, not a
client surprise: the gateway synthesizes one full-text delta for the
frontend so the render path stays uniform. Node lifecycle events still
stream normally (the pipeline ran; only generation was skipped).

## Error codes

| Code | Retryable | Meaning |
|---|---|---|
| `validation` | `false` | Input rejected by the prompt-injection guard; no LLM call was made. Emitted as the **only** event on the stream. |
| `internal` | `true` | The pipeline failed mid-stream (provider outage, infrastructure error). Any events already emitted are valid but the message is incomplete. |

The gateway maps these onto its `ErrorCode` GraphQL enum (`VALIDATION`,
`INTERNAL`); transport-level codes like `UPSTREAM_UNAVAILABLE`,
`RATE_LIMITED`, and `BUDGET_EXHAUSTED` are produced by the gateway itself
and never appear on this stream.

Retrieval failures are **not** stream errors: the pipeline degrades
gracefully (empty retrieval, a human-readable warning prepended to
`complete.content`) and the stream finishes normally.

## Example stream (captured)

Captured from the contract-test pipeline (real LangGraph execution,
faked LLM/retrieval; the token run is elided for brevity):

```
{"event":"node_started","node":"analyze_query"}
{"event":"node_started","node":"route"}
{"event":"node_started","node":"parallel_retrieval"}
{"event":"node_started","node":"rank_context"}
{"event":"sources","items":[{"kind":"vector","title":"2026 Monaco Grand Prix","url":null,"snippet":"Max Verstappen won the 2026 Monaco Grand Prix from pole, leading every lap.","score":0.69},{"kind":"web","title":"Monaco GP 2026 race report","url":"https://www.formula1.com/en/latest/article/monaco-2026-race-report","snippet":"Verstappen converted pole into a lights-to-flag win at Monaco on Sunday.","score":0.852}]}
{"event":"node_started","node":"generate"}
{"event":"token","text":"Max"}
{"event":"token","text":" "}
{"event":"token","text":"Verstappen"}
{"event":"token","text":" "}
{"event":"token","text":"won"}
... 27 more token events ...
{"event":"token","text":"flag."}
{"event":"node_started","node":"format_response"}
{"event":"complete","content":"Max Verstappen won the most recent race, the 2026 Monaco Grand Prix, leading from pole to flag.","cached":false,"usage":null}
```

The same request repeated within the LLM-cache TTL (1 h):

```
{"event":"node_started","node":"analyze_query"}
{"event":"node_started","node":"route"}
{"event":"node_started","node":"parallel_retrieval"}
{"event":"node_started","node":"rank_context"}
{"event":"sources","items":[...]}
{"event":"node_started","node":"generate"}
{"event":"node_started","node":"format_response"}
{"event":"complete","content":"Max Verstappen won the most recent race, the 2026 Monaco Grand Prix, leading from pole to flag.","cached":true,"usage":null}
```

A guard rejection:

```
{"event":"error","code":"validation","message":"Message rejected by prompt-injection guard.","retryable":false}
```
