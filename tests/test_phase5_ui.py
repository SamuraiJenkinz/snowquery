"""Phase 5 acceptance gate: prove all 5 Phase 5 success criteria.

Each test function maps to one of:
  - The 5 numbered Phase 5 ROADMAP success criteria
  - The RESEARCH.md regression guards (Pitfalls 1, 6, 8, 11, 13)
  - The docs-content surface (DOC-01..04)

Conventions inherited from Phase 1/2/3/4 acceptance gates:
  - autouse _clear_factory_cache + _strip_llm_env fixtures isolate
    module-level singletons and env-var state between tests
  - Streamlit primitives mocked via the _build_streamlit_mock_surface()
    helper + unittest.mock.patch.multiple — NO live Streamlit
  - Inline test setup — NO fixture files
  - Tests have ZERO live external dependencies (no HTTP, no LLM, no Streamlit
    runtime, no real file system writes)

Run with: `pytest tests/test_phase5_ui.py -v`
Or combined with prior phases: `pytest tests/ -v` (expected: ~90 tests)
"""
from __future__ import annotations

import hashlib
import inspect
import os
from unittest.mock import MagicMock, patch

import pytest


# Realistic env values — mirror prior phases for cross-phase consistency
_AZURE_ENDPOINT = "https://example.openai.azure.com/openai/deployments/gpt-4o-mini/chat/completions"
_AZURE_MODEL = "gpt-4o-mini"  # The extracted deployment name from _AZURE_ENDPOINT
_AZURE_KEY = "azure-test-key-not-real"
_BASE_URL = "https://stage.int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1"
_API_KEY = "test-key-not-real"
_MODEL_SONNET = "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"


# ---------------------------------------------------------------------------
# Streamlit mock surface helper — single source of truth for ALL render_*
# tests. Builds context-manager mocks BEFORE patch.multiple is entered so
# `with st.sidebar:` / `with st.chat_message(...)` / `with st.spinner(...)`
# all behave correctly. (DRY across multiple tests; supersedes the earlier
# draft's broken inline pattern which mis-typed context-manager attrs.)
# ---------------------------------------------------------------------------

def _build_streamlit_mock_surface() -> dict:
    """Return a dict of correctly-shaped Streamlit primitive mocks.

    Splat into `patch.multiple("streamlit", **surface)`. Each test overrides
    the 1-2 primitives it asserts on by re-assigning surface[name] BEFORE
    the `with patch.multiple` line is entered.

    Context managers (sidebar, expander, chat_message, spinner) are built
    here with working __enter__/__exit__ so `with` statements in the
    production code don't raise.
    """
    def _make_cm():
        """Build a MagicMock that behaves as a context manager (with __enter__/__exit__)."""
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=None)
        cm.__exit__ = MagicMock(return_value=None)
        return cm

    sidebar_cm = _make_cm()

    # Columns: each call may pass a different count; production code uses
    # st.columns(2), st.columns(3), st.columns([3,1]), etc. Build a side_effect
    # that returns the right number of context-manager mocks based on the call.
    def _columns_side_effect(spec, *args, **kwargs):
        if isinstance(spec, int):
            count = spec
        else:
            try:
                count = len(spec)
            except TypeError:
                count = 2
        return tuple(_make_cm() for _ in range(count))

    return {
        # Context managers (pre-built with __enter__/__exit__)
        "sidebar": sidebar_cm,
        "expander": MagicMock(side_effect=lambda *a, **kw: _make_cm()),
        "chat_message": MagicMock(side_effect=lambda *a, **kw: _make_cm()),
        "spinner": MagicMock(side_effect=lambda *a, **kw: _make_cm()),
        # Layout
        "columns": MagicMock(side_effect=_columns_side_effect),
        "divider": MagicMock(),
        "markdown": MagicMock(),
        # Inputs
        "text_input": MagicMock(return_value=""),
        "button": MagicMock(return_value=False),
        "checkbox": MagicMock(return_value=True),
        "slider": MagicMock(return_value=10),
        "selectbox": MagicMock(return_value="Azure OpenAI"),
        "chat_input": MagicMock(return_value=""),
        "download_button": MagicMock(),
        # Output / feedback
        "caption": MagicMock(),
        "warning": MagicMock(),
        "info": MagicMock(),
        "success": MagicMock(),
        "error": MagicMock(),
        # Data
        "metric": MagicMock(),
        "dataframe": MagicMock(),
    }


