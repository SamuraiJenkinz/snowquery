---
phase: 03-anthropic-mgti-adapter
plan: 01
subsystem: infra
tags: [config, env, logging, observability, adapter, azure-openai]

# Dependency graph
requires:
  - phase: 02-azure-extraction-parity-gate
    provides: "AzureOpenAIClient (Phase 2 locked __init__, complete, classify_with_tool, __repr__, helpers); 18-test parity gate must stay green"
  - phase: 01-abstraction-seam
    provides: "Factory cache in src/llm/__init__.py (_cache dict) — guarantees __init__ runs once per provider per process"
provides:
  - "Extended .env.example with all 9 Phase 3 vars (LLM_PROVIDER_DEFAULT + 8 ANTHROPIC_*) at NAME=value with documented defaults matching LLMSettings"
  - "AzureOpenAIClient.__init__ emits one llm_provider_loaded log event with extra={provider, base_url} — Azure half of SC #5"
  - "Symmetric startup-log pattern that Plan 03 mirrors verbatim in AnthropicMGTIClient.__init__"
affects: [03-02-compat-dispatch, 03-03-anthropic-adapter, 03-04-acceptance-gate, 05-ui-cache-key]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Structured startup-log pattern: logger.info('llm_provider_loaded', extra={provider, base_url}) inside adapter __init__; cache provides at-most-once-per-process semantics"
    - "Documented-defaults convention: .env.example carries the same default values as LLMSettings dataclass — both files are the operator-facing contract"

key-files:
  created: []
  modified:
    - ".env.example (4 lines + LOG_LEVEL → 34 lines; +9 Anthropic vars + section comments)"
    - "src/llm/azure_openai.py (+10 lines inside __init__ only; all other Phase 2 code byte-identical)"

key-decisions:
  - "Startup log lives in adapter __init__ (not in factory __init__.py) so each adapter owns its own observability contract; factory cache handles idempotence"
  - "Event tag llm_provider_loaded is distinct from llm_call (different event type, different field-name namespace: 'provider'/'base_url' vs 'llm_provider'/'llm_model')"
  - "Log fires unconditionally — even with empty base_url — so the operator sees 'I tried to load azure_openai and got base_url=\"\"' as actionable signal, not a silent skip"
  - "ANTHROPIC_MODEL placeholder uses a concrete eu.anthropic.claude- value (not a generic stub) so cp .env.example .env produces a config that constructs without LLMConfigError; SC #2's prefix check passes against the template"
  - ".env.example default LLM_PROVIDER_DEFAULT=azure_openai is locked from Phase 5 — Phase 3 does NOT flip the default; existing deployments remain byte-identical until an operator opts in"

patterns-established:
  - "Wave-1 / Plan-01: foundational additive edits (config + observability) that decouple from later adapter rewrites — no file conflict with parallel Plan 02 (which edits _compat.py)"
  - "Append-don't-replace discipline for .env.example: existing Azure/LOG_LEVEL lines preserved verbatim; new section sits below a blank line + section comment"
  - "Phase 2 acceptance gate (18 tests) is treated as a regression contract — any Phase 3 plan that touches azure_openai.py must re-run it and show 18/18 before commit"

# Metrics
duration: 3min
completed: 2026-05-21
---

# Phase 3 Plan 01: env + startup log Summary

**Extended .env.example with 9 Anthropic-related vars and added a single llm_provider_loaded log event to AzureOpenAIClient.__init__ so SC #4 (config template) and the Azure half of SC #5 (startup observability) are wired in before the adapter rewrite lands.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-05-21T14:57:33Z
- **Completed:** 2026-05-21T15:00:17Z
- **Tasks:** 2/2
- **Files modified:** 2

## Accomplishments

- `.env.example` extended from 4 vars + LOG_LEVEL (7 non-blank lines) to 4 vars + LOG_LEVEL + 9 Anthropic vars + section comments (34 lines total). All 9 new vars present as `NAME=value` with non-empty documented defaults matching `LLMSettings` in `src/llm/config.py`.
- `AzureOpenAIClient.__init__` now emits exactly one `logger.info("llm_provider_loaded", extra={"provider": "azure_openai", "base_url": self._endpoint})` event at construction. Factory cache guarantees once-per-process per provider.
- Phase 1 + Phase 2 acceptance gates: **18 passed in 8.48s** — zero regression. `__repr__`, `complete`, `classify_with_tool`, `_log_llm_call`, `_extract_model_from_endpoint`, and the module docstring/imports are byte-identical to Phase 2.

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend .env.example with 9 Anthropic vars** — `5ba5e0b` (chore)
2. **Task 2: Add llm_provider_loaded startup log to AzureOpenAIClient.__init__** — `5c09979` (feat)

## Files Created/Modified

### `.env.example` (4 vars + LOG_LEVEL → 4 vars + LOG_LEVEL + 9 Anthropic vars; 7 → 34 lines)

Newly added `NAME=value` pairs (in file order):

