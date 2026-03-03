# Tavily Integration Guide

This document explains how the Chat P1 Agent uses Tavily's search capabilities to retrieve the latest and most accurate F1 news and information.

## Overview

The integration uses `langchain-tavily` which provides:
- **TavilySearchResults**: Real-time web search with AI-powered relevance
- **Advanced Search Depth**: More comprehensive source coverage
- **Domain Filtering**: Focus on trusted F1 sources
- **Raw Content Extraction**: Full article content for vector DB ingestion
- **Crawl Capabilities**: Deep content extraction from specific URLs

## Features

### 1. Real-Time F1 Search

Search for the latest F1 information with automatic relevance ranking:

```python
from src.config import get_settings
from src.search import TavilyClient

settings = get_settings()
client = TavilyClient(settings)

# Search for latest race results
results = await client.search("Max Verstappen Abu Dhabi GP 2024 results")

# Get latest F1 news
news = await client.get_latest_f1_news("driver transfers")
```

### 2. Contextual Search

Add context to refine search results:

```python
# Search with season context
results = await client.search_with_context(
    query="Monaco Grand Prix qualifying",
    context="2024 season"
)
```

### 3. Domain Mapping

Discover new content on trusted F1 sources:

```python
# Map Formula1.com for 2024 season content
pages = await client.map_f1_domain(
    domain="formula1.com",
    query="2024 season highlights"
)
```

### 4. Deep Content Crawling

Extract full article content for vector DB ingestion:

```python
# Crawl a specific F1 article
documents = await client.crawl_f1_source(
    url="https://www.formula1.com/en/latest/article.html",
    max_depth=2
)

# Documents are ready for vector DB ingestion
for doc in documents:
    print(f"Title: {doc.metadata['title']}")
    print(f"Content: {doc.page_content[:200]}...")
```

### 5. Convert to LangChain Documents

Convert search results to documents for vector DB:

```python
# Search and convert to documents
results = await client.search("F1 2024 regulations changes")
documents = client.convert_to_documents(results)

# Now ingest into Pinecone
# vector_store.add_documents(documents)
```

## Configuration

### Environment Variables

Configure Tavily in your `.env` file:

```bash
# Required
TAVILY_API_KEY=your_tavily_api_key_here

# Optional - Search Configuration
TAVILY_MAX_RESULTS=5                    # Number of results per search
TAVILY_SEARCH_DEPTH=advanced            # basic or advanced
TAVILY_INCLUDE_ANSWER=true              # Include AI-generated answer
TAVILY_INCLUDE_RAW_CONTENT=true         # Include full content for ingestion
TAVILY_INCLUDE_IMAGES=false             # Include images in results
TAVILY_MAX_CRAWL_DEPTH=2                # Depth for crawl operations
```

### Trusted F1 Domains

The client is pre-configured with trusted F1 sources:

- formula1.com (Official F1 website)
- fia.com (FIA official)
- autosport.com
- motorsport.com
- racefans.net
- the-race.com
- espn.com/f1
- bbc.com/sport/formula1
- skysports.com/f1

You can customize this list in `settings.py`:

```python
tavily_include_domains: list[str] = Field(
    default_factory=lambda: [
        "formula1.com",
        "your-custom-domain.com",
    ]
)
```

## Use Cases

### 1. Real-Time Race Updates

```python
# Get latest race results
results = await client.get_latest_f1_news("race results", max_results=3)

for result in results:
    print(f"Title: {result['title']}")
    print(f"URL: {result['url']}")
    print(f"Content: {result['content'][:200]}...")
```

### 2. Driver Information

```python
# Search for driver stats
results = await client.search(
    "Lewis Hamilton career statistics 2024",
    max_results=5,
    include_raw_content=True
)
```

### 3. Technical Regulations

```python
# Find technical regulation changes
results = await client.search_with_context(
    query="aerodynamic regulations changes",
    context="2024 F1 season"
)
```

### 4. Historical Data Ingestion

```python
# Crawl historical articles for vector DB
urls = [
    "https://www.formula1.com/en/latest/article.2024-season-review.html",
    "https://www.autosport.com/f1/news/2024-championship-analysis",
]

all_documents = []
for url in urls:
    docs = await client.crawl_f1_source(url)
    all_documents.extend(docs)

# Ingest into vector store
# vector_store.add_documents(all_documents)
```

### 5. News Aggregation Pipeline

