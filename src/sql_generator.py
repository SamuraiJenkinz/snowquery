"""
SQL generator for natural language to SQL conversion.
Uses Azure OpenAI to generate DuckDB-compatible SQL from user queries.
"""
from __future__ import annotations

import json
from typing import Any, Optional

import duckdb
import pandas as pd

from config import (
    DEFAULT_QUERY_LIMIT,
    DUCKDB_PATH,
    MAX_QUERY_LIMIT,
)
from src.llm import get_llm
from src.llm._compat import llm_to_query_error
from src.utils import QueryError, format_schema_for_llm, logger

# System prompt for SQL generation
SYSTEM_PROMPT = """You are a SQL expert converting natural language to DuckDB SQL for ServiceNow incident data.

Rules:
1. Use DuckDB SQL syntax (similar to PostgreSQL)
2. Table name is 'incidents'
3. Date/timestamp columns use TIMESTAMP type. Use DuckDB date functions like:
   - CURRENT_DATE, CURRENT_TIMESTAMP
   - date_trunc('month', column)
   - column >= CURRENT_DATE - INTERVAL '30 days'
4. Priority values are typically like "1 - Critical", "2 - High", "3 - Moderate", "4 - Low"
   - For "P1" queries, match "1 - Critical" or use LIKE '%1%' or '%Critical%'
5. Always include a LIMIT clause (default 100, max 1000)
6. For aggregations, include meaningful column aliases
7. Only generate SELECT statements - never UPDATE, DELETE, INSERT, DROP, etc.
8. If the query is ambiguous, make reasonable assumptions and explain them
9. COLUMN FIDELITY (critical): Use ONLY column names that appear EXACTLY in the
   Schema section below. NEVER invent, guess, or pluralize column names
   (no "incident_number", no "incident_id" unless they are literally in the Schema).
   If the user references a concept with no obvious matching column, choose the
   closest column that DOES appear in the Schema.
10. ServiceNow incident identifiers like "INC10154562" / "INC0010001" are stored
    in the `number` column. To look up a specific incident, match `number = '<ID>'`.
11. If a column name contains uppercase letters, spaces, dots, or other special
    characters, wrap it in double quotes (e.g., "caller_id.location").

Respond with a JSON object:
{
    "sql": "SELECT ... FROM incidents ...",
    "explanation": "Brief explanation of what the query does",
    "confidence": 0.0-1.0
}"""


# Few-shot examples
FEW_SHOT_EXAMPLES = [
    {
        "query": "Show me information about incident INC0010001",
        "response": {
            "sql": "SELECT * FROM incidents WHERE number = 'INC0010001' LIMIT 1",
            "explanation": "Looks up the single incident whose `number` matches the requested ServiceNow ID.",
            "confidence": 0.97
        }
    },
    {
        "query": "Show all P1 incidents from last month",
        "response": {
            "sql": "SELECT * FROM incidents WHERE (priority LIKE '%1%' OR priority LIKE '%Critical%') AND opened_at >= date_trunc('month', CURRENT_DATE - INTERVAL '1 month') AND opened_at < date_trunc('month', CURRENT_DATE) ORDER BY opened_at DESC LIMIT 100",
            "explanation": "Filters for priority 1 (Critical) incidents opened in the previous calendar month, ordered by most recent first.",
            "confidence": 0.95
        }
    },
    {
        "query": "Top 5 assignment groups by incident volume",
        "response": {
            "sql": "SELECT assignment_group, COUNT(*) as incident_count FROM incidents WHERE assignment_group IS NOT NULL GROUP BY assignment_group ORDER BY incident_count DESC LIMIT 5",
            "explanation": "Counts incidents per assignment group and returns the top 5 groups with the most incidents.",
            "confidence": 0.98
        }
    },
    {
        "query": "Incidents opened today",
        "response": {
            "sql": "SELECT * FROM incidents WHERE CAST(opened_at AS DATE) = CURRENT_DATE ORDER BY opened_at DESC LIMIT 100",
            "explanation": "Returns all incidents where the opened_at date matches today's date.",
            "confidence": 0.95
        }
    },
    {
        "query": "Average resolution time by priority",
        "response": {
            "sql": "SELECT priority, AVG(EXTRACT(EPOCH FROM (resolved_at - opened_at)) / 3600) as avg_hours_to_resolve, COUNT(*) as incident_count FROM incidents WHERE resolved_at IS NOT NULL AND opened_at IS NOT NULL GROUP BY priority ORDER BY priority LIMIT 10",
            "explanation": "Calculates the average time to resolution in hours for each priority level, including the count of resolved incidents.",
            "confidence": 0.90
        }
    }
]


