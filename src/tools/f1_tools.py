"""LangChain tools for ChatFormula1 agent capabilities.

This module provides tools that the LangGraph agent can use to:
1. Search for current F1 data using Tavily
2. Query historical F1 data from Pinecone vector store
3. Generate race predictions combining historical and current data
"""

from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ..config.logging import get_logger
from ..config.settings import Settings
from ..search.tavily_client import TavilyClient
from ..vector_store.manager import VectorStoreManager

logger = get_logger(__name__)


# Input schemas for structured tools
class QueryF1HistoryInput(BaseModel):
    """Input schema for query_f1_history tool."""

    query: str = Field(description="The search query for historical F1 data")
    year_range: Optional[str] = Field(
        default=None,
        description="Year range filter in format 'YYYY-YYYY' or single year 'YYYY'",
    )
    category: Optional[str] = Field(
        default=None,
        description="Category filter (e.g., 'race_result', 'driver_stats', 'technical')",
    )
    max_results: int = Field(
        default=5, ge=1, le=20, description="Maximum number of results to return"
    )


class PredictRaceOutcomeInput(BaseModel):
    """Input schema for predict_race_outcome tool."""

    race: str = Field(
        description="Name of the race or Grand Prix (e.g., 'Monaco Grand Prix')"
    )
    season: int = Field(description="Season year for the prediction")
    factors: Optional[List[str]] = Field(
        default=None,
        description="Specific factors to consider (e.g., 'weather', 'driver_form', 'circuit_history')",
    )


# Tool instances will be created by the factory function
_tavily_client: Optional[TavilyClient] = None
_vector_store_manager: Optional[VectorStoreManager] = None


def initialize_tools(
    settings: Settings,
    vector_store: VectorStoreManager,
    tavily_client: Optional[TavilyClient] = None,
) -> None:
    """Initialize tool dependencies.

    This must be called before using the tools.

    Args:
        settings: Application settings
        vector_store: Initialized VectorStoreManager instance
        tavily_client: Optional pre-initialized TavilyClient instance
    """
    global _tavily_client, _vector_store_manager

    _tavily_client = (
        tavily_client if tavily_client is not None else TavilyClient(settings)
    )
    _vector_store_manager = vector_store

    logger.info("f1_tools_initialized")


@tool
async def search_current_f1_data(query: str) -> str:
    """Search for current F1 news, standings, and race results.

    Use this tool when users ask about:
    - Current season standings (drivers or constructors)
    - Recent race results and highlights
    - Latest F1 news and updates
    - Upcoming race schedule and information
    - Current driver or team performance
    - Breaking news or recent developments

    This tool uses Tavily Search API to retrieve real-time information
    from trusted F1 sources like formula1.com, fia.com, autosport.com, etc.

    Args:
        query: The search query for current F1 information

    Returns:
        Formatted string containing search results with sources

    Example:
        >>> result = await search_current_f1_data("Max Verstappen 2024 championship standings")
        >>> print(result)
    """
    if _tavily_client is None:
        error_msg = "Tools not initialized. Call initialize_tools() first."
        logger.error("tool_not_initialized", tool="search_current_f1_data")
        return f"Error: {error_msg}"

    try:
        logger.info("search_current_f1_data_invoked", query=query)

        # Use safe_search for graceful degradation
        results, error = await _tavily_client.safe_search(
            query=query,
            include_answer=True,
            include_raw_content=False,
            search_depth="advanced",
        )

        # Handle search failure
        if error:
            logger.warning("search_failed_gracefully", query=query, error=error)
            return f"⚠️ {error}\n\nPlease try asking about historical F1 data instead."

        # Handle no results
        if not results:
            logger.info("no_search_results", query=query)
            return (
                "No current information found for your query. "
                "Try rephrasing or ask about historical F1 data."
            )

        # Format results
        formatted_output = _format_search_results(results, query)

        logger.info(
            "search_current_f1_data_completed",
            query=query,
            results_count=len(results),
        )

        return formatted_output

    except Exception as e:
        logger.error(
            "search_current_f1_data_failed",
            query=query,
            error=str(e),
            error_type=type(e).__name__,
        )
        return (
            f"An error occurred while searching for current F1 data: {str(e)}\n\n"
            "Please try again or ask about historical F1 information."
        )


