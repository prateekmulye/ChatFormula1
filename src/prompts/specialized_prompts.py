"""Specialized prompt templates for specific tasks.

This module contains prompts for query analysis, predictions, and other
specialized tasks requiring structured outputs or specific reasoning patterns.
"""

from typing import Any, Dict, List, Optional

from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.prompts import (ChatPromptTemplate, FewShotPromptTemplate,
                                    PromptTemplate)
from pydantic import BaseModel, Field

# ============================================================================
# Query Analysis Prompts (Intent Detection)
# ============================================================================


class QueryIntent(BaseModel):
    """Structured output for query analysis."""

    intent: str = Field(
        description="Primary intent: 'current_info', 'historical', 'prediction', 'comparison', 'explanation', 'general'"
    )
    entities: Dict[str, List[str]] = Field(
        description="Extracted entities: drivers, teams, races, years, circuits"
    )
    requires_search: bool = Field(description="Whether query requires real-time search")
    requires_vector: bool = Field(
        description="Whether query requires historical knowledge base"
    )
    complexity: str = Field(
        description="Query complexity: 'simple', 'moderate', 'complex'"
    )
    confidence: float = Field(description="Confidence in intent classification (0-1)")


QUERY_ANALYSIS_TEMPLATE = """Analyze the following F1-related query and extract structured information.

**Query:** {query}

**Analysis Instructions:**
1. Identify the primary intent (current_info, historical, prediction, comparison, explanation, general)
2. Extract all relevant entities (drivers, teams, races, years, circuits)
3. Determine if real-time search is needed (for current season, recent news)
4. Determine if historical knowledge base is needed (for past data, statistics)
5. Assess query complexity
6. Provide confidence score

**Intent Definitions:**
- current_info: Questions about current season, standings, recent races
- historical: Questions about past seasons, records, historical events
- prediction: Questions about future race outcomes, championship scenarios
- comparison: Comparing drivers, teams, or eras
- explanation: Explaining rules, technical concepts, strategies
- general: General F1 questions or casual conversation

{format_instructions}

Analyze the query and provide the structured output.
"""


def create_query_analysis_prompt() -> tuple[ChatPromptTemplate, PydanticOutputParser]:
    """Create query analysis prompt with structured output parser.

    Returns:
        Tuple of (prompt_template, output_parser)
    """
    parser = PydanticOutputParser(pydantic_object=QueryIntent)

    prompt = PromptTemplate(
        template=QUERY_ANALYSIS_TEMPLATE,
        input_variables=["query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    return (
        ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an expert at analyzing F1 queries and extracting structured information.",
                ),
                ("human", prompt.template),
            ]
        ),
        parser,
    )


# ============================================================================
# Prediction Prompts with Structured Output
# ============================================================================


class RacePrediction(BaseModel):
    """Structured output for race predictions."""

    race_name: str = Field(description="Name of the race")
    circuit: str = Field(description="Circuit name")
    predicted_winner: str = Field(description="Predicted race winner")
    podium: List[str] = Field(description="Predicted top 3 finishers")
    confidence_level: str = Field(
        description="Confidence level: 'low', 'medium', 'high'"
    )
    confidence_score: float = Field(description="Numerical confidence (0-1)")
    key_factors: List[str] = Field(description="Key factors influencing prediction")
    reasoning: str = Field(description="Detailed explanation of prediction reasoning")
    alternative_scenarios: Optional[List[str]] = Field(
        default=None, description="Alternative outcomes and conditions"
    )


PREDICTION_TEMPLATE = """You are ChatFormula1, an expert F1 analyst making race predictions.

**Race Information:**
{race_info}

**Historical Performance at Circuit:**
{historical_context}

**Current Season Form:**
{current_form}

**Additional Factors:**
{additional_factors}

**Prediction Task:**
Generate a detailed race prediction considering:
1. Driver current form and recent performance
2. Historical performance at this specific circuit
3. Team car performance and development trajectory
4. Weather conditions and track characteristics
5. Strategic considerations (tire strategy, pit stops)
6. Recent technical updates and their impact

**Reasoning Approach:**
- Start with historical circuit performance
- Layer in current season form
- Consider team and car factors
- Account for external variables (weather, incidents)
- Synthesize into cohesive prediction

{format_instructions}

Provide your structured prediction with detailed reasoning.
"""


def create_prediction_prompt() -> tuple[ChatPromptTemplate, PydanticOutputParser]:
    """Create race prediction prompt with structured output.

    Returns:
        Tuple of (prompt_template, output_parser)
    """
    parser = PydanticOutputParser(pydantic_object=RacePrediction)

    prompt = PromptTemplate(
        template=PREDICTION_TEMPLATE,
        input_variables=[
            "race_info",
            "historical_context",
            "current_form",
            "additional_factors",
        ],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    return (
        ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are an expert F1 analyst specializing in race predictions.",
                ),
                ("human", prompt.template),
            ]
        ),
        parser,
    )


