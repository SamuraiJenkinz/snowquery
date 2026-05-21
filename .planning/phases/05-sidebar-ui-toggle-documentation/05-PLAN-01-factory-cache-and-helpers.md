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
autonomous: true

must_haves:
  truths:
    - "get_llm() resolves through @st.cache_resource keyed on (provider, base_url, model, api_key_fingerprint) — switching providers re-resolves the adapter"
    - "The Phase 1 module-level _cache: dict is DELETED — single cache layer only (RESEARCH.md Pitfall 6)"
    - "_fingerprint(api_key) returns a one-way 8-hex-char SHA-256 prefix; empty key returns '' (never a hash-of-empty-bytes); raw key never appears in the cache key tuple (RESEARCH.md Pitfall 1)"
    - "src/llm/config.py exposes missing_vars(provider) -> list[str] — non-raising sibling of validate_config(); empty list = ok"
    - "LLMClient.provider_name is an abstract property on the ABC; AzureOpenAIClient returns 'azure_openai'; AnthropicMGTIClient returns 'anthropic_mgti'"
    - "Outside a Streamlit session (e.g. pytest, python -c), get_llm still works — the @st.cache_resource decorated helper is callable without Streamlit context"
    - "All Phase 1+2+3+4 tests still pass (69/69) — no behavior regression at adapter or factory boundary"
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
Refactor `src/llm/__init__.py` to use `@st.cache_resource` with a tuple cache key `(provider, base_url, model, api_key_fingerprint)`; DELETE the Phase 1 module-level `_cache: dict` (single cache layer per RESEARCH.md Pitfall 6); add a one-way SHA-256 `_fingerprint()` helper (RESEARCH.md Pitfall 1); add `missing_vars(provider) -> list[str]` to `src/llm/config.py` as the non-raising UI variant of `validate_config()`; add an abstract `provider_name` property to `LLMClient` and concrete overrides on both adapters (resolves Open Question #1 / RESEARCH.md Pitfall 8).

Purpose: This plan is the foundation Wave 2 plans consume. Without the cache key tuple, switching providers mid-session reuses the wrong adapter (SC #2 broken). Without `missing_vars()`, the sidebar warning either throws or has to parse exception messages (SC #3 broken). Without `provider_name`, the per-message caption falls back to brittle session_state reads (SC #4 fragile). The five files touched here are all under `src/llm/` — pure infrastructure, no UI, no docs.

Output: Three behavior changes — (a) the factory cache key includes raw key fingerprint and re-resolves on provider/key/url/model change; (b) `missing_vars()` returns a list of missing env-var names without raising; (c) every adapter instance reports its canonical provider name via a stable property. All existing 69 tests still pass.
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

7. **Test isolation: `_cache.clear()` is gone — tests now use `_get_llm_cached.clear()`.** The autouse `_clear_factory_cache` fixture in `tests/test_phase3_adapter.py:59-68` and `tests/test_phase4_strict_tools.py:217-223` reaches in via `llm_pkg._cache.clear()`. Phase 5 deletes that dict, so the tests would AttributeError. **Fix:** In each test file, the fixture must change from `llm_pkg._cache.clear()` to `llm_pkg._get_llm_cached.clear()`. This is a 1-line change per test file (3 files total: test_llm_seam.py, test_phase3_adapter.py, test_phase4_strict_tools.py). The `phase2_parity` file uses a different mechanism (Level B injection) so it does NOT need changing — but verify with grep before declaring done. **Add this to the task action** — tests must remain green.

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
# should be missing the override — fix any that are)
pytest tests/ -v --tb=short
# Expected: 69 passed (same as before this task)
```
  </verify>
  <done>
`src/llm/base.py` exposes `provider_name` as an `@property @abc.abstractmethod` on `LLMClient`. `AzureOpenAIClient.provider_name` returns the literal `"azure_openai"`; `AnthropicMGTIClient.provider_name` returns the literal `"anthropic_mgti"` — both matching their existing startup-log `provider=` strings and `_REGISTRY` keys. All 69 prior tests still pass. Any inline `LLMClient` subclasses in the test suite have been given a `provider_name` override.
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

# Suite still green (this task is purely additive)
pytest tests/ -v --tb=short
# Expected: 69 passed
```
  </verify>
  <done>
`missing_vars(provider: str) -> list[str]` is defined in `src/llm/config.py` after `validate_config`, reads `_REQUIRED_VARS` as single source of truth, returns `[]` for unknown providers, NEVER raises. `from src.llm import missing_vars` works. `__all__` updated. All 69 prior tests still pass. `validate_config()` itself is unchanged.
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

7. **Audit test files for `_cache` references that would AttributeError:**

```bash
grep -nE "(llm_pkg|src.llm|src\.llm)\._cache" tests/
# Expected hits (BEFORE Task 1.3 runs the test suite):
#   tests/test_llm_seam.py — Phase 1 acceptance gate (likely uses _cache)
#   tests/test_phase3_adapter.py:59-68 — autouse _clear_factory_cache fixture
#   tests/test_phase4_strict_tools.py:217-223 — autouse _clear_factory_cache fixture
```

For each hit, replace `_cache.clear()` (or `_cache = {}` etc.) with `_get_llm_cached.clear()`. Then run the targeted file:

```bash
pytest tests/test_phase3_adapter.py tests/test_phase4_strict_tools.py tests/test_llm_seam.py -v --tb=short
```

If any test still fails, read the failure and fix — common patterns:
- Direct dict access `_cache[resolved]` → replace with `_get_llm_cached(...)` direct call (with synthesized env).
- `assert len(_cache) == 1` → reword as a behavioral assert (e.g. `get_llm() is get_llm()` for same args).
- `_cache.clear()` → `_get_llm_cached.clear()`.

8. **Final sanity:** the 4 plans below this one depend on the contract that `get_llm()` returns a fresh adapter when ANY of `(provider, base_url, model, fingerprint)` changes. Verify with this manual exercise:

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

This manual exercise is informational — the load-bearing verification is the test suite.
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
assert _fingerprint(None) == '', _fingerprint(None) if None else 'ok-with-empty-str'
hashed = _fingerprint('a-real-key-of-some-length')
assert len(hashed) == 8 and all(c in '0123456789abcdef' for c in hashed)
# Critical: fingerprint must NOT be a substring of the raw key
assert 'a-real-key' not in hashed and 'some' not in hashed
print('fingerprint:', hashed, 'OK')
"
# Expected: fingerprint: <8 hex chars> OK

# 6. Test suite still green — Phase 1+2+3+4 all pass with new cache mechanism
pytest tests/ -v --tb=short
# Expected: 69 passed
# (If any test still ATTR-errors on _cache, fix the test file and re-run.)

# 7. Public surface preserved
python -c "from src.llm import get_llm, missing_vars, validate_config, load_settings, LLMSettings, DEFAULT_PROVIDER, LLMClient; print('OK')"
# Expected: OK

# 8. get_llm() still raises LLMConfigError on unknown provider
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

# 9. No leftover Phase-1 comment
grep -nE "Phase 5 may wrap this with" src/llm/__init__.py
# Expected: 0 matches (comment block removed with _cache dict)
```
  </verify>
  <done>
`src/llm/__init__.py` uses a single cache layer: `@_cache_resource` on `_get_llm_cached(provider, base_url, model, api_key_fingerprint)`. The Phase 1 `_cache: dict` AND its surrounding comment block are deleted. `_fingerprint()` is one-way SHA-256 truncated to 8 hex chars; empty key returns `""` and the raw key never appears as a cache-key argument. Streamlit import has a no-op decorator fallback for non-Streamlit contexts. `_resolve_provider` is unchanged. `get_llm()` preserves the Phase 1 error contract (LLMConfigError on unknown provider, kwarg > session > env > default resolution order). All 3 prior-phase test files have had their `_cache.clear()` calls updated to `_get_llm_cached.clear()`; full 69-test suite is green.
  </done>
</task>

</tasks>

<verification>
Plan-level verification:

1. **All 5 files modified, no others:**
   ```bash
   git diff --stat HEAD -- src/llm/ tests/
   # Expected: ONLY src/llm/{__init__.py, config.py, base.py, azure_openai.py, anthropic_mgti.py}
   # PLUS any test files that had _cache.clear() → _get_llm_cached.clear() edits
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
   # Expected: 69 passed in ~10s
   ```

6. **No unintended scope creep:**
   ```bash
   git diff src/llm/_compat.py src/llm/errors.py src/llm/types.py
   # Expected: ZERO output — these files NOT touched in Plan 05-01
   ```

7. **app.py untouched:**
   ```bash
   git diff app.py
   # Expected: ZERO output — Plan 05-01 is pure src/llm/ infrastructure
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
- [ ] All 3 prior-phase test files updated: `_cache.clear()` → `_get_llm_cached.clear()`
- [ ] Full 69-test suite is green
- [ ] Only files modified: `src/llm/{__init__.py, config.py, base.py, azure_openai.py, anthropic_mgti.py}` plus the test-fixture `clear()` rewires
- [ ] `app.py`, `src/llm/_compat.py`, `src/llm/errors.py`, `src/llm/types.py`, `src/llm/_log_helper` (none) — UNTOUCHED
</success_criteria>

<output>
After completion, create `.planning/phases/05-sidebar-ui-toggle-documentation/05-01-SUMMARY.md` documenting:
- Files modified (5 src + N tests for `_cache.clear()` rewires)
- Key behaviors added: `provider_name` property, `missing_vars()`, `_fingerprint()`, `@_cache_resource` cache
- Test-fixture rewires: which test files needed `_cache.clear()` → `_get_llm_cached.clear()`
- Combined Phase 1+2+3+4 result: `69 passed in ~Xs`
- Confirmation of "no UI / no docs touched" — pure src/llm/ infrastructure
- Unblocks: Plans 05-02 (sidebar consumes `missing_vars` + cache-key invalidation), 05-03 (caption reads `provider_name`)
</output>