def _format_search_results(results: List[Dict[str, Any]], query: str) -> str:
    """Format Tavily search results into readable text.

    Args:
        results: List of search results from Tavily
        query: Original search query

    Returns:
        Formatted string with results and sources
    """
    output_lines = [f"# Current F1 Information: {query}\n"]

    for i, result in enumerate(results, 1):
        title = result.get("title", "Untitled")
        content = result.get("content", "")
        url = result.get("url", "")
        score = result.get("score", 0.0)

        output_lines.append(f"## Result {i}: {title}")
        output_lines.append(f"**Relevance:** {score:.2f}")
        output_lines.append(f"**Source:** {url}")
        output_lines.append(f"\n{content}\n")
        output_lines.append("---\n")

    return "\n".join(output_lines)


@tool
async def query_f1_history(
    query: str,
    year_range: Optional[str] = None,
    category: Optional[str] = None,
    max_results: int = 5,
) -> str:
    """Query historical F1 data from the knowledge base.

    Use this tool when users ask about:
    - Historical statistics and records
    - Past championships and seasons
    - Driver or team history and achievements
    - Circuit records and historical race data
    - Technical regulations from past eras
    - Comparisons between different time periods

    This tool searches the Pinecone vector store containing curated
    F1 historical data from 1950 to present.

    Args:
        query: The search query for historical F1 data
        year_range: Optional year range filter (e.g., "2020-2024" or "2023")
        category: Optional category filter (e.g., "race_result", "driver_stats")
        max_results: Maximum number of results to return (1-20, default: 5)

    Returns:
        Formatted string containing historical data with citations

    Example:
        >>> result = await query_f1_history(
        ...     "Lewis Hamilton championship wins",
        ...     year_range="2014-2020"
        ... )
    """
    if _vector_store_manager is None:
        error_msg = "Tools not initialized. Call initialize_tools() first."
        logger.error("tool_not_initialized", tool="query_f1_history")
        return f"Error: {error_msg}"

    try:
        logger.info(
            "query_f1_history_invoked",
            query=query,
            year_range=year_range,
            category=category,
            max_results=max_results,
        )

        # Build metadata filters
        filters = _build_metadata_filters(year_range, category)

        # Perform similarity search with scores
        results = await _vector_store_manager.similarity_search_with_score(
            query=query,
            k=max_results,
            filters=filters,
        )

        # Handle no results
        if not results:
            logger.info("no_history_results", query=query, filters=filters)
            return (
                "No historical data found matching your query. "
                "Try broadening your search or removing filters."
            )

        # Format results
        formatted_output = _format_history_results(results, query, year_range, category)

        logger.info(
            "query_f1_history_completed",
            query=query,
            results_count=len(results),
        )

        return formatted_output

    except Exception as e:
        logger.error(
            "query_f1_history_failed",
            query=query,
            error=str(e),
            error_type=type(e).__name__,
        )
        return (
            f"An error occurred while querying historical F1 data: {str(e)}\n\n"
            "Please try rephrasing your query."
        )


def _build_metadata_filters(
    year_range: Optional[str],
    category: Optional[str],
) -> Optional[Dict[str, Any]]:
    """Build Pinecone metadata filters from parameters.

    Args:
        year_range: Year range string (e.g., "2020-2024" or "2023")
        category: Category filter string

    Returns:
        Dictionary of Pinecone filters or None if no filters
    """
    filters = {}

    # Parse year range
    if year_range:
        if "-" in year_range:
            # Range format: "2020-2024"
            try:
                start_year, end_year = year_range.split("-")
                filters["year"] = {
                    "$gte": int(start_year.strip()),
                    "$lte": int(end_year.strip()),
                }
            except (ValueError, AttributeError):
                logger.warning("invalid_year_range_format", year_range=year_range)
        else:
            # Single year format: "2023"
            try:
                filters["year"] = int(year_range.strip())
            except ValueError:
                logger.warning("invalid_year_format", year_range=year_range)

    # Add category filter
    if category:
        filters["category"] = category.strip()

    return filters if filters else None


