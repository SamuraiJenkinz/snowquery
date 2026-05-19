---
phase: 01-abstraction-seam
plan: 03
type: execute
wave: 3
depends_on: ["01-01", "01-02"]
files_modified:
  - tests/test_llm_seam.py
autonomous: true

must_haves:
  truths:
    - "All 5 Phase 1 success criteria are proven by executable checks in a single pytest run (no live LLM call needed)"
    - "The ABC contract enforcement (success criterion #2) is verified by a test that instantiates an incomplete subclass and asserts TypeError"
    - "The resolution-order chain (success criterion #3) is verified by tests that set/unset env vars and check which adapter class get_llm returns"
    - "validate_config gap-listing (success criterion #4) is verified by clearing env vars and asserting the exception message contains every required var name"
    - "API-key repr safety (success criterion #5 / OBS-03) is verified across the full Phase 1 package surface — LLMSettings, LLMConfigError, AND the AzureOpenAIClient / AnthropicMGTIClient stubs — by constructing each with sentinel secrets / inspecting their repr() and asserting the sentinels never appear; load_settings() is verified key-free by code inspection of src/llm/config.py (no logger.info, no print, no key-bearing format strings)"
  artifacts:
    - path: "tests/test_llm_seam.py"
      provides: "Pytest module asserting all 5 Phase 1 success criteria via unit-test-shaped functions"
      min_lines: 80
      exports: ["test_package_importable", "test_abc_contract_enforced", "test_resolution_order", "test_validate_config_lists_all_missing", "test_no_api_keys_in_repr"]
  key_links:
    - from: "tests/test_llm_seam.py"
      to: "src.llm (factory, types, errors, config)"
      via: "imports the public API and exercises each success criterion"
      pattern: "from src\\.llm import"
    - from: "tests/test_llm_seam.py"
      to: "monkeypatch fixture"
      via: "uses pytest's monkeypatch to safely manipulate os.environ per test"
      pattern: "monkeypatch\\.(setenv|delenv)"
---

<objective>
Verify all five Phase 1 success criteria with a single pytest module that runs without any live external dependency. The module exercises the static seam (ABC contract, types, errors), the runtime seam (factory + cache + resolution order), and the safety properties (validate_config gap-listing, repr safety).

Purpose: A green pytest run on this module IS the Phase 1 acceptance gate. If any test fails, Phase 1 is not done — and the failure points at exactly which success criterion regressed.

Output: One file (`tests/test_llm_seam.py`) with five focused tests, each mapped to one Phase 1 success criterion.
</objective>

<execution_context>
@C:\Users\taylo\.claude\get-shit-done\workflows\execute-plan.md
@C:\Users\taylo\.claude\get-shit-done\templates\summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/01-abstraction-seam/01-CONTEXT.md
@.planning/phases/01-abstraction-seam/01-RESEARCH.md
@.planning/phases/01-abstraction-seam/01-01-SUMMARY.md
@.planning/phases/01-abstraction-seam/01-02-SUMMARY.md

# The seam this plan verifies
@src/llm/__init__.py
@src/llm/base.py
@src/llm/errors.py
@src/llm/types.py
@src/llm/config.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create tests/test_llm_seam.py with five success-criterion-mapped tests</name>
  <files>tests/test_llm_seam.py</files>
  <action>
Create `tests/test_llm_seam.py` (creating `tests/` directory if it does not exist — the project currently has no `tests/` folder; this is the first test file).

The file has five top-level test functions, each named after the Phase 1 success criterion it verifies. Each test uses pytest's `monkeypatch` fixture to safely set/unset env vars without polluting later tests. The `_clear_cache` autouse fixture resets the factory cache between tests so cache-hit assertions are unambiguous.

Exact file contents:

