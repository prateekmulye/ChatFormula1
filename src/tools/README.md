# Chat P1 LangChain Tools

This module provides LangChain tools that enable the Chat P1 agent to access various data sources and capabilities.

## Overview

The tools module implements three main tools using the LangChain `@tool` decorator:

1. **search_current_f1_data** - Search for current F1 information using Tavily API
2. **query_f1_history** - Query historical F1 data from Pinecone vector store
3. **predict_race_outcome** - Generate race predictions combining historical and current data

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    LangGraph Agent                       │
│                  (Orchestration Layer)                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                   F1 Tools Module                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Search     │  │   History    │  │  Prediction  │  │
│  │   Current    │  │    Query     │  │    Tool      │  │
│  │     Tool     │  │     Tool     │  │              │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
└─────────┼──────────────────┼──────────────────┼─────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐
│  Tavily Client  │  │  Vector Store   │  │    Both     │
│                 │  │    Manager      │  │  Sources    │
└─────────────────┘  └─────────────────┘  └─────────────┘
```

## Tools

### 1. search_current_f1_data

Searches for current F1 news, standings, and race results using Tavily Search API.

**Use Cases:**
- Current season standings (drivers or constructors)
- Recent race results and highlights
- Latest F1 news and updates
- Upcoming race schedule
- Current driver or team performance

**Parameters:**
- `query` (str): The search query for current F1 information

**Returns:**
- Formatted string containing search results with sources

**Example:**
```python
result = await search_current_f1_data.ainvoke({
    "query": "Max Verstappen 2024 championship standings"
})
```

**Features:**
- Graceful degradation with fallback handling
- Searches trusted F1 sources (formula1.com, fia.com, autosport.com, etc.)
- Includes relevance scores and source attribution
- Rate limiting protection

### 2. query_f1_history

Queries historical F1 data from the Pinecone vector store using semantic search.

**Use Cases:**
- Historical statistics and records
- Past championships and seasons
- Driver or team history and achievements
- Circuit records and historical race data
- Technical regulations from past eras
- Comparisons between different time periods

**Parameters:**
- `query` (str): The search query for historical F1 data
- `year_range` (Optional[str]): Year range filter (e.g., "2020-2024" or "2023")
- `category` (Optional[str]): Category filter (e.g., "race_result", "driver_stats")
- `max_results` (int): Maximum number of results (1-20, default: 5)

**Returns:**
- Formatted string containing historical data with citations

**Example:**
```python
result = await query_f1_history.ainvoke({
    "query": "Lewis Hamilton championship wins",
    "year_range": "2014-2020",
    "category": "driver_stats",
    "max_results": 5
})
```

**Features:**
- Semantic similarity search with relevance scores
- Metadata filtering by year range and category
- Result caching for performance
- Citation with source attribution

### 3. predict_race_outcome

Generates race predictions by combining historical data and current season information.

**Use Cases:**
- Race outcome predictions
- Qualifying predictions
- Championship scenarios
- "What if" scenarios for upcoming races
- Driver or team performance forecasts

**Parameters:**
- `race` (str): Name of the race or Grand Prix (e.g., "Monaco Grand Prix")
- `season` (int): Season year for the prediction (e.g., 2024)
- `factors` (Optional[List[str]]): Specific factors to consider:
  - `"weather"`: Weather conditions and forecasts
  - `"driver_form"`: Recent driver performance
  - `"circuit_history"`: Historical performance at this circuit
  - `"team_form"`: Recent team/constructor performance
  - `"qualifying"`: Qualifying results if available

**Returns:**
- Structured prediction with confidence scores and reasoning

**Example:**
```python
result = await predict_race_outcome.ainvoke({
    "race": "Monaco Grand Prix",
    "season": 2024,
    "factors": ["circuit_history", "driver_form", "weather"]
})
```

**Features:**
- Combines historical circuit data from vector store
- Gathers current season data from Tavily search
- Considers multiple prediction factors
- Provides structured output with reasoning

## Initialization

Before using the tools, you must initialize them with the required dependencies:

```python
from src.config.settings import get_settings
from src.tools import initialize_tools
from src.vector_store.manager import VectorStoreManager

