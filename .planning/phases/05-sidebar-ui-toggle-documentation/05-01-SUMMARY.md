---
phase: 05-sidebar-ui-toggle-documentation
plan: 01
subsystem: infra
tags: [streamlit, cache_resource, sha256, abc, llm-factory]

# Dependency graph
requires:
  - phase: 01-abstraction-seam
    provides: LLMClient ABC + factory cache scaffold (_cache dict, _REGISTRY)
  - phase: 03-anthropic-mgti-adapter
    provides: AnthropicMGTIClient + startup-log provider= strings
  - phase: 04-strict-tools-and-smoke
    provides: 69-test combined acceptance suite (Phases 1+2+3+4)
provides:
  - "LLMClient.provider_name @property @abc.abstractmethod (single source of truth for provider identity strings)"
  - "src/llm/config.py::missing_vars(provider) — non-raising sibling of validate_config()"
  - "@_cache_resource on _get_llm_cached keyed on (provider, base_url, model, api_key_fingerprint)"
  - "_fingerprint(api_key) — one-way SHA-256 8-hex helper (RESEARCH.md Pitfall 1 guard)"
  - "Streamlit decorator with no-op pass-through fallback for non-Streamlit contexts"
affects: [05-02-sidebar-toggle, 05-03-per-message-caption, 05-04-documentation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "@st.cache_resource with no-op fallback for non-Streamlit contexts"
    - "Abstract property pattern (@property + @abc.abstractmethod) on ABC"
    - "patch.object on cached resolver (replaces dict-injection test pattern)"

key-files:
  created: []
  modified:
    - "src/llm/__init__.py (Phase 1 _cache dict deleted; @_cache_resource added; _fingerprint helper)"
    - "src/llm/config.py (missing_vars helper appended)"
    - "src/llm/base.py (provider_name abstract property added)"
    - "src/llm/azure_openai.py (concrete provider_name returns 'azure_openai')"
    - "src/llm/anthropic_mgti.py (concrete provider_name returns 'anthropic_mgti')"
    - "tests/test_llm_seam.py (autouse fixture + mid-test clear rewired; abstract-methods set updated)"
    - "tests/test_phase2_parity.py (autouse fixture + 7 LLMError-translation assertions rewired to patch.object)"
    - "tests/test_phase3_adapter.py (autouse fixture rewired)"
    - "tests/test_phase4_strict_tools.py (autouse fixture rewired)"

key-decisions:
  - "Single cache layer — Phase 1 module-level _cache dict deleted; @_cache_resource on _get_llm_cached is the only cache (RESEARCH.md Pitfall 6)"
  - "Cache key tuple order LOCKED: (provider, base_url, model, api_key_fingerprint) — switching ANY of these four re-resolves the adapter"
  - "_fingerprint empty key returns '' (NOT hash of empty bytes) — unconfigured-provider cache slot is distinct from any real key"
  - "_fingerprint uses hashlib.sha256(key.encode('utf-8')).hexdigest()[:8] — one-way, 32-bit entropy, infeasible to reverse"
  - "Streamlit decorator with try/except fallback — @_cache_resource works as pass-through for pytest/python -c (Phase 1 contract preserved)"
  - "missing_vars() as separate function (NOT validate_config(raise_on_missing=False)) — distinct API for distinct purpose (Open Question 3 resolved)"
  - "missing_vars unknown provider returns [] (not raises) — sidebar selectbox enum validates upstream; Pitfall 7 guard"
  - "provider_name as @property @abc.abstractmethod (NOT class attribute) — forces every future adapter to deliberately implement it (Open Question 1 resolved)"
  - "test_phase2_parity:354 WRITE rewired via patch.object (Option A from decision §7) — chosen over Option B (test mock at different seam, too invasive) and Option C (debug-only API surface, violates Pitfall 6)"
  - "_install_raising_client renamed to _make_raising_client (builder, not installer) — sets fake.provider_name = 'azure_openai' for spec=AzureOpenAIClient + Task 1.1 abstract property compatibility"
  - "_extract_model_from_endpoint imported from src.llm.azure_openai (NOT reimplemented) — leading underscore intentional, Phase 5 reaches across package internals"

patterns-established:
  - "Streamlit cache_resource decorator fallback: try import; except → def _cache_resource(func=None, **kw): pass-through. Tests defend missing .clear() via getattr+callable."
  - "Cache-key derivation order: load_settings() → provider-specific tuple extraction → _fingerprint(raw_key) → _get_llm_cached(*positional) — never construct adapter to read its cache-key fields"
  - "Test fake injection: patch.object(llm_pkg, '_get_llm_cached', return_value=fake) — replaces dict-injection (llm_pkg._cache[key] = fake) without adding debug-only API"

# Metrics
duration: ~15 min
completed: 2026-05-21
---

# Phase 5 Plan 01: Factory Cache + Helpers Summary

**Single cache layer with 4-arg tuple key (provider, base_url, model, api_key_fingerprint), SHA-256 one-way fingerprint, `missing_vars()` non-raising helper, and `provider_name` abstract property — pure src/llm/ infrastructure for Wave-2 Phase 5 plans to consume**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-05-21T21:40:00Z
- **Completed:** 2026-05-21T21:55:00Z
- **Tasks:** 4
- **Files modified:** 9 (5 src + 4 tests)

## Accomplishments
- Deleted Phase 1 module-level `_cache: dict[str, LLMClient]` — single cache layer only (RESEARCH.md Pitfall 6)
- Added `@_cache_resource` on `_get_llm_cached(provider, base_url, model, api_key_fingerprint)` — Streamlit cache_resource with no-op fallback for non-Streamlit contexts
- Added `_fingerprint(api_key)` — one-way SHA-256 8-hex; empty key returns `""` (distinct unconfigured slot, never `sha256(b"")`)
- Added `missing_vars(provider) -> list[str]` to `src/llm/config.py` — non-raising sibling of `validate_config()` for UI use
- Added `provider_name` as `@property @abc.abstractmethod` on `LLMClient`; concrete returns `"azure_openai"` / `"anthropic_mgti"` matching `_REGISTRY` keys and startup-log strings
- Rewired all 4 prior-phase test files (autouse fixtures + 1 WRITE-pattern + 7 inline `_cache.clear()` calls + 1 mid-test reset)
- Full 69-test suite remains GREEN (8 sec) — zero behavior regression at adapter or factory boundary

## Task Commits

Each task was committed atomically:

1. **Task 1.1: Add provider_name abstract property to LLMClient ABC** — `e8e50ed` (feat)
2. **Task 1.2: Add missing_vars() helper + re-export** — `cb124a1` (feat)
3. **Task 1.3: Refactor __init__.py — @_cache_resource + delete _cache + _fingerprint** — `0a9c5b6` (refactor)
4. **Task 1.4: Rewire all 4 prior-phase test files** — `cfa2a3c` (test)

**Plan metadata:** [pending — committed after this summary lands]

## Files Created/Modified

### src/ (5 files)
- `src/llm/__init__.py` — Phase 1 `_cache: dict` DELETED; `@_cache_resource` on `_get_llm_cached`; `_fingerprint()`; Streamlit import with no-op fallback; `missing_vars` re-exported
- `src/llm/config.py` — `missing_vars(provider) -> list[str]` appended after `validate_config` (which is unchanged)
- `src/llm/base.py` — `provider_name` abstract property added to `LLMClient`
- `src/llm/azure_openai.py` — concrete `provider_name` returns `"azure_openai"`
- `src/llm/anthropic_mgti.py` — concrete `provider_name` returns `"anthropic_mgti"`

### tests/ (4 files — REWIRED for the deleted `_cache` dict)
- `tests/test_llm_seam.py` — autouse fixture + line ~194 mid-test reset use `getattr(_get_llm_cached, "clear", None) + callable(...)`; `test_abc_contract_enforced` updated to expect `frozenset({"complete", "classify_with_tool", "provider_name"})`; inline `Complete`/`MissingOne` test subclasses got `provider_name` overrides
- `tests/test_phase2_parity.py` — autouse fixture rewired; `_install_raising_client` renamed to `_make_raising_client` (returns fake, no module mutation); all 7 LLMError-translation assertions wrapped in `with patch.object(llm_pkg, "_get_llm_cached", return_value=fake): ...`; `fake.provider_name = "azure_openai"` set for spec compatibility
- `tests/test_phase3_adapter.py` — autouse fixture rewired (same `getattr+callable` pattern)
- `tests/test_phase4_strict_tools.py` — autouse fixture rewired (same pattern)

## Decisions Made

All locked decisions §1–§12 from the plan executed verbatim. The two load-bearing choices:

- **Decision §7 — Option A for `test_phase2_parity.py:354` WRITE rewire.** Replaced `llm_pkg._cache["azure_openai"] = fake` with `with patch.object(llm_pkg, "_get_llm_cached", return_value=fake): ...`. Chosen over Option B (mock at different seam — too invasive) and Option C (`_set_cached_for_testing()` helper — violates Pitfall 6 single-cache lock). Side effect: refactored `_install_raising_client` into `_make_raising_client` (builder pattern, no module mutation); set `fake.provider_name = "azure_openai"` explicitly for Task 1.1 abstract-property compatibility under `MagicMock(spec=AzureOpenAIClient)`.

- **Decision §6 — Streamlit decorator no-op fallback.** `try: import streamlit; _cache_resource = st.cache_resource; except: def _cache_resource(func=None, **kwargs): ...` — pass-through when Streamlit unavailable; tests defend missing `.clear()` attribute via `getattr(..., "clear", None) + callable(...)`. Decision §6's "non-blocking Info 9" note (no `.clear()` in fallback) confirmed accurate — in pytest the decorator is the real `st.cache_resource` because Streamlit is installed, so `.clear()` resolves naturally; the defensive pattern still applies for environments without Streamlit.

## Deviations from Plan

**None — plan executed exactly as written.**

The plan's premise check (Step 0 of Task 1.4) listed expected `_cache` hits in tests; the live grep matched line numbers and counts closely enough (drift within ±2 lines on some), and all rewires landed without surprise. Step 6 (full pytest run) returned `69 passed in 7.91s` on first try — no debug loop needed.

## Issues Encountered

**None.**

The Task 1.1 → Task 1.4 ordering meant `pytest` would have produced expected `AttributeError`s if run between Task 1.3 and Task 1.4 (the plan's `<verify>` block flagged this explicitly; we honored the "do NOT yet run the test suite" instruction in Task 1.3 and ran the suite only after Task 1.4 completed). Result: a single green pytest run, not a debug loop.

## User Setup Required

None — Plan 05-01 is pure src/llm/ infrastructure + test isolation. `app.py` is untouched, no docs touched, no env vars added.

## Next Phase Readiness

### Unblocked

- **Plan 05-02 (sidebar toggle):** The sidebar renderer can now `from src.llm import missing_vars` for inline warning rendering, and trust that the cache invalidates on provider/key/url/model change via the 4-arg tuple.
- **Plan 05-03 (per-message caption):** `client.provider_name` is stable and abstract-enforced — captions read `getattr(client, "provider_name", ...)` with a guaranteed-correct stable string.
- **Plan 05-04 (documentation):** No documentation has been written yet; the README + USER_GUIDE work lands here per the phase plan.

### Combined Phase 1+2+3+4 result

`69 passed in 7.91s` (zero failures, one pre-existing deprecation warning about `jsonschema.__version__`). Same count and run-time as the Phase 4 close-out baseline — no regression.

### Verified untouched (no scope creep)

- `src/llm/_compat.py` — UNCHANGED (Phase 5 does not touch error-translation seam)
- `src/llm/errors.py` — UNCHANGED (no new typed errors)
- `src/llm/types.py` — UNCHANGED (no dataclass changes)
- `app.py` — UNCHANGED (Plan 05-02 territory)

### Concerns / Blockers

- The Phase 4 close-out concern stands: operator-run smoke gate against stage gateway (`python scripts/smoke_llm.py --provider both --verbose`) is still pending. Plan 05-01 does NOT depend on the smoke run because it only refactors infrastructure that was already exercised by the 69-test acceptance suite. Subsequent Phase 5 plans (especially 05-04 documentation) should reference the smoke gate as the final acceptance ritual before any deployment.

---
*Phase: 05-sidebar-ui-toggle-documentation*
*Completed: 2026-05-21*