def _build_prompt(
    user_query: str,
    schema_summary: dict[str, Any],
    repair_context: tuple[str, str] | None = None,
) -> list[dict]:
    """
    Build the prompt messages for OpenAI.

    Args:
        user_query: User's natural language query
        schema_summary: Schema information from ingest module
        repair_context: Optional (failed_sql, error_message) pair. When set, an
            extra repair instruction is appended telling the model its previous
            SQL failed at execution (typically a hallucinated/misnamed column)
            and to regenerate using ONLY columns from the Schema.

    Returns:
        List of message dicts for OpenAI API
    """
    schema_text = format_schema_for_llm(schema_summary)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + f"\n\nSchema:\n{schema_text}"}
    ]

    # Add few-shot examples
    for example in FEW_SHOT_EXAMPLES:
        messages.append({
            "role": "user",
            "content": example["query"]
        })
        messages.append({
            "role": "assistant",
            "content": json.dumps(example["response"])
        })

    # Add actual query
    messages.append({
        "role": "user",
        "content": user_query
    })

    # Repair turn: feed back the failed SQL + execution error so the model can
    # self-correct. Most common cause is a column name not present in the Schema
    # (DuckDB "Binder Error ... not found in FROM clause"). The instruction is
    # explicit that ONLY Schema columns may be used.
    if repair_context is not None:
        failed_sql, error_message = repair_context
        messages.append({
            "role": "assistant",
            "content": json.dumps({"sql": failed_sql, "explanation": "", "confidence": 0.0})
        })
        messages.append({
            "role": "user",
            "content": (
                "That SQL FAILED to execute with this database error:\n"
                f"{error_message}\n\n"
                "The most likely cause is a column name that does not exist in the "
                "Schema. Regenerate the SQL for my original request using ONLY column "
                "names that appear EXACTLY in the Schema above. Do not invent column "
                "names. Respond with the same JSON object format."
            )
        })

    return messages


def generate_sql(
    user_query: str,
    schema_summary: dict[str, Any],
    repair_context: tuple[str, str] | None = None,
) -> dict[str, Any]:
    """
    Generate DuckDB-compatible SQL from natural language.

    Args:
        user_query: User's natural language query
        schema_summary: Schema information from ingest module
        repair_context: Optional (failed_sql, error_message) pair to drive a
            self-repair regeneration after an execution failure.

    Returns:
        Dict with sql, explanation, confidence

    Raises:
        QueryError: If SQL generation fails
    """
    logger.info(f"Generating SQL for: {user_query}")

    try:
        messages = _build_prompt(user_query, schema_summary, repair_context)
        client = get_llm()
        with llm_to_query_error():
            content = client.complete(messages, max_tokens=1000).strip()

        # Parse JSON response
        try:
            # Handle potential markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            result = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {content}")
            raise QueryError(
                "Failed to parse SQL generation response",
                f"Invalid JSON: {str(e)}"
            )

        # Validate response structure
        if "sql" not in result:
            raise QueryError(
                "Invalid response from SQL generator",
                "Response missing 'sql' field"
            )

        # Security check - only allow SELECT
        sql_upper = result["sql"].upper().strip()
        dangerous_keywords = ["UPDATE", "DELETE", "INSERT", "DROP", "ALTER", "TRUNCATE", "CREATE"]
        for keyword in dangerous_keywords:
            if sql_upper.startswith(keyword) or f" {keyword} " in sql_upper:
                raise QueryError(
                    "Query blocked for security",
                    f"Only SELECT queries are allowed. Detected: {keyword}"
                )

        logger.info(f"Generated SQL: {result['sql']}")

        return {
            "sql": result["sql"],
            "explanation": result.get("explanation", ""),
            "confidence": result.get("confidence", 0.5)
        }

    except QueryError:
        raise
    except Exception as e:
        logger.exception("Error generating SQL")
        raise QueryError(
            "Failed to generate SQL",
            str(e)
        )


