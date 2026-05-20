"""
Query router for intelligent query classification and routing.
Determines whether to use SQL or semantic search based on query intent.
"""
from __future__ import annotations

import json
from typing import Any, Optional

import pandas as pd

from config import TOP_K_SEMANTIC
from src.llm import get_llm
from src.llm._compat import llm_to_query_error
from src.semantic_search import semantic_query
from src.sql_generator import query_with_sql
from src.utils import QueryError, format_schema_for_llm, logger


# Chart detection keywords
CHART_KEYWORDS = {
    "pie": ["pie chart", "pie graph", "breakdown by", "proportion"],
    "bar": ["bar chart", "bar graph", "compare", "top \\d+", "ranking"],
    "line": ["line chart", "trend", "over time", "per week", "per month"],
    "histogram": ["histogram", "distribution of"],
}


# System prompt for intent classification
CLASSIFICATION_PROMPT = """You are a query classifier for a ServiceNow incident management system.

Classify the user's query into one of three categories:

1. STRUCTURED - Queries that need SQL:
   - Aggregations: "how many", "count", "total", "average", "top N", "sum"
   - Filters: "show all", "list all", specific field values, exact matches
   - Date ranges: "last month", "this week", "between dates", "since"
   - Sorting: "most recent", "oldest", "highest priority", "latest"
   - Grouping: "by category", "per group", "breakdown"

2. SEMANTIC - Queries that need similarity search:
   - Similarity: "similar to", "like", "related to", "resembling"
   - Descriptive: "about X", "involving", "regarding", "concerning"
   - Symptom-based: "where users report...", "with error...", "experiencing"
   - Vague/exploratory: "help with", "issues with", "problems like"
   - Natural descriptions: sentences describing a problem or situation

3. HYBRID - Queries that need both approaches:
   - Complex questions combining filters AND similarity
   - "Find P1 incidents similar to network outages"
   - "Top 5 assignment groups for Outlook issues"
   - Structured filter with semantic content description

Also detect any filters mentioned in the query:
- Priority (P1, P2, Critical, High, etc.)
- Assignment group names
- Date ranges

Respond with JSON:
{
    "intent": "structured|semantic|hybrid",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of why this classification",
    "detected_filters": {
        "priority": ["value"] or null,
        "assignment_group": "group name" or null,
        "date_range": "description" or null
    }
}"""


def _detect_chart_request(query: str) -> tuple[bool, str | None]:
    """
    Detect if query requests a chart and what type.

    Args:
        query: The user's query string

    Returns:
        Tuple of (chart_requested: bool, chart_type: str | None)
        chart_type will be "pie", "bar", "line", "histogram", or None
    """
    import re

    query_lower = query.lower()

    # Check each chart type's keywords
    for chart_type, keywords in CHART_KEYWORDS.items():
        for keyword in keywords:
            # Use regex if keyword contains regex patterns (like \d+)
            if "\\" in keyword:
                if re.search(keyword, query_lower):
                    return True, chart_type
            else:
                if keyword in query_lower:
                    return True, chart_type

    return False, None


def classify_intent(
    user_query: str,
    schema_summary: dict[str, Any]
) -> dict[str, Any]:
    """
    Classify the user's query intent using OpenAI.

    Args:
        user_query: The user's natural language query
        schema_summary: Schema information for context

    Returns:
        Dict with intent, confidence, reasoning, detected_filters, chart_requested, chart_type

    Raises:
        QueryError: If classification fails
    """
    logger.info(f"Classifying intent for: {user_query}")

    # Detect chart request first
    chart_requested, chart_type = _detect_chart_request(user_query)

    try:
        schema_text = format_schema_for_llm(schema_summary)

        messages = [
            {
                "role": "system",
                "content": CLASSIFICATION_PROMPT + f"\n\nAvailable columns:\n{schema_text}"
            },
            {
                "role": "user",
                "content": user_query
            }
        ]

        client = get_llm()
        with llm_to_query_error():
            content = client.complete(messages, max_tokens=500).strip()

        # Parse JSON response
        try:
            # Handle markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            result = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse classification response: {content}")
            # Fallback to heuristic classification
            return _heuristic_classify(user_query)

        # Validate intent
        if result.get("intent") not in ["structured", "semantic", "hybrid"]:
            result["intent"] = _heuristic_classify(user_query)["intent"]

        logger.info(f"Classified as: {result['intent']} (confidence: {result.get('confidence', 0)})")

        return {
            "intent": result.get("intent", "structured"),
            "confidence": result.get("confidence", 0.5),
            "reasoning": result.get("reasoning", ""),
            "detected_filters": result.get("detected_filters", {}),
            "chart_requested": chart_requested,
            "chart_type": chart_type
        }

    except QueryError:
        raise
    except Exception as e:
        logger.warning(f"Classification failed, using heuristic: {e}")
        return _heuristic_classify(user_query)


