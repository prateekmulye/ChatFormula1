# 🏎️ ChatFormula1

An AI-powered Formula 1 chatbot built on a RAG (Retrieval-Augmented
Generation) pipeline: LangGraph orchestration, Pinecone semantic search,
and Tavily real-time web search.

> **v2 conversion in progress.** The repo is being rebuilt as a
> three-app monorepo: an Elixir/Phoenix GraphQL gateway, a slimmed
> Python LangGraph inference engine, and a React/Apollo frontend.
> Phase 1 (the Python agent + monorepo skeleton) is complete; the
> blueprint lives in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and
> the build plan in [docs/ROADMAP.md](docs/ROADMAP.md).

> ChatFormula1 is an unofficial fan project. It is not affiliated with,
> endorsed by, or connected to Formula 1, the FIA, or any F1 team.

---

## 📖 What It Does

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

## 🛠️ Tech Stack

### Agent (implemented — Phase 1)
- **[Python 3.12](https://www.python.org/)** + **[FastAPI](https://fastapi.tiangolo.com/)** — internal-only NDJSON streaming API
- **[LangGraph](https://langchain-ai.github.io/langgraph/)** / **[LangChain](https://python.langchain.com/)** — pipeline orchestration (exact-pinned)
- **[OpenAI gpt-4o-mini](https://platform.openai.com/)** — generation and analysis, behind a provider seam
- **[Pinecone](https://www.pinecone.io/)** — vector search (`static_corpus` / `news` namespaces, deterministic SHA-256 IDs)
- **[Tavily](https://tavily.com/)** — real-time web search via `langchain-tavily`

### Coming next (see [docs/ROADMAP.md](docs/ROADMAP.md))
- **Gateway** (Phase 2-3): Elixir 1.18, Phoenix, Absinthe GraphQL, Oban — the only public backend
- **Web** (Phase 4): React 18, TypeScript, Vite, Apollo Client

---

## 🏗️ Architecture

```
React (web/)  ──GraphQL──▶  Phoenix gateway (gateway/)  ──NDJSON──▶  LangGraph agent (agent/)
   Phase 4                       Phase 2-3                              Phase 1 ✓
```

The agent pipeline: `analyze_query → route → (vector | web | parallel
retrieval) → rank_context → generate → format_response`, compiled once at
startup and streamed as typed NDJSON events — the frozen contract in
[docs/STREAMING_PROTOCOL.md](docs/STREAMING_PROTOCOL.md).

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12 and [Poetry](https://python-poetry.org/docs/#installation)
- Docker (for the local Postgres + agent containers)
- API keys (all have free tiers): [OpenAI](https://platform.openai.com/api-keys), [Pinecone](https://app.pinecone.io/), [Tavily](https://app.tavily.com/)

### Local development

```bash
git clone https://github.com/prateekmulye/ChatFormula1.git
cd ChatFormula1

# Install (agent only in Phase 1)
make setup

# Configure
cp agent/.env.example agent/.env   # add your API keys + INTERNAL_API_TOKEN

# Run the agent natively...
cd agent && poetry run uvicorn chatf1_agent.server:app --reload

# ...or run postgres + agent via Docker
make dev
```

Stream an answer:

```bash
curl -N -X POST http://localhost:8000/internal/chat \
  -H "Authorization: Bearer $INTERNAL_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "Who won the last race?", "history": [], "request_id": "demo-1"}'
```

### Tests and linting

```bash
make test   # pytest — runs with dummy keys, no credentials needed
make lint   # ruff + black + mypy
```

---

## 📁 Project Structure

```
chatformula1/
├── agent/                    # Python LangGraph inference service (Phase 1 ✓)
│   ├── src/chatf1_agent/    # graph, state, providers, retrieval, guards, server
│   ├── ingestion/           # offline ingestion CLI (deterministic SHA-256 IDs)
│   └── tests/               # incl. NDJSON streaming contract tests
├── gateway/                  # Phoenix GraphQL gateway (Phase 2 — placeholder)
├── web/                      # React frontend (Phase 4 — placeholder)
├── data/                     # F1 datasets (gateway seeds + agent RAG input)
├── docs/                     # ARCHITECTURE, ROADMAP, STREAMING_PROTOCOL, ...
├── Makefile                  # make setup / dev / test / lint — fans out per app
└── docker-compose.yml        # postgres:16 + agent for local dev
```

---

## 📚 Documentation

- **[Architecture](docs/ARCHITECTURE.md)** — the v2 blueprint: services, schema, streaming design
- **[Roadmap](docs/ROADMAP.md)** — six phases, each demoable in 5 minutes
- **[Streaming Protocol](docs/STREAMING_PROTOCOL.md)** — the frozen agent↔gateway NDJSON contract
- **[Agent README](agent/README.md)** — running, testing, and ingesting
- **[Tavily Integration](docs/TAVILY_INTEGRATION.md)** — web search client details
- **[Secrets Management](docs/SECRETS_MANAGEMENT.md)** — credential handling
- **[Contributing](docs/CONTRIBUTING.md)** — guidelines and workflow

---

## 🔒 Security

- The agent is **internal-only**: every route requires a static bearer
  token (constant-time compared); the public surface arrives with the
  Phase 2 gateway
- Prompt-injection heuristics guard the LLM boundary
- API keys live in environment variables, never in the repo
- CI runs with dummy keys only — real secrets never touch test runs

---

## 💰 Cost

Designed for $0/month fixed: free tiers of Render, Pinecone, and Tavily,
with gpt-4o-mini as the only variable cost (capped and budgeted — see
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) §7).

---

## 🤝 Contributing

Contributions are welcome — see [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

## 📄 License

MIT — see [LICENSE](LICENSE).

## 📞 Contact

- **GitHub**: [Current Projects 🧠 🚧](https://github.com/prateekmulye)
- **LinkedIn**: [Say Hi! 🤝](https://www.linkedin.com/in/prateekmulye/)
- **Email**: prateek@chatformula1.com

---

**Built with ❤️ for Formula 1 fans and AI enthusiasts**
