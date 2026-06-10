# Tavily Integration Guide

How the agent uses Tavily web search (via the `langchain-tavily` package)
to retrieve real-time F1 news and information. The client lives at
`agent/src/chatf1_agent/retrieval/tavily.py`.

## Overview

The `TavilyClient` wraps `langchain_tavily.TavilySearch` with:

- **Domain filtering** — trusted F1 sources preferred by default
- **Sliding-window rate limiting** — 60 requests/min by default
- **Retry with exponential backoff** — up to 3 attempts on API errors
- **Graceful degradation** — after 3 consecutive failures the client
  enters a 5-minute fallback mode; `safe_search` returns empty results
  plus a user-facing message instead of raising
- **TTL caching** — identical searches within 15 minutes hit the cache

## Usage

```python
from chatf1_agent.retrieval.tavily import TavilyClient
from chatf1_agent.settings import get_settings

client = TavilyClient(get_settings())

# Search for the latest race information
results = await client.search("Max Verstappen Monaco GP results")

# Never-raises variant used inside the graph
results, error = await client.safe_search("latest F1 news")
if error:
    print(f"Search unavailable: {error}")  # fall back to vector store only

# Latest news helper (used by news ingestion)
news = await client.get_latest_f1_news("driver transfers", max_results=5)

# Convert results to LangChain documents for vector store ingestion
documents = client.convert_to_documents(news)
```

`convert_to_documents` normalizes results (content, URL, title, clamped
score, published date) and deduplicates by URL and content prefix before
producing `Document` objects ready for the `news` Pinecone namespace.

## Configuration

Set in `agent/.env` (see `agent/.env.example`):

```bash
# Required
TAVILY_API_KEY=your_tavily_api_key_here

# Optional
TAVILY_MAX_RESULTS=5            # 1-10 results per search
TAVILY_SEARCH_DEPTH=advanced    # basic (faster) or advanced (more sources)
```

### Trusted F1 domains

The client prefers these sources by default (configurable via
`TAVILY_INCLUDE_DOMAINS` as a comma-separated or JSON list):

- formula1.com (official), fia.com (FIA official)
- autosport.com, motorsport.com, racefans.net, the-race.com
- espn.com/f1, bbc.com/sport/formula1, skysports.com/f1

During context ranking, results from formula1.com, fia.com, and
autosport.com additionally receive an authority boost.

## How it feeds the pipeline

- **Runtime**: the `tavily_search` graph node calls `safe_search`; an
  outage degrades to vector-only answers with a warning prepended to the
  response — never a failed stream.
- **Ingestion**: `POST /internal/ingest {"source": "news"}` fetches the
  latest news, converts to documents, and upserts into the `news`
  Pinecone namespace with deterministic SHA-256 IDs.

## Error handling

| Failure | Behavior |
|---|---|
| API error | Retried up to 3 times with exponential backoff, then `SearchAPIError` |
| Rate limit window full | `RateLimitError` with `retry_after` seconds |
| 3 consecutive failures | Fallback mode for 5 minutes; `safe_search` short-circuits |
| Any error via `safe_search` | `([], user_facing_message)` — never raises |

## Free-tier budget

Tavily's free tier allows 1000 searches/month. The 15-minute result
cache and the agent's 60/min rate limiter keep runtime usage bounded;
the nightly news ingest (Phase 5 Oban job) uses roughly 30/month.