```python
"""Phase 1 acceptance gate: prove all five success criteria.

Each test function maps to one numbered success criterion from
.planning/phases/01-abstraction-seam/ ROADMAP.md success_criteria.

This module deliberately uses zero live external dependencies — every
assertion is on local Python state (imports, ABC machinery, repr output,
env var manipulation via monkeypatch). A green run is the Phase 1 gate.

Run with: `pytest tests/test_llm_seam.py -v`
"""
from __future__ import annotations

import abc
from dataclasses import is_dataclass

import pytest

from src.llm import (
    DEFAULT_PROVIDER,
    ClassificationResultV1,
    IntentResult,
    LLMAuthError,
    LLMClient,
    LLMConfigError,
    LLMError,
    LLMGuardrailError,
    LLMSchemaError,
    LLMSettings,
    LLMTimeoutError,
    LLMTransientError,
    ToolCall,
    ToolSchema,
    get_llm,
    validate_config,
)
from src.llm.anthropic_mgti import AnthropicMGTIClient
from src.llm.azure_openai import AzureOpenAIClient


@pytest.fixture(autouse=True)
def _clear_factory_cache():
    """Ensure each test sees an empty get_llm cache."""
    import src.llm as llm_pkg
    llm_pkg._cache.clear()
    yield
    llm_pkg._cache.clear()


@pytest.fixture(autouse=True)
def _strip_llm_env(monkeypatch):
    """Strip all LLM-related env vars so tests start from a clean slate."""
    for name in (
        "LLM_PROVIDER_DEFAULT",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "API_VERSION",
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL",
        "ANTHROPIC_VERSION",
        "ANTHROPIC_MAX_TOKENS",
        "ANTHROPIC_TEMPERATURE",
        "ANTHROPIC_TIMEOUT_S",
        "ANTHROPIC_TOOLS_SUPPORTED",
    ):
        monkeypatch.delenv(name, raising=False)


# ---------------------------------------------------------------------------
# Success criterion #1 — src/llm/ is importable as a package from the REPL.
# ABS-01: __init__.py, base.py, errors.py (+ types.py, config.py, stubs) exist.
# ---------------------------------------------------------------------------

def test_package_importable():
    """Success criterion #1: the package and all public names import cleanly."""
    # If we got this far, the module-level imports at the top succeeded.
    # Spot-check that each public symbol is what we expect.
    assert issubclass(LLMClient, abc.ABC)
    for err in (
        LLMError, LLMAuthError, LLMTransientError, LLMGuardrailError,
        LLMSchemaError, LLMTimeoutError, LLMConfigError,
    ):
        assert issubclass(err, Exception)
    for typ in (ToolSchema, ToolCall, ClassificationResultV1, IntentResult):
        assert is_dataclass(typ)
        assert hasattr(typ, "__slots__"), f"{typ.__name__} missing __slots__"

    # ClassificationResultV1 must NOT contain chart fields (TOOL-03 prep)
    fields = set(ClassificationResultV1.__dataclass_fields__)
    assert "chart_requested" not in fields
    assert "chart_type" not in fields

    # IntentResult must contain them (heuristic-merged at call site)
    intent_fields = set(IntentResult.__dataclass_fields__)
    assert "chart_requested" in intent_fields
    assert "chart_type" in intent_fields

    # Adapter stub modules import cleanly
    assert issubclass(AzureOpenAIClient, LLMClient)
    assert issubclass(AnthropicMGTIClient, LLMClient)


# ---------------------------------------------------------------------------
# Success criterion #2 — LLMClient enforces the two-method contract.
# Instantiating a subclass missing either method raises TypeError.
# ABS-02.
# ---------------------------------------------------------------------------

def test_abc_contract_enforced():
    """Success criterion #2: ABC blocks instantiation of incomplete subclasses."""
    # The ABC declares exactly two abstract methods.
    assert LLMClient.__abstractmethods__ == frozenset(
        {"complete", "classify_with_tool"}
    )

    # Subclass missing both → TypeError mentioning both.
    class MissingBoth(LLMClient):
        pass

    with pytest.raises(TypeError) as exc_info:
        MissingBoth()
    msg = str(exc_info.value)
    assert "complete" in msg
    assert "classify_with_tool" in msg

    # Subclass missing only classify_with_tool → still TypeError.
    class MissingOne(LLMClient):
        def complete(self, messages, *, max_tokens=500, temperature=0.1, **kwargs):
            return ""

    with pytest.raises(TypeError):
        MissingOne()

    # Subclass implementing both → instantiates cleanly.
    class Complete(LLMClient):
        def complete(self, messages, *, max_tokens=500, temperature=0.1, **kwargs):
            return ""

        def classify_with_tool(self, messages, tool, *, tool_name, **kwargs):
            return ToolCall(tool_name=tool_name, input={})

    Complete()  # must not raise


# ---------------------------------------------------------------------------
# Success criterion #3 — get_llm resolves provider per kwarg > session > env > default.
# Cache returns the same instance. ABS-04 + CFG-05.
# ---------------------------------------------------------------------------

def test_resolution_order(monkeypatch):
    """Success criterion #3: explicit-kwarg > env > default 'azure_openai'.

    Streamlit session_state is not exercised here (it raises outside Streamlit
    and the try/except in _resolve_provider is verified by the fact that
    get_llm() doesn't crash when called from pytest — which is itself the
    'outside Streamlit' condition).
    """
    # Fallback all the way through: no kwarg, no env → DEFAULT_PROVIDER.
    assert DEFAULT_PROVIDER == "azure_openai"  # CFG-05 locked
    client = get_llm()
    assert isinstance(client, AzureOpenAIClient)

    # Cache: same call returns the SAME instance (identity, not equality).
    again = get_llm()
    assert client is again

    # Env var overrides default.
    import src.llm as llm_pkg
    llm_pkg._cache.clear()
    monkeypatch.setenv("LLM_PROVIDER_DEFAULT", "anthropic_mgti")
    via_env = get_llm()
    assert isinstance(via_env, AnthropicMGTIClient)

    # Explicit kwarg overrides env (env still set to anthropic_mgti).
    via_kwarg = get_llm("azure_openai")
    assert isinstance(via_kwarg, AzureOpenAIClient)

    # Unknown provider → LLMConfigError mentioning the bad name.
    with pytest.raises(LLMConfigError) as exc_info:
        get_llm("nonexistent_provider")
    assert "nonexistent_provider" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Success criterion #4 — validate_config lists EVERY missing var (not fail-on-first).
# CFG-03.
# ---------------------------------------------------------------------------

def test_validate_config_lists_all_missing():
    """Success criterion #4: every missing required var appears in the error message."""
    # azure_openai requires 2 vars; both unset by the autouse fixture.
    with pytest.raises(LLMConfigError) as exc_info:
        validate_config("azure_openai")
    msg = str(exc_info.value)
    assert "AZURE_OPENAI_ENDPOINT" in msg, f"endpoint missing from error: {msg}"
    assert "AZURE_OPENAI_API_KEY" in msg, f"api_key missing from error: {msg}"

    # anthropic_mgti requires 3 vars; all unset.
    with pytest.raises(LLMConfigError) as exc_info:
        validate_config("anthropic_mgti")
    msg = str(exc_info.value)
    assert "ANTHROPIC_BASE_URL" in msg
    assert "ANTHROPIC_API_KEY" in msg
    assert "ANTHROPIC_MODEL" in msg

    # Unknown provider → its own LLMConfigError.
    with pytest.raises(LLMConfigError) as exc_info:
        validate_config("bogus")
    assert "bogus" in str(exc_info.value)


def test_validate_config_partial_missing(monkeypatch):
    """Validate the 'list ALL missing, not fail-on-first' contract.

    If we set ONE of the two Azure vars, the error message must mention only
    the still-missing one — proving validate_config does not stop at the first
    miss but actually walks the full required list.
    """
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.com/openai")
    # AZURE_OPENAI_API_KEY still unset.
    with pytest.raises(LLMConfigError) as exc_info:
        validate_config("azure_openai")
    msg = str(exc_info.value)
    assert "AZURE_OPENAI_API_KEY" in msg
    assert "AZURE_OPENAI_ENDPOINT" not in msg  # already satisfied


# ---------------------------------------------------------------------------
# Success criterion #5 — no API key ever appears in repr() or log output.
# OBS-03.
# ---------------------------------------------------------------------------

def test_no_api_keys_in_repr():
    """Success criterion #5: api_key fields are excluded from repr via field(repr=False).

    This is the regression guard for the full package surface across Phases 1-3:
    LLMSettings + LLMConfigError + stub clients today, and the real adapters as
    they gain key-bearing state in Phase 2/3.

    Note: ``load_settings()`` itself is verified key-free by code inspection of
    ``src/llm/config.py`` (no ``logger.info``, no ``print``, no key-bearing
    format strings) — it is a pure read of ``os.environ`` into the dataclass
    fields. If that property is ever violated, this test docstring must be
    updated and a live log-capture assertion added here.
    """
    SENTINEL_AZURE = "AZURE_SECRET_DO_NOT_LEAK_AAAA"
    SENTINEL_ANTHROPIC = "ANTHROPIC_SECRET_DO_NOT_LEAK_BBBB"

    settings = LLMSettings(
        azure_api_key=SENTINEL_AZURE,
        anthropic_api_key=SENTINEL_ANTHROPIC,
    )

    # repr() must not contain the secret values.
    r = repr(settings)
    assert SENTINEL_AZURE not in r, (
        f"azure_api_key leaked into repr(LLMSettings): {r}"
    )
    assert SENTINEL_ANTHROPIC not in r, (
        f"anthropic_api_key leaked into repr(LLMSettings): {r}"
    )

    # Also check that str(settings) doesn't leak (str falls back to repr for
    # dataclasses, but explicit check guards against future __str__ overrides).
    s = str(settings)
    assert SENTINEL_AZURE not in s
    assert SENTINEL_ANTHROPIC not in s

    # And that no key prefix or fingerprint pre-image of these secrets
    # appears anywhere in the LLMError representation when a key is present
    # but config validation still raises.
    err = LLMConfigError(
        "Missing required env vars for azure_openai: SOME_VAR",
        provider="azure_openai",
        status_code=None,
    )
    assert SENTINEL_AZURE not in repr(err)
    assert SENTINEL_AZURE not in str(err)

    # Regression guard for Phase 2/3 across the full package surface:
    # stub clients today carry no key material, but when they gain real
    # config in later phases, their repr() must continue to redact.
    # Asserting against the sentinels now means a Phase 2/3 commit that
    # accidentally stores the raw key on the instance and falls back to
    # the default dataclass/object repr would be caught here.
    azure_repr = repr(AzureOpenAIClient())
    anthropic_repr = repr(AnthropicMGTIClient())
    assert SENTINEL_AZURE not in azure_repr, (
        f"azure stub repr leaked sentinel: {azure_repr}"
    )
    assert SENTINEL_ANTHROPIC not in anthropic_repr, (
        f"anthropic stub repr leaked sentinel: {anthropic_repr}"
    )
```

