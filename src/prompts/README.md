# Chat P1 Prompt Templates

This module contains comprehensive prompt engineering templates for the Chat P1 agent, built using LangChain's prompt framework.

## Overview

The prompts module is organized into three main categories:

1. **System Prompts** - Define agent persona, capabilities, and guardrails
2. **RAG Prompts** - Combine retrieved context with user queries
3. **Specialized Prompts** - Task-specific prompts with structured outputs

## Module Structure

```
prompts/
├── __init__.py              # Module exports
├── system_prompts.py        # System-level prompts and persona
├── rag_prompts.py          # RAG pipeline prompts
├── specialized_prompts.py  # Query analysis, predictions, etc.
└── README.md               # This file
```

## System Prompts (`system_prompts.py`)

### Features

- **F1 Expert Persona**: Comprehensive system prompt defining the agent as an F1 expert
- **Guardrails**: Off-topic query detection and handling
- **Role-Based Prompts**: Tailored prompts for different user expertise levels
- **Safety Validation**: Input validation to prevent prompt injection

### Key Functions

```python
from src.prompts import create_system_prompt, validate_prompt_safety

# Create a system prompt with guardrails
prompt = create_system_prompt(include_guardrails=True)

# Validate user input for safety
is_safe, warning = validate_prompt_safety(user_query)
```

### Pre-configured Templates

- `CONCISE_SYSTEM_PROMPT` - Brief, focused responses
- `DETAILED_SYSTEM_PROMPT` - Comprehensive, detailed responses
- `PREDICTION_SYSTEM_PROMPT` - Specialized for race predictions

## RAG Prompts (`rag_prompts.py`)

### Features

- **Context Integration**: Combine vector store and search results
- **Conversation History**: Include chat history for context-aware responses
- **Source Attribution**: Automatic citation formatting
- **Fallback Modes**: Prompts for vector-only or search-only scenarios

### Key Functions

```python
from src.prompts import (
    create_rag_prompt_template,
    format_vector_context,
    format_search_context,
)

# Create RAG prompt with conversation history
rag_prompt = create_rag_prompt_template(include_conversation_history=True)

# Format contexts for prompt inclusion
vector_ctx = format_vector_context(documents)
search_ctx = format_search_context(results)
```

### Available Templates

- `RAG_CONTEXT_TEMPLATE` - Full RAG with both contexts
- `VECTOR_ONLY_PROMPT` - Historical knowledge base only
- `SEARCH_ONLY_PROMPT` - Real-time search only
- `CONVERSATIONAL_RAG_PROMPT` - Multi-turn conversations
- `MULTI_SOURCE_SYNTHESIS_PROMPT` - Synthesize multiple sources

## Specialized Prompts (`specialized_prompts.py`)

### Features

- **Structured Outputs**: Pydantic models for type-safe outputs
- **Query Analysis**: Intent detection and entity extraction
- **Predictions**: Race outcome predictions with reasoning
- **Few-Shot Learning**: Examples for better LLM performance
- **Chain-of-Thought**: Step-by-step reasoning for complex queries

### Query Analysis

```python
from src.prompts import create_query_analysis_prompt, QueryIntent

# Create prompt with output parser
prompt, parser = create_query_analysis_prompt()

# Use with LLM to get structured output
# result: QueryIntent with intent, entities, etc.
```

**Output Schema:**
```python
class QueryIntent(BaseModel):
    intent: str  # current_info, historical, prediction, etc.
    entities: Dict[str, List[str]]  # drivers, teams, races, etc.
    requires_search: bool
    requires_vector: bool
    complexity: str  # simple, moderate, complex
    confidence: float
```

### Race Predictions

```python
from src.prompts import create_prediction_prompt, RacePrediction

# Create prediction prompt with parser
prompt, parser = create_prediction_prompt()

# Use with LLM to get structured prediction
# result: RacePrediction with winner, podium, reasoning, etc.
```

**Output Schema:**
```python
class RacePrediction(BaseModel):
    race_name: str
    circuit: str
    predicted_winner: str
    podium: List[str]
    confidence_level: str  # low, medium, high
    confidence_score: float
    key_factors: List[str]
    reasoning: str
    alternative_scenarios: Optional[List[str]]
```

### Few-Shot Learning

