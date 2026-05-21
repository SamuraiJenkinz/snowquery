---
phase: 5
plan: 1
name: factory-cache-and-helpers
type: execute
wave: 1
depends_on: []
files_modified:
  - src/llm/__init__.py
  - src/llm/config.py
  - src/llm/base.py
  - src/llm/azure_openai.py
  - src/llm/anthropic_mgti.py
  - tests/test_llm_seam.py
  - tests/test_phase2_parity.py
  - tests/test_phase3_adapter.py
  - tests/test_phase4_strict_tools.py
autonomous: true

must_haves:
  truths:
    - "get_llm() resolves through @st.cache_resource keyed on (provider, base_url, model, api_key_fingerprint) — switching providers re-resolves the adapter"
    - "The Phase 1 module-level _cache: dict is DELETED — single cache layer only (RESEARCH.md Pitfall 6)"
    - "_fingerprint(api_key) returns a one-way 8-hex-char SHA-256 prefix; empty key returns '' (never a hash-of-empty-bytes); raw key never appears in the cache key tuple (RESEARCH.md Pitfall 1)"
    - "src/llm/config.py exposes missing_vars(provider) -> list[str] — non-raising sibling of validate_config(); empty list = ok"
    - "LLMClient.provider_name is an abstract property on the ABC; AzureOpenAIClient returns 'azure_openai'; AnthropicMGTIClient returns 'anthropic_mgti'"
    - "Outside a Streamlit session (e.g. pytest, python -c), get_llm still works — the @st.cache_resource decorated helper is callable without Streamlit context"
    - "All Phase 1+2+3+4 tests still pass (69/69) — no behavior regression at adapter or factory boundary; ALL 4 prior-phase test files (test_llm_seam, test_phase2_parity, test_phase3_adapter, test_phase4_strict_tools) have had their _cache touches rewired to the new cache surface"
  artifacts:
    - path: "src/llm/__init__.py"
      provides: "Refactored get_llm() using @st.cache_resource; _fingerprint() helper; deleted _cache dict"
      contains: "@st.cache_resource"
    - path: "src/llm/config.py"
      provides: "missing_vars(provider) -> list[str] non-raising helper"
      exports: ["missing_vars", "validate_config", "load_settings", "LLMSettings", "DEFAULT_PROVIDER", "_REQUIRED_VARS"]
    - path: "src/llm/base.py"
      provides: "LLMClient ABC with abstract provider_name property"
      contains: "provider_name"
    - path: "src/llm/azure_openai.py"
      provides: "AzureOpenAIClient.provider_name = 'azure_openai'"
      contains: 'return "azure_openai"'
    - path: "src/llm/anthropic_mgti.py"
      provides: "AnthropicMGTIClient.provider_name = 'anthropic_mgti'"
      contains: 'return "anthropic_mgti"'
  key_links:
    - from: "src/llm/__init__.py::get_llm"
      to: "src/llm/__init__.py::_get_llm_cached"
      via: "computes (provider, base_url, model, fingerprint) BEFORE the cached call"
      pattern: "_get_llm_cached\\(provider, base_url, model, fingerprint\\)"
    - from: "src/llm/__init__.py::_fingerprint"
      to: "hashlib.sha256"
      via: "one-way hash, truncated to 8 hex chars; empty input returns ''"
      pattern: "hashlib\\.sha256.*hexdigest"
    - from: "src/llm/config.py::missing_vars"
      to: "src/llm/config.py::_REQUIRED_VARS"
      via: "iterate _REQUIRED_VARS[provider]; return names where os.getenv() falsy"
      pattern: "_REQUIRED_VARS\\["
---