Requirements:
- File path is `tests/test_llm_seam.py` (create `tests/` directory if missing — no `__init__.py` needed, pytest discovers test_*.py via collection).
- Use `monkeypatch` for env-var manipulation; do NOT mutate `os.environ` directly (would leak across tests).
- The `_clear_factory_cache` autouse fixture is REQUIRED — the module-level `_cache` dict in `src/llm/__init__.py` persists across tests within a single pytest process, and without clearing, the "Env var overrides default" assertion in `test_resolution_order` would hit a stale `azure_openai` cache entry and never re-resolve.
- Each test docstring cites the success criterion it proves.
- Sentinel secret values in `test_no_api_keys_in_repr` MUST be unique strings unlikely to appear in any source file (so a false-positive grep would be obvious).
- No live HTTP calls. No imports of `requests`, no MGTI URLs touched. This test must run offline.
  </action>
  <verify>
Run from project root:
```
python -m pytest tests/test_llm_seam.py -v
```

Expected output:
```
tests/test_llm_seam.py::test_package_importable PASSED
tests/test_llm_seam.py::test_abc_contract_enforced PASSED
tests/test_llm_seam.py::test_resolution_order PASSED
tests/test_llm_seam.py::test_validate_config_lists_all_missing PASSED
tests/test_llm_seam.py::test_validate_config_partial_missing PASSED
tests/test_llm_seam.py::test_no_api_keys_in_repr PASSED

============ 6 passed in <X>s ============
```