# Load settings
settings = get_settings()

# Initialize vector store
vector_store = VectorStoreManager(settings)
await vector_store.initialize()

# Initialize tools
initialize_tools(settings, vector_store)
```

## Integration with LangGraph

The tools are designed to be used with LangGraph agents:

```python
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from src.tools import (
    search_current_f1_data,
    query_f1_history,
    predict_race_outcome,
)

# Create LLM
llm = ChatOpenAI(model="gpt-4-turbo", temperature=0.7)

# Create agent with tools
agent = create_react_agent(
    llm,
    tools=[
        search_current_f1_data,
        query_f1_history,
        predict_race_outcome,
    ],
)

# Use the agent
result = await agent.ainvoke({
    "messages": [("user", "Who won the last race?")]
})
```

## Error Handling

All tools implement comprehensive error handling:

1. **Initialization Errors**: Tools check if they're properly initialized before use
2. **API Failures**: Graceful degradation with user-friendly error messages
3. **Rate Limiting**: Automatic handling of rate limits with fallback
4. **Data Validation**: Input validation using Pydantic models
5. **Logging**: Structured logging for debugging and monitoring

## Input Schemas

The tools use Pydantic models for input validation:

### QueryF1HistoryInput
```python
class QueryF1HistoryInput(BaseModel):
    query: str
    year_range: Optional[str] = None
    category: Optional[str] = None
    max_results: int = Field(default=5, ge=1, le=20)
```

### PredictRaceOutcomeInput
```python
class PredictRaceOutcomeInput(BaseModel):
    race: str
    season: int
    factors: Optional[List[str]] = None
```

## Testing

See `examples/tools_example.py` for a complete working example.

Run the example:
```bash
cd apps/chatp1-agent
python -m examples.tools_example
```

## Requirements

The tools require the following dependencies:
- `langchain-core` - Core LangChain functionality and @tool decorator
- `langchain-tavily` - Tavily search integration
- `langchain-pinecone` - Pinecone vector store integration
- `langchain-openai` - OpenAI embeddings

## Configuration

Tools use settings from `src.config.settings.Settings`:

**Tavily Configuration:**
- `tavily_api_key`: Tavily API key
- `tavily_max_results`: Maximum search results (default: 5)
- `tavily_search_depth`: Search depth "basic" or "advanced" (default: "advanced")
- `tavily_include_domains`: Trusted F1 domains

**Pinecone Configuration:**
- `pinecone_api_key`: Pinecone API key
- `pinecone_index_name`: Index name (default: "f1-knowledge")
- `pinecone_dimension`: Vector dimension (default: 1536)

**OpenAI Configuration:**
- `openai_api_key`: OpenAI API key
- `openai_embedding_model`: Embedding model (default: "text-embedding-3-small")

## Best Practices

1. **Always initialize tools** before use with `initialize_tools()`
2. **Use appropriate tools** for the query type (current vs historical)
3. **Leverage metadata filters** in `query_f1_history` for precise results
4. **Specify prediction factors** for more accurate race predictions
5. **Handle errors gracefully** - tools return user-friendly error messages
6. **Monitor rate limits** - tools implement automatic rate limiting

## Future Enhancements

Potential improvements for the tools module:

1. **Caching Layer**: Add Redis caching for frequently accessed data
2. **Batch Operations**: Support batch queries for efficiency
3. **Streaming Results**: Stream large result sets for better UX
4. **Custom Metrics**: Track tool usage and performance metrics
5. **Additional Tools**: Add tools for specific F1 domains (technical regs, driver profiles, etc.)
6. **Multi-language Support**: Support queries in multiple languages

## Related Documentation

- [Tavily Client](../search/tavily_client.py) - Tavily search implementation
- [Vector Store Manager](../vector_store/manager.py) - Pinecone integration
- [Agent Module](../agent/) - LangGraph agent orchestration
- [Prompt Templates](../prompts/) - Prompt engineering for tools