# ---------------------------------------------------------------------------
# Autouse fixtures — mirror prior-phase gates with Plan 05-01 cache-name update
# ---------------------------------------------------------------------------

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


@pytest.fixture(autouse=True)
def _strip_llm_env(monkeypatch):
    """Strip ALL LLM-related env vars so tests start from a clean slate."""
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
    yield


@pytest.fixture(autouse=True)
def _clear_streamlit_session_state():
    """Reset st.session_state between tests so seeded keys don't leak.

    Streamlit's session_state persists across test invocations in the same
    process. Clear via .clear() if available, else by deleting all keys.
    Safe outside Streamlit run context — wrapped in try/except.
    """
    try:
        import streamlit as st
        try:
            for key in list(st.session_state.keys()):
                del st.session_state[key]
        except Exception:
            pass
    except Exception:
        pass
    yield
    try:
        import streamlit as st
        try:
            for key in list(st.session_state.keys()):
                del st.session_state[key]
        except Exception:
            pass
    except Exception:
        pass


@pytest.fixture
def azure_env(monkeypatch):
    """Realistic Azure env."""
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", _AZURE_ENDPOINT)
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", _AZURE_KEY)


@pytest.fixture
def anthropic_env(monkeypatch):
    """Realistic Anthropic env."""
    monkeypatch.setenv("ANTHROPIC_BASE_URL", _BASE_URL)
    monkeypatch.setenv("ANTHROPIC_API_KEY", _API_KEY)
    monkeypatch.setenv("ANTHROPIC_MODEL", _MODEL_SONNET)


@pytest.fixture
def both_env(azure_env, anthropic_env):
    """Both providers fully configured."""
    yield


# ===========================================================================
# SC #1: Sidebar selectbox label/options/state-init
# ===========================================================================

def test_sc1_provider_options_dict_has_exact_locked_keys_and_values():
    """SC #1: _PROVIDER_OPTIONS dict has exact locked label->key mappings."""
    import app
    assert app._PROVIDER_OPTIONS == {
        "Azure OpenAI": "azure_openai",
        "Anthropic Claude (MGTI)": "anthropic_mgti",
    }
    # Order matters for the default selectbox index
    assert list(app._PROVIDER_OPTIONS.keys())[0] == "Azure OpenAI"
    # Internal keys MUST match _REGISTRY
    from src.llm import _REGISTRY
    assert set(app._PROVIDER_OPTIONS.values()) == set(_REGISTRY.keys())


def test_sc1_render_sidebar_calls_selectbox_with_locked_label_and_options(azure_env):
    """SC #1: render_sidebar() calls st.selectbox with the exact locked
    label='LLM provider' and options=['Azure OpenAI', 'Anthropic Claude (MGTI)'].
    """
    import app
    import streamlit as st

    # Seed minimal session_state so other render_sidebar paths don't crash
    st.session_state["upload_authenticated"] = True
    st.session_state["data_loaded"] = False
    st.session_state["embeddings_ready"] = False
    st.session_state["schema"] = None

    # Build mock surface; override selectbox return so st.session_state update is clean
    surface = _build_streamlit_mock_surface()
    surface["selectbox"] = MagicMock(return_value="Azure OpenAI")

    with patch.multiple("streamlit", **surface):
        try:
            app.render_sidebar()
        except Exception as e:
            raise AssertionError(
                f"render_sidebar() raised {type(e).__name__}: {e}. "
                f"If a NEW Streamlit primitive was added to render_sidebar, "
                f"extend _build_streamlit_mock_surface() to include it."
            ) from e

    # Filter selectbox calls by label — render_sidebar may call selectbox
    # multiple times (e.g. for other dropdowns); we want the LLM-provider one.
    selectbox_calls = surface["selectbox"].call_args_list
    llm_provider_calls = [
        c for c in selectbox_calls
        if (c.args and c.args[0] == "LLM provider")
        or c.kwargs.get("label") == "LLM provider"
    ]
    assert len(llm_provider_calls) == 1, (
        f"Expected exactly 1 selectbox call with label 'LLM provider'; "
        f"got {len(llm_provider_calls)}. All selectbox calls: {selectbox_calls}"
    )
    c = llm_provider_calls[0]
    options = c.kwargs.get("options") or (c.args[1] if len(c.args) >= 2 else None)
    assert options == ["Azure OpenAI", "Anthropic Claude (MGTI)"], (
        f"options must be exactly ['Azure OpenAI', 'Anthropic Claude (MGTI)']; "
        f"got {options}"
    )