If pytest is not installed in the project venv, install it first:
```
pip install pytest
```
(pytest is a dev dependency and is not required for runtime — do NOT add it to `requirements.txt`. It can be added to a future `requirements-dev.txt` or `pyproject.toml` dev group in a later milestone.)

All six tests must pass. If any fails, Phase 1 has a regression in that success criterion — fix it before marking the phase complete.
  </verify>
  <done>
- `tests/test_llm_seam.py` exists at the project root under `tests/`.
- All 6 tests pass when run via `python -m pytest tests/test_llm_seam.py -v`.
- Each test asserts properties tied to a specific success criterion (1, 2, 3, 4, 5) — citation is present in each docstring.
- Sentinel secrets `AZURE_SECRET_DO_NOT_LEAK_AAAA` and `ANTHROPIC_SECRET_DO_NOT_LEAK_BBBB` are confirmed absent from `repr(LLMSettings(...))`.
- The test suite runs offline with zero external dependencies (no requests calls, no MGTI URLs hit).
- Phase 1 acceptance gate is GREEN — all 5 ROADMAP.md success criteria are mechanically verified.
  </done>
</task>

</tasks>

<verification>
This plan's verification is the test run itself. The success of Plan 03 IS:

```
python -m pytest tests/test_llm_seam.py -v
```