```python
from src.prompts import (
    create_few_shot_query_analysis_prompt,
    create_few_shot_prediction_prompt,
)

# Create prompts with built-in examples
query_prompt = create_few_shot_query_analysis_prompt()
prediction_prompt = create_few_shot_prediction_prompt()
```

### Chain-of-Thought Reasoning

```python
from src.prompts import create_chain_of_thought_prompt

# Create CoT prompt for complex analysis
cot_prompt = create_chain_of_thought_prompt()
```

### Other Specialized Prompts

- **Comparison Analysis**: Compare drivers, teams, or eras
- **Technical Explanations**: Explain F1 concepts at appropriate level
- **Entity Extraction**: Extract F1 entities from text

## Usage Examples

### Basic System Prompt

```python
from langchain_openai import ChatOpenAI
from src.prompts import DETAILED_SYSTEM_PROMPT

llm = ChatOpenAI(model="gpt-4-turbo")
chain = DETAILED_SYSTEM_PROMPT | llm

response = chain.invoke({"query": "Who won the 2023 championship?"})
```

### RAG with Context

```python
from src.prompts import (
    create_rag_prompt_template,
    format_vector_context,
    format_search_context,
)

# Format contexts
vector_ctx = format_vector_context(retrieved_docs)
search_ctx = format_search_context(search_results)

# Create and use prompt
rag_prompt = create_rag_prompt_template()
chain = rag_prompt | llm

response = chain.invoke({
    "vector_context": vector_ctx,
    "search_context": search_ctx,
    "query": user_query,
})
```

### Structured Query Analysis

```python
from src.prompts import create_query_analysis_prompt

prompt, parser = create_query_analysis_prompt()
chain = prompt | llm | parser

# Get structured output
intent: QueryIntent = chain.invoke({"query": "Who will win in Monaco?"})
print(f"Intent: {intent.intent}")
print(f"Requires search: {intent.requires_search}")
```

### Race Prediction

```python
from src.prompts import create_prediction_prompt

prompt, parser = create_prediction_prompt()
chain = prompt | llm | parser

prediction: RacePrediction = chain.invoke({
    "race_info": "Monaco Grand Prix 2024",
    "historical_context": historical_data,
    "current_form": current_season_data,
    "additional_factors": "Weather: Sunny, Track: Dry",
})

print(f"Winner: {prediction.predicted_winner}")
print(f"Confidence: {prediction.confidence_level}")
print(f"Reasoning: {prediction.reasoning}")
```

## Best Practices

1. **Always validate user input** using `validate_prompt_safety()` before processing
2. **Use appropriate prompt templates** for different scenarios (concise vs detailed)
3. **Include conversation history** for multi-turn conversations
4. **Format contexts properly** using provided formatting functions
5. **Use structured outputs** for tasks requiring specific data formats
6. **Leverage few-shot examples** for better LLM performance
7. **Apply chain-of-thought** for complex reasoning tasks

## Requirements Mapping

This implementation satisfies the following requirements:

- **Requirement 7.1**: Structured prompts with clear role definitions ✓
- **Requirement 7.2**: Chain-of-thought reasoning for complex queries ✓
- **Requirement 7.3**: Output format specifications using JSON schema ✓
- **Requirement 7.5**: Guardrails preventing off-topic responses ✓
- **Requirement 1.2**: RAG pipeline combining context with queries ✓
- **Requirement 2.4**: Conversation history formatting ✓
- **Requirement 3.4**: Prediction prompts with structured output ✓

## Testing

Run the example script to verify all prompts work correctly:

```bash
python examples/prompt_examples.py
```

This will demonstrate:
- System prompt creation
- Prompt safety validation
- RAG prompt templates
- Context formatting
- Query analysis
- Prediction prompts

## Integration with LangGraph

These prompts are designed to integrate seamlessly with LangGraph nodes:

```python
from langgraph.graph import StateGraph
from src.prompts import create_query_analysis_prompt

async def analyze_query_node(state):
    prompt, parser = create_query_analysis_prompt()
    chain = prompt | llm | parser
    intent = await chain.ainvoke({"query": state["query"]})
    return {"intent": intent}

graph = StateGraph(AgentState)
graph.add_node("analyze_query", analyze_query_node)
```

## Future Enhancements

- Multi-language support for international users
- Dynamic prompt optimization based on user feedback
- A/B testing framework for prompt variations
- Prompt versioning and rollback capabilities
- Performance metrics tracking per prompt template