def test_sc1_session_state_initialized_from_env_default(anthropic_env, monkeypatch):
    """SC #1: st.session_state['llm_provider'] is initialized from LLM_PROVIDER_DEFAULT."""
    import app
    import streamlit as st

    monkeypatch.setenv("LLM_PROVIDER_DEFAULT", "anthropic_mgti")
    st.session_state["upload_authenticated"] = True
    st.session_state["data_loaded"] = False
    st.session_state["embeddings_ready"] = False
    st.session_state["schema"] = None

    surface = _build_streamlit_mock_surface()
    surface["selectbox"] = MagicMock(return_value="Anthropic Claude (MGTI)")

    with patch.multiple("streamlit", **surface):
        app.render_sidebar()

    # Session state was initialized from env, then updated by selectbox return
    assert st.session_state["llm_provider"] == "anthropic_mgti"


def test_sc1_session_state_clamps_unknown_env_to_azure(azure_env, monkeypatch):
    """SC #1 + RESEARCH Pitfall 2: unknown LLM_PROVIDER_DEFAULT falls back to azure_openai."""
    import app
    import streamlit as st

    monkeypatch.setenv("LLM_PROVIDER_DEFAULT", "anthropic_typo_oops")
    st.session_state["upload_authenticated"] = True
    st.session_state["data_loaded"] = False
    st.session_state["embeddings_ready"] = False
    st.session_state["schema"] = None

    surface = _build_streamlit_mock_surface()
    surface["selectbox"] = MagicMock(return_value="Azure OpenAI")

    with patch.multiple("streamlit", **surface):
        app.render_sidebar()

    assert st.session_state["llm_provider"] == "azure_openai", (
        f"Unknown LLM_PROVIDER_DEFAULT must clamp to azure_openai (Pitfall 2); "
        f"got {st.session_state.get('llm_provider')!r}"
    )


# ===========================================================================
# SC #2: Cache-key tuple invariant + fingerprint privacy
# ===========================================================================

def test_sc2_fingerprint_one_way_and_does_not_leak_key():
    """SC #2 + RESEARCH Pitfall 1: _fingerprint is one-way; no substring of raw key
    appears in the output; empty key returns ''.
    """
    from src.llm import _fingerprint

    assert _fingerprint("") == ""

    raw = "sk-a-very-real-looking-api-key-of-some-length-xyz123"
    fp = _fingerprint(raw)
    assert len(fp) == 8
    assert all(c in "0123456789abcdef" for c in fp), f"non-hex in fingerprint: {fp}"

    for substr in ("sk-", "a-very-real", "xyz123", raw[:8], raw[-8:]):
        assert substr not in fp, (
            f"Pitfall 1 VIOLATED — fingerprint {fp!r} contains key substring {substr!r}."
        )

    expected = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
    assert fp == expected

    fp_other = _fingerprint("a-completely-different-key")
    assert fp != fp_other


