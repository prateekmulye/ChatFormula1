# ADR-002: Model-agnostic providers (OpenAI + Ollama first-class)

- **Status:** Accepted
- **Date:** 2026-06-10
- **Owner direction:** "go Ollama, and make the whole app model-agnostic."

## Context

The agent was OpenAI-only: `ChatOpenAI` and `OpenAIEmbeddings` were
constructed with implicit OpenAI assumptions (endpoint, function calling,
1536-dim embeddings) in two different modules. That coupling had three
costs:

1. **Vendor lock-in** — no way to run the app on local or self-hosted
   models, and no negotiating position on inference cost.
2. **Hidden capability assumptions** — the query-analysis step used
   `with_structured_output`, which compiles to OpenAI function calling.
   Most local models don't implement tool calling reliably; the failure
   mode is silent garbage, not an error.
3. **A buried embedding constant** — the Pinecone index dimension (1536)
   was an OpenAI fact pretending to be an application fact. Switching
   embedding models without realizing this corrupts retrieval quietly:
   queries embed in one space, documents in another.

Meanwhile, the local-model ecosystem converged on a de facto standard:
Ollama, vLLM, LM Studio, and OpenRouter all serve the **OpenAI wire
protocol** (Ollama at `/v1`, Ollama Cloud at `https://ollama.com/v1`).

## Decision

### 1. One factory, one wire protocol

All model construction goes through `agent/src/chatf1_agent/providers.py`:
`create_generation_llm`, `create_analysis_llm`, `create_embeddings`. The
factory always builds `langchain-openai` clients (exact-pinned at 1.1.0)
and varies only `base_url`, `api_key`, and capability flags from settings:

- `llm_provider`: `openai` | `ollama` | `openai_compatible`
- `llm_base_url`: `None` → provider default (OpenAI's API, or
  `http://localhost:11434/v1` for Ollama); **required** for
  `openai_compatible` because there is no endpoint to guess
- Ollama gets a dummy `api_key` (`"ollama"`) when none is set — the
  OpenAI client library demands one, local servers ignore it

We deliberately did **not** add `langchain-ollama` (a second dependency
and code path when `/v1` suffices), a LiteLLM proxy (extra infra for a
single service), or a provider plugin registry (YAGNI — the protocol is
the abstraction).

The factory is also where the streaming contract is enforced: only the
generation model carries the `["generation"]` tag that the NDJSON server
filters on. Constructing a model outside the factory would bypass that.

### 2. Capabilities are configuration: the JSON fallback

`llm_supports_function_calling` (default: true for `openai`, false
otherwise) tells the graph which structured-output strategy to use:

- **true** — unchanged `with_structured_output` (function calling).
- **false** — prompt-and-parse: the analysis prompt embeds the
  `QueryAnalysis` JSON Schema and demands a bare JSON object, parsed with
  Pydantic `model_validate_json`. One repair retry with the validation
  error appended; if that fails too, a safe default routes retrieval to
  **both** sources rather than failing the user's turn.

We chose prompt-and-parse over the OpenAI `response_format=json_object`
flag because support for it varies across compatible servers; a prompt
plus a strict parser works everywhere. Both paths keep the analysis model
untagged, so analysis output can never leak into the user-visible token
stream — the frozen NDJSON contract tests pass unchanged.

### 3. The embedding dimension travels with the provider

`embedding_provider` / `embedding_model` / `embedding_dimension` are
independent of the chat settings (chat on Ollama Cloud + embeddings on
OpenAI is a supported, sensible split). The rules:

- `embedding_dimension` is implied (1536) **only** for OpenAI's
  `text-embedding-3-small`. For every other provider it MUST be explicit
  (`nomic-embed-text` = 768, `mxbai-embed-large` = 1024) — construction
  fails otherwise.
- The vector store validates the **live** Pinecone index dimension
  against settings at startup and fails loudly with the remediation:
  delete + recreate via `make reindex`, **then** re-ingest. Today the
  index is empty, so a provider switch is free; after launch it costs a
  full re-ingestion, which is exactly why the check is loud.

## Why Ollama

- **Local:** zero API cost, no data egress, offline dev, and the test of
  honesty for "model-agnostic" claims — if it runs on a laptop model, the
  seam is real. Tradeoffs: cold model loads (seconds to tens of seconds
  on first request), small models analyze queries less reliably (hence
  the JSON fallback's safe default), and embedding quality below
  `text-embedding-3-small` for retrieval.
- **Cloud:** big open models (e.g. `gpt-oss:120b`) without local VRAM,
  same wire protocol, just `LLM_BASE_URL=https://ollama.com/v1` plus an
  API key. Tradeoffs: free-tier rate/usage limits, chat-only catalog (run
  embeddings locally or keep OpenAI), and another vendor — agnostic, not
  vendor-free.

## Consequences

- Switching providers is a 4-line env change (see `agent/README.md`);
  no code changes, and the streaming contract is provider-invariant.
- Changing the **embedding** provider/model is never just env: it
  requires `make reindex` + re-ingest, and the system enforces that
  instead of degrading silently.
- The test suite still runs with zero real keys; the factory matrix,
  JSON fallback, and dimension validation are all covered offline.
- We own a small JSON-repair loop instead of depending on every
  provider's structured-output implementation.