# ============================================================================
# Few-Shot Learning Prompts
# ============================================================================

# Examples for few-shot learning
QUERY_ANALYSIS_EXAMPLES = [
    {
        "query": "Who won the 2023 Monaco Grand Prix?",
        "output": """Intent: historical
Entities: {races: ["Monaco Grand Prix"], years: ["2023"]}
Requires Search: false
Requires Vector: true
Complexity: simple
Confidence: 0.95""",
    },
    {
        "query": "What are the current driver standings?",
        "output": """Intent: current_info
Entities: {}
Requires Search: true
Requires Vector: false
Complexity: simple
Confidence: 0.98""",
    },
    {
        "query": "Compare Hamilton's and Verstappen's performance at Spa over their careers",
        "output": """Intent: comparison
Entities: {drivers: ["Hamilton", "Verstappen"], circuits: ["Spa"]}
Requires Search: false
Requires Vector: true
Complexity: complex
Confidence: 0.92""",
    },
    {
        "query": "Who will win the next race in Singapore?",
        "output": """Intent: prediction
Entities: {races: ["Singapore Grand Prix"]}
Requires Search: true
Requires Vector: true
Complexity: moderate
Confidence: 0.90""",
    },
]

PREDICTION_EXAMPLES = [
    {
        "input": "Predict the winner of the Monaco Grand Prix with Verstappen leading the championship",
        "output": """Predicted Winner: Max Verstappen
Podium: [Verstappen, Leclerc, Alonso]
Confidence: Medium (0.65)
Key Factors:
- Verstappen's strong qualifying performance
- Red Bull's superior race pace
- Monaco's overtaking difficulty favors pole position
- Leclerc's home race motivation
Reasoning: While Monaco traditionally favors Ferrari and Leclerc has home advantage, Verstappen's current form and Red Bull's dominant car give him the edge. Qualifying will be crucial.""",
    },
]


def create_few_shot_query_analysis_prompt() -> FewShotPromptTemplate:
    """Create few-shot prompt for query analysis.

    Returns:
        FewShotPromptTemplate with examples
    """
    example_prompt = PromptTemplate(
        input_variables=["query", "output"],
        template="Query: {query}\nAnalysis: {output}",
    )

    return FewShotPromptTemplate(
        examples=QUERY_ANALYSIS_EXAMPLES,
        example_prompt=example_prompt,
        prefix="Analyze F1 queries and extract structured information. Here are some examples:",
        suffix="Now analyze this query:\nQuery: {query}\nAnalysis:",
        input_variables=["query"],
    )


def create_few_shot_prediction_prompt() -> FewShotPromptTemplate:
    """Create few-shot prompt for race predictions.

    Returns:
        FewShotPromptTemplate with prediction examples
    """
    example_prompt = PromptTemplate(
        input_variables=["input", "output"],
        template="Request: {input}\nPrediction: {output}",
    )

    return FewShotPromptTemplate(
        examples=PREDICTION_EXAMPLES,
        example_prompt=example_prompt,
        prefix="Generate detailed F1 race predictions with reasoning. Here's an example:",
        suffix="Now generate a prediction for:\n{input}\nPrediction:",
        input_variables=["input"],
    )


# ============================================================================
# Chain-of-Thought Prompts for Complex Reasoning
# ============================================================================

CHAIN_OF_THOUGHT_TEMPLATE = """You are ChatFormula1, solving a complex F1 analysis question.

**Question:** {query}

**Available Context:**
{context}

**Instructions - Think Step by Step:**

Step 1: **Understand the Question**
- What is being asked?
- What information is needed?
- What time period is relevant?

Step 2: **Gather Relevant Information**
- What data from the context is relevant?
- What historical patterns apply?
- What current factors matter?

Step 3: **Analyze and Reason**
- How do the factors interact?
- What are the cause-and-effect relationships?
- What patterns or trends emerge?

Step 4: **Consider Alternatives**
- What other interpretations exist?
- What could change the outcome?
- What are the uncertainties?

Step 5: **Synthesize Conclusion**
- What is the most likely answer?
- How confident are we?
- What caveats apply?

**Work through each step explicitly, then provide your final answer.**
"""

CHAIN_OF_THOUGHT_PROMPT = PromptTemplate(
    template=CHAIN_OF_THOUGHT_TEMPLATE,
    input_variables=["query", "context"],
)


def create_chain_of_thought_prompt() -> ChatPromptTemplate:
    """Create chain-of-thought prompt for complex reasoning.

    Returns:
        ChatPromptTemplate with CoT structure
    """
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are an expert F1 analyst who thinks step-by-step through complex problems.",
            ),
            ("human", CHAIN_OF_THOUGHT_TEMPLATE),
        ]
    )