def test_sc2_get_llm_cached_called_with_full_tuple(azure_env, anthropic_env):
    """SC #2: get_llm() invokes _get_llm_cached with the locked 4-arg tuple
    (provider, base_url, model, api_key_fingerprint).
    """
    import src.llm as llm_pkg
    from src.llm import _fingerprint

    real_cached = llm_pkg._get_llm_cached
    with patch.object(llm_pkg, "_get_llm_cached", wraps=real_cached) as spy:
        llm_pkg.get_llm("azure_openai")
        assert spy.call_count == 1
        args, _ = spy.call_args
        assert len(args) == 4
        provider, base_url, model, fingerprint = args
        assert provider == "azure_openai"
        assert base_url == _AZURE_ENDPOINT
        assert model == _AZURE_MODEL
        assert fingerprint == _fingerprint(_AZURE_KEY)


def test_sc2_switching_provider_calls_with_different_tuple(both_env):
    """SC #2: switching provider produces a different cache-key tuple
    (so @_cache_resource re-resolves the adapter).
    """
    import src.llm as llm_pkg
    from src.llm import _fingerprint

    real_cached = llm_pkg._get_llm_cached
    with patch.object(llm_pkg, "_get_llm_cached", wraps=real_cached) as spy:
        llm_pkg.get_llm("azure_openai")
        llm_pkg.get_llm("anthropic_mgti")

        assert spy.call_count == 2
        call1_args = spy.call_args_list[0].args
        call2_args = spy.call_args_list[1].args
        assert call1_args != call2_args
        assert call1_args[0] != call2_args[0]
        assert call1_args[3] != call2_args[3]
        assert call2_args[0] == "anthropic_mgti"
        assert call2_args[1] == _BASE_URL
        assert call2_args[2] == _MODEL_SONNET
        assert call2_args[3] == _fingerprint(_API_KEY)


def test_sc2_module_level_cache_dict_is_deleted():
    """SC #2 + RESEARCH Pitfall 6: the Phase 1 module-level _cache dict is GONE.
    Only @_cache_resource on _get_llm_cached remains — single cache layer.
    """
    import src.llm as llm_pkg
    assert not hasattr(llm_pkg, "_cache"), (
        "Phase 1 _cache: dict should be deleted in Phase 5 (single cache layer). "
        "RESEARCH.md Pitfall 6 violated."
    )
    assert hasattr(llm_pkg, "_get_llm_cached")


# ===========================================================================
# SC #3: missing-vars warning + chat_input disable wiring (BOTH branches)
# ===========================================================================

def test_sc3_missing_vars_returns_required_list_for_anthropic():
    """SC #3 + Plan 05-01: missing_vars('anthropic_mgti') returns the 3 required
    vars when env is empty (autouse fixture stripped env). Non-raising contract.
    """
    from src.llm import missing_vars
    result = missing_vars("anthropic_mgti")
    assert sorted(result) == sorted([
        "ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"
    ]), result
    assert missing_vars("garbage_provider") == []


def test_sc3_sidebar_renders_warning_with_missing_vars_named(monkeypatch):
    """SC #3: when Anthropic creds are missing AND Anthropic is selected,
    sidebar renders st.warning naming each missing variable.
    """
    import app
    import streamlit as st

    monkeypatch.setenv("LLM_PROVIDER_DEFAULT", "anthropic_mgti")
    st.session_state["upload_authenticated"] = True
    st.session_state["data_loaded"] = False
    st.session_state["embeddings_ready"] = False
    st.session_state["schema"] = None

    surface = _build_streamlit_mock_surface()
    surface["selectbox"] = MagicMock(return_value="Anthropic Claude (MGTI)")

    with patch.multiple("streamlit", **surface):
        app.render_sidebar()

    warning_calls = surface["warning"].call_args_list
    assert len(warning_calls) >= 1, "Expected at least one st.warning call"
    llm_warnings = [
        c for c in warning_calls
        if "not configured" in str(c) or "Missing env vars" in str(c)
    ]
    assert len(llm_warnings) >= 1, (
        f"No LLM-provider warning matched; all warnings: {warning_calls}"
    )
    warning_text = str(llm_warnings[0])
    for var in ("ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"):
        assert var in warning_text, f"Warning must name missing var {var}"

    assert st.session_state["_llm_provider_blocked"] is True


