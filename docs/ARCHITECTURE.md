# Chat P1 Agent - Architecture Documentation

This document provides a comprehensive overview of the Chat P1 Agent architecture, including system design, component interactions, and data flow.

## Table of Contents

- [System Overview](#system-overview)
- [Architecture Diagrams](#architecture-diagrams)
- [Component Details](#component-details)
- [Data Flow](#data-flow)
- [Technology Stack](#technology-stack)
- [Design Decisions](#design-decisions)

## System Overview

Chat P1 Agent is a conversational AI system built using RAG (Retrieval-Augmented Generation) architecture. It combines real-time F1 data retrieval, semantic search over historical knowledge, and large language models to provide expert-level Formula 1 insights.

### Key Features

- **Real-time Data**: Latest F1 news and updates via Tavily Search API
- **Historical Knowledge**: Semantic search over F1 history using Pinecone vector database
- **Conversational AI**: Natural language interactions powered by OpenAI GPT models
- **Agent Orchestration**: LangGraph-based workflow for intelligent query routing
- **Multi-interface**: Both API and UI interfaces for different use cases

## Architecture Diagrams

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Layer                               │
│  ┌──────────────────┐              ┌──────────────────┐         │
│  │  Streamlit UI    │              │   API Clients    │         │
│  │  (Port 8501)     │              │   (REST/HTTP)    │         │
│  └────────┬─────────┘              └────────┬─────────┘         │
└───────────┼──────────────────────────────────┼──────────────────┘
            │                                  │
            └──────────────┬───────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────────┐
│                    Application Layer                             │
│                           │                                      │
│  ┌────────────────────────▼────────────────────────┐            │
│  │         FastAPI Backend (Port 8000)             │            │
│  │  ┌──────────────────────────────────────────┐   │            │
│  │  │      LangGraph Agent Orchestrator        │   │            │
│  │  │  ┌────────────────────────────────────┐  │   │            │
│  │  │  │  Query Analysis → Route Decision   │  │   │            │
│  │  │  │         ↓              ↓            │  │   │            │
│  │  │  │  Vector Search   Tavily Search     │  │   │            │
│  │  │  │         ↓              ↓            │  │   │            │
│  │  │  │    Context Ranking & Fusion        │  │   │            │
│  │  │  │              ↓                      │  │   │            │
│  │  │  │      LLM Response Generation       │  │   │            │
│  │  │  └────────────────────────────────────┘  │   │            │
│  │  └──────────────────────────────────────────┘   │            │
│  └─────────────────────────────────────────────────┘            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
┌───────────▼────┐  ┌──────▼──────┐  ┌───▼──────────┐
│   Pinecone     │  │   Tavily    │  │   OpenAI     │
│ Vector Store   │  │ Search API  │  │   LLM API    │
│                │  │             │  │              │
│ - Embeddings   │  │ - Web Search│  │ - GPT-4      │
│ - Similarity   │  │ - F1 News   │  │ - Embeddings │
│   Search       │  │ - Real-time │  │ - Streaming  │
└────────────────┘  └─────────────┘  └──────────────┘
```

### RAG Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      User Query Input                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Query Analysis Node                           │
│  - Intent Detection (historical vs current vs prediction)        │
│  - Entity Extraction (drivers, teams, races, years)             │
│  - Query Classification (factual, analytical, conversational)    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Routing Decision Node                         │
│  - Vector Search Only (historical queries)                       │
│  - Tavily Search Only (current events)                          │
│  - Hybrid Search (requires both)                                │
└────────────┬───────────────┬────────────────┬───────────────────┘
             │               │                │
    ┌────────▼────┐   ┌──────▼──────┐   ┌────▼─────────┐
    │   Vector    │   │   Tavily    │   │    Both      │
    │   Search    │   │   Search    │   │  (Parallel)  │
    └────────┬────┘   └──────┬──────┘   └────┬─────────┘
             │               │                │
             └───────────────┼────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Context Ranking & Fusion Node                   │
│  - Score relevance of retrieved documents                        │
│  - Deduplicate information                                       │
│  - Merge vector and search results                              │
│  - Select top K most relevant contexts                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Prompt Construction Node                       │
│  - System prompt (F1 expert persona)                            │
│  - Retrieved context (formatted)                                │
│  - Conversation history                                         │
│  - User query                                                   │
│  - Output format instructions                                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   LLM Generation Node                            │
│  - OpenAI GPT-4 / GPT-3.5                                       │
│  - Streaming response                                           │
│  - Citation generation                                          │
│  - Confidence scoring                                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Response Formatting Node                        │
│  - Markdown formatting                                          │
│  - Source attribution                                           │
│  - Metadata attachment                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Response to User                            │
└─────────────────────────────────────────────────────────────────┘
```

### Data Ingestion Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    Data Sources                                  │
│  - Historical race results (CSV)                                │
│  - Driver statistics (JSON)                                     │
│  - Circuit information                                          │
│  - F1 regulations documents                                     │
│  - Curated F1 articles                                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Loader                                 │
│  - Read CSV/JSON files                                          │
│  - Validate data schemas                                        │
│  - Handle encoding issues                                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Document Processor                             │
│  - Text extraction and cleaning                                 │
│  - Semantic chunking (1000 chars, 200 overlap)                 │
│  - Preserve context across chunks                              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Metadata Enricher                              │
│  - Extract entities (drivers, teams, races)                     │
│  - Add temporal metadata (year, season)                         │
│  - Categorize content type                                      │
│  - Add source attribution                                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Embedding Generation                           │
│  - OpenAI text-embedding-3-small                                │
│  - Batch processing (100 docs/batch)                            │
│  - Retry logic for failures                                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Pinecone Upsert                                │
│  - Batch upsert to vector store                                 │
│  - Progress tracking                                            │
│  - Error handling and logging                                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Indexed Knowledge Base                         │
└─────────────────────────────────────────────────────────────────┘
```

### Conversation State Management

```
┌─────────────────────────────────────────────────────────────────┐
│                      User Session                                │
│  - Session ID                                                    │
│  - User preferences                                             │
│  - Conversation history                                         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   LangGraph Memory Saver                         │
│  - Checkpoint conversation state                                │
│  - Sliding window (last 10 messages)                            │
│  - Context summarization for long conversations                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Agent State                                   │
│  {                                                              │
│    "messages": [...],                                           │
│    "query": "...",                                              │
│    "intent": "...",                                             │
│    "entities": {...},                                           │
│    "retrieved_docs": [...],                                     │
│    "search_results": [...],                                     │
│    "context": "...",                                            │
│    "response": "...",                                           │
│    "metadata": {...}                                            │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. FastAPI Backend

**Responsibilities**:
- HTTP request handling
- API endpoint routing
- Request validation
- Response formatting
- CORS management
- Rate limiting
- Health checks

**Key Endpoints**:
- `POST /chat` - Process chat messages
- `GET /health` - Health check
- `POST /ingest` - Trigger data ingestion
- `GET /stats` - Vector store statistics

### 2. LangGraph Agent

**Responsibilities**:
- Conversation orchestration
- Query routing
- Tool execution
- State management
- Error handling
- Response streaming

**Nodes**:
- `analyze_query` - Intent detection and entity extraction
- `route` - Decide which retrieval strategy to use
- `vector_search` - Query Pinecone vector store
- `tavily_search` - Query Tavily search API
- `rank_context` - Score and merge results
- `generate` - LLM response generation

### 3. Vector Store Manager

**Responsibilities**:
- Pinecone connection management
- Document embedding
- Similarity search
- Metadata filtering
- Index statistics

**Key Methods**:
- `upsert_documents()` - Add documents to vector store
- `similarity_search()` - Retrieve similar documents
- `hybrid_search()` - Combine semantic and keyword search

### 4. Tavily Search Client

**Responsibilities**:
- Real-time web search
- F1-specific domain filtering
- Result parsing
- Rate limiting
- Error handling

**Key Methods**:
- `search()` - Execute search query
- `search_with_context()` - Contextual search
- `crawl_f1_source()` - Deep content extraction

### 5. Prompt Templates

**Responsibilities**:
- Structured prompt construction
- Context formatting
- Few-shot examples
- Output format specification
- Guardrails

**Templates**:
- System prompts (role definition)
- RAG prompts (context + query)
- Specialized prompts (predictions, analysis)

### 6. Streamlit UI

**Responsibilities**:
- User interface rendering
- Chat history display
- Message input handling
- Streaming response display
- Source citation display
- Session management

**Components**:
- Chat interface
- Sidebar settings
- Message history
- Source expandables

## Data Flow

### Query Processing Flow

1. **User Input** → User submits query via UI or API
2. **Query Analysis** → Extract intent and entities
3. **Routing Decision** → Determine retrieval strategy
4. **Parallel Retrieval** → Query vector store and/or search API
5. **Context Ranking** → Score and merge results
6. **Prompt Construction** → Build structured prompt
7. **LLM Generation** → Generate response with streaming
8. **Response Formatting** → Format with citations
9. **User Output** → Display to user

### Data Ingestion Flow

1. **Data Loading** → Read source files
2. **Document Processing** → Clean and chunk text
3. **Metadata Enrichment** → Add structured metadata
4. **Embedding Generation** → Convert to vectors
5. **Vector Store Upsert** → Store in Pinecone
6. **Verification** → Validate ingestion

## Technology Stack

### Core Technologies

- **Python 3.11** - Application runtime
- **Poetry** - Dependency management
- **FastAPI** - Web framework
- **Streamlit** - UI framework
- **Docker** - Containerization

### AI/ML Stack

- **LangChain** - LLM framework
- **LangGraph** - Agent orchestration
- **OpenAI GPT-4** - Language model
- **OpenAI Embeddings** - Text embeddings
- **Pinecone** - Vector database
- **Tavily** - Search API

### Infrastructure

- **Docker Compose** - Local orchestration
- **Nginx** - Reverse proxy (optional)
- **Kubernetes** - Production orchestration (optional)

### Observability

- **Structlog** - Structured logging
- **LangSmith** - LLM tracing
- **Prometheus** - Metrics (optional)

## Design Decisions

### Why LangGraph?

- **State Management**: Built-in conversation state handling
- **Flexibility**: Easy to modify agent workflow
- **Observability**: Native LangSmith integration
- **Streaming**: First-class streaming support

### Why Pinecone?

- **Managed Service**: No infrastructure management
- **Performance**: Fast similarity search
- **Scalability**: Handles large datasets
- **Metadata Filtering**: Rich query capabilities

### Why Tavily?

- **F1-Specific**: Can filter by trusted F1 domains
- **Real-time**: Latest news and updates
- **Quality**: AI-powered relevance ranking
- **Reliability**: High uptime and rate limits

### Why Streamlit?

- **Rapid Development**: Quick to build UI
- **Python-Native**: No JavaScript required
- **Rich Components**: Built-in chat interface
- **Easy Deployment**: Simple hosting options

### Architectural Patterns

1. **RAG Pattern**: Combines retrieval with generation for accuracy
2. **Agent Pattern**: Intelligent routing and tool use
3. **Multi-stage Build**: Optimized Docker images
4. **Dependency Injection**: Testable and maintainable code
5. **Graceful Degradation**: Fallbacks for API failures

### Trade-offs

| Decision | Pros | Cons |
|----------|------|------|
| Python-only stack | Unified language, easier maintenance | May be slower than compiled languages |
| Managed services | Less ops overhead | Vendor lock-in, costs |
| Streamlit UI | Fast development | Limited customization |
| Docker deployment | Consistent environments | Additional complexity |
| Synchronous API | Simpler code | Lower throughput |

## Future Enhancements

### Planned Improvements

1. **Caching Layer**: Redis for response caching
2. **Async Operations**: Full async/await throughout
3. **Multi-modal**: Image analysis for race incidents
4. **Personalization**: User preference learning
5. **Advanced Analytics**: Deeper statistical analysis
6. **Real-time Updates**: WebSocket for live race data
7. **Mobile App**: Native mobile experience
8. **Multi-language**: Internationalization support

### Scalability Considerations

- Horizontal scaling of API instances
- Load balancing across replicas
- Distributed caching with Redis
- CDN for static assets
- Database connection pooling
- Rate limiting per user
- Circuit breakers for external APIs

## References

- [LangChain Documentation](https://python.langchain.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Pinecone Documentation](https://docs.pinecone.io/)
- [Tavily Documentation](https://docs.tavily.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)