def _format_history_results(
    results: List[tuple],
    query: str,
    year_range: Optional[str],
    category: Optional[str],
) -> str:
    """Format vector store results into readable text with citations.

    Args:
        results: List of (Document, score) tuples from vector store
        query: Original search query
        year_range: Year range filter used
        category: Category filter used

    Returns:
        Formatted string with results and citations
    """
    output_lines = [f"# Historical F1 Data: {query}\n"]

    # Add filter information
    if year_range or category:
        filters_applied = []
        if year_range:
            filters_applied.append(f"Years: {year_range}")
        if category:
            filters_applied.append(f"Category: {category}")
        output_lines.append(f"**Filters:** {', '.join(filters_applied)}\n")

    # Format each result
    for i, (doc, score) in enumerate(results, 1):
        metadata = doc.metadata
        content = doc.page_content

        # Extract metadata fields
        source = metadata.get("source", "Unknown")
        year = metadata.get("year", "N/A")
        doc_category = metadata.get("category", "N/A")

        output_lines.append(f"## Result {i} (Relevance: {score:.3f})")
        output_lines.append(f"**Year:** {year} | **Category:** {doc_category}")
        output_lines.append(f"**Source:** {source}")
        output_lines.append(f"\n{content}\n")
        output_lines.append("---\n")

    return "\n".join(output_lines)


@tool
async def predict_race_outcome(
    race: str,
    season: int,
    factors: Optional[List[str]] = None,
) -> str:
    """Generate race predictions based on current form and historical data.

    Use this tool when users ask about:
    - Race outcome predictions
    - Qualifying predictions
    - Championship scenarios and possibilities
    - "What if" scenarios for upcoming races
    - Driver or team performance forecasts

    This tool combines:
    1. Historical race data from the vector store (circuit history, past results)
    2. Current season data from Tavily search (recent form, standings)
    3. Specific factors like weather, driver form, circuit characteristics

    Args:
        race: Name of the race or Grand Prix (e.g., "Monaco Grand Prix", "Silverstone")
        season: Season year for the prediction (e.g., 2024)
        factors: Optional list of factors to consider:
                 - "weather": Weather conditions and forecasts
                 - "driver_form": Recent driver performance
                 - "circuit_history": Historical performance at this circuit
                 - "team_form": Recent team/constructor performance
                 - "qualifying": Qualifying results if available

    Returns:
        Structured prediction with confidence scores and reasoning

    Example:
        >>> result = await predict_race_outcome(
        ...     race="Monaco Grand Prix",
        ...     season=2024,
        ...     factors=["circuit_history", "driver_form"]
        ... )
    """
    if _tavily_client is None or _vector_store_manager is None:
        error_msg = "Tools not initialized. Call initialize_tools() first."
        logger.error("tool_not_initialized", tool="predict_race_outcome")
        return f"Error: {error_msg}"

    try:
        logger.info(
            "predict_race_outcome_invoked",
            race=race,
            season=season,
            factors=factors,
        )

        # Default factors if none provided
        if not factors:
            factors = ["circuit_history", "driver_form"]

        # Step 1: Gather historical data from vector store
        historical_data = await _gather_historical_data(race, season)

        # Step 2: Gather current form data from Tavily
        current_data = await _gather_current_data(race, season, factors)

        # Step 3: Generate structured prediction
        prediction = _generate_prediction(
            race=race,
            season=season,
            historical_data=historical_data,
            current_data=current_data,
            factors=factors,
        )

        logger.info(
            "predict_race_outcome_completed",
            race=race,
            season=season,
        )

        return prediction

    except Exception as e:
        logger.error(
            "predict_race_outcome_failed",
            race=race,
            season=season,
            error=str(e),
            error_type=type(e).__name__,
        )
        return (
            f"An error occurred while generating race prediction: {str(e)}\n\n"
            "Please try again with different parameters."
        )


async def _gather_historical_data(race: str, season: int) -> Dict[str, Any]:
    """Gather historical data for the race from vector store.

    Args:
        race: Race name
        season: Season year

    Returns:
        Dictionary containing historical context
    """
    # Search for historical data about this circuit
    circuit_query = f"{race} circuit history results statistics"

    # Get data from past 5 years
    year_filter = {
        "year": {
            "$gte": season - 5,
            "$lt": season,
        }
    }

    try:
        results = await _vector_store_manager.similarity_search(
            query=circuit_query,
            k=5,
            filters=year_filter,
        )

        historical_context = {
            "circuit_history": [doc.page_content for doc in results],
            "data_points": len(results),
        }

        logger.info(
            "historical_data_gathered",
            race=race,
            data_points=len(results),
        )

        return historical_context

    except Exception as e:
        logger.warning(
            "historical_data_gathering_failed",
            race=race,
            error=str(e),
        )
        return {"circuit_history": [], "data_points": 0}