def execute_sql(
    sql: str,
    limit: int = DEFAULT_QUERY_LIMIT
) -> tuple[pd.DataFrame, str | None]:
    """
    Execute SQL against DuckDB.

    Args:
        sql: SQL query to execute
        limit: Maximum rows to return

    Returns:
        Tuple of (results DataFrame, error message or None)
    """
    if not DUCKDB_PATH.exists():
        return pd.DataFrame(), "No data loaded. Please upload a CSV file first."

    try:
        conn = duckdb.connect(str(DUCKDB_PATH), read_only=True)

        try:
            # Enforce limit
            sql_upper = sql.upper()
            if "LIMIT" not in sql_upper:
                sql = f"{sql.rstrip(';')} LIMIT {min(limit, MAX_QUERY_LIMIT)}"

            logger.info(f"Executing SQL: {sql}")

            result = conn.execute(sql).fetchdf()

            logger.info(f"Query returned {len(result)} rows")

            return result, None

        finally:
            conn.close()

    except duckdb.Error as e:
        error_msg = str(e)
        logger.error(f"DuckDB error: {error_msg}")
        return pd.DataFrame(), f"SQL execution error: {error_msg}"

    except Exception as e:
        logger.exception("Unexpected error executing SQL")
        return pd.DataFrame(), f"Unexpected error: {str(e)}"


def _is_column_error(error_message: str) -> bool:
    """Detect a DuckDB column-resolution failure worth a self-repair retry.

    Targets the "Binder Error: Referenced column X not found in FROM clause"
    family (and close relatives) that arise when the LLM hallucinates a column
    name. Deliberately narrow: syntax errors, type errors, and missing-table
    errors are NOT retried (a repair turn won't reliably fix those, and we want
    to avoid burning a second LLM call on unrecoverable failures).
    """
    if not error_message:
        return False
    lowered = error_message.lower()
    return (
        "binder error" in lowered
        or "not found in from clause" in lowered
        or "referenced column" in lowered
    )


def query_with_sql(
    user_query: str,
    schema_summary: dict[str, Any],
    limit: int = DEFAULT_QUERY_LIMIT
) -> dict[str, Any]:
    """
    Generate SQL from natural language and execute it.

    Args:
        user_query: User's natural language query
        schema_summary: Schema information from ingest module
        limit: Maximum rows to return

    Returns:
        Dict with results, sql, explanation, row_count, error
    """
    try:
        # Generate SQL
        generation_result = generate_sql(user_query, schema_summary)

        sql = generation_result["sql"]
        explanation = generation_result["explanation"]
        confidence = generation_result["confidence"]

        # Execute SQL
        results, error = execute_sql(sql, limit)

        # Self-repair: a hallucinated/misnamed column produces a DuckDB Binder
        # Error. Feed the failed SQL + error back to the model ONCE so it can
        # regenerate using only real Schema columns, then re-execute.
        if error and _is_column_error(error):
            logger.warning(f"Column error on first attempt, retrying with repair: {error}")
            try:
                repaired = generate_sql(user_query, schema_summary, repair_context=(sql, error))
                repaired_sql = repaired["sql"]
                repaired_results, repaired_error = execute_sql(repaired_sql, limit)
                # Adopt the repaired attempt regardless of outcome — it carries
                # the most relevant SQL/error for the user. On success the error
                # clears; on failure the user sees the corrected-attempt error.
                sql = repaired_sql
                explanation = repaired.get("explanation", explanation)
                confidence = repaired.get("confidence", confidence)
                results, error = repaired_results, repaired_error
                if not error:
                    logger.info("SQL repair retry succeeded")
            except QueryError as repair_exc:
                logger.warning(f"SQL repair generation failed: {repair_exc}")
                # Keep the original error — repair could not produce new SQL.

        if error:
            return {
                "results": pd.DataFrame(),
                "sql": sql,
                "explanation": explanation,
                "confidence": confidence,
                "row_count": 0,
                "error": error
            }

        return {
            "results": results,
            "sql": sql,
            "explanation": explanation,
            "confidence": confidence,
            "row_count": len(results),
            "error": None
        }

    except QueryError as e:
        return {
            "results": pd.DataFrame(),
            "sql": "",
            "explanation": "",
            "confidence": 0,
            "row_count": 0,
            "error": e.message + (f"\n{e.details}" if e.details else "")
        }

    except Exception as e:
        logger.exception("Error in query_with_sql")
        return {
            "results": pd.DataFrame(),
            "sql": "",
            "explanation": "",
            "confidence": 0,
            "row_count": 0,
            "error": f"Unexpected error: {str(e)}"
        }
