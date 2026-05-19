---
phase: 01-abstraction-seam
plan: 02
subsystem: api
tags: [python, dataclass, factory, lazy-import, importlib, jsonschema, azure-openai, anthropic]

# Dependency graph
requires:
  - phase: 01-abstraction-seam plan 01
    provides: LLMClient ABC, LLMError hierarchy, ToolSchema/ToolCall/ClassificationResultV1/IntentResult types
provides:
  - LLMSettings frozen dataclass (Azure + Anthropic fields, api_keys repr=False)
  - validate_config(provider) collecting ALL missing env vars before raising
  - load_settings() pure env reader
  - get_llm(provider=None) factory with module-level cache and lazy-import registry
  - AzureOpenAIClient stub (Phase 2 placeholder)
  - AnthropicMGTIClient stub (Phase 3 placeholder)
  - jsonschema>=4.26.0,<5 in requirements.txt
affects:
  - 01-abstraction-seam plan 03 (seam verification tests call get_llm, validate_config)
  - Phase 2 (Azure extraction replaces AzureOpenAIClient stub)
  - Phase 3 (Anthropic adapter replaces AnthropicMGTIClient stub)
  - Phase 4 (strict-tools uses jsonschema pin from requirements.txt)
  - Phase 5 (UI provider toggle uses get_llm + st.cache_resource)

# Tech tracking
tech-stack:
  added: [jsonschema>=4.26.0]
  patterns:
    - "Lazy-import registry: _REGISTRY maps provider name to 'module:ClassName' string resolved via importlib.import_module"
    - "Module-level cache: _cache dict keyed by resolved provider string, never by api_key (Phase 5 adds fingerprint if needed)"
    - "Streamlit-safe resolution: st.session_state access wrapped in try/except Exception for pytest/CLI compatibility"
    - "Collect-all validation: validate_config accumulates missing vars into list before raising (not fail-on-first)"

key-files:
  created:
    - src/llm/config.py
    - src/llm/azure_openai.py
    - src/llm/anthropic_mgti.py
  modified:
    - src/llm/__init__.py
    - requirements.txt

key-decisions:
  - "Factory does NOT call validate_config itself — explicit call at app.py top (Phase 5 wiring)"
  - "Cache key is provider string only — no api_key fingerprint (Phase 5 adds if mid-session reload needed)"
  - "Adapter stubs do NOT raise on __init__() so factory cache can store them in Phase 1"
  - "Streamlit access uses try/except Exception (not hasattr) per RESEARCH.md verified pattern"

patterns-established:
  - "Config pattern: frozen+slots dataclass with repr=False on secret fields (OBS-03)"
  - "Lazy adapter loading: string registry + importlib defers Phase 2/3 heavy imports until first call"

# Metrics
duration: 3min
completed: 2026-05-19
---

# Phase 1 Plan 02: Config + Factory + Stubs Summary

**get_llm factory with lazy-import registry, LLMSettings frozen dataclass (repr=False api keys), validate_config collecting all missing vars, and AzureOpenAI/Anthropic stubs — completing the Phase 1 abstraction seam**

## Performance

- **Duration:** 3 min
- **Started:** 2026-05-19T23:15:14Z
- **Completed:** 2026-05-19T23:18:14Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- `LLMSettings` frozen dataclass with all Azure and Anthropic fields; `azure_api_key` and `anthropic_api_key` use `field(repr=False)` enforcing OBS-03 by construction
- `validate_config(provider)` collects ALL missing required env vars before raising `LLMConfigError` (not fail-on-first), satisfying CFG-03
- `get_llm(provider=None)` factory resolves via kwarg > st.session_state > LLM_PROVIDER_DEFAULT env > "azure_openai" default (ABS-04, CFG-05) with module-level `_cache` keyed by provider string
- `AzureOpenAIClient` and `AnthropicMGTIClient` stubs instantiate without error and raise `NotImplementedError` on method calls; factory registers them via `_REGISTRY` lazy-import strings
- `jsonschema>=4.26.0,<5` added to requirements.txt for Phase 4 strict-tools validation (CFG-06)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create LLMSettings + validate_config config layer** — `2e4d678` (feat)
2. **Task 2: Wire adapter stubs and get_llm factory into __init__.py** — `dec5392` (feat)
3. **Task 3: Add jsonschema>=4.26.0,<5 to requirements.txt** — `193abcf` (chore)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

| File | Lines | Role |
|------|-------|------|
| `src/llm/config.py` | 133 | LLMSettings dataclass + _REQUIRED_VARS + load_settings + validate_config + DEFAULT_PROVIDER |
| `src/llm/azure_openai.py` | 46 | AzureOpenAIClient stub extending LLMClient (Phase 2 placeholder) |
| `src/llm/anthropic_mgti.py` | 47 | AnthropicMGTIClient stub extending LLMClient (Phase 3/4 placeholder) |
| `src/llm/__init__.py` | 143 | Upgraded to full factory: get_llm, _REGISTRY, _cache, all re-exports |
| `requirements.txt` | 17 | Added jsonschema>=4.26.0,<5 with Phase 4 context comment |

## Verification Results

All verification assertions passed (output: `PLAN 02 VERIFICATION OK`):

1. **get_llm resolution order verified** — kwarg overrides env, env overrides default, `get_llm()` with nothing set falls back to `azure_openai` (CFG-05)
2. **Cache idempotence verified** — `get_llm('azure_openai')` twice returns `c1 is c2`
3. **validate_config lists ALL missing vars** — both `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` appear in the error message when both are absent; Anthropic validation lists `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`
4. **OBS-03 repr safety verified** — `repr(LLMSettings(azure_api_key='LEAK_ME_1', anthropic_api_key='LEAK_ME_2'))` contains neither value
5. **jsonschema pin verified** — `jsonschema>=4.26.0,<5` present in requirements.txt and readable as pip-parseable line

## Decisions Made

- Factory does NOT call `validate_config()` itself — that's an explicit call at `app.py` startup (Phase 5 wiring, per locked decision in RESEARCH.md Open Question #1)
- Cache key is resolved provider string only (no api_key fingerprint) — Phase 5 adds fingerprint if mid-session key reload becomes a requirement
- Adapter `__init__` methods are no-ops in Phase 1 (do NOT raise) so the factory can cache the instance; Phase 2/3 will add env-var reading and validation there
- Streamlit session_state access wrapped in `try/except Exception` (not `hasattr`) per RESEARCH.md "Streamlit-safety issue" verified pattern

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. The Streamlit runtime warnings (`missing ScriptRunContext`) during verification runs are expected and handled gracefully by the `try/except Exception` wrapper in `_resolve_provider`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 03 (seam verification tests) can now run against the complete seam:
- `get_llm` factory is callable and returns cached `LLMClient` instances
- `validate_config` exposes the full missing-var list
- Both adapter stubs exist and their `NotImplementedError` messages reference correct phases
- `repr(LLMSettings(...))` is confirmed safe (no key leakage)

No blockers. Phase 1 carries forward existing concerns from STATE.md (MGTI strict-tools staging verification, usage block pass-through) — these are Phase 3/4 concerns, not blockers for Plan 03.

---
*Phase: 01-abstraction-seam*
*Completed: 2026-05-19*