def test_sc3_chat_input_disabled_when_blocked_flag_true(azure_env):
    """SC #3 BLOCKED branch: render_main_content's st.chat_input receives disabled=True
    AND placeholder swaps to 'QUERY DISABLED - see sidebar warning' when blocked.
    """
    import app
    import streamlit as st

    st.session_state["_llm_provider_blocked"] = True
    st.session_state["messages"] = []
    st.session_state["data_loaded"] = True
    st.session_state["schema"] = {"table_name": "t", "columns": [], "row_count": 0}
    st.session_state["embeddings_ready"] = True
    st.session_state["llm_provider"] = "azure_openai"

    surface = _build_streamlit_mock_surface()
    surface["chat_input"] = MagicMock(return_value="")
    surface["selectbox"] = MagicMock(return_value="REPORT [SQL]")

    with patch.multiple("streamlit", **surface):
        try:
            app.render_main_content()
        except Exception:
            # render_main_content may exercise paths beyond our mock surface;
            # we only need chat_input to have been called once before any
            # failure for the assertion below to be valid.
            pass

    chat_calls = surface["chat_input"].call_args_list
    assert len(chat_calls) >= 1, "st.chat_input was never called"
    c = chat_calls[0]
    placeholder = c.args[0] if c.args else c.kwargs.get("placeholder")
    disabled = c.kwargs.get("disabled", False)
    assert disabled is True, f"chat_input must be disabled=True when blocked; got {disabled!r}"
    assert placeholder == "QUERY DISABLED — see sidebar warning", (
        f"placeholder must swap to 'QUERY DISABLED — see sidebar warning'; "
        f"got {placeholder!r}"
    )


def test_sc3_chat_input_enabled_when_not_blocked(azure_env):
    """SC #3 UNBLOCKED branch (Warning 5 fix): when _llm_provider_blocked is False,
    chat_input is called with disabled=False AND the default placeholder.
    Locks the placeholder string 'ENTER QUERY...' against drift (Warning 7 fix).

    Without this test, a regression that always sets disabled=True (or that drifts
    the default placeholder) would still pass the BLOCKED-only assertion above.
    """
    import app
    import streamlit as st

    st.session_state["_llm_provider_blocked"] = False
    st.session_state["messages"] = []
    st.session_state["data_loaded"] = True
    st.session_state["schema"] = {"table_name": "t", "columns": [], "row_count": 0}
    st.session_state["embeddings_ready"] = True
    st.session_state["llm_provider"] = "azure_openai"

    surface = _build_streamlit_mock_surface()
    surface["chat_input"] = MagicMock(return_value="")
    surface["selectbox"] = MagicMock(return_value="REPORT [SQL]")

    with patch.multiple("streamlit", **surface):
        try:
            app.render_main_content()
        except Exception:
            pass

    chat_calls = surface["chat_input"].call_args_list
    assert len(chat_calls) >= 1, "st.chat_input was never called"
    c = chat_calls[0]
    placeholder = c.args[0] if c.args else c.kwargs.get("placeholder")
    disabled = c.kwargs.get("disabled", False)
    assert disabled is False, (
        f"chat_input must be disabled=False when NOT blocked; got {disabled!r}. "
        f"A regression that always sets disabled=True would now be caught."
    )
    assert placeholder == "ENTER QUERY...", (
        f"Default chat_input placeholder drifted — must be exactly 'ENTER QUERY...'; "
        f"got {placeholder!r}. This locks the default UI string against silent drift."
    )


# ===========================================================================
# SC #4: per-message caption + history-survives-switch + user-msg guard
# ===========================================================================

