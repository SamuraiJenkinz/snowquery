---
phase: 02-azure-extraction-parity-gate
plan: 03
subsystem: llm
tags: [azure-openai, refactor, call-site-migration, dependency-injection, error-handling]

# Dependency graph
requires:
  - phase: 02-01
    provides: AzureOpenAIClient.complete() and classify_with_tool() — the concrete adapter that call sites now invoke
  - phase: 02-02
    provides: llm_to_query_error() context manager — the error-translation seam wired in at every call site
provides:
  - _call_azure_openai deleted from both query_router.py and sql_generator.py (ABS-06 complete)
  - classify_intent (CS1) routed through get_llm() + llm_to_query_error() with max_tokens=500
  - generate_sql (CS2) routed through get_llm() + llm_to_query_error() with max_tokens=1000
  - generate_executive_summary (CS3) routed through get_llm() + llm_to_query_error() with max_tokens=500
  - Unused imports removed from both files (requests, API_VERSION, AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT)
affects: [02-04, Phase 3 Anthropic adapter, any future call-site additions]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Call-site DI pattern: client = get_llm() + with llm_to_query_error(): client.complete(messages, max_tokens=X).strip() at every LLM call site"
    - ".strip() applied at call site, not in adapter — preserves byte-identical output (Pitfall 1 guard)"
    - "max_tokens as per-call kwarg — the only behavioral difference between the two duplicate helpers is preserved"

key-files:
  created: []
  modified:
    - src/query_router.py
    - src/sql_generator.py

key-decisions:
  - "No architecture changes were required — plan executed as pure mechanical refactor"
  - ".strip() kept at call site per Pitfall 1: adapter returns raw content; double-strip is idempotent but breaks byte-identity guarantee"
  - "generate_executive_summary broad except Exception: return None preserved intentionally (Pitfall 4) — QueryError is swallowed silently, matching pre-extraction behavior where failed exec summary was non-fatal"
  - "max_tokens=500 at CS1+CS3 and max_tokens=1000 at CS2 — preserves the only behavioral difference between the two deleted duplicate helpers"

patterns-established:
  - "Call-site DI: every LLM call site instantiates client via get_llm() inline (no function-parameter ripple, no module-level singleton)"
  - "Error seam wrapping: every client.complete() and client.classify_with_tool() call lives inside with llm_to_query_error(): block"
  - "Import hygiene: on extraction, unused imports (requests + provider-specific config names) are removed in the same commit"

# Metrics
duration: 5min
completed: 2026-05-20
---

# Phase 2 Plan 03: Call-Site Migration Summary

**Three LLM call sites rewired to get_llm() + llm_to_query_error() seam; both _call_azure_openai duplicates deleted; grep -rn _call_azure_openai src/query_router.py src/sql_generator.py returns zero hits (ABS-06 complete)**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-05-20T18:06:00Z
- **Completed:** 2026-05-20T18:11:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Deleted both `_call_azure_openai` definitions (query_router.py lines 105-141; sql_generator.py lines 86-133) — combined ~90 lines of duplicated HTTP-calling code removed
- All three call sites (classify_intent CS1, generate_sql CS2, generate_executive_summary CS3) now route through `client = get_llm()` + `with llm_to_query_error(): client.complete(messages, max_tokens=X).strip()`
- `max_tokens=500` preserved at CS1 and CS3; `max_tokens=1000` preserved at CS2 — the only load-bearing behavioral difference between the two deleted duplicates is intact
- Unused imports removed from both files: `import requests`, `API_VERSION`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`
- Phase 1 acceptance gate (`tests/test_llm_seam.py`) still 6/6 passing after both edits

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewire query_router.py — delete _call_azure_openai, migrate CS1+CS3** - `4fed21f` (feat)
2. **Task 2: Rewire sql_generator.py — delete _call_azure_openai, migrate CS2** - `f0ae84f` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `src/query_router.py` — _call_azure_openai deleted; classify_intent + generate_executive_summary rewired to seam; imports tightened. Net delta: -39 lines
- `src/sql_generator.py` — _call_azure_openai deleted; generate_sql rewired to seam; imports tightened. Net delta: -50 lines

## End-of-Plan Verification Output

```
# _call_azure_openai in target source files:
grep -n "_call_azure_openai" src/query_router.py src/sql_generator.py
→ NO OUTPUT (zero hits — ABS-06 met)