1. `LLM_PROVIDER_DEFAULT=azure_openai` — Phase 5 locked default
2. `ANTHROPIC_BASE_URL=https://stage.int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1` — staging URL (safer template; prod URL documented in comment above)
3. `ANTHROPIC_API_KEY=your-anthropic-api-key-here` — placeholder
4. `ANTHROPIC_MODEL=eu.anthropic.claude-sonnet-4-5-20250929-v1:0` — concrete value, passes SC #2 `eu.anthropic.claude-` prefix check
5. `ANTHROPIC_VERSION=bedrock-2023-05-31` — matches `LLMSettings.anthropic_version` default
6. `ANTHROPIC_MAX_TOKENS=1024` — matches default
7. `ANTHROPIC_TEMPERATURE=0.0` — matches default
8. `ANTHROPIC_TIMEOUT_S=30` — matches default
9. `ANTHROPIC_TOOLS_SUPPORTED=true` — matches default; Phase 4 escape hatch

### `src/llm/azure_openai.py` — `__init__` diff (only change; everything else byte-identical)

```diff
@@ -83,6 +83,16 @@ class AzureOpenAIClient(LLMClient):
         self._api_version: str = settings.azure_api_version
         self._model: str = _extract_model_from_endpoint(self._endpoint)

+        # SC #5: log the configured base URL once per loadable provider. The
+        # factory cache (src/llm/__init__.py _cache dict) ensures __init__ runs
+        # at most once per provider per process — so this emits exactly one
+        # llm_provider_loaded event per provider, even if get_llm() is called
+        # repeatedly. Symmetric with AnthropicMGTIClient.__init__ (Phase 3 Plan 03).
+        logger.info(
+            "llm_provider_loaded",
+            extra={"provider": "azure_openai", "base_url": self._endpoint},
+        )
+
     def __repr__(self) -> str:
         # OBS-03: never include self._api_key in repr.
         return "AzureOpenAIClient()"
```

## Decisions Made

- **Startup log lives in adapter `__init__`, not in factory** — Each adapter owns its own observability contract; symmetric pattern between providers; factory cache handles "once per process" idempotence at the consumer boundary, not the producer.
- **Distinct event tag `llm_provider_loaded` vs `llm_call`** — Two different lifecycle events deserve two different tags; field-name namespaces also kept disjoint (`provider`/`base_url` here vs `llm_*` in `_log_llm_call`) so dashboards can filter cleanly.
- **Log fires unconditionally with empty `base_url` allowed** — Operator wants to see "I tried to load `azure_openai` and got `base_url=''`" as a signal, not a silent skip; verified by Task 2's verification harness which strips Azure env vars and asserts the log still fires.
- **ANTHROPIC_MODEL placeholder is a concrete `eu.anthropic.claude-sonnet-4-5-20250929-v1:0`** — Not a generic stub, because SC #2's prefix check (`eu.anthropic.claude-`) runs against whatever the operator drops into `.env`; a stub like `your-model-here` would force every fresh-clone developer to hit `LLMConfigError` at construction before they can even smoke-test.

## Deviations from Plan

None - plan executed exactly as written.

Both tasks ran clean against the written verification harness. Phase 2 acceptance gate (18 tests) green on first run after the `__init__` edit; no Phase 2 invariant disturbed.

## Issues Encountered

None.

The only ambient noise was the parallel Wave 1 sibling plan (03-02) leaving `src/llm/_compat.py` modified in the working tree — expected per the plan's parallel-execution contract, and explicitly outside this plan's commit surface. This plan's two commits touched exactly `.env.example` and `src/llm/azure_openai.py`, verified by `git diff --name-only HEAD~2 HEAD`.

## User Setup Required

None - no external service configuration required for this plan. (Operators will eventually need to populate `.env` with real `ANTHROPIC_API_KEY` and adjust `ANTHROPIC_BASE_URL` to prod when Phase 3 ships end-to-end — that handoff is owned by Plan 04's acceptance documentation, not this plan.)

## Next Phase Readiness

- **SC #4** is now wholly satisfied at the file level — every required Anthropic env var has a documented default in `.env.example` matching `LLMSettings`. Plan 04's pytest grep-assertion will confirm.
- **SC #5** is half-satisfied — Azure adapter logs once per process. Plan 03 must add the symmetric `logger.info("llm_provider_loaded", extra={"provider": "anthropic_mgti", "base_url": self._base_url})` block inside `AnthropicMGTIClient.__init__` to complete it.
- **Wave 1 contract honored** — Plan 02 (compat dispatch) and Plan 01 (this plan) had zero file conflict; both can be committed independently and Plan 04 will assert against the combined result.
- **No blockers** for Plan 03 (Anthropic adapter rewrite). The settings dataclass, env template, and observability hook are all in place; Plan 03's only remaining contract is to mirror this `__init__` log block.

---
*Phase: 03-anthropic-mgti-adapter*
*Completed: 2026-05-21*
