# ADR-003: NDJSON over chunked HTTP, not SSE

- **Status:** Accepted
- **Date:** 2026-06-10

## Context

The agent must stream typed events (node transitions, sources, tokens,
completion) to the gateway. Candidate transports: Server-Sent Events,
WebSockets, gRPC streaming, or newline-delimited JSON over a chunked
HTTP response.

The deciding observation: **the consumer is one trusted backend, not a
browser.** The gateway reads the stream with a Req/Finch `into:`
reducer; browsers never touch this interface (they get GraphQL
subscriptions from the gateway instead).

## Decision

`POST /internal/chat` returns `application/x-ndjson`: one JSON object
per line, UTF-8, `\n`-terminated. The protocol is **frozen** in
[STREAMING_PROTOCOL.md](../STREAMING_PROTOCOL.md) and enforced by
contract tests on both sides — pytest asserts the exact event sequence;
the gateway replays a recorded stream against its parser via Bypass.

Why not the alternatives:

- **SSE** earns its keep through browser `EventSource` semantics —
  auto-reconnect, `Last-Event-ID`, `retry:` — none of which a
  server-side consumer uses. It adds framing (`event:`/`data:` prefixes,
  blank-line separators) on top of the JSON we'd send anyway. Reconnect
  semantics live in the gateway's replay buffer, where they are needed
  for *browsers*.
- **WebSockets** are bidirectional; this interface is strictly
  request→stream. A socket lifecycle to manage with zero benefit.
- **gRPC** brings codegen, HTTP/2 infrastructure, and a schema
  toolchain to a two-party interface that changes rarely and is owned
  by one person.

NDJSON is also the most testable option: recorded streams are plain
text files, replayable byte-for-byte, and a human can read a capture or
produce one with `curl -N`.

## Consequences

- Line-buffering is the gateway's job (Finch chunks don't respect line
  boundaries) — implemented once in the StreamRunner, covered by
  contract tests.
- The HTTP status is only meaningful before the first byte; failures
  after that are in-band `error` events. Explicit in the protocol.
- LangChain/LangGraph version churn is contained: upstream changes that
  alter event shapes fail loudly in CI on both sides (ROADMAP risk #7),
  not silently in the gateway stream.
- Protocol changes are breaking changes by definition — bump
  deliberately, never drift.