def _heuristic_classify(user_query: str) -> dict[str, Any]:
    """
    Fallback heuristic classification when OpenAI is unavailable.

    Args:
        user_query: The user's query

    Returns:
        Classification dict
    """
    query_lower = user_query.lower()

    # Detect chart request
    chart_requested, chart_type = _detect_chart_request(user_query)

    # Semantic indicators
    semantic_keywords = [
        "similar to", "like", "related to", "about", "involving",
        "regarding", "issues with", "problems like", "find incidents like",
        "resembling", "concerning"
    ]

    # Structured indicators
    structured_keywords = [
        "how many", "count", "total", "average", "top ", "sum",
        "show all", "list all", "last month", "this week", "between",
        "most recent", "oldest", "highest", "lowest", "by category",
        "per group", "breakdown", "since"
    ]

    semantic_score = sum(1 for kw in semantic_keywords if kw in query_lower)
    structured_score = sum(1 for kw in structured_keywords if kw in query_lower)

    if semantic_score > 0 and structured_score > 0:
        intent = "hybrid"
        confidence = 0.6
    elif semantic_score > structured_score:
        intent = "semantic"
        confidence = 0.7
    else:
        intent = "structured"
        confidence = 0.7

    return {
        "intent": intent,
        "confidence": confidence,
        "reasoning": "Classified using keyword heuristics (OpenAI unavailable)",
        "detected_filters": {},
        "chart_requested": chart_requested,
        "chart_type": chart_type
    }


def route_query(
    user_query: str,
    schema_summary: dict[str, Any],
    mode: str = "auto",
    top_k: int = TOP_K_SEMANTIC
) -> dict[str, Any]:
    """
    Route query to appropriate search method.

    Args:
        user_query: The user's natural language query
        schema_summary: Schema information from ingest module
        mode: Query mode - "auto", "structured", "semantic", or "hybrid"
        top_k: Number of results for semantic search

    Returns:
        Dict with results, route info, and metadata
    """
    logger.info(f"Routing query with mode: {mode}")

    # Determine route
    if mode == "auto":
        classification = classify_intent(user_query, schema_summary)
        intent = classification["intent"]
        confidence = classification["confidence"]
        reasoning = classification["reasoning"]
    else:
        # Even with mode override, detect chart requests
        chart_requested, chart_type = _detect_chart_request(user_query)
        intent = mode
        confidence = 1.0
        reasoning = f"Mode override: {mode}"
        classification = {
            "intent": intent,
            "confidence": confidence,
            "reasoning": reasoning,
            "detected_filters": {},
            "chart_requested": chart_requested,
            "chart_type": chart_type
        }

    # Execute based on intent
    if intent == "structured":
        result = query_with_sql(user_query, schema_summary)
        return {
            "results": result["results"],
            "route_used": "structured",
            "classification": classification,
            "sql": result.get("sql", ""),
            "explanation": result.get("explanation", ""),
            "row_count": result.get("row_count", 0),
            "error": result.get("error")
        }

    elif intent == "semantic":
        filters = classification.get("detected_filters", {})
        # Clean up empty filters
        filters = {k: v for k, v in filters.items() if v}

        result = semantic_query(user_query, top_k=top_k, filters=filters if filters else None)
        return {
            "results": result["results"],
            "route_used": "semantic",
            "classification": classification,
            "sql": None,
            "explanation": f"Found {result['found']} semantically similar incidents",
            "row_count": result.get("found", 0),
            "error": result.get("error")
        }

    else:  # hybrid
        return _execute_hybrid(user_query, schema_summary, classification, top_k)


def _execute_hybrid(
    user_query: str,
    schema_summary: dict[str, Any],
    classification: dict[str, Any],
    top_k: int
) -> dict[str, Any]:
    """
    Execute hybrid query combining SQL and semantic search.

    Args:
        user_query: The user's query
        schema_summary: Schema information
        classification: Classification result
        top_k: Number of semantic results

    Returns:
        Combined result dict
    """
    logger.info("Executing hybrid query")

    # Run both queries
    sql_result = query_with_sql(user_query, schema_summary)
    semantic_result = semantic_query(user_query, top_k=top_k)

    # Combine results
    combined = combine_results(sql_result, semantic_result)

    return {
        "results": combined,
        "route_used": "hybrid",
        "classification": classification,
        "sql": sql_result.get("sql", ""),
        "explanation": f"Combined {sql_result.get('row_count', 0)} SQL results with {semantic_result.get('found', 0)} semantic results",
        "row_count": len(combined),
        "error": sql_result.get("error") or semantic_result.get("error")
    }


