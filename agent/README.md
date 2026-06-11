# ChatFormula1 Agent

Stateless LangGraph inference engine for ChatFormula1 v2. Internal-only:
the [Phoenix gateway](../gateway/README.md) is the sole public backend and
the only intended caller. See [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)
for the full system design.

## What it does

`POST /internal/chat` runs a routed RAG pipeline compiled once at startup:

```
analyze_query → route → (vector_search | tavily_search | parallel_retrieval)
              → rank_context → generate → format_response
```

- **Query analysis** — intent + entity extraction at temperature 0, via
  function-calling structured output or a prompted-JSON fallback depending
  on the provider (see [Model providers](#model-providers))
- **Retrieval** — Pinecone semantic search (`f1-knowledge` index, namespaces
  `static_corpus` / `news`) and/or Tavily web search, in parallel when both
  are needed
- **Ranking** — multi-factor scoring (relevance 40%, recency 30%,
  authority 20%, completeness 10%)
- **Generation** — the configured chat model (default gpt-4o-mini) tagged
  `generation`; only its tokens are forwarded on the stream

Responses stream as NDJSON events — the frozen contract between this service
and the gateway, documented in
[docs/STREAMING_PROTOCOL.md](../docs/STREAMING_PROTOCOL.md) and enforced by
contract tests (`tests/test_streaming_contract.py`).

## Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /internal/chat` | NDJSON streaming chat. Body: `{message, history, request_id}`. Stateless — history arrives in the payload. |
| `POST /internal/ingest` | Trigger an ingestion run (`{"source": "static"}` or `{"source": "news"}`). |
| `GET /internal/health` | Liveness probe; doubles as the cold-start pre-warm target. |

## Model providers

The agent is model-agnostic: both chat models and the embedding client are
built exclusively by the provider factory
(`src/chatf1_agent/providers.py`), which speaks the OpenAI wire protocol to
OpenAI, Ollama (local or cloud), and any other OpenAI-compatible server
(vLLM, LM Studio, OpenRouter). Full reasoning:
[ADR-002](../docs/adr/002-model-agnostic-providers.md).

OpenAI is the default. Switching to local Ollama is four lines of env:

```bash
LLM_PROVIDER=ollama              # endpoint defaults to http://localhost:11434/v1
LLM_MODEL=qwen3:8b
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_DIMENSION=768          # the index dimension travels with the model
```

> **⚠️ Changing the embedding provider/model changes the vector space.**
> Vectors from different models are not interchangeable, so the Pinecone
> index must be rebuilt: `make reindex` (delete + recreate, destroys all
> vectors), **then** `make ingest`. The agent validates the live index
> dimension at startup and refuses to run against a mismatch. Always
> reindex *before* re-ingesting — never after.

Ollama Cloud serves big open models over the same protocol — set
`LLM_BASE_URL=https://ollama.com/v1` and `LLM_API_KEY` (see
`.env.example`, provider block 3). Honest tradeoffs:

| | OpenAI | Ollama local | Ollama Cloud |
|---|---|---|---|
| Cost | per-token | free (your hardware) | free tier with rate/usage limits, then paid |
| Latency | consistent | cold model loads on first request (seconds-tens of seconds) | shared infra; cold loads possible |
| Function calling | reliable | model-dependent, often unreliable → JSON fallback | model-dependent |
| Embeddings | text-embedding-3-small (1536) | nomic-embed-text 768 / mxbai-embed-large 1024 | chat-only catalog — run embeddings locally or keep OpenAI (`EMBEDDING_PROVIDER=openai`) |

**Structured output**: `llm_supports_function_calling` (default true only
for `openai`) selects the analysis strategy. When false, the analysis
prompt embeds the `QueryAnalysis` JSON Schema and the reply is parsed with
Pydantic — one repair retry with the validation error appended, then a
safe default that retrieves from both sources. Either way the analysis
model is untagged, so its output never reaches the NDJSON token stream.

Check the effective configuration any time:

```bash
poetry run f1-ingest --data-dir ../data check-config
```

## Security

- **Static bearer auth on every route** — set `INTERNAL_API_TOKEN` to a long
  random value shared with the gateway; comparison is constant-time. The
  service must never be exposed publicly.
- **Prompt-injection guards** (`chatf1_agent/guards.py`) scan messages at the
  LLM boundary; flagged input gets a `validation` error event, no LLM call.
  Transport-level validation (length caps, sanitization, rate limiting) is
  the gateway's job.
- **Secrets** come exclusively from environment variables / `.env` (never
  committed); CI runs with dummy keys only.

## Development

```bash
cd agent
poetry install
cp .env.example .env        # add real keys

poetry run uvicorn chatf1_agent.server:app --reload   # run the service
poetry run pytest                                      # tests (no API keys needed)
poetry run ruff check src ingestion tests              # lint
poetry run mypy src ingestion                          # types
```

Try a stream:

```bash
curl -N -X POST http://localhost:8000/internal/chat \
  -H "Authorization: Bearer $INTERNAL_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Who won the last race?", "history": [], "request_id": "demo-1"}'
```

Integration tests that need real keys are marked `integration` and skip
automatically when only dummy keys are present.

## Ingestion

Offline pipeline (`ingestion/`) loads `data/` CSV/JSON sources, chunks and
enriches them, and upserts to Pinecone with **deterministic SHA-256
content-hash vector IDs** — re-ingestion upserts instead of duplicating, so
the index is rebuildable from scratch. Dedup state persists in
`data/.dedup_state.json`.

```bash
poetry run f1-ingest --data-dir ../data ingest-all
poetry run f1-ingest --data-dir ../data check-config
```

## Caching

In-process TTL caches (`chatf1_agent/caching.py`) cover the inference path:
vector search (5 min), Tavily search (15 min), and LLM responses (1 h).
An LLM cache hit emits zero `token` events and a single `complete` with
`cached: true` — explicit in the streaming contract. Single-replica by
design (see ADR-000 in the roadmap).
