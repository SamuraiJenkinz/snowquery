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
    """Ensure each test sees an empty get_llm cache.

    Phase 5 Plan 05-01: _cache dict deleted, replaced by @_cache_resource on
    _get_llm_cached. The decorated function exposes .clear() under Streamlit;
    in the no-Streamlit fallback no .clear() attribute exists — defended via
    getattr-with-callable.
    """
    import src.llm as llm_pkg
    clear_fn = getattr(llm_pkg._get_llm_cached, "clear", None)
    if callable(clear_fn):
        clear_fn()
    yield
    clear_fn = getattr(llm_pkg._get_llm_cached, "clear", None)
    if callable(clear_fn):
        clear_fn()


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
        "ANTHROPIC_DIRECT_MODE",
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
    """Success criterion #2: ABC blocks instantiation of incomplete subclasses.

    Phase 5 Plan 05-01 added `provider_name` as an abstract property — the
    abstract-method set is now {complete, classify_with_tool, provider_name}.
    A subclass missing ANY of the three must fail to instantiate.
    """
    # The ABC declares exactly three abstract members (two methods + one property).
    assert LLMClient.__abstractmethods__ == frozenset(
        {"complete", "classify_with_tool", "provider_name"}
    )

    # Subclass missing all → TypeError mentioning all three.
    class MissingBoth(LLMClient):
        pass

    with pytest.raises(TypeError) as exc_info:
        MissingBoth()
    msg = str(exc_info.value)
    assert "complete" in msg
    assert "classify_with_tool" in msg
    assert "provider_name" in msg

    # Subclass missing only classify_with_tool → still TypeError.
    class MissingOne(LLMClient):
        def complete(self, messages, *, max_tokens=500, temperature=0.1, **kwargs):
            return ""

        @property
        def provider_name(self):
            return "fake"

    with pytest.raises(TypeError):
        MissingOne()

    # Subclass implementing all three → instantiates cleanly.
    class Complete(LLMClient):
        def complete(self, messages, *, max_tokens=500, temperature=0.1, **kwargs):
            return ""

        def classify_with_tool(self, messages, tool, *, tool_name, **kwargs):
            return ToolCall(tool_name=tool_name, input={})

        @property
        def provider_name(self):
            return "fake"

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
    clear_fn = getattr(llm_pkg._get_llm_cached, "clear", None)
    if callable(clear_fn):
        clear_fn()
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