# ============================================================================
# Comparison Analysis Prompt
# ============================================================================

COMPARISON_TEMPLATE = """You are ChatFormula1, conducting a detailed comparison analysis.

**Comparison Request:** {query}

**Entity 1 Data:**
{entity1_data}

**Entity 2 Data:**
{entity2_data}

**Comparison Framework:**

1. **Direct Metrics Comparison**
   - Compare quantitative statistics
   - Highlight significant differences
   - Provide context for numbers

2. **Contextual Analysis**
   - Consider era differences (if applicable)
   - Account for car/team performance
   - Factor in external circumstances

3. **Qualitative Assessment**
   - Driving style differences
   - Strengths and weaknesses
   - Situational performance

4. **Historical Significance**
   - Career achievements
   - Records and milestones
   - Legacy and impact

5. **Conclusion**
   - Balanced summary
   - Key differentiators
   - Acknowledge subjectivity where applicable

Provide a comprehensive, balanced comparison.
"""

COMPARISON_PROMPT = PromptTemplate(
    template=COMPARISON_TEMPLATE,
    input_variables=["query", "entity1_data", "entity2_data"],
)


# ============================================================================
# Technical Explanation Prompt
# ============================================================================

TECHNICAL_EXPLANATION_TEMPLATE = """You are ChatFormula1, explaining F1 technical concepts clearly.

**Topic:** {topic}

**User Knowledge Level:** {knowledge_level}

**Relevant Technical Information:**
{technical_context}

**Explanation Structure:**

1. **Simple Definition**
   - What is it in plain language?
   - Why does it exist?

2. **How It Works**
   - Basic mechanism or principle
   - Key components or factors

3. **F1 Application**
   - How is it used in F1?
   - Real-world examples from races

4. **Impact on Racing**
   - How does it affect performance?
   - Strategic implications

5. **Additional Context**
   - Historical evolution
   - Regulatory aspects
   - Future developments

**Tone:** {tone_instruction}

Provide a clear, engaging explanation appropriate for the user's knowledge level.
"""


def create_technical_explanation_prompt(
    knowledge_level: str = "intermediate",
) -> PromptTemplate:
    """Create technical explanation prompt tailored to user knowledge.

    Args:
        knowledge_level: User's F1 knowledge (beginner, intermediate, expert)

    Returns:
        PromptTemplate for technical explanations
    """
    tone_instructions = {
        "beginner": "Use simple language, avoid jargon, provide analogies",
        "intermediate": "Balance technical terms with explanations, assume basic F1 knowledge",
        "expert": "Use technical terminology freely, focus on nuanced details",
    }

    tone = tone_instructions.get(knowledge_level, tone_instructions["intermediate"])

    return PromptTemplate(
        template=TECHNICAL_EXPLANATION_TEMPLATE,
        input_variables=["topic", "technical_context"],
        partial_variables={
            "knowledge_level": knowledge_level,
            "tone_instruction": tone,
        },
    )


# ============================================================================
# Entity Extraction Prompt
# ============================================================================


class ExtractedEntities(BaseModel):
    """Structured output for entity extraction."""

    drivers: List[str] = Field(
        default_factory=list, description="Driver names mentioned"
    )
    teams: List[str] = Field(default_factory=list, description="Team names mentioned")
    circuits: List[str] = Field(
        default_factory=list, description="Circuit names mentioned"
    )
    races: List[str] = Field(default_factory=list, description="Race names mentioned")
    years: List[int] = Field(default_factory=list, description="Years mentioned")
    seasons: List[int] = Field(default_factory=list, description="Seasons mentioned")
    technical_terms: List[str] = Field(
        default_factory=list, description="Technical F1 terms"
    )


ENTITY_EXTRACTION_TEMPLATE = """Extract all F1-related entities from the following text.

**Text:** {text}

**Entity Categories:**
- Drivers: Current and historical F1 drivers
- Teams: Constructor teams (e.g., Ferrari, Mercedes, Red Bull)
- Circuits: Race track names (e.g., Monaco, Silverstone, Spa)
- Races: Grand Prix names
- Years/Seasons: Specific years or seasons mentioned
- Technical Terms: F1-specific technical terminology

{format_instructions}

Extract all entities from the text.
"""


def create_entity_extraction_prompt() -> tuple[PromptTemplate, PydanticOutputParser]:
    """Create entity extraction prompt with structured output.

    Returns:
        Tuple of (prompt_template, output_parser)
    """
    parser = PydanticOutputParser(pydantic_object=ExtractedEntities)

    prompt = PromptTemplate(
        template=ENTITY_EXTRACTION_TEMPLATE,
        input_variables=["text"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    return prompt, parser