def combine_results(
    sql_result: dict[str, Any],
    semantic_result: dict[str, Any]
) -> pd.DataFrame:
    """
    Combine results from SQL and semantic searches.

    Deduplicates by incident number, keeping SQL results (exact matches) first,
    then adds unique semantic results.

    Args:
        sql_result: Result from query_with_sql
        semantic_result: Result from semantic_query

    Returns:
        Combined DataFrame
    """
    sql_df = sql_result.get("results", pd.DataFrame())
    semantic_df = semantic_result.get("results", pd.DataFrame())

    if sql_df.empty and semantic_df.empty:
        return pd.DataFrame()

    if sql_df.empty:
        return semantic_df

    if semantic_df.empty:
        return sql_df

    # Determine ID column - handle aggregated queries without ID columns
    if "number" in sql_df.columns:
        id_col = "number"
    elif "sys_id" in sql_df.columns:
        id_col = "sys_id"
    else:
        # Aggregated SQL result (no ID column) - return both without deduplication
        sql_df = sql_df.copy()
        semantic_df = semantic_df.copy()
        sql_df["_source"] = "sql"
        semantic_df["_source"] = "semantic"
        return pd.concat([sql_df, semantic_df], ignore_index=True)

    # Get IDs from SQL results
    sql_ids = set(sql_df[id_col].astype(str).tolist())

    # Filter semantic results to only include new IDs
    if id_col in semantic_df.columns:
        semantic_df = semantic_df[~semantic_df[id_col].astype(str).isin(sql_ids)]

    # Add source column
    sql_df = sql_df.copy()
    semantic_df = semantic_df.copy()
    sql_df["_source"] = "sql"
    semantic_df["_source"] = "semantic"

    # Combine
    combined = pd.concat([sql_df, semantic_df], ignore_index=True)

    # Sort: SQL results first (they're exact matches), then semantic by similarity
    if "similarity_score" in combined.columns:
        combined = combined.sort_values(
            ["_source", "similarity_score"],
            ascending=[True, False]
        )

    return combined


def get_mode_description(mode: str) -> str:
    """
    Get human-readable description of query mode.

    Args:
        mode: Query mode string

    Returns:
        Description string
    """
    descriptions = {
        "auto": "Automatically determine the best search method",
        "structured": "Use SQL for filtered/aggregated queries (Report mode)",
        "semantic": "Use vector similarity for finding similar incidents",
        "hybrid": "Combine SQL and semantic search for comprehensive results"
    }
    return descriptions.get(mode, "Unknown mode")


# System prompt for executive summary generation
SUMMARY_PROMPT = """You are an executive summary generator for ServiceNow incident data analysis.

Given a user's question and the query results, provide a concise executive summary suitable for management.

Guidelines:
1. Start with key findings (2-3 sentences max)
2. Highlight patterns, trends, or notable insights
3. If applicable, provide a brief recommendation
4. Keep total response under 150 words
5. Use business-friendly language, avoid technical jargon
6. If results are empty, acknowledge no data was found for the criteria

Format your response as:
**Key Findings**: [Main insights]

**Patterns/Trends**: [Notable observations, if any]

**Recommendation**: [Actionable suggestion, if applicable]"""


def generate_executive_summary(
    user_query: str,
    results: pd.DataFrame,
    route_used: str
) -> str | None:
    """
    Generate an executive summary of query results using LLM.

    Args:
        user_query: The original user question
        results: DataFrame with query results
        route_used: The query route that was used

    Returns:
        Executive summary string or None if generation fails
    """
    if results is None or results.empty:
        return None

    try:
        # Prepare results for LLM (limit to avoid token overflow)
        max_rows = 20
        if len(results) > max_rows:
            results_sample = results.head(max_rows)
            row_note = f"(showing top {max_rows} of {len(results)} results)"
        else:
            results_sample = results
            row_note = f"({len(results)} results)"

        # Convert to readable format
        results_text = results_sample.to_string(index=False, max_colwidth=50)

        messages = [
            {
                "role": "system",
                "content": SUMMARY_PROMPT
            },
            {
                "role": "user",
                "content": f"""Question: {user_query}

Query Type: {route_used}

Results {row_note}:
{results_text}

Please provide an executive summary of these results."""
            }
        ]

        client = get_llm()
        with llm_to_query_error():
            summary = client.complete(messages, max_tokens=500).strip()
        logger.info("Executive summary generated successfully")
        return summary

    except Exception as e:
        logger.warning(f"Failed to generate executive summary: {e}")
        return None