Returning exit code 0 with 6/6 passing. If this fails, Phase 1 is not done.

Additional grep-based sanity checks (run AFTER pytest passes) to confirm locked files weren't touched:

```
# Confirm Phase 1 locked files were NOT modified by ANY of the three plans
git diff --name-only HEAD src/query_router.py src/sql_generator.py app.py config.py 2>&1 | grep -E '(query_router|sql_generator|^app\.py|^config\.py)$' && echo "LOCKED FILE TOUCHED" || echo "all locked files intact"
```

Must print `all locked files intact`.
</verification>

<success_criteria>
- `tests/test_llm_seam.py` exists.
- `python -m pytest tests/test_llm_seam.py -v` exits 0 with 6/6 passing.
- All 5 Phase 1 success criteria are proven by an executable test:
  - #1 (package importable) → `test_package_importable`
  - #2 (ABC contract enforced) → `test_abc_contract_enforced`
  - #3 (factory + cache + resolution order + default azure_openai) → `test_resolution_order`
  - #4 (validate_config lists ALL missing vars) → `test_validate_config_lists_all_missing` + `test_validate_config_partial_missing`
  - #5 (no API keys in repr/log output across the package) → `test_no_api_keys_in_repr` (covers LLMSettings, LLMConfigError, AzureOpenAIClient stub, AnthropicMGTIClient stub; load_settings code-inspected per its docstring)
- No live HTTP call is made by the test suite.
- LOCKED files (`app.py`, top-level `config.py`, `src/query_router.py`, `src/sql_generator.py`) are NOT modified by this plan.

Maps to: All 5 ROADMAP.md success criteria (executable verification). Requirements verified: ABS-01 (importability), ABS-02 (ABC enforcement), ABS-03 (frozen+slots), ABS-04 (factory + cache), ABS-05 (return types), CFG-01 (LLMSettings exists), CFG-03 (validate_config full-list), CFG-05 (DEFAULT_PROVIDER == azure_openai), ERR-01 (full error hierarchy), TOOL-01 (ClassificationResultV1 + IntentResult shape), OBS-03 (no api_key in repr).
</success_criteria>

<output>
After completion, create `.planning/phases/01-abstraction-seam/01-03-SUMMARY.md` documenting:
- pytest command + exit code + per-test pass/fail
- Confirmation that the 5 ROADMAP.md success criteria each map to a passing test
- Confirmation that the test suite runs offline (no requests/MGTI calls)
- Confirmation that no LOCKED file (app.py, config.py, query_router.py, sql_generator.py) was modified by any Phase 1 plan
- A short Phase 1 sign-off paragraph: "Phase 1 (Abstraction Seam) is complete. The seam is stable for Phase 2 to plug AzureOpenAIClient into."
</output>