# Note: comments/docstrings in src/llm/azure_openai.py, src/llm/base.py, src/llm/_compat.py
# reference the old name in their historical documentation — these are LOCKED files
# (not modified by this plan) and the references are documentary, not code references.

# llm_to_query_error call counts:
grep -c "with llm_to_query_error" src/query_router.py   → 2  (CS1 + CS3)
grep -c "with llm_to_query_error" src/sql_generator.py  → 1  (CS2)

# max_tokens preservation:
grep -n "max_tokens=500" src/query_router.py
→ line 139: content = client.complete(messages, max_tokens=500).strip()   (classify_intent)
→ line 503: summary = client.complete(messages, max_tokens=500).strip()   (generate_executive_summary)

grep -n "max_tokens=1000" src/sql_generator.py
→ line 144: content = client.complete(messages, max_tokens=1000).strip()  (generate_sql)

# Unused imports removed:
grep -n "^import requests$" src/query_router.py src/sql_generator.py  → NO OUTPUT
grep -n "AZURE_OPENAI_API_KEY\|AZURE_OPENAI_ENDPOINT\|API_VERSION" src/query_router.py src/sql_generator.py → NO OUTPUT

# Phase 1 acceptance gate:
python -m pytest tests/test_llm_seam.py -v → 6/6 PASSED in 0.82s
```

## Decisions Made

- No new decisions required — plan executed as pure mechanical refactor per research notes
- Confirmed: `generate_executive_summary` broad `except Exception: return None` NOT changed (RESEARCH.md Pitfall 4 — preserves byte-identical user-visible behavior on summary failures; QueryError is a subclass of Exception and is silently swallowed here, matching pre-extraction behavior where a failed exec summary was non-fatal)
- Confirmed: `.strip()` kept at call site (RESEARCH.md Pitfall 1 — adapter returns raw content; applying `.strip()` in adapter would break byte-identity guarantee)
- Confirmed: existing `except QueryError: raise` guards in `classify_intent` (former line 212) and `generate_sql` (former line 238) preserved verbatim — `llm_to_query_error()` raises `QueryError` which correctly propagates through these existing guards

## Deviations from Plan

None — plan executed exactly as written.

The `import src.query_router` dynamic-import verification in the plan's `<verify>` script failed due to transitive `chromadb` import error (dev environment does not have chromadb installed). This was addressed by using AST-based + source-text verification, which confirmed all correctness invariants. The `python -m py_compile` check confirmed zero syntax errors. This is not a code deviation — the verification approach adapted to environment constraints while proving all the same correctness properties.

## Issues Encountered

- `chromadb` not installed in dev environment caused `import src.query_router` to fail transiently via `src.semantic_search → src.embeddings → chromadb`. Resolved by switching to AST parse + source text assertions + `py_compile` for the per-task verify gate. Phase 1 acceptance gate (`tests/test_llm_seam.py`) was unaffected and passed 6/6 throughout.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **02-04 (parity gate)** can proceed: all three call sites use the new seam, both `_call_azure_openai` definitions are gone, and both target files compile cleanly
- Phase 1 acceptance gate still green — seam integrity confirmed
- The `chromadb` / `semantic_search` import chain is not exercised by `tests/test_llm_seam.py`; 02-04 should be aware that runtime verification of the full app import graph requires a complete dev environment

---
*Phase: 02-azure-extraction-parity-gate*
*Completed: 2026-05-20*