async def _gather_current_data(
    race: str,
    season: int,
    factors: List[str],
) -> Dict[str, Any]:
    """Gather current season data from Tavily search.

    Args:
        race: Race name
        season: Season year
        factors: Factors to consider

    Returns:
        Dictionary containing current data
    """
    current_context = {}

    # Build search query based on factors
    search_queries = []

    if "driver_form" in factors or "team_form" in factors:
        search_queries.append(f"F1 {season} current standings driver form")

    if "weather" in factors:
        search_queries.append(f"{race} {season} weather forecast")

    if "qualifying" in factors:
        search_queries.append(f"{race} {season} qualifying results")

    # Default query for race information
    if not search_queries:
        search_queries.append(f"{race} {season} F1 preview predictions")

    # Execute searches
    for query in search_queries:
        try:
            results, error = await _tavily_client.safe_search(
                query=query,
                max_results=3,
                search_depth="advanced",
            )

            if not error and results:
                current_context[query] = [
                    result.get("content", "") for result in results
                ]
        except Exception as e:
            logger.warning(
                "current_data_search_failed",
                query=query,
                error=str(e),
            )
            continue

    logger.info(
        "current_data_gathered",
        race=race,
        queries_executed=len(search_queries),
        data_sources=len(current_context),
    )

    return current_context


def _generate_prediction(
    race: str,
    season: int,
    historical_data: Dict[str, Any],
    current_data: Dict[str, Any],
    factors: List[str],
) -> str:
    """Generate structured prediction output.

    Args:
        race: Race name
        season: Season year
        historical_data: Historical context from vector store
        current_data: Current data from Tavily
        factors: Factors considered

    Returns:
        Formatted prediction string
    """
    output_lines = [
        f"# Race Prediction: {race} {season}\n",
        "## Prediction Analysis\n",
    ]

    # Add factors considered
    output_lines.append("**Factors Considered:**")
    for factor in factors:
        output_lines.append(f"- {factor.replace('_', ' ').title()}")
    output_lines.append("")

    # Add historical context
    output_lines.append("## Historical Context")
    if historical_data.get("data_points", 0) > 0:
        output_lines.append(
            f"Analyzed {historical_data['data_points']} historical data points "
            f"from past races at this circuit.\n"
        )
        # Include first historical snippet
        if historical_data.get("circuit_history"):
            first_snippet = historical_data["circuit_history"][0][:300]
            output_lines.append(f"{first_snippet}...\n")
    else:
        output_lines.append("Limited historical data available for this circuit.\n")

    # Add current data context
    output_lines.append("## Current Season Context")
    if current_data:
        output_lines.append(
            f"Gathered current information from {len(current_data)} sources:\n"
        )
        for query, contents in list(current_data.items())[:2]:
            if contents:
                snippet = contents[0][:200]
                output_lines.append(f"**{query}:**")
                output_lines.append(f"{snippet}...\n")
    else:
        output_lines.append("Limited current season data available.\n")

    # Add prediction framework
    output_lines.extend(
        [
            "## Prediction Framework",
            "",
            "To generate an accurate prediction, the LLM should analyze:",
            "1. Historical performance patterns at this circuit",
            "2. Current driver and team form from recent races",
            "3. Circuit characteristics and how they favor certain teams/drivers",
            "4. Any specific factors mentioned (weather, qualifying, etc.)",
            "",
            "**Note:** The actual prediction should be generated by the LLM using",
            "the historical and current context provided above, along with its",
            "knowledge of F1 racing dynamics.",
            "",
            "**Confidence Level:** The prediction confidence should be based on:",
            "- Data availability (historical + current)",
            "- Consistency of historical patterns",
            "- Reliability of current form indicators",
        ]
    )

    return "\n".join(output_lines)


# Export all tools
__all__ = [
    "search_current_f1_data",
    "query_f1_history",
    "predict_race_outcome",
    "initialize_tools",
    "QueryF1HistoryInput",
    "PredictRaceOutcomeInput",
]
