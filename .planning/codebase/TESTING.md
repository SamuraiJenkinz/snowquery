# Testing

**Analysis Date:** 2026-05-19

## Summary

**Test coverage: 0%** — no test infrastructure exists in this codebase.

This is a notable gap given the application:
- Generates SQL from LLM output (correctness + injection risk)
- Persists data to DuckDB and ChromaDB (state mutations)
- Integrates with an external API (Azure OpenAI)
- Routes user intent with fallback logic (multiple branches)

## What's Missing

**Test directory:** No `tests/`, `test/`, or `__tests__/` directory.

**Test files:** No `test_*.py` or `*_test.py` files found anywhere in the repo.

**Test config:** No `pytest.ini`, `pyproject.toml`, `setup.cfg`, `conftest.py`, or `tox.ini`.

**Test dependencies:** `requirements.txt` does not include `pytest`, `pytest-mock`, `pytest-cov`, `hypothesis`, or any other testing library.

**CI:** No `.github/workflows/`, `.gitlab-ci.yml`, or other CI configuration present.

## Manual Testing Posture

Based on git history and code structure, testing appears to be manual via:
- Streamlit UI interaction (`streamlit run app.py`)
- Iterative bug-fix commits (`fix: ...`, `Revert to stable version from 3 days ago` x2 in recent history)
- Visual inspection of chart output

The `Revert to stable version from 3 days ago` commits (`8877128`, `df545e7`) are a signal that regressions are caught by user observation rather than automated tests.

## High-Risk Untested Areas

These modules carry the most risk and would benefit from tests first:

| Module | Risk | Why |
|--------|------|-----|
| `src/sql_generator.py` | High | LLM output → SQL execution. SELECT-only check is regex-based. Prompt-injection could subvert. |
| `src/query_router.py` | High | Branching logic (semantic vs SQL vs hybrid). LLM-classified intent with heuristic fallback — many code paths. |
| `src/ingest.py` | Medium | CSV parsing with multi-encoding fallback, type inference, append/replace modes. Easy to silently corrupt data. |
| `src/embeddings.py` | Medium | ChromaDB collection lifecycle, batch embedding. Failures here degrade semantic search silently. |
| `src/chart_generator.py` | Medium | Chart type inference + category consolidation on arbitrary dataframes. Edge cases (empty df, single category, all-null columns). |
| `src/utils.py` | Low | Pure helpers — easiest to unit test, good starting point. |

## Recommended Test Strategy (when added)

**Phase 1 — Foundations:**
- Add `pytest`, `pytest-mock`, `pytest-cov` to `requirements.txt` (or split into `requirements-dev.txt`)
- Create `tests/` with `conftest.py` providing a temp DuckDB + ChromaDB fixture
- Unit tests for `src/utils.py` (pure helpers, no I/O)

**Phase 2 — Risky paths:**
- Unit tests for `src/sql_generator.py` SELECT-only validator with adversarial inputs (CTEs, comments, stacked statements)
- Mock Azure OpenAI client to test `src/query_router.py` branching deterministically
- Integration test: small CSV → ingest → embed → query → result (full pipeline)

**Phase 3 — UI:**
- Streamlit `AppTest` (>=1.40) for the Streamlit app surface
- Smoke test that `streamlit run app.py` doesn't import-error

## Frameworks & Tools (recommended, not installed)

- **pytest** — test runner
- **pytest-mock** — mocking helper
- **pytest-cov** — coverage
- **streamlit AppTest** — Streamlit-native UI testing (built into Streamlit >=1.28)
- **respx** or **requests-mock** — mock the Azure OpenAI HTTP calls
- **hypothesis** — property-based testing for the SQL validator

## Coverage Targets (proposed)

| Area | Initial target | Long-term |
|------|---------------|-----------|
| `src/utils.py` | 90% | 95% |
| `src/sql_generator.py` (validator) | 100% | 100% |
| `src/ingest.py` | 70% | 85% |
| `src/query_router.py` | 60% | 80% |
| Apps (`app*.py`, `designui.py`) | smoke only | 40% |

---

*Testing analysis: 2026-05-19 — written by orchestrator after quality mapper sandbox-write failure.*