def test_sc4_render_history_caption_reads_from_stored_dict_not_session_state():
    """SC #4 + RESEARCH Pitfall 11: historical messages keep their original
    provenance after a provider switch — caption is rendered from the stored
    message dict, NOT from the currently selected provider in session_state.
    """
    import app
    import streamlit as st

    st.session_state["messages"] = [
        {"role": "user", "content": "find P1 incidents this week"},
        {
            "role": "assistant",
            "content": "Found 12 P1 incidents.",
            "results": None,
            "provider": "anthropic_mgti",
            "model": "eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
        },
    ]
    st.session_state["llm_provider"] = "azure_openai"  # User has SINCE switched

    surface = _build_streamlit_mock_surface()

    with patch.multiple("streamlit", **surface):
        app.render_chat_history()

    caption_calls = surface["caption"].call_args_list

    # Exactly one caption — for the assistant message; user message has none
    assert len(caption_calls) == 1, (
        f"Expected exactly 1 caption (assistant only); got {len(caption_calls)}. "
        f"User messages must NOT render a caption (Pitfall 11)."
    )

    caption_text = caption_calls[0].args[0] if caption_calls[0].args else ""
    assert "Anthropic Claude (MGTI)" in caption_text, (
        f"Caption must name ORIGINAL provider 'Anthropic Claude (MGTI)' "
        f"(not currently-selected Azure); got: {caption_text!r}."
    )
    assert "Azure OpenAI" not in caption_text
    assert "eu.anthropic.claude-sonnet-4-5-20250929-v1:0" in caption_text


def test_sc4_render_history_no_caption_for_user_messages():
    """SC #4 + Pitfall 11: user messages never render a provenance caption."""
    import app
    import streamlit as st

    st.session_state["messages"] = [{"role": "user", "content": "test"}]
    st.session_state["llm_provider"] = "azure_openai"

    surface = _build_streamlit_mock_surface()

    with patch.multiple("streamlit", **surface):
        app.render_chat_history()

    assert surface["caption"].call_count == 0


def test_sc4_render_history_no_caption_when_provider_key_missing():
    """SC #4 + Pitfall 11: assistant messages WITHOUT a 'provider' key skip the
    caption (backwards-compat for messages from before Phase 5 / error returns)."""
    import app
    import streamlit as st

    st.session_state["messages"] = [
        {"role": "assistant", "content": "old message with no provider", "results": None},
    ]
    st.session_state["llm_provider"] = "azure_openai"

    surface = _build_streamlit_mock_surface()

    with patch.multiple("streamlit", **surface):
        app.render_chat_history()

    assert surface["caption"].call_count == 0


def test_sc4_render_provenance_caption_does_not_read_session_state():
    """SC #4 + RESEARCH Pitfall 11: the _render_provenance_caption helper MUST
    NOT reference st.session_state. Static-source check locks the invariant.
    """
    from app import _render_provenance_caption
    src = inspect.getsource(_render_provenance_caption)
    # Locate the helper's body — strip the docstring so docstring mentions of
    # 'session_state' (which document the invariant) don't trigger this guard.
    # The docstring itself is the load-bearing reminder for future maintainers;
    # what we actually need to lock is the *executable* body.
    import ast
    tree = ast.parse(src)
    func_node = tree.body[0]
    assert isinstance(func_node, ast.FunctionDef), (
        f"Expected _render_provenance_caption to be a function; got {type(func_node).__name__}"
    )
    # Drop docstring expr if present
    body_nodes = func_node.body
    if (
        body_nodes
        and isinstance(body_nodes[0], ast.Expr)
        and isinstance(body_nodes[0].value, ast.Constant)
        and isinstance(body_nodes[0].value.value, str)
    ):
        body_nodes = body_nodes[1:]
    body_src = "\n".join(ast.unparse(n) for n in body_nodes)
    assert "session_state" not in body_src, (
        f"_render_provenance_caption MUST NOT reference session_state in its "
        f"executable body — Phase 5 RESEARCH.md Pitfall 11 violated. "
        f"Body:\n{body_src}"
    )


# ===========================================================================
# Pitfall 8 + provider_name on ABC + adapter overrides
# ===========================================================================