<objective>
Refactor `src/llm/__init__.py` to use `@st.cache_resource` with a tuple cache key `(provider, base_url, model, api_key_fingerprint)`; DELETE the Phase 1 module-level `_cache: dict` (single cache layer per RESEARCH.md Pitfall 6); add a one-way SHA-256 `_fingerprint()` helper (RESEARCH.md Pitfall 1); add `missing_vars(provider) -> list[str]` to `src/llm/config.py` as the non-raising UI variant of `validate_config()`; add an abstract `provider_name` property to `LLMClient` and concrete overrides on both adapters (resolves Open Question #1 / RESEARCH.md Pitfall 8). Rewire ALL prior-phase test files that touched the old `_cache` dict so the full 69-test suite stays green.

Purpose: This plan is the foundation Wave 2 plans consume. Without the cache key tuple, switching providers mid-session reuses the wrong adapter (SC #2 broken). Without `missing_vars()`, the sidebar warning either throws or has to parse exception messages (SC #3 broken). Without `provider_name`, the per-message caption falls back to brittle session_state reads (SC #4 fragile). The five `src/llm/` files touched here are pure infrastructure (no UI, no docs). The four test-file rewires are mandatory to prevent the `_cache.clear()` and `_cache["..."] = fake` references in prior-phase tests from `AttributeError`-ing under the new cache surface.

Output: Three behavior changes — (a) the factory cache key includes raw key fingerprint and re-resolves on provider/key/url/model change; (b) `missing_vars()` returns a list of missing env-var names without raising; (c) every adapter instance reports its canonical provider name via a stable property. All existing 69 tests still pass after their `_cache`-touching fixtures and test bodies are rewired.
</objective>

<execution_context>
@C:\Users\taylo\.claude/get-shit-done/workflows/execute-plan.md
@C:\Users\taylo\.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/05-sidebar-ui-toggle-documentation/05-CONTEXT.md
@.planning/phases/05-sidebar-ui-toggle-documentation/05-RESEARCH.md

# Files modified
@src/llm/__init__.py
@src/llm/config.py
@src/llm/base.py
@src/llm/azure_openai.py
@src/llm/anthropic_mgti.py
@tests/test_llm_seam.py
@tests/test_phase2_parity.py
@tests/test_phase3_adapter.py
@tests/test_phase4_strict_tools.py

# Reference: existing Streamlit st.session_state try/except pattern in get_llm()
# Reference: _extract_model_from_endpoint exists at azure_openai.py:35 — module-level, callable from outside
</context>

<decisions>
## Decisions locked for this plan

1. **Single cache layer.** DELETE `_cache: dict[str, LLMClient] = {}` and all `_cache[...]` / `_cache.clear()` references inside `src/llm/__init__.py`. The new `@st.cache_resource`-decorated `_get_llm_cached(...)` IS the only cache. RESEARCH.md Pitfall 6 + Phase 1 comment at `__init__.py:59-60` explicitly anticipates this.

2. **Cache key tuple order:** `(provider: str, base_url: str, model: str, api_key_fingerprint: str)` — exactly the order from SC #2 and RESEARCH.md Recommendation 1. All positional args, all hashable strings. `@st.cache_resource` keys per-argument-tuple.

3. **`_fingerprint(api_key)` rule** (RESEARCH.md Pitfall 1):
   - Empty / None / falsy key → return `""` (NOT `hashlib.sha256(b"").hexdigest()[:8]` — empty-key cache slot must be distinct from any real key's slot).
   - Non-empty key → `hashlib.sha256(key.encode("utf-8")).hexdigest()[:8]`.
   - NEVER use substring of raw key. NEVER include the raw key as a cache-key arg.

4. **Pre-construction key derivation order is FIXED:**
   ```
   settings = load_settings()
   if provider == "azure_openai":
       base_url = settings.azure_endpoint
       model = _extract_model_from_endpoint(settings.azure_endpoint)
       raw_key = settings.azure_api_key
   elif provider == "anthropic_mgti":
       base_url = settings.anthropic_base_url
       model = settings.anthropic_model
       raw_key = settings.anthropic_api_key
   else:
       raise LLMConfigError(...)  # unknown provider — pre-construction check
   fingerprint = _fingerprint(raw_key)
   return _get_llm_cached(provider, base_url, model, fingerprint)
   ```
   The cache-key inputs are read from `load_settings()` BEFORE constructing the adapter — we cannot compute the key from `self._model` / `self._base_url` because we need the key BEFORE the cached call (it IS the cache key).

5. **`_extract_model_from_endpoint` is imported, not reimplemented.** It already exists at `src/llm/azure_openai.py:35` as a module-level function. Import it: `from src.llm.azure_openai import _extract_model_from_endpoint`. Yes, the leading underscore is intentional — Phase 5 is allowed to reach across the package internals.

6. **Streamlit import is at function scope, NOT module scope.** Keep the `try: import streamlit as st ... except Exception:` pattern. The `@st.cache_resource` decorator must come from a module-level Streamlit import — but with a fallback: if Streamlit is not installed (e.g. testing minimal envs), define a no-op pass-through decorator. **Implementation:**
   ```python
   try:
       import streamlit as st
       _cache_resource = st.cache_resource
   except Exception:
       def _cache_resource(func=None, **kwargs):
           # No-op decorator for non-Streamlit contexts (pytest, python -c).
           # The cache is "always miss" — each get_llm() builds a new instance.
           # Acceptable: tests already create fresh adapters per-test.
           if func is None:
               return lambda f: f
           return func
   ```
   Then: `@_cache_resource` on the helper. This preserves the Phase-1 contract that `get_llm()` works outside a Streamlit session.

   **Limitation note (non-blocking — Info 9):** In the fallback (no-Streamlit) path, the no-op `_cache_resource` does NOT expose a `.clear()` method matching Streamlit's real `cache_resource.clear()` API. Tests that call `llm_pkg._get_llm_cached.clear()` are defended via `getattr(..., 'clear', None) + callable(...)` in the autouse fixtures (see Task 1.4) — so the absence of `.clear()` in the fallback is harmless (clear becomes a no-op when streamlit isn't decorating, which is correct because the fallback doesn't cache anyway).

7. **Test isolation: ALL FOUR prior-phase test files need rewires — not three.**

   **Premise check (run before editing — Blocker 1 grounding):**
   ```bash
   grep -nE "_cache" tests/*.py
   ```

   Verified findings (run this yourself; the planner did and got these exact hits):
   - `tests/test_llm_seam.py` — 3 hits, all `llm_pkg._cache.clear()` (lines 45, 47, 170).
   - `tests/test_phase2_parity.py` — **10 hits**, including:
     - 9× `llm_pkg._cache.clear()` (lines 55, 57, 357, 368, 377, 389, 411, 420, 437).
     - **1× WRITE: `llm_pkg._cache["azure_openai"] = fake` (line 354).**
   - `tests/test_phase3_adapter.py` — 2 hits (lines 63, 65), both `llm_pkg._cache.clear()` in the autouse fixture; plus the test name `test_factory_cache_dedupes_startup_log` at line 469 (just a name, no `_cache` reference — safe).
   - `tests/test_phase4_strict_tools.py` — 2 hits (lines 78, 80), both `llm_pkg._cache.clear()` in the autouse fixture.

   The earlier draft of this plan (and its decision §7) said `test_phase2_parity` "uses a different mechanism (Level B injection) so it does NOT need changing." **That was WRONG.** Line 354's `llm_pkg._cache["azure_openai"] = fake` is a WRITE to the module-level `_cache` dict — after Plan 05-01 deletes that dict, that write raises `AttributeError: module 'src.llm' has no attribute '_cache'`, killing the entire Phase 2 LLMError→QueryError translation cascade.

   **Rewire strategy for the WRITE at `test_phase2_parity.py:354` (decision — Option A chosen):**

   - **Option A (CHOSEN):** Replace the WRITE-to-`_cache`-then-rely-on-`get_llm`-cache-hit pattern with `patch.object(llm_pkg, "_get_llm_cached", return_value=fake)` inside a `with` block scoped to the assertion. This patches the cached resolver to return the test fake directly, bypassing real adapter construction — exactly the intent of the original `_cache["azure_openai"] = fake` injection.
   - **Option B** (refactor the test to mock at a different seam, e.g. `route_query`): rejected — too invasive; multiplies blast radius across the parity test surface.
   - **Option C** (re-introduce a public `_set_cached_for_testing(provider, client)` helper in `src/llm/__init__.py`): rejected — adds a debug-only API surface that exists ONLY for tests, which is exactly the kind of one-off escape hatch RESEARCH.md Pitfall 6 (single cache layer) is trying to prevent.

   **Why Option A:** `unittest.mock.patch.object` is a stdlib, well-understood pattern; the scope is local to one test; it preserves the test's original intent (substitute a fake client for `get_llm` resolution) without leaking new test surface into production code.

   **The four-file rewire scope is summarized in Task 1.4 below.**

   **Tests are part of this plan's `files_modified`** — frontmatter and `<files>` blocks updated accordingly.

8. **`missing_vars()` API surface = separate function** (resolves Open Question #3). Researcher recommended a separate function for API clarity over overloading `validate_config()` with a `raise_on_missing` flag. Confirmed. Signature: `missing_vars(provider: str) -> list[str]`. Empty list = ok. Unknown provider returns `[]` (caller validates against the selectbox enum; the function should not be the place to validate the provider string — that's `validate_config`'s job).

9. **`provider_name` is an abstract property on `LLMClient`** (resolves Open Question #1). Adding it now is one line on the ABC and one line per adapter. Phase 1 base.py uses `abc.abstractmethod` decorators; the property version is `@property @abc.abstractmethod` (two decorators). **Concrete returns:** `AzureOpenAIClient.provider_name → "azure_openai"`; `AnthropicMGTIClient.provider_name → "anthropic_mgti"`. These are the EXACT strings that appear in startup logs at `azure_openai.py:90` and `anthropic_mgti.py:190` (`extra={"provider": "azure_openai"/"anthropic_mgti", ...}`) — single source of truth lock.

10. **Public re-export of `missing_vars` in `src/llm/__init__.py`.** Add to `__all__` and the imports from `src.llm.config`. The sidebar in Plan 05-02 will `from src.llm import missing_vars`. Without re-export, callers must use `from src.llm.config import missing_vars` — less clean.

11. **No edits to `src/llm/_compat.py`, `src/llm/errors.py`, or `src/llm/types.py`.** Phase 5 does not touch the error translation seam, the typed errors, or the dataclass types. Plans 05-02 / 05-03 / 05-04 also do not touch these.

12. **No new dependencies.** `hashlib` is stdlib. `streamlit` is already in requirements.txt. `os` and `importlib` are stdlib (already imported).
</decisions>

<tasks>

<task type="auto">
  <name>Task 1.1: Add provider_name abstract property to LLMClient ABC + concrete overrides on both adapters</name>
  <files>src/llm/base.py, src/llm/azure_openai.py, src/llm/anthropic_mgti.py</files>
  <action>
**Goal:** Expose a stable canonical provider name on every adapter instance. Phase 5 Plan 05-03 reads `client.provider_name` for the per-message caption. Without this, the caption falls back to `st.session_state["llm_provider"]` which is brittle to refactors (RESEARCH.md Pitfall 8).

**Step 1 — `src/llm/base.py`** — add an abstract property AFTER the `classify_with_tool` method and BEFORE the closing of the class:

```python
    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Canonical provider identifier string.

        Stable strings that match the keys in src.llm.__init__._REGISTRY and
        the 'provider' field in the llm_provider_loaded / llm_call structured
        log events. Phase 5 UI reads this at message-write time to caption
        the assistant message with the provider that produced it.

        Returns:
            One of: "azure_openai", "anthropic_mgti" (or any future provider
            key — must match its _REGISTRY entry exactly).
        """
```

Two decorators are required (`@property` ABOVE `@abc.abstractmethod`) — Python evaluates bottom-up, so `abstractmethod` wraps the function, then `property` wraps the abstract function. This is the documented pattern for abstract properties.

**Step 2 — `src/llm/azure_openai.py`** — add the concrete override. Place it AFTER `__init__` and BEFORE `complete` for readability:

```python
    @property
    def provider_name(self) -> str:
        return "azure_openai"
```

**Step 3 — `src/llm/anthropic_mgti.py`** — add the concrete override in the same position (after `__init__`, before `complete`):

```python
    @property
    def provider_name(self) -> str:
        return "anthropic_mgti"
```

**Critical constraints:**
- The return string MUST match the existing `extra={"provider": "azure_openai"}` / `extra={"provider": "anthropic_mgti"}` strings in each adapter's `__init__` startup log block (search for `provider=` in each file to confirm).
- Both return strings MUST match the `_REGISTRY` keys in `src/llm/__init__.py:54-57`.
- Do NOT make this an attribute — the abstract property forces every future adapter to implement it deliberately.

**Verification of impact on existing tests:**
- `tests/test_llm_seam.py` — verify `LLMClient.__abstractmethods__` test (if present) still passes; `provider_name` is now in that set.
- If any test instantiates a `LLMClient` subclass that does NOT implement `provider_name`, that test will now fail with `TypeError`. Grep the test files for inline test subclasses (e.g. `class _Stub(LLMClient):`) and add a `provider_name` override to each.
  </action>
  <verify>
```bash
# Abstract property is present on the ABC
grep -nE "def provider_name|@abc.abstractmethod" src/llm/base.py

# Concrete returns exact strings
grep -nE "return \"azure_openai\"" src/llm/azure_openai.py
grep -nE "return \"anthropic_mgti\"" src/llm/anthropic_mgti.py

# Smoke: instantiate both adapters and check the property reads
python -c "
import os
os.environ['AZURE_OPENAI_ENDPOINT'] = 'https://example.openai.azure.com/openai/deployments/gpt-4o-mini/chat/completions'
os.environ['AZURE_OPENAI_API_KEY'] = 'k'
os.environ['ANTHROPIC_BASE_URL'] = 'https://example.com'
os.environ['ANTHROPIC_API_KEY'] = 'k'
os.environ['ANTHROPIC_MODEL'] = 'eu.anthropic.claude-sonnet-4-5-20250929-v1:0'
from src.llm.azure_openai import AzureOpenAIClient
from src.llm.anthropic_mgti import AnthropicMGTIClient
assert AzureOpenAIClient().provider_name == 'azure_openai'
assert AnthropicMGTIClient().provider_name == 'anthropic_mgti'
print('OK')
"
# Expected: OK

# Existing 69-test suite still green (none of the inline test subclasses
# should be missing the override — fix any that are). Note: this MAY fail
# until Task 1.4 rewires the prior-phase _cache touches — that's expected.
# Run pytest only after Task 1.4 completes if Task 1.4 hasn't run yet.
pytest tests/ -v --tb=short
# Expected (post-Task-1.4): 69 passed (same as before this task)
```
  </verify>
  <done>
`src/llm/base.py` exposes `provider_name` as an `@property @abc.abstractmethod` on `LLMClient`. `AzureOpenAIClient.provider_name` returns the literal `"azure_openai"`; `AnthropicMGTIClient.provider_name` returns the literal `"anthropic_mgti"` — both matching their existing startup-log `provider=` strings and `_REGISTRY` keys. Any inline `LLMClient` subclasses in the test suite have been given a `provider_name` override. (Full 69-test suite green is asserted at end-of-plan after Tasks 1.3 and 1.4.)
  </done>
</task>

<task type="auto">
  <name>Task 1.2: Add missing_vars() to src/llm/config.py + re-export from src/llm/__init__.py</name>
  <files>src/llm/config.py, src/llm/__init__.py</files>
  <action>
**Goal:** Provide a non-raising helper that the sidebar can call to detect missing env vars and render an inline warning. `validate_config()` raises `LLMConfigError`; the UI must not raise (RESEARCH.md Pitfall 7).

**Step 1 — append to `src/llm/config.py`** (after `validate_config`, do NOT modify `validate_config`):

```python
def missing_vars(provider: str) -> list[str]:
    """Return the list of missing required env-var names for `provider`.

    Non-raising sibling of validate_config(). For UI use — the Streamlit
    sidebar (Phase 5) calls this on every rerun to decide whether to show
    a missing-credentials warning and whether to disable chat input.

    Args:
        provider: Provider key (e.g. "azure_openai", "anthropic_mgti").

    Returns:
        List of env-var names that are unset or empty. Empty list means
        all required vars are populated and the provider is usable.
        Unknown provider returns [] — the caller is responsible for
        validating the provider string (the sidebar selectbox enum already
        guarantees this).

    Why a separate function (not validate_config(raise=False))?
        validate_config() is the startup-time guard — it raises on bad
        config so the app fails fast. missing_vars() is the runtime
        UI helper — it never raises, so the script keeps running and
        the user can switch providers without a crash.
    """
    if provider not in _REQUIRED_VARS:
        return []
    return [name for name in _REQUIRED_VARS[provider] if not os.getenv(name)]
```

**Step 2 — re-export from `src/llm/__init__.py`:**

In the `from src.llm.config import (...)` block (currently lines 26-31), add `missing_vars` to the imports list (alphabetical-ish — between `load_settings` and `validate_config` keeps order tidy).

In the `__all__` list at the bottom (currently around line 128), add `"missing_vars"` in the `# Config` group, between `"load_settings"` and `"validate_config"`.

**Step 3 — verify symmetry with `validate_config`:**

The "required" set must be the same for both. Both functions read `_REQUIRED_VARS` (the single source of truth in `config.py:53`) — no list duplication. If a future change adds a required var, both functions pick it up automatically.

**Step 4 — defensive note in code:**

The docstring's "Unknown provider returns []" choice is intentional — `validate_config("nonsense")` raises, but `missing_vars("nonsense")` returns `[]`. The sidebar selectbox in Plan 05-02 only emits known provider keys (the enum), so this can never happen in normal flow. If a typo'd `LLM_PROVIDER_DEFAULT=anthrop` reaches the sidebar, the clamp in Plan 05-02 catches it before `missing_vars` runs.

**Step 5 — do NOT touch `_REQUIRED_VARS` or `validate_config`.** This task is additive.
  </action>
  <verify>
```bash
# missing_vars exists with the right signature
grep -nE "^def missing_vars" src/llm/config.py
# Expected: 1 match

# Re-exported from src.llm package
grep -nE "missing_vars" src/llm/__init__.py
# Expected: 2+ matches (import line + __all__ entry)

# Smoke: behavior matches spec
python -c "
import os
# Clean env first
for k in ('AZURE_OPENAI_ENDPOINT','AZURE_OPENAI_API_KEY','ANTHROPIC_BASE_URL','ANTHROPIC_API_KEY','ANTHROPIC_MODEL'):
    os.environ.pop(k, None)
from src.llm import missing_vars
# All missing
assert missing_vars('azure_openai') == ['AZURE_OPENAI_ENDPOINT', 'AZURE_OPENAI_API_KEY'], missing_vars('azure_openai')
assert missing_vars('anthropic_mgti') == ['ANTHROPIC_BASE_URL', 'ANTHROPIC_API_KEY', 'ANTHROPIC_MODEL'], missing_vars('anthropic_mgti')
# Unknown provider: []
assert missing_vars('nonsense') == []
# Populate Azure → []
os.environ['AZURE_OPENAI_ENDPOINT'] = 'x'
os.environ['AZURE_OPENAI_API_KEY'] = 'y'
assert missing_vars('azure_openai') == []
# Partial Anthropic → only the still-missing one
os.environ['ANTHROPIC_BASE_URL'] = 'u'
assert missing_vars('anthropic_mgti') == ['ANTHROPIC_API_KEY', 'ANTHROPIC_MODEL']
print('OK')
"
# Expected: OK
```
  </verify>
  <done>
`missing_vars(provider: str) -> list[str]` is defined in `src/llm/config.py` after `validate_config`, reads `_REQUIRED_VARS` as single source of truth, returns `[]` for unknown providers, NEVER raises. `from src.llm import missing_vars` works. `__all__` updated. `validate_config()` itself is unchanged.
  </done>
</task>

<task type="auto">
  <name>Task 1.3: Refactor src/llm/__init__.py — @st.cache_resource on _get_llm_cached, delete _cache dict, add _fingerprint helper</name>
  <files>src/llm/__init__.py</files>
  <action>
**Goal:** Replace the Phase 1 module-level `_cache: dict[str, LLMClient]` with a single `@st.cache_resource`-decorated helper keyed on `(provider, base_url, model, api_key_fingerprint)`. RESEARCH.md Pitfalls 1 and 6.

**Read first:** `src/llm/__init__.py` end-to-end. Know what you are replacing.

**Refactor plan (write the new file in one Edit):**

1. **Imports — ADD:**
   - `import hashlib` (stdlib, no dependency add)
   - At module scope, add the Streamlit decorator fallback per locked decision §6:
     ```python
     try:
         import streamlit as st
         _cache_resource = st.cache_resource
     except Exception:
         def _cache_resource(func=None, **kwargs):
             """No-op cache_resource for non-Streamlit contexts (pytest, python -c).
             Each call to the wrapped function builds a fresh instance — which is
             fine because tests already isolate per-test via the autouse fixture
             that calls _get_llm_cached.clear()."""
             if func is None:
                 return lambda f: f
             return func
     ```
   - ADD `missing_vars` to the existing `from src.llm.config import (...)` block (Task 1.2 added it; this task surfaces it through the package re-export — alphabetical-ish place: between `load_settings` and `validate_config`).

2. **DELETE:**
   - The module-level `_cache: dict[str, LLMClient] = {}` line (currently line 61).
   - The comment block immediately above it (currently lines 59-60) — the comment is no longer accurate.

3. **ADD `_fingerprint` helper** AFTER `_import_class` and BEFORE `_resolve_provider`:

```python
def _fingerprint(api_key: str) -> str:
    """One-way 8-hex-char SHA-256 of the API key for cache-key inclusion.

    Empty key returns "" (the unconfigured-provider cache slot, distinct
    from any real key). Non-empty key returns the first 8 hex characters
    of the SHA-256 digest — sufficient to detect key rotation (32 bits of
    entropy, ~4 billion-way uniqueness), cryptographically infeasible to
    reverse.

    RESEARCH.md Pitfall 1: NEVER use a substring of the raw key (that
    leaks key material). NEVER put the raw key in the @st.cache_resource
    argument list (Streamlit may render arg values in debug output and
    error messages).
    """
    if not api_key:
        return ""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:8]
```

4. **REPLACE `get_llm` body** with a two-layer dispatch — the public `get_llm()` computes the cache-key tuple inputs, then delegates to the cached helper:

```python
@_cache_resource
def _get_llm_cached(
    provider: str, base_url: str, model: str, api_key_fingerprint: str
) -> LLMClient:
    """Cached adapter resolver — @st.cache_resource keyed on the 4-arg tuple.

    Called by get_llm() with pre-derived cache-key inputs. The cache key is
    (provider, base_url, model, api_key_fingerprint) per ROADMAP SC #2;
    switching ANY of these four re-resolves a fresh adapter instance.

    Args (all positional, all hashable strings — Streamlit cache-key requirement):
        provider: One of _REGISTRY keys.
        base_url: For Azure, the endpoint URL; for Anthropic, the proxy base URL.
        model: Model identifier (Azure deployment name or Anthropic model id).
        api_key_fingerprint: 8-hex-char SHA-256 of the raw API key, or "" if unset.
            NEVER the raw key itself (RESEARCH.md Pitfall 1).

    Returns:
        Cached LLMClient instance for this exact (provider, base_url, model, fingerprint)
        tuple. The cache survives across reruns inside a Streamlit session and is
        cleared automatically when any of the 4 args change.

    Raises:
        LLMConfigError: if `provider` is not in _REGISTRY.
    """
    if provider not in _REGISTRY:
        raise LLMConfigError(
            f"Unknown provider: {provider!r}. Known providers: "
            f"{sorted(_REGISTRY)}",
            provider=provider,
        )
    cls = _import_class(_REGISTRY[provider])
    return cls()


def get_llm(provider: str | None = None) -> LLMClient:
    """Return a cached LLMClient for the resolved provider (ABS-04).

    Resolution order (preserved from Phase 1):
        1. explicit kwarg
        2. Streamlit session_state["llm_provider"] (try/except — safe outside Streamlit)
        3. LLM_PROVIDER_DEFAULT env var
        4. fallback "azure_openai" (DEFAULT_PROVIDER)

    Cache: @st.cache_resource on _get_llm_cached, keyed on the 4-arg tuple
    (provider, base_url, model, api_key_fingerprint) per ROADMAP Phase 5 SC #2.
    Cache survives across Streamlit reruns and re-resolves on any key-tuple change.

    Outside a Streamlit session (e.g. pytest, python -c), the @_cache_resource
    decorator falls back to a no-op pass-through — each call builds a fresh
    instance. Tests isolate via _get_llm_cached.clear() in their autouse fixtures.

    Raises:
        LLMConfigError: if the resolved provider is not in _REGISTRY.
    """
    resolved = _resolve_provider(provider)

    # Compute cache-key inputs BEFORE the cached call (the tuple IS the key).
    # We cannot read base_url/model from a constructed instance because the
    # instance doesn't exist yet — that's the whole point of the cache.
    settings = load_settings()
    if resolved == "azure_openai":
        from src.llm.azure_openai import _extract_model_from_endpoint
        base_url = settings.azure_endpoint
        model = _extract_model_from_endpoint(settings.azure_endpoint)
        raw_key = settings.azure_api_key
    elif resolved == "anthropic_mgti":
        base_url = settings.anthropic_base_url
        model = settings.anthropic_model
        raw_key = settings.anthropic_api_key
    else:
        # Unknown provider — defer to _get_llm_cached, which raises with the
        # known-providers list (preserves Phase 1 error contract verbatim).
        return _get_llm_cached(resolved, "", "", "")

    fingerprint = _fingerprint(raw_key)
    return _get_llm_cached(resolved, base_url, model, fingerprint)
```

5. **Update `__all__`** — `missing_vars` already added by Task 1.2, but verify it's there. No other `__all__` changes needed (we are not exporting `_get_llm_cached` or `_fingerprint` — underscores = internal).

6. **Verify the existing `_resolve_provider` is UNCHANGED.** Its try/except Streamlit pattern still works. The fallback chain (kwarg > session > env > default) is preserved.

7. **Do NOT yet run the test suite.** Task 1.4 rewires the prior-phase tests that still reference the deleted `_cache` dict. Running pytest BEFORE Task 1.4 will produce AttributeErrors — that's expected. Run pytest at the END of Task 1.4.

8. **Final sanity (informational only — manual smoke):** the 4 plans below this one depend on the contract that `get_llm()` returns a fresh adapter when ANY of `(provider, base_url, model, fingerprint)` changes. Verify with this manual exercise:

```bash
python -c "
import os, importlib
# Set Azure env
os.environ['AZURE_OPENAI_ENDPOINT'] = 'https://a.openai.azure.com/openai/deployments/x/chat/completions'
os.environ['AZURE_OPENAI_API_KEY'] = 'key1'
import src.llm as llm_pkg
importlib.reload(llm_pkg)
c1 = llm_pkg.get_llm('azure_openai')
c2 = llm_pkg.get_llm('azure_openai')
print('same-args same instance:', c1 is c2)
# Change key → different fingerprint → different instance
os.environ['AZURE_OPENAI_API_KEY'] = 'key2'
c3 = llm_pkg.get_llm('azure_openai')
print('key-rotated different instance:', c1 is not c3)
"
# Expected (in a Streamlit context): both prints True
# Expected (outside Streamlit / fallback): same-args returns same instance because
# @_cache_resource is a no-op; the test suite tolerates both.
```

This manual exercise is informational — the load-bearing verification is the test suite (after Task 1.4).
  </action>
  <verify>
```bash
# 1. _cache dict is gone
grep -nE "^_cache" src/llm/__init__.py
# Expected: 0 matches

# 2. @_cache_resource decorator present
grep -nE "@_cache_resource" src/llm/__init__.py
# Expected: 1 match (on _get_llm_cached)

# 3. _fingerprint helper present and uses SHA-256
grep -nE "def _fingerprint|hashlib\.sha256" src/llm/__init__.py
# Expected: 2 matches (def line + hashlib usage)

# 4. Streamlit import with fallback
grep -nE "import streamlit|def _cache_resource" src/llm/__init__.py
# Expected: ≥2 matches (try import + except fallback def)

# 5. Empty-key fingerprint returns ""
python -c "
from src.llm import _fingerprint
assert _fingerprint('') == '', _fingerprint('')
hashed = _fingerprint('a-real-key-of-some-length')
assert len(hashed) == 8 and all(c in '0123456789abcdef' for c in hashed)
# Critical: fingerprint must NOT be a substring of the raw key
assert 'a-real-key' not in hashed and 'some' not in hashed
print('fingerprint:', hashed, 'OK')
"
# Expected: fingerprint: <8 hex chars> OK

# 6. Public surface preserved
python -c "from src.llm import get_llm, missing_vars, validate_config, load_settings, LLMSettings, DEFAULT_PROVIDER, LLMClient; print('OK')"
# Expected: OK

# 7. get_llm() still raises LLMConfigError on unknown provider
python -c "
from src.llm import get_llm
from src.llm.errors import LLMConfigError
try:
    get_llm('nonsense_provider')
    print('FAIL — should have raised')
except LLMConfigError as e:
    print('OK:', e)
"
# Expected: OK: Unknown provider: 'nonsense_provider'. Known providers: ['anthropic_mgti', 'azure_openai']

# 8. No leftover Phase-1 comment
grep -nE "Phase 5 may wrap this with" src/llm/__init__.py
# Expected: 0 matches (comment block removed with _cache dict)

# NOTE: do NOT run pytest here — Task 1.4 must complete first to rewire the
# prior-phase _cache touches. Running pytest before Task 1.4 produces expected
# AttributeErrors against the deleted _cache dict.
```
  </verify>
  <done>
`src/llm/__init__.py` uses a single cache layer: `@_cache_resource` on `_get_llm_cached(provider, base_url, model, api_key_fingerprint)`. The Phase 1 `_cache: dict` AND its surrounding comment block are deleted. `_fingerprint()` is one-way SHA-256 truncated to 8 hex chars; empty key returns `""` and the raw key never appears as a cache-key argument. Streamlit import has a no-op decorator fallback for non-Streamlit contexts. `_resolve_provider` is unchanged. `get_llm()` preserves the Phase 1 error contract (LLMConfigError on unknown provider, kwarg > session > env > default resolution order). Test suite is NOT yet expected to pass — Task 1.4 follows to rewire the four prior-phase test files that still reference `_cache`.
  </done>
</task>

<task type="auto">
  <name>Task 1.4: Rewire ALL FOUR prior-phase test files — replace _cache.clear() with _get_llm_cached.clear(); rewire the _cache["..."] = fake WRITE at test_phase2_parity.py:354 via patch.object</name>
  <files>tests/test_llm_seam.py, tests/test_phase2_parity.py, tests/test_phase3_adapter.py, tests/test_phase4_strict_tools.py</files>
  <action>
**Goal:** After Task 1.3 deletes the module-level `_cache` dict, four prior-phase test files still reference it. Rewire each so the full 69-test suite stays green.

**Step 0 — Premise check (Blocker 1 grounding):** run the grep below to confirm the exact hits on disk:

```bash
grep -nE "_cache" tests/*.py
```

Confirmed hits (from the planner's run; verify yours match — line numbers may have drifted slightly):
- `tests/test_llm_seam.py` — lines 45, 47, 170 (all `llm_pkg._cache.clear()`).
- `tests/test_phase2_parity.py` — lines 55, 57, 354 (WRITE), 357, 368, 377, 389, 411, 420, 437.
- `tests/test_phase3_adapter.py` — lines 63, 65 (in autouse `_clear_factory_cache` fixture); line 469 contains test name `test_factory_cache_dedupes_startup_log` (just a name, no rewire needed).
- `tests/test_phase4_strict_tools.py` — lines 78, 80 (in autouse `_clear_factory_cache` fixture).

If your grep returns a SIGNIFICANTLY different set, STOP and reconcile before editing — the test files may have been touched between this plan and execution.

**Step 1 — `tests/test_phase3_adapter.py` autouse fixture rewire.** Locate the `_clear_factory_cache` fixture at lines 60-68:

```python
@pytest.fixture(autouse=True)
def _clear_factory_cache():
    import src.llm as llm_pkg
    llm_pkg._cache.clear()
    yield
    llm_pkg._cache.clear()
```

Replace both `llm_pkg._cache.clear()` calls with the new defensive pattern:

```python
@pytest.fixture(autouse=True)
def _clear_factory_cache():
    """Each test sees an empty get_llm cache.

    Plan 05-01 deleted the module-level _cache dict and replaced it with
    @_cache_resource on _get_llm_cached. The decorated function exposes
    .clear() in real Streamlit; in the no-Streamlit fallback the decorator
    is a pass-through and no .clear() exists — getattr-with-callable check
    handles both contexts.
    """
    import src.llm as llm_pkg
    clear_fn = getattr(llm_pkg._get_llm_cached, "clear", None)
    if callable(clear_fn):
        clear_fn()
    yield
    clear_fn = getattr(llm_pkg._get_llm_cached, "clear", None)
    if callable(clear_fn):
        clear_fn()
```

**Step 2 — `tests/test_phase4_strict_tools.py` autouse fixture rewire.** Same exact pattern as Step 1 (lines 78, 80). Replace both `llm_pkg._cache.clear()` calls with the `getattr(... "clear", None) + callable(...)` pattern from Step 1.

**Step 3 — `tests/test_llm_seam.py` autouse fixture + line 170 rewire.** Locate the `_clear_factory_cache` fixture around lines 42-47:

```python
@pytest.fixture(autouse=True)
def _clear_factory_cache():
    import src.llm as llm_pkg
    llm_pkg._cache.clear()
    yield
    llm_pkg._cache.clear()
```

Replace both calls with the same `getattr + callable` pattern from Step 1.

Locate line 170 (an `llm_pkg._cache.clear()` outside the fixture — likely inside a specific test that needs an explicit mid-test cache reset). Replace with:

```python
clear_fn = getattr(llm_pkg._get_llm_cached, "clear", None)
if callable(clear_fn):
    clear_fn()
```

If the surrounding test relies on the cache being empty for a specific assertion (e.g. "first call after clear builds a fresh instance"), preserve that intent.

**Step 4 — `tests/test_phase2_parity.py` MULTIPLE rewires.** This is the file with the WRITE at line 354 (Blocker 1).

**(4a) The autouse fixture at lines 51-57:**

```python
@pytest.fixture(autouse=True)
def _clear_factory_cache():
    """Ensure each test sees an empty get_llm cache (the module-level _cache
    ...)"""
    import src.llm as llm_pkg
    llm_pkg._cache.clear()
    yield
    llm_pkg._cache.clear()
```

Replace both `llm_pkg._cache.clear()` with the `getattr + callable` pattern from Step 1. Update the docstring to reference `_get_llm_cached.clear()` instead of `module-level _cache dict`.

**(4b) The WRITE at line 354 — Option A rewire (Blocker 1 primary fix):**

Read the surrounding test (likely 10-30 lines around line 354) before editing. The pattern is approximately:

```python
def test_some_llmerror_path(...):
    fake = MagicMock(spec=LLMClient)
    fake.complete.side_effect = LLMError("...")
    llm_pkg._cache["azure_openai"] = fake     # ← LINE 354 — WRITE to deleted dict
    # ... rest of test calls route_query / process_query which internally calls get_llm()
    # ... and expects the LLMError to be translated to QueryError
    ...
    llm_pkg._cache.clear()                     # ← LINE 357 — also rewire (use Step-1 pattern)
```

**Rewire pattern — wrap the dependent code in `patch.object`:**

```python
def test_some_llmerror_path(...):
    fake = MagicMock(spec=LLMClient)
    fake.complete.side_effect = LLMError("...")
    # Plan 05-01 deleted llm_pkg._cache. To inject a fake adapter for the duration
    # of this test, patch _get_llm_cached to return the fake directly. This
    # preserves the original test intent: substitute a fake client for get_llm()
    # resolution without touching real adapter construction.
    with patch.object(llm_pkg, "_get_llm_cached", return_value=fake):
        # ... rest of test body — calls into route_query / process_query etc.
        ...
    # Post-with cleanup (still useful — clears any cache state from imports etc.)
    clear_fn = getattr(llm_pkg._get_llm_cached, "clear", None)
    if callable(clear_fn):
        clear_fn()
```

Critical notes for this rewire:

1. **Import `patch`** at the top of `test_phase2_parity.py` if not already imported: `from unittest.mock import patch, MagicMock`. Check first; only add if missing.
2. **Scope `patch.object` narrowly** — wrap only the section of the test that calls into `get_llm()`. Outside the `with` block the original cache behavior resumes.
3. **The fake must satisfy `provider_name` (Plan 05-01 Task 1.1 adds it as an abstract property).** If `MagicMock(spec=LLMClient)` is used, `MagicMock` auto-stubs the property as a `MagicMock` (truthy but not a string) — for tests that read `fake.provider_name`, set it explicitly: `fake.provider_name = "azure_openai"` (or whatever the test needs).
4. **`_get_llm_cached` is called WITH ARGS** by `get_llm()`. `return_value=fake` returns the fake regardless of args — exactly the substitute-the-resolver intent. If the test asserts on `_get_llm_cached` call args, replace `return_value=fake` with `side_effect=lambda *a, **kw: fake` and add the args-assertion separately.

**(4c) Lines 357, 368, 377, 389, 411, 420, 437 (the remaining `llm_pkg._cache.clear()` calls):**

Each is a manual mid-test cache reset. Replace each with the Step-1 `getattr + callable` pattern OR — preferred where the surrounding test no longer needs a real cache reset because the test was rewired to `patch.object` — remove the line entirely. Be cautious: if the test was relying on `_cache.clear()` to flush state set up by an earlier test step, the rewire must preserve that intent. Read each callsite before deleting.

**Step 5 — Test files imports verification.** After all rewires, verify imports in each modified file include `patch` if `patch.object` is now used:

```bash
grep -nE "from unittest.mock import" tests/test_phase2_parity.py
# Expected: a line that includes 'patch' (and likely MagicMock)
```

If `patch` is missing, add it.

**Step 6 — Run the full suite.** This is the load-bearing verification for the entire plan:

```bash
pytest tests/ -v --tb=short
# Expected: 69 passed in <15s
```

If any test still AttributeErrors on `_cache` or otherwise fails, READ the traceback and fix:
- `AttributeError: module 'src.llm' has no attribute '_cache'` → grep that file for `_cache` and rewire any missed callsite.
- A behavior assertion fails (e.g. "expected LLMError, got QueryError-like") → the `patch.object` scope is wrong; widen it to include the assertion.
- A test that asserts `len(_cache) == 1` or similar dict-introspection assertion → reword to a behavioral assert (e.g. `get_llm() is get_llm()` for same args).

**Step 7 — Final scope-confirmation grep.** Confirm `_cache` is COMPLETELY GONE from the test surface:

```bash
grep -nE "_cache" tests/*.py
# Expected: zero matches OUTSIDE of:
#   - The test name 'test_factory_cache_dedupes_startup_log' at test_phase3_adapter.py:469
#     (just a name; not a reference to the dict — leave it alone)
#   - The autouse fixture name '_clear_factory_cache' (kept — same name, new body)
# To filter:
grep -nE "_cache" tests/*.py | grep -vE "test_factory_cache_dedupes_startup_log|_clear_factory_cache"
# Expected: 0 matches
```
  </action>
  <verify>
```bash
# All 4 test files rewired — no _cache.clear() or _cache[...] references remain
# (except the test name and fixture name as documented above)
grep -nE "llm_pkg\._cache" tests/*.py
# Expected: 0 matches

# New _get_llm_cached.clear() pattern is in all 4 files
grep -nE "_get_llm_cached" tests/*.py
# Expected: ≥8 matches (clear_fn lookup before+after yield in each of 4 fixtures + standalone uses)

# patch.object is in test_phase2_parity for the WRITE rewire
grep -nE "patch\.object\(llm_pkg, *.\"_get_llm_cached\"" tests/test_phase2_parity.py
# Expected: ≥1 match (the rewire of the original line 354 WRITE)

# Full suite green — the LOAD-BEARING verification
pytest tests/ -v --tb=short
# Expected: 69 passed in <15s

# Phase 1+2+3+4 individual gates still pass
pytest tests/test_llm_seam.py tests/test_phase2_parity.py tests/test_phase3_adapter.py tests/test_phase4_strict_tools.py -v
# Expected: 69 passed
```
  </verify>
  <done>
All four prior-phase test files (`test_llm_seam.py`, `test_phase2_parity.py`, `test_phase3_adapter.py`, `test_phase4_strict_tools.py`) have been rewired. The autouse `_clear_factory_cache` fixtures in each now use the `getattr(llm_pkg._get_llm_cached, "clear", None) + callable(...)` pattern. The `llm_pkg._cache["azure_openai"] = fake` WRITE at `test_phase2_parity.py:354` has been replaced with `with patch.object(llm_pkg, "_get_llm_cached", return_value=fake): ...` (Option A — chosen for minimal blast radius and no debug-only API addition). All standalone `llm_pkg._cache.clear()` callsites have been replaced or removed appropriately. The full `pytest tests/ -v` suite is GREEN at 69/69. The grep `_cache` over tests/ returns only the test-name and fixture-name occurrences (which are NOT references to the deleted dict).
  </done>
</task>

</tasks>

<verification>
Plan-level verification:

1. **All 9 files modified, no others:**
   ```bash
   git diff --stat HEAD -- src/llm/ tests/
   # Expected: src/llm/{__init__.py, config.py, base.py, azure_openai.py, anthropic_mgti.py}
   #           + tests/{test_llm_seam.py, test_phase2_parity.py, test_phase3_adapter.py, test_phase4_strict_tools.py}
   # NO other src/ or app.py edits in this plan.
   ```

2. **provider_name surface:**
   ```bash
   python -c "
   import os
   os.environ['AZURE_OPENAI_ENDPOINT'] = 'https://x.openai.azure.com/openai/deployments/d/chat/completions'
   os.environ['AZURE_OPENAI_API_KEY'] = 'k'
   os.environ['ANTHROPIC_BASE_URL'] = 'https://y.com'
   os.environ['ANTHROPIC_API_KEY'] = 'k'
   os.environ['ANTHROPIC_MODEL'] = 'eu.anthropic.claude-sonnet-4-5-20250929-v1:0'
   from src.llm import get_llm
   assert get_llm('azure_openai').provider_name == 'azure_openai'
   assert get_llm('anthropic_mgti').provider_name == 'anthropic_mgti'
   print('OK')
   "
   # Expected: OK
   ```

3. **missing_vars surface:**
   ```bash
   python -c "
   import os
   for k in ('AZURE_OPENAI_ENDPOINT','AZURE_OPENAI_API_KEY','ANTHROPIC_BASE_URL','ANTHROPIC_API_KEY','ANTHROPIC_MODEL'):
       os.environ.pop(k, None)
   from src.llm import missing_vars
   assert sorted(missing_vars('azure_openai')) == ['AZURE_OPENAI_API_KEY', 'AZURE_OPENAI_ENDPOINT']
   assert sorted(missing_vars('anthropic_mgti')) == ['ANTHROPIC_API_KEY', 'ANTHROPIC_BASE_URL', 'ANTHROPIC_MODEL']
   assert missing_vars('garbage') == []  # Non-raising on unknown provider
   print('OK')
   "
   # Expected: OK
   ```

4. **Cache key contains fingerprint, never raw key:**
   ```bash
   grep -nE "api_key|raw_key" src/llm/__init__.py | grep -v "# " | grep -v 'fingerprint'
   # Verify: NO line passes raw_key into _get_llm_cached arguments.
   # raw_key only appears in the local variable + _fingerprint(raw_key) call.
   ```

5. **Test suite fully green:**
   ```bash
   pytest tests/ -v --tb=short
   # Expected: 69 passed in <15s
   ```

6. **`_cache` is GONE from src AND from tests (except documented exceptions):**
   ```bash
   grep -nE "_cache" src/llm/__init__.py
   # Expected: 0 matches (no leftover _cache dict references)

   grep -nE "llm_pkg\._cache" tests/*.py
   # Expected: 0 matches

   grep -nE "_cache" tests/*.py | grep -vE "test_factory_cache_dedupes_startup_log|_clear_factory_cache"
   # Expected: 0 matches
   ```

7. **No unintended scope creep:**
   ```bash
   git diff src/llm/_compat.py src/llm/errors.py src/llm/types.py
   # Expected: ZERO output — these files NOT touched in Plan 05-01
   ```

8. **app.py untouched:**
   ```bash
   git diff app.py
   # Expected: ZERO output — Plan 05-01 is pure src/llm/ infrastructure + test rewires
   ```
</verification>

<success_criteria>
- [ ] `LLMClient.provider_name` is `@property @abc.abstractmethod`; both adapters override; returns match `_REGISTRY` keys and startup-log `provider=` strings
- [ ] `missing_vars(provider) -> list[str]` exists in `src/llm/config.py`, is non-raising, returns `[]` for unknown provider; re-exported via `from src.llm import missing_vars`
- [ ] `_cache: dict[str, LLMClient]` is DELETED from `src/llm/__init__.py`
- [ ] `@_cache_resource`-decorated `_get_llm_cached(provider, base_url, model, fingerprint)` is the single cache layer
- [ ] `_fingerprint(api_key)` is one-way SHA-256, 8-hex-char output; empty key → `""`; raw key never appears in cache-key tuple
- [ ] Streamlit import has a no-op decorator fallback for non-Streamlit contexts (pytest, python -c)
- [ ] `_resolve_provider` resolution order (kwarg > session > env > default) is unchanged
- [ ] **ALL 4 prior-phase test files updated** — `test_llm_seam.py`, `test_phase2_parity.py`, `test_phase3_adapter.py`, `test_phase4_strict_tools.py` — all `_cache.clear()` calls replaced with the `getattr + callable` pattern on `_get_llm_cached`
- [ ] `test_phase2_parity.py:354` WRITE `llm_pkg._cache["azure_openai"] = fake` rewired to `with patch.object(llm_pkg, "_get_llm_cached", return_value=fake): ...` (Option A)
- [ ] Full 69-test suite is green (`pytest tests/ -v` → 69 passed)
- [ ] Only files modified: `src/llm/{__init__.py, config.py, base.py, azure_openai.py, anthropic_mgti.py}` + the 4 test files listed above
- [ ] `app.py`, `src/llm/_compat.py`, `src/llm/errors.py`, `src/llm/types.py` — UNTOUCHED
</success_criteria>

<output>
After completion, create `.planning/phases/05-sidebar-ui-toggle-documentation/05-01-SUMMARY.md` documenting:
- Files modified: 5 src + 4 tests
- Key behaviors added: `provider_name` property, `missing_vars()`, `_fingerprint()`, `@_cache_resource` cache
- Test-fixture rewires: which test files needed what (autouse fixture replaced in all 4; PLUS `patch.object` rewire of the WRITE at test_phase2_parity.py:354 — chosen Option A from decision §7)
- Combined Phase 1+2+3+4 result: `69 passed in ~Xs` — confirm the count and time
- Confirmation of "no app.py / no UI / no docs touched" — pure src/llm/ infrastructure + test isolation
- Unblocks: Plan 05-02 (sidebar consumes `missing_vars` + cache-key invalidation), Plan 05-03 (caption reads `provider_name`)
</output>