```python
# Automated news ingestion pipeline
async def ingest_latest_f1_news():
    """Ingest latest F1 news into vector DB."""
    topics = [
        "race results",
        "driver transfers",
        "team updates",
        "technical developments",
        "championship standings"
    ]
    
    all_documents = []
    for topic in topics:
        results = await client.get_latest_f1_news(topic, max_results=3)
        documents = client.convert_to_documents(results)
        all_documents.extend(documents)
    
    # Ingest into Pinecone
    # vector_store.add_documents(all_documents)
    
    return len(all_documents)
```

## Advanced Features

### Search Depth

- **Basic**: Faster, fewer sources, good for quick queries
- **Advanced**: Slower, more sources, better for comprehensive research

```python
# Override search depth for specific query
results = await client.search(
    "detailed technical analysis F1 2024",
    max_results=10
)
```

### Raw Content for Ingestion

Enable `include_raw_content=True` to get full article text:

```python
results = await client.search(
    "F1 2024 season review",
    include_raw_content=True  # Full content for vector DB
)
```

### AI-Generated Answers

Tavily can provide AI-generated summaries:

```python
results = await client.search(
    "Who won the 2024 F1 championship?",
    include_answer=True
)

# Access the AI answer
if results and "answer" in results[0]:
    print(f"Answer: {results[0]['answer']}")
```

## Error Handling

The client includes automatic retry logic with exponential backoff:

```python
from src.exceptions import SearchAPIError

try:
    results = await client.search("F1 news")
except SearchAPIError as e:
    print(f"Search failed: {e.message}")
    print(f"Details: {e.details}")
    # Handle gracefully - maybe use cached data
```

## Performance Considerations

### Rate Limits

- Tavily has rate limits based on your plan
- The client automatically retries with backoff
- Consider caching frequently accessed data

### Optimization Tips

1. **Use Domain Filtering**: Faster results from trusted sources
2. **Adjust Max Results**: Lower for speed, higher for comprehensiveness
3. **Cache Results**: Store recent searches to reduce API calls
4. **Batch Operations**: Group related queries together

### Caching Strategy

```python
from functools import lru_cache
from datetime import datetime, timedelta

class CachedTavilyClient(TavilyClient):
    def __init__(self, settings):
        super().__init__(settings)
        self._cache = {}
        self._cache_ttl = timedelta(minutes=15)
    
    async def search(self, query: str, **kwargs):
        # Check cache
        cache_key = f"{query}:{kwargs}"
        if cache_key in self._cache:
            cached_time, cached_result = self._cache[cache_key]
            if datetime.now() - cached_time < self._cache_ttl:
                return cached_result
        
        # Fetch fresh data
        result = await super().search(query, **kwargs)
        self._cache[cache_key] = (datetime.now(), result)
        return result
```

## Integration with Vector Store

### Ingestion Pipeline

```python
from src.search import TavilyClient
from src.vector_store import PineconeClient
from src.config import get_settings

async def ingest_f1_news_to_vector_db():
    """Complete pipeline: Search -> Extract -> Embed -> Store"""
    settings = get_settings()
    
    # Initialize clients
    tavily = TavilyClient(settings)
    pinecone = PineconeClient(settings)
    
    # Search for latest F1 content
    results = await tavily.get_latest_f1_news(max_results=10)
    
    # Convert to documents
    documents = tavily.convert_to_documents(results)
    
    # Add to vector store (will be embedded automatically)
    await pinecone.add_documents(documents)
    
    return len(documents)
```

## Monitoring and Logging

All operations are logged with structured logging:

```python
# Logs include:
# - Query details
# - Result counts
# - Performance metrics
# - Error information

# Example log output:
{
    "event": "tavily_search_completed",
    "query": "Max Verstappen championship",
    "results_count": 5,
    "timestamp": "2024-12-01T10:30:00Z",
    "app": "chatp1"
}
```

## Best Practices

1. **Use Specific Queries**: More specific = better results
2. **Enable Raw Content**: For vector DB ingestion
3. **Filter by Domain**: Focus on trusted F1 sources
4. **Handle Errors Gracefully**: Always have fallback strategies
5. **Monitor API Usage**: Track rate limits and costs
6. **Cache Aggressively**: Reduce redundant API calls
7. **Batch When Possible**: Group related operations

## Troubleshooting

### No Results Returned

- Check API key is valid
- Verify query is not too specific
- Try removing domain filters
- Check Tavily service status

### Rate Limit Errors

- Implement caching
- Reduce search frequency
- Upgrade Tavily plan
- Use exponential backoff (built-in)

### Poor Result Quality

- Use advanced search depth
- Add more context to queries
- Filter by trusted domains
- Refine query phrasing

## Next Steps

- Implement automated news ingestion pipeline
- Set up scheduled crawling of F1 sources
- Build query optimization based on user patterns
- Create result quality metrics and monitoring
