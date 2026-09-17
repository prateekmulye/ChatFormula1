# ChatFormula1

A Formula 1 research application with routed retrieval and streamed answers.
The developing v2 separates Python/LangGraph inference, an Elixir/Phoenix
GraphQL gateway, and a typed React client.

**Current source:** all three applications contain implementations. The agent
routes queries to Pinecone, Tavily, or both; the gateway handles conversations
and streaming; the client reconciles duplicate and replayed events. Source
availability does not establish a deployed v2 release or answer-quality result.
The public v1 demo is separate from this v2 code.

Start with the [architecture](docs/ARCHITECTURE.md),
[streaming contract](docs/STREAMING_PROTOCOL.md), or
[client reducer](web/src/features/chat/stream-reducer.ts).

> ChatFormula1 is an unofficial fan project. It is not affiliated with,
> endorsed by, or connected to Formula 1, the FIA, or any F1 team.

---

## What It Does

ChatFormula1 answers Formula 1 questions through a routed RAG pipeline:

- Current standings, race results, and breaking F1 news (live web search)
- Historical statistics and records (vector search over a curated corpus)
- Technical concepts and regulations explained
- Multi-source answers with ranked, cited context

**Example questions:**
- "Who won the last race?"
- "How many championships has Hamilton won?"
- "Explain DRS in Formula 1"

---

## Tech Stack

### Agent
- **[Python 3.12](https://www.python.org/)** + **[FastAPI](https://fastapi.tiangolo.com/)** — internal-only NDJSON streaming API
- **[LangGraph](https://langchain-ai.github.io/langgraph/)** / **[LangChain](https://python.langchain.com/)** — pipeline orchestration (exact-pinned)
- **Configurable LLM providers** — [OpenAI](https://platform.openai.com/) and [Ollama](https://ollama.com/) configurations are documented in [agent/.env.example](agent/.env.example) and [ADR-002](docs/adr/002-model-agnostic-providers.md).
- **[Pinecone](https://www.pinecone.io/)** — vector search (`static_corpus` / `news` namespaces, deterministic SHA-256 IDs)
- **[Tavily](https://tavily.com/)** — real-time web search via `langchain-tavily`

### Gateway and web client
- **Gateway:** Elixir 1.18, Phoenix 1.8, Absinthe GraphQL, and PostgreSQL — conversation persistence and a streaming boundary around the internal agent
- **Web:** React 18, TypeScript, Vite, Apollo Client, and GraphQL subscriptions

The [stream runner](gateway/lib/chat_f1/conversations/stream_runner.ex) handles
agent transport failures. The [client reducer](web/src/features/chat/stream-reducer.ts)
deduplicates token batches and flags unexplained sequence gaps for recovery from
persisted message content. These mechanisms do not imply exactly-once delivery.

---

## Architecture

```
React (web/)  ──GraphQL──▶  Phoenix gateway (gateway/)  ──NDJSON──▶  LangGraph agent (agent/)
   typed client                 conversations + streams                routed retrieval
```

The agent pipeline: `analyze_query → route → (vector | web | parallel
retrieval) → rank_context → generate → format_response`, compiled once at
startup and streamed as typed NDJSON events — the frozen contract in
[docs/STREAMING_PROTOCOL.md](docs/STREAMING_PROTOCOL.md).

---

## Quick Start

### Prerequisites

- Python 3.12 and [Poetry](https://python-poetry.org/docs/#installation)
- Docker (for the local Postgres + agent containers)
- Provider credentials appropriate to your configuration: [OpenAI](https://platform.openai.com/api-keys) or a compatible LLM endpoint, [Pinecone](https://app.pinecone.io/), and [Tavily](https://app.tavily.com/)
- For the full application: Elixir 1.18, Node.js/npm, and PostgreSQL; see the [gateway](gateway/README.md) and [web](web/README.md) guides

### Local development

```bash
git clone https://github.com/prateekmulye/ChatFormula1.git
cd ChatFormula1

# Install the agent
make setup-agent

# Configure
cp agent/.env.example agent/.env   # add your API keys + INTERNAL_API_TOKEN

# Run the agent natively
(cd agent && poetry run uvicorn chatf1_agent.server:app --reload)
```

Alternatively, run `make dev` from the repository root to start PostgreSQL and
the agent through Docker. Start the gateway and client using their linked guides.

In a second terminal, set `INTERNAL_API_TOKEN` to the same value you configured in
`agent/.env`, then stream an answer:

```bash
curl -N -X POST http://localhost:8000/internal/chat \
  -H "Authorization: Bearer $INTERNAL_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Who won the last race?", "history": [], "request_id": "demo-1"}'
```

### Tests and linting

```bash
make test-agent   # Python tests
make lint-agent   # ruff + black + mypy

# After installing gateway/web dependencies and starting the test database:
make test         # agent + gateway + web
make lint         # all three applications
```

---

## Project Structure

```
chatformula1/
├── agent/                    # Python LangGraph inference service
│   ├── src/chatf1_agent/    # graph, state, providers, retrieval, guards, server
│   ├── ingestion/           # offline ingestion CLI (deterministic SHA-256 IDs)
│   └── tests/               # incl. NDJSON streaming contract tests
├── gateway/                  # Phoenix GraphQL gateway and streaming
├── web/                      # React client and stream reconciliation
├── data/                     # F1 datasets (gateway seeds + agent RAG input)
├── docs/                     # ARCHITECTURE, ROADMAP, STREAMING_PROTOCOL, ...
├── Makefile                  # make setup / dev / test / lint — fans out per app
└── docker-compose.yml        # postgres:16 + agent for local dev
```

---

## Documentation

- **[Architecture](docs/ARCHITECTURE.md)** — the v2 blueprint: services, schema, streaming design
- **[Roadmap](docs/ROADMAP.md)** — implementation phases and remaining work
- **[Streaming Protocol](docs/STREAMING_PROTOCOL.md)** — the frozen agent↔gateway NDJSON contract
- **[Agent README](agent/README.md)** — running, testing, and ingesting
- **[Tavily Integration](docs/TAVILY_INTEGRATION.md)** — web search client details
- **[Secrets Management](docs/SECRETS_MANAGEMENT.md)** — credential handling
- **[Contributing](docs/CONTRIBUTING.md)** — guidelines and workflow

---

## Security

- The agent's internal endpoints require a static bearer token, checked with
  constant-time comparison. The Phoenix gateway is the intended public boundary.
- Prompt-injection heuristics are a defensive layer, not a guarantee that retrieved
  content or model output is trustworthy.
- Configure API keys through environment variables; do not commit credentials.

---

## Cost

Hosting, retrieval, search, and model costs depend on the services and usage you
configure. Review provider quotas and billing before enabling live traffic; no
zero-cost deployment or hard spending guarantee is claimed here.

---

## Contributing

Contributions are welcome — see [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

## License

Apache-2.0 — see [LICENSE](LICENSE).

## Contact

- [Portfolio](https://prateekmulye.dev/)
- [GitHub](https://github.com/prateekmulye)
- [LinkedIn](https://www.linkedin.com/in/prateekmulye/)