def test_provider_name_is_abstract_on_llmclient_abc():
    """Plan 05-01 + Pitfall 8: provider_name is an abstract property on LLMClient."""
    from src.llm.base import LLMClient
    assert "provider_name" in LLMClient.__abstractmethods__


def test_provider_name_concrete_returns_canonical_strings(both_env):
    """Plan 05-01 + Pitfall 8: each adapter exposes the canonical provider key
    via provider_name; values match _REGISTRY keys.
    """
    from src.llm.azure_openai import AzureOpenAIClient
    from src.llm.anthropic_mgti import AnthropicMGTIClient
    assert AzureOpenAIClient().provider_name == "azure_openai"
    assert AnthropicMGTIClient().provider_name == "anthropic_mgti"


# ===========================================================================
# SC #5: README and USER_GUIDE content checks
# ===========================================================================

def test_sc5_readme_contains_required_topics():
    """SC #5 + DOC-01 + DOC-03 + DOC-04 (Warning 6 — explicit MGTI assertion):
    README mentions LLM Provider Selection, Anthropic Claude, smoke_llm.py,
    USER_GUIDE.md, MGTI (the constraint reference), and Hubble.

    Note: the warning-resolution topic is intentionally covered via the
    README->USER_GUIDE cross-link (README is short; deep walkthrough lives in
    USER_GUIDE — see Plan 05-04 decision §1).
    """
    with open("README.md", encoding="utf-8") as f:
        text = f.read()
    for token in (
        "LLM Provider Selection",
        "Anthropic Claude",
        "smoke_llm.py",
        "USER_GUIDE.md",
    ):
        assert token in text, f"README.md missing required token: {token!r}"
    # MGTI constraint must be explicitly referenced (Warning 6 — not just inferred via Hubble)
    assert "MGTI" in text, "README.md missing MGTI constraint reference"
    # Hubble / hubble.mmc.com is the operational onboarding link
    assert "Hubble" in text or "hubble.mmc.com" in text, (
        "README.md missing MGTI/Hubble onboarding pointer"
    )


def test_sc5_user_guide_contains_locked_ui_strings_and_required_topics():
    """SC #5 + DOC-02 + DOC-03 + DOC-04 + RESEARCH Pitfall 13: USER_GUIDE quotes
    the EXACT locked UI strings AND covers the four required documentation topics.
    """
    with open("USER_GUIDE.md", encoding="utf-8") as f:
        text = f.read()

    locked_strings = [
        "LLM provider",                 # selectbox label
        "Azure OpenAI",
        "Anthropic Claude (MGTI)",
        "LLM PROVIDER",                 # sidebar section header (uppercase)
        "QUERY DISABLED",
        "hubble.mmc.com",
        "smoke_llm.py",
    ]
    for s in locked_strings:
        assert s in text, f"USER_GUIDE.md missing locked UI string: {s!r}"

    required_topics = [
        "LLM Provider Selection",
        "MGTI",
        "First-Time",
        "Mid-Session",
    ]
    for t in required_topics:
        assert t in text, f"USER_GUIDE.md missing required topic: {t!r}"

    for var in ("ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"):
        assert var in text, f"USER_GUIDE.md warning table missing {var}"


# ===========================================================================
# Helper sanity (additive — increases confidence; not strictly required for SC proof)
# ===========================================================================

def test_helper_missing_vars_is_non_raising():
    """Plan 05-01: missing_vars is non-raising and exposed from src.llm."""
    from src.llm import missing_vars
    assert isinstance(missing_vars("azure_openai"), list)
    assert isinstance(missing_vars("anthropic_mgti"), list)
    assert missing_vars("garbage_xyz") == []


def test_helper_provider_options_keys_match_registry():
    """Defensive: PROVIDER_OPTIONS internal keys must match _REGISTRY keys."""
    import app
    from src.llm import _REGISTRY
    assert set(app._PROVIDER_OPTIONS.values()) == set(_REGISTRY.keys())
