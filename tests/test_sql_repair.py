"""Regression tests for SQL column-hallucination guards + self-repair retry.

Context: a query like "Show me information about incident INC10154562" caused
the LLM to invent a non-existent column (`incident_number` / `incident_id`),
producing a DuckDB "Binder Error: Referenced column ... not found in FROM
clause". The real ServiceNow ID column is `number`.

Behaviors locked here:
  1. _is_column_error classifies Binder/column errors as retryable, and leaves
     unrelated errors (syntax, empty) alone.
  2. SYSTEM_PROMPT forbids inventing columns and teaches the `number` lookup;
     a few-shot example demonstrates `number = '<ID>'`.
  3. _build_prompt(repair_context=...) feeds the failed SQL + execution error
     back to the model with an explicit "use ONLY Schema columns" instruction.
  4. query_with_sql retries ONCE on a column error and adopts the repaired SQL;
     it does NOT retry on success or on non-column errors.

Run with: PYTHONPATH=. python -m pytest tests/test_sql_repair.py -q
Or with the full suite: PYTHONPATH=. python -m pytest tests/ -q
"""
from __future__ import annotations

import json

import pandas as pd

import src.sql_generator as sg

_SCHEMA = {
    "table_name": "incidents",
    "row_count": 1276,
    "columns": [
        {"name": "number", "type": "VARCHAR", "sample": "INC10334485"},
        {"name": "short_description", "type": "VARCHAR", "sample": "Outlook crash"},
        {"name": "priority", "type": "VARCHAR", "sample": "1 - Critical"},
    ],
}


# ---- 1. error classifier ------------------------------------------------

def test_is_column_error_detects_binder_errors():
    binder = (
        'SQL execution error: Binder Error: Referenced column "incident_number" '
        'not found in FROM clause!'
    )
    assert sg._is_column_error(binder) is True
    assert sg._is_column_error("Catalog Error: column not found in FROM clause") is True


def test_is_column_error_ignores_unrelated_errors():
    assert sg._is_column_error("") is False
    assert sg._is_column_error("Parser Error: syntax error at or near SELEC") is False
    assert sg._is_column_error("Conversion Error: could not cast VARCHAR") is False


# ---- 2. prompt + few-shot guards ---------------------------------------

def test_system_prompt_forbids_inventing_columns_and_teaches_number():
    prompt = sg.SYSTEM_PROMPT.lower()
    assert "only" in prompt and "column" in prompt, "Prompt must constrain column usage"
    assert "invent" in prompt or "guess" in prompt, "Prompt must forbid inventing columns"
    assert "`number`" in sg.SYSTEM_PROMPT or "number column" in prompt, (
        "Prompt must teach that incident IDs live in the `number` column"
    )


def test_fewshot_has_number_lookup_example():
    sqls = [ex["response"]["sql"].lower() for ex in sg.FEW_SHOT_EXAMPLES]
    assert any("where number =" in s for s in sqls), (
        "A few-shot example should demonstrate `WHERE number = '<ID>'`"
    )


# ---- 3. repair prompt construction -------------------------------------

def test_build_prompt_repair_context_appends_error_and_failed_sql():
    failed_sql = "SELECT * FROM incidents WHERE incident_number = 'INC10154562'"
    error = 'Binder Error: Referenced column "incident_number" not found in FROM clause!'
    messages = sg._build_prompt(
        "Show me information about incident INC10154562",
        _SCHEMA,
        repair_context=(failed_sql, error),
    )
    blob = json.dumps(messages)
    assert failed_sql in blob, "Repair prompt must echo the failed SQL"
    assert "incident_number" in blob and "not found in FROM clause" in blob, (
        "Repair prompt must include the execution error"
    )
    last_user = [m for m in messages if m["role"] == "user"][-1]["content"].lower()
    assert "only" in last_user and "column" in last_user, (
        "Repair instruction must tell the model to use ONLY Schema columns"
    )


# ---- 4. retry orchestration in query_with_sql --------------------------

class _Spy:
    """Tracks calls and returns scripted values for generate_sql/execute_sql."""

    def __init__(self):
        self.gen_calls: list[dict] = []
        self.exec_calls: list[str] = []


def _install(monkeypatch, spy, gen_side_effect, exec_side_effect):
    def fake_generate(user_query, schema_summary, repair_context=None):
        spy.gen_calls.append({"repair_context": repair_context})
        return gen_side_effect(repair_context)

    def fake_execute(sql, limit=1000):
        spy.exec_calls.append(sql)
        return exec_side_effect(sql)

    monkeypatch.setattr(sg, "generate_sql", fake_generate)
    monkeypatch.setattr(sg, "execute_sql", fake_execute)


def test_query_with_sql_repairs_on_column_error(monkeypatch):
    spy = _Spy()
    bad = "SELECT * FROM incidents WHERE incident_number = 'INC10154562'"
    good = "SELECT * FROM incidents WHERE number = 'INC10154562' LIMIT 1"
    binder = 'Binder Error: Referenced column "incident_number" not found in FROM clause!'

    def gen(repair_context):
        if repair_context is None:
            return {"sql": bad, "explanation": "first try", "confidence": 0.5}
        return {"sql": good, "explanation": "repaired", "confidence": 0.9}

    def execute(sql):
        if sql == bad:
            return pd.DataFrame(), f"SQL execution error: {binder}"
        return pd.DataFrame({"number": ["INC10154562"]}), None

    _install(monkeypatch, spy, gen, execute)

    result = sg.query_with_sql("Show me information about incident INC10154562", _SCHEMA)

    assert result["error"] is None, "Repair retry should clear the column error"
    assert result["sql"] == good, "Result should carry the repaired SQL"
    assert result["row_count"] == 1
    assert len(spy.gen_calls) == 2, "generate_sql should be called twice (initial + repair)"
    assert spy.gen_calls[0]["repair_context"] is None
    assert spy.gen_calls[1]["repair_context"] is not None, "2nd call must pass repair_context"
    assert spy.gen_calls[1]["repair_context"][0] == bad


def test_query_with_sql_no_repair_on_success(monkeypatch):
    spy = _Spy()
    good = "SELECT * FROM incidents WHERE number = 'INC10154562' LIMIT 1"

    def gen(repair_context):
        return {"sql": good, "explanation": "ok", "confidence": 0.9}

    def execute(sql):
        return pd.DataFrame({"number": ["INC10154562"]}), None

    _install(monkeypatch, spy, gen, execute)
    result = sg.query_with_sql("Show incident INC10154562", _SCHEMA)

    assert result["error"] is None
    assert len(spy.gen_calls) == 1, "No repair should occur when the first execute succeeds"


def test_query_with_sql_no_repair_on_non_column_error(monkeypatch):
    spy = _Spy()
    sql = "SELECT bogus(("

    def gen(repair_context):
        return {"sql": sql, "explanation": "x", "confidence": 0.5}

    def execute(_sql):
        return pd.DataFrame(), "SQL execution error: Parser Error: syntax error"

    _install(monkeypatch, spy, gen, execute)
    result = sg.query_with_sql("bad query", _SCHEMA)

    assert result["error"] is not None and "Parser Error" in result["error"]
    assert len(spy.gen_calls) == 1, "Syntax errors must NOT trigger a repair retry"
