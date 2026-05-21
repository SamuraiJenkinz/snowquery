---
phase: 5
plan: 5
name: acceptance-gate
type: execute
wave: 3
depends_on: [1, 2, 3, 4]
files_modified:
  - tests/test_phase5_ui.py
autonomous: true

must_haves:
  truths:
    - "tests/test_phase5_ui.py exists as a self-contained pytest module — NO conftest.py, NO pytest.ini, NO new fixture files (matches Phase 1/2/3/4 gate pattern)"
    - "All 5 Phase 5 success criteria from ROADMAP.md are proven by named test functions"
    - "Sidebar code paths are exercised via unittest.mock.patch against streamlit module — zero live Streamlit, zero live HTTP, zero live LLM"
    - "Test for cache key tuple invariant: switching provider, base_url, model, OR api_key_fingerprint produces a DIFFERENT cached adapter instance"
    - "Test for fingerprint privacy: _fingerprint(key) MUST NOT contain any substring of the raw key; empty key returns ''"
    - "Test for SC #4 history-survives-switch: write a message with provider='anthropic_mgti', set session_state['llm_provider']='azure_openai', re-render, assert historical caption still names Anthropic"
    - "Test for caption guard: helper renders for assistant+provider; does NOT render for user messages OR assistant without provider key"
    - "Test for chat_input disable wiring: when blocked flag True, chat_input is called with disabled=True AND swapped placeholder"
    - "Test for docs content: README and USER_GUIDE grep-assert each of the 7 locked UI strings + the 4 required documentation topics"
    - "Combined Phase 1+2+3+4+5 suite is ~69 + ~20 = ~89 tests, all passing, zero live HTTP"
  artifacts:
    - path: "tests/test_phase5_ui.py"
      provides: "Phase 5 acceptance gate — pytest module proving all 5 SCs + cache key invariants + caption regression guards + docs-content checks"
      contains: "def test_sc1_"
  key_links:
    - from: "tests/test_phase5_ui.py SC #1 test"
      to: "app.py render_sidebar (via patch('streamlit.selectbox'))"
      via: "patch streamlit primitives; call render_sidebar; capture selectbox kwargs"
      pattern: "patch.*streamlit\\.selectbox|patch\\(.streamlit\\."
    - from: "tests/test_phase5_ui.py SC #2 test"
      to: "src.llm.__init__._get_llm_cached (Plan 05-01)"
      via: "inspect cache-key arguments via _get_llm_cached call records"
      pattern: "_get_llm_cached"
    - from: "tests/test_phase5_ui.py SC #4 test"
      to: "app._render_provenance_caption (Plan 05-03)"
      via: "patch('streamlit.caption'); render history; assert caption captured for original provider not current"
      pattern: "_render_provenance_caption"
    - from: "tests/test_phase5_ui.py SC #5 test"
      to: "README.md AND USER_GUIDE.md (Plan 05-04)"
      via: "open file, read text, assert required tokens present"
      pattern: "README\\.md|USER_GUIDE\\.md"
---

<objective>
Create `tests/test_phase5_ui.py` — a pytest module proving ALL 5 Phase 5 success criteria PLUS the documented regression guards from RESEARCH.md (Pitfalls 1, 6, 8, 11, 13). A green run on this module IS the Phase 5 gate, just as Phase 1-4 had their dedicated acceptance gates.

Purpose: This is the rate-limiting evidence document for Phase 5 close-out. Following the Phase 1/2/3/4 precedent, the gate is one self-contained pytest module — no conftest.py, no pytest.ini, no fixture files, all mocks inline. Streamlit is mocked via `unittest.mock.patch` against the `streamlit` module (the render functions are called directly; the mocks capture call arguments for assertions). Zero live HTTP, zero live LLM, zero live Streamlit.

Output: `tests/test_phase5_ui.py` (~20 tests) covering: SC #1 (sidebar selectbox label/options/session-state init), SC #2 (cache-key invariant + fingerprint privacy), SC #3 (missing-vars warning + chat_input disable wiring), SC #4 (per-message caption + history-survives-switch + user-msg guard), SC #5 (docs content grep). Combined Phase 1+2+3+4+5 run yields approximately 89 tests, all green, in under 20 seconds.
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

# This plan depends on all four prior Wave 1/2 plans
@.planning/phases/05-sidebar-ui-toggle-documentation/05-01-SUMMARY.md
@.planning/phases/05-sidebar-ui-toggle-documentation/05-02-SUMMARY.md
@.planning/phases/05-sidebar-ui-toggle-documentation/05-03-SUMMARY.md
@.planning/phases/05-sidebar-ui-toggle-documentation/05-04-SUMMARY.md

# Reference patterns (READ THESE FIRST — mirror their structure):
@tests/test_phase4_strict_tools.py
@tests/test_phase3_adapter.py

# Files this test verifies
@app.py
@src/llm/__init__.py
@src/llm/config.py
@src/llm/base.py
@README.md
@USER_GUIDE.md
</context>

<decisions>
## Decisions locked for this plan

1. **Test module is SELF-CONTAINED.** NO `conftest.py`. NO `pytest.ini`. NO new fixture files in `tests/fixtures/`. NO new helpers in `tests/`. Matches Phase 1/2/3/4 acceptance-gate pattern (STATE.md Phase 4-04 decision: "Test module self-contained — no conftest.py, no pytest.ini, no new tests/fixtures/ files (matches Phase 1/2/3 acceptance-gate pattern; four phases consistent now)").

2. **Streamlit is patched via `unittest.mock.patch`.** Strategy:
   - Use `with patch.multiple("streamlit", selectbox=MagicMock(...), caption=MagicMock(...), warning=MagicMock(...), ...)` to capture each primitive's invocation args.
   - For `st.session_state` (a dict-like, not a function), use `monkeypatch.setattr` or directly write to `st.session_state` after importing `streamlit as st`.
   - For `with st.sidebar:` and `with st.chat_message(...):` context managers, patch them to return `MagicMock()` instances (which support `__enter__`/`__exit__`).
   - For `st.divider()`, `st.markdown()`, `st.expander()`, etc. — patch as no-op MagicMocks; we don't assert on them (Plan 05-02 left those existing widgets alone).

3. **Autouse `_clear_factory_cache` fixture** mirrors prior phases but uses the Plan 05-01-renamed `_get_llm_cached.clear()`:
   ```python
   @pytest.fixture(autouse=True)
   def _clear_factory_cache():
       import src.llm as llm_pkg
       llm_pkg._get_llm_cached.clear()
       yield
       llm_pkg._get_llm_cached.clear()
   ```

4. **Autouse `_strip_llm_env` fixture** mirrors prior phases verbatim — strips all LLM env vars between tests so each test sees a clean slate. Same var list as Phase 4 gate (`tests/test_phase4_strict_tools.py:226-244`).

5. **Realistic env constants** match prior phases:
   - `_AZURE_ENDPOINT = "https://example.openai.azure.com/openai/deployments/gpt-4o-mini/chat/completions"`
   - `_AZURE_KEY = "azure-test-key-not-real"`
   - `_BASE_URL = "https://stage.int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1"`
   - `_API_KEY = "test-key-not-real"`
   - `_MODEL_SONNET = "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"`

6. **Streamlit session_state seeding pattern:** Streamlit's `session_state` is a special object. In tests, after `import streamlit as st`, we can write to it directly: `st.session_state["llm_provider"] = "azure_openai"`. Between tests, clear it: `st.session_state.clear()`. Use an autouse fixture to handle this.

7. **SC #2 cache-key test strategy:**
   - Build env so Azure has key="k1", Anthropic has key="k2".
   - Call `get_llm("azure_openai")` → instance A.
   - Call `get_llm("anthropic_mgti")` → instance B (different).
   - Call `get_llm("azure_openai")` again → instance A (cache hit on same args).
   - Rotate Azure key: env["AZURE_OPENAI_API_KEY"] = "k1-rotated".
   - Clear the @_cache_resource cache (or just bypass — Streamlit's no-op fallback in test context means each call is a fresh build anyway). Verify the cache-key tuple's `fingerprint` field changed.
   - **Cleaner approach:** test `_fingerprint` directly + test the `get_llm()` happy path produces the right tuple. Since `@_cache_resource` is a no-op in tests (Plan 05-01 fallback), we cannot directly assert "cache hit returns same instance" — instead, assert the BEHAVIOR (`get_llm` resolves correctly with different env values) and the WIRING (the tuple computed inside `get_llm` matches the expected `(provider, base_url, model, fingerprint)`).
   - Use `unittest.mock.patch` to wrap `_get_llm_cached` and capture call args: `with patch('src.llm._get_llm_cached', wraps=src.llm._get_llm_cached) as mock_cached: get_llm('azure_openai'); assert mock_cached.call_args == call('azure_openai', _AZURE_ENDPOINT, 'gpt-4o-mini', expected_fp)`.

8. **SC #3 warning test strategy:**
   - Strip env so `missing_vars("anthropic_mgti")` returns the full list of 3 names.
   - Seed `st.session_state["llm_provider"] = "anthropic_mgti"`.
   - Patch `streamlit.warning` to capture invocations.
   - Call `app.render_sidebar()`.
   - Assert `st.warning.call_count >= 1` and the captured warning text contains all three var names (`ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`) and the recovery-path phrase.
   - Assert `st.session_state["_llm_provider_blocked"] is True`.

9. **SC #3 chat_input disable test strategy:**
   - Set `st.session_state["_llm_provider_blocked"] = True`.
   - Patch `streamlit.chat_input` to capture invocations (return value: empty string, so the `if user_query :=` branch doesn't execute).
   - Call `app.render_main_content()`.
   - Assert `st.chat_input.call_args.kwargs.get("disabled")` is `True` (or positional disabled=True — check both).
   - Assert the placeholder argument is `"QUERY DISABLED — see sidebar warning"`.
   - Repeat with `_llm_provider_blocked = False`; assert `disabled=False` and placeholder is `"ENTER QUERY..."`.

10. **SC #4 history-survives-switch test strategy (the LOAD-BEARING test of this plan):**
    - Seed `st.session_state["messages"]` with two messages: one assistant message with `provider="anthropic_mgti"`, `model="eu.anthropic.claude-sonnet-4-5"`, and a user message (no provider key).
    - Set `st.session_state["llm_provider"] = "azure_openai"` (the OPPOSITE provider — simulating a switch after the message was written).
    - Patch `streamlit.caption` to capture invocations.
    - Call `app.render_chat_history()`.
    - Assert `st.caption` was called with a string containing `"Anthropic Claude (MGTI)"` AND `"eu.anthropic.claude-sonnet-4-5"` (the ORIGINAL provider's name + model — NOT the currently selected Azure OpenAI). If the caption text says "Azure OpenAI" or pulls the model from session_state, the test FAILS — this is the RESEARCH Pitfall 11 regression guard.
    - Also assert `st.caption` was NOT called for the user message (guard from Pitfall 11).

11. **SC #4 helper invariant test:** open `app.py`, find `_render_provenance_caption`, parse with `ast`, and assert its body does NOT reference `session_state`. This is a static check — the helper must NEVER read session_state. Plan 05-03 documented this invariant; this test locks it in CI.

12. **SC #5 docs-content test strategy:**
    - Open `README.md`. Read into a string. Assert each of: `"LLM Provider Selection"`, `"Anthropic Claude"`, `"smoke_llm.py"`, `"hubble.mmc.com"` (or `"Hubble"`), `"USER_GUIDE.md"` are present.
    - Open `USER_GUIDE.md`. Read into a string. Assert each of: `"LLM provider"`, `"Azure OpenAI"`, `"Anthropic Claude (MGTI)"`, `"LLM PROVIDER"` (uppercase header), `"QUERY DISABLED"`, `"hubble.mmc.com"`, `"smoke_llm.py"`, `"First-Time"` (checklist heading) are present.
    - Use case-sensitive matching (the locked UI strings are case-sensitive).

13. **NO live Streamlit run.** All tests run under pytest with `streamlit` mocked. The `streamlit` package IS imported (it's a dependency), but every primitive is patched per-test. This means tests work in any environment where pytest + streamlit are installed; CI compatibility is preserved.

14. **NO `pytest.importorskip("streamlit")`.** Streamlit is a hard dependency of the app — `requirements.txt:1`. If pytest is running without streamlit, that's a setup error worth surfacing as an ImportError, not a SKIP.

15. **Test count target ~20**, structured by SC:
    - SC #1 (sidebar selectbox label/options/state-init): 4 tests
    - SC #2 (cache-key tuple + fingerprint): 4 tests
    - SC #3 (warning content + chat_input disable + blocked flag): 4 tests
    - SC #4 (caption render + history-survives-switch + user-msg guard + helper invariant): 4 tests
    - SC #5 (README + USER_GUIDE content): 2 tests
    - Helper sanity: ~2 tests (`_fingerprint` empty/non-empty, `missing_vars` non-raise)
    - Total: ~20 tests

16. **`provider_name` on ABC test:** since Plan 05-01 added `provider_name` as `@property @abc.abstractmethod`, add ONE test verifying the ABC's `__abstractmethods__` contains `provider_name` AND both adapters return their canonical strings. Simple, doubles as Phase 1 hygiene.

17. **Static-source assertion approach for helper invariant** (locked decision §11 / RESEARCH Pitfall 11):
    ```python
    def test_render_provenance_caption_does_not_read_session_state():
        import ast, inspect
        from app import _render_provenance_caption
        src = inspect.getsource(_render_provenance_caption)
        assert "session_state" not in src, (
            f"_render_provenance_caption MUST NOT reference session_state — "
            f"Phase 5 RESEARCH.md Pitfall 11 violated. Body:\n{src}"
        )
    ```
    `inspect.getsource` works even if the function lives in `app.py` — fast and reliable.

18. **No new dependencies.** `unittest.mock`, `os`, `pytest`, `inspect`, `ast`, `hashlib` are all stdlib or already installed (`pytest` from prior phases).
</decisions>

<tasks>

<task type="auto">
  <name>Task 5.1: Write tests/test_phase5_ui.py — full acceptance gate (~20 tests)</name>
  <files>tests/test_phase5_ui.py</files>
  <action>
**Write `tests/test_phase5_ui.py`.** Use the skeleton below; flesh out each test per the SC breakdown in locked decision §15. Write all test bodies verbatim — no `# TODO` markers, no `...` placeholders.

**MODULE HEADER + IMPORTS + AUTOUSE FIXTURES + ENV CONSTANTS:**

```python
"""Phase 5 acceptance gate: prove all 5 Phase 5 success criteria.

Each test function maps to one of:
  - The 5 numbered Phase 5 ROADMAP success criteria
  - The RESEARCH.md regression guards (Pitfalls 1, 6, 8, 11, 13)
  - The docs-content surface (DOC-01..04)

Conventions inherited from Phase 1/2/3/4 acceptance gates:
  - autouse _clear_factory_cache + _strip_llm_env fixtures isolate
    module-level singletons and env-var state between tests
  - Streamlit primitives mocked via unittest.mock.patch — NO live Streamlit
  - Inline test setup — NO fixture files
  - Tests have ZERO live external dependencies (no HTTP, no LLM, no Streamlit
    runtime, no real file system writes)

Run with: `pytest tests/test_phase5_ui.py -v`
Or combined with prior phases: `pytest tests/ -v` (expected: ~89 tests)
"""
from __future__ import annotations

import ast
import hashlib
import inspect
import os
from unittest.mock import MagicMock, call, patch

import pytest

# Realistic env values — mirror prior phases for cross-phase consistency
_AZURE_ENDPOINT = "https://example.openai.azure.com/openai/deployments/gpt-4o-mini/chat/completions"
_AZURE_MODEL = "gpt-4o-mini"  # The extracted deployment name from _AZURE_ENDPOINT
_AZURE_KEY = "azure-test-key-not-real"
_BASE_URL = "https://stage.int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1"
_API_KEY = "test-key-not-real"
_MODEL_SONNET = "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"


# ---------------------------------------------------------------------------
# Autouse fixtures — mirror prior-phase gates with Plan 05-01 cache-name update
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_factory_cache():
    """Each test sees an empty get_llm cache.

    Plan 05-01 deleted the module-level _cache: dict and replaced it with
    @_cache_resource on _get_llm_cached. The cached function exposes .clear()
    (Streamlit cache_resource API; the no-op fallback decorator in non-Streamlit
    contexts also provides .clear via duck typing — but since the wrapped
    function IS the underlying function in fallback mode, .clear may not exist.
    Defensive .clear-if-callable.)
    """
    import src.llm as llm_pkg
    clear_fn = getattr(llm_pkg._get_llm_cached, "clear", None)
    if callable(clear_fn):
        clear_fn()
    yield
    clear_fn2 = getattr(llm_pkg._get_llm_cached, "clear", None)
    if callable(clear_fn2):
        clear_fn2()


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

    Streamlit's session_state is a singleton-like object that persists across
    test invocations within the same process. We clear it via .clear() if
    available, else by deleting all keys. Safe outside Streamlit run context.
    """
    try:
        import streamlit as st
        # Don't crash if session_state behaves oddly outside Streamlit runtime.
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
```

**Continue writing the test functions** — group by SC. Each test function has a one-line docstring referencing the SC or pitfall it proves.

**Required test functions (write all of these):**

```python
# ===========================================================================
# SC #1: Sidebar selectbox label/options/state-init
# ===========================================================================

def test_sc1_provider_options_dict_has_exact_locked_keys_and_values():
    """SC #1: _PROVIDER_OPTIONS dict has exact locked label→key mappings."""
    import app
    assert app._PROVIDER_OPTIONS == {
        "Azure OpenAI": "azure_openai",
        "Anthropic Claude (MGTI)": "anthropic_mgti",
    }, (
        f"_PROVIDER_OPTIONS must have exact label→key mapping; got "
        f"{app._PROVIDER_OPTIONS}. ROADMAP SC #1 + CONTEXT.md lock the UI strings."
    )
    # Order matters for the default selectbox index
    assert list(app._PROVIDER_OPTIONS.keys())[0] == "Azure OpenAI", (
        "Azure OpenAI MUST be the first option so default index=0 selects it "
        "(SC #1 + Phase 3 decision: 'Default provider stays azure_openai')."
    )
    # Internal keys MUST match _REGISTRY
    from src.llm import _REGISTRY
    assert set(app._PROVIDER_OPTIONS.values()) == set(_REGISTRY.keys()), (
        f"PROVIDER_OPTIONS internal keys {set(app._PROVIDER_OPTIONS.values())} "
        f"must match _REGISTRY keys {set(_REGISTRY.keys())}"
    )


def test_sc1_render_sidebar_calls_selectbox_with_locked_label_and_options(azure_env):
    """SC #1: render_sidebar() calls st.selectbox with the exact locked
    label='LLM provider' and options=['Azure OpenAI', 'Anthropic Claude (MGTI)'].
    """
    import app
    import streamlit as st

    # Seed session_state minimally so other render_sidebar paths don't crash
    st.session_state["upload_authenticated"] = True
    st.session_state["data_loaded"] = False
    st.session_state["embeddings_ready"] = False
    st.session_state["schema"] = None

    # Patch every Streamlit primitive the sidebar touches. We only assert on
    # selectbox; the rest are no-op MagicMocks.
    with patch.multiple(
        "streamlit",
        sidebar=MagicMock().__enter__.return_value,  # 'with st.sidebar:' returns this
        markdown=MagicMock(),
        divider=MagicMock(),
        text_input=MagicMock(return_value=""),
        button=MagicMock(return_value=False),
        caption=MagicMock(),
        warning=MagicMock(),
        info=MagicMock(),
        success=MagicMock(),
        error=MagicMock(),
        expander=MagicMock().__enter__.return_value,
        slider=MagicMock(return_value=10),
        checkbox=MagicMock(return_value=True),
        columns=MagicMock(return_value=(MagicMock(), MagicMock())),
        metric=MagicMock(),
        dataframe=MagicMock(),
        selectbox=MagicMock(return_value="Azure OpenAI"),
    ) as mocks:
        # 'with st.sidebar:' needs a context-manager-shaped mock — wrap separately.
        mocks["sidebar"] = MagicMock()
        mocks["sidebar"].__enter__ = MagicMock(return_value=None)
        mocks["sidebar"].__exit__ = MagicMock(return_value=None)
        # Same for expander and columns context managers
        mocks["expander"].__enter__ = MagicMock(return_value=None)
        mocks["expander"].__exit__ = MagicMock(return_value=None)

        try:
            app.render_sidebar()
        except Exception as e:
            # render_sidebar exercises many code paths — some may need more mock
            # surface area. Catch and re-raise with context so debug is easy.
            raise AssertionError(
                f"render_sidebar() raised {type(e).__name__}: {e}. "
                f"This test patches Streamlit primitives; if a NEW primitive "
                f"was added to render_sidebar, extend the patch.multiple list."
            ) from e

        # Find the LLM provider selectbox call. selectbox is called multiple
        # times (e.g. MODE selectbox in render_main_content — but we only call
        # render_sidebar here, so MODE shouldn't appear). Filter by label.
        selectbox_calls = mocks["selectbox"].call_args_list
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
        # Options must be the exact locked list (order matters)
        options = c.kwargs.get("options") or (c.args[1] if len(c.args) >= 2 else None)
        assert options == ["Azure OpenAI", "Anthropic Claude (MGTI)"], (
            f"options must be exactly ['Azure OpenAI', 'Anthropic Claude (MGTI)']; "
            f"got {options}"
        )


def test_sc1_session_state_initialized_from_env_default(azure_env, monkeypatch):
    """SC #1: st.session_state['llm_provider'] is initialized from LLM_PROVIDER_DEFAULT."""
    import app
    import streamlit as st

    monkeypatch.setenv("LLM_PROVIDER_DEFAULT", "anthropic_mgti")
    # Don't pre-seed session_state — let render_sidebar initialize it
    st.session_state["upload_authenticated"] = True
    st.session_state["data_loaded"] = False

    with patch.multiple(
        "streamlit",
        markdown=MagicMock(),
        divider=MagicMock(),
        text_input=MagicMock(return_value=""),
        button=MagicMock(return_value=False),
        caption=MagicMock(),
        warning=MagicMock(),
        info=MagicMock(),
        success=MagicMock(),
        error=MagicMock(),
        slider=MagicMock(return_value=10),
        checkbox=MagicMock(return_value=True),
        columns=MagicMock(return_value=(MagicMock(), MagicMock())),
        metric=MagicMock(),
        dataframe=MagicMock(),
        selectbox=MagicMock(return_value="Anthropic Claude (MGTI)"),
        sidebar=MagicMock(),
        expander=MagicMock(),
    ):
        # Provide context-manager shape for `with` users:
        import streamlit as st2
        st2.sidebar.__enter__ = MagicMock(return_value=None)
        st2.sidebar.__exit__ = MagicMock(return_value=None)
        st2.expander.__enter__ = MagicMock(return_value=None)
        st2.expander.__exit__ = MagicMock(return_value=None)
        app.render_sidebar()

    # Session state was initialized from env, then updated by selectbox return
    # (selectbox returned 'Anthropic Claude (MGTI)' → state set to 'anthropic_mgti')
    assert st.session_state["llm_provider"] == "anthropic_mgti"


def test_sc1_session_state_clamps_unknown_env_to_azure(monkeypatch):
    """SC #1 + RESEARCH Pitfall 2: unknown LLM_PROVIDER_DEFAULT falls back to azure_openai."""
    import app
    import streamlit as st

    monkeypatch.setenv("LLM_PROVIDER_DEFAULT", "anthropic_typo_oops")

    # Patch enough Streamlit to call render_sidebar without crash
    with patch.multiple(
        "streamlit",
        markdown=MagicMock(),
        divider=MagicMock(),
        text_input=MagicMock(return_value=""),
        button=MagicMock(return_value=False),
        caption=MagicMock(),
        warning=MagicMock(),
        info=MagicMock(),
        success=MagicMock(),
        error=MagicMock(),
        slider=MagicMock(return_value=10),
        checkbox=MagicMock(return_value=True),
        columns=MagicMock(return_value=(MagicMock(), MagicMock())),
        metric=MagicMock(),
        dataframe=MagicMock(),
        selectbox=MagicMock(return_value="Azure OpenAI"),
        sidebar=MagicMock(),
        expander=MagicMock(),
    ):
        import streamlit as st2
        st2.sidebar.__enter__ = MagicMock(return_value=None)
        st2.sidebar.__exit__ = MagicMock(return_value=None)
        st2.expander.__enter__ = MagicMock(return_value=None)
        st2.expander.__exit__ = MagicMock(return_value=None)
        st.session_state["upload_authenticated"] = True
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

    # Empty / None / whitespace → ""
    assert _fingerprint("") == ""

    # Non-empty: deterministic 8-hex-char SHA-256 prefix
    raw = "sk-a-very-real-looking-api-key-of-some-length-xyz123"
    fp = _fingerprint(raw)
    assert len(fp) == 8
    assert all(c in "0123456789abcdef" for c in fp), f"non-hex in fingerprint: {fp}"

    # Key material does NOT appear in the fingerprint (one-way hash, NOT a substring)
    # Check several substrings of the raw key
    for substr in ("sk-", "a-very-real", "xyz123", raw[:8], raw[-8:]):
        assert substr not in fp, (
            f"Pitfall 1 VIOLATED — fingerprint {fp!r} contains key substring {substr!r}. "
            f"_fingerprint must be one-way; never a prefix/substring of the raw key."
        )

    # Verify it's actually SHA-256 truncated (cryptographically correct)
    expected = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
    assert fp == expected, f"_fingerprint should be SHA-256[:8]; got {fp}, expected {expected}"

    # Different keys → different fingerprints (rotation detectable)
    fp_other = _fingerprint("a-completely-different-key")
    assert fp != fp_other


def test_sc2_get_llm_cached_called_with_full_tuple(azure_env, anthropic_env):
    """SC #2: get_llm() invokes _get_llm_cached with the locked 4-arg tuple
    (provider, base_url, model, api_key_fingerprint).
    """
    import src.llm as llm_pkg
    from src.llm import _fingerprint

    # Patch _get_llm_cached to capture its call args (wraps the real one so the
    # adapter still constructs successfully)
    real_cached = llm_pkg._get_llm_cached
    with patch.object(llm_pkg, "_get_llm_cached", wraps=real_cached) as spy:
        llm_pkg.get_llm("azure_openai")
        # The call args should be (provider, base_url, model, fingerprint)
        assert spy.call_count == 1, f"Expected 1 call, got {spy.call_count}"
        args, _ = spy.call_args
        assert len(args) == 4, f"Expected 4 positional args; got {len(args)}: {args}"
        provider, base_url, model, fingerprint = args
        assert provider == "azure_openai"
        assert base_url == _AZURE_ENDPOINT
        assert model == _AZURE_MODEL  # extracted from endpoint
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
        assert call1_args != call2_args, (
            f"Different providers must produce different cache-key tuples; "
            f"got call1={call1_args} call2={call2_args}"
        )
        # Spot-check: provider differs; fingerprints differ (different keys)
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
    # Sanity: the new cached function IS exported
    assert hasattr(llm_pkg, "_get_llm_cached")


# ===========================================================================
# SC #3: missing-vars warning + chat_input disable wiring
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
    # Non-raising on unknown provider
    assert missing_vars("garbage_provider") == []


def test_sc3_sidebar_renders_warning_with_missing_vars_named(monkeypatch):
    """SC #3: when Anthropic creds are missing AND Anthropic is selected,
    sidebar renders st.warning naming each missing variable.
    """
    import app
    import streamlit as st

    # Env: Azure missing too, but selection is Anthropic
    monkeypatch.setenv("LLM_PROVIDER_DEFAULT", "anthropic_mgti")
    st.session_state["upload_authenticated"] = True

    with patch.multiple(
        "streamlit",
        markdown=MagicMock(),
        divider=MagicMock(),
        text_input=MagicMock(return_value=""),
        button=MagicMock(return_value=False),
        caption=MagicMock(),
        warning=MagicMock(),
        info=MagicMock(),
        success=MagicMock(),
        error=MagicMock(),
        slider=MagicMock(return_value=10),
        checkbox=MagicMock(return_value=True),
        columns=MagicMock(return_value=(MagicMock(), MagicMock())),
        metric=MagicMock(),
        dataframe=MagicMock(),
        selectbox=MagicMock(return_value="Anthropic Claude (MGTI)"),
        sidebar=MagicMock(),
        expander=MagicMock(),
    ) as mocks:
        import streamlit as st2
        st2.sidebar.__enter__ = MagicMock(return_value=None)
        st2.sidebar.__exit__ = MagicMock(return_value=None)
        st2.expander.__enter__ = MagicMock(return_value=None)
        st2.expander.__exit__ = MagicMock(return_value=None)
        app.render_sidebar()

        # st.warning was called at least once
        warning_calls = mocks["warning"].call_args_list
        assert len(warning_calls) >= 1, "Expected at least one st.warning call"
        # Check the LLM-provider warning specifically (not the upload-password warning)
        llm_warnings = [
            c for c in warning_calls
            if "not configured" in str(c) or "Missing env vars" in str(c)
        ]
        assert len(llm_warnings) >= 1, (
            f"No LLM-provider warning matched 'not configured / Missing env vars'; "
            f"all warnings: {warning_calls}"
        )
        warning_text = str(llm_warnings[0])
        for var in ("ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"):
            assert var in warning_text, (
                f"Warning must name missing var {var}; warning text: {warning_text!r}"
            )

    # Blocked flag set
    assert st.session_state["_llm_provider_blocked"] is True


def test_sc3_sidebar_clears_blocked_flag_when_creds_present(azure_env, monkeypatch):
    """SC #3: when creds are present, blocked flag is False and no LLM warning."""
    import app
    import streamlit as st

    monkeypatch.setenv("LLM_PROVIDER_DEFAULT", "azure_openai")
    st.session_state["upload_authenticated"] = True

    with patch.multiple(
        "streamlit",
        markdown=MagicMock(),
        divider=MagicMock(),
        text_input=MagicMock(return_value=""),
        button=MagicMock(return_value=False),
        caption=MagicMock(),
        warning=MagicMock(),
        info=MagicMock(),
        success=MagicMock(),
        error=MagicMock(),
        slider=MagicMock(return_value=10),
        checkbox=MagicMock(return_value=True),
        columns=MagicMock(return_value=(MagicMock(), MagicMock())),
        metric=MagicMock(),
        dataframe=MagicMock(),
        selectbox=MagicMock(return_value="Azure OpenAI"),
        sidebar=MagicMock(),
        expander=MagicMock(),
    ) as mocks:
        import streamlit as st2
        st2.sidebar.__enter__ = MagicMock(return_value=None)
        st2.sidebar.__exit__ = MagicMock(return_value=None)
        st2.expander.__enter__ = MagicMock(return_value=None)
        st2.expander.__exit__ = MagicMock(return_value=None)
        app.render_sidebar()

    assert st.session_state["_llm_provider_blocked"] is False


def test_sc3_chat_input_disabled_when_blocked_flag_true(azure_env):
    """SC #3: render_main_content's st.chat_input receives disabled=True
    AND placeholder swaps to 'QUERY DISABLED — see sidebar warning' when blocked.
    """
    import app
    import streamlit as st

    st.session_state["_llm_provider_blocked"] = True
    st.session_state["messages"] = []
    st.session_state["data_loaded"] = True
    st.session_state["schema"] = {"table_name": "t", "columns": [], "row_count": 0}
    st.session_state["embeddings_ready"] = True
    st.session_state["llm_provider"] = "azure_openai"

    with patch.multiple(
        "streamlit",
        markdown=MagicMock(),
        chat_input=MagicMock(return_value=""),
        chat_message=MagicMock(),
        caption=MagicMock(),
        button=MagicMock(return_value=False),
        columns=MagicMock(return_value=(MagicMock(), MagicMock(), MagicMock())),
        selectbox=MagicMock(return_value="REPORT [SQL]"),
        expander=MagicMock(),
        info=MagicMock(),
        warning=MagicMock(),
        success=MagicMock(),
        error=MagicMock(),
        dataframe=MagicMock(),
        download_button=MagicMock(),
        spinner=MagicMock(),
    ) as mocks:
        import streamlit as st2
        st2.chat_message.return_value.__enter__ = MagicMock(return_value=None)
        st2.chat_message.return_value.__exit__ = MagicMock(return_value=None)
        st2.expander.__enter__ = MagicMock(return_value=None)
        st2.expander.__exit__ = MagicMock(return_value=None)
        st2.spinner.return_value.__enter__ = MagicMock(return_value=None)
        st2.spinner.return_value.__exit__ = MagicMock(return_value=None)

        try:
            app.render_main_content()
        except Exception:
            # render_main_content may try to call functions we don't mock fully
            # (e.g. render_chat_history side-effects). We only need chat_input
            # to be called once before any exception — if it was called, verify.
            pass

        chat_calls = mocks["chat_input"].call_args_list
        assert len(chat_calls) >= 1, "st.chat_input was never called"
        c = chat_calls[0]
        # Placeholder is positional arg 0
        placeholder = c.args[0] if c.args else c.kwargs.get("placeholder")
        disabled = c.kwargs.get("disabled", False)
        assert disabled is True, f"chat_input must be disabled=True when blocked; got {disabled!r}"
        assert placeholder == "QUERY DISABLED — see sidebar warning", (
            f"placeholder must swap to 'QUERY DISABLED — see sidebar warning'; "
            f"got {placeholder!r}"
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

    # Seed: one assistant message was originally produced by Anthropic
    st.session_state["messages"] = [
        {
            "role": "user",
            "content": "find P1 incidents this week",
        },
        {
            "role": "assistant",
            "content": "Found 12 P1 incidents.",
            "results": None,
            "provider": "anthropic_mgti",
            "model": "eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
        },
    ]
    # User has SINCE switched the sidebar selector to Azure
    st.session_state["llm_provider"] = "azure_openai"

    with patch.multiple(
        "streamlit",
        markdown=MagicMock(),
        chat_message=MagicMock(),
        caption=MagicMock(),
    ) as mocks:
        import streamlit as st2
        st2.chat_message.return_value.__enter__ = MagicMock(return_value=None)
        st2.chat_message.return_value.__exit__ = MagicMock(return_value=None)
        app.render_chat_history()

        caption_calls = mocks["caption"].call_args_list

        # Exactly one caption — for the assistant message; user message has none
        assert len(caption_calls) == 1, (
            f"Expected exactly 1 caption (assistant only); got {len(caption_calls)}. "
            f"User messages must NOT render a caption (Pitfall 11). "
            f"All caption calls: {caption_calls}"
        )

        caption_text = caption_calls[0].args[0] if caption_calls[0].args else ""
        # The caption must name Anthropic (original producer) — NOT Azure (current selection)
        assert "Anthropic Claude (MGTI)" in caption_text, (
            f"Caption must name ORIGINAL provider 'Anthropic Claude (MGTI)' "
            f"(not currently-selected Azure); got: {caption_text!r}. "
            f"Pitfall 11 violated — historical caption recomputed from session_state."
        )
        assert "Azure OpenAI" not in caption_text, (
            f"Caption must NOT name the currently-selected Azure provider "
            f"for a message produced by Anthropic; got: {caption_text!r}"
        )
        # And the original model is named
        assert "eu.anthropic.claude-sonnet-4-5-20250929-v1:0" in caption_text


def test_sc4_render_history_no_caption_for_user_messages():
    """SC #4 + Pitfall 11: user messages never render a provenance caption."""
    import app
    import streamlit as st

    st.session_state["messages"] = [
        {"role": "user", "content": "test"},
    ]
    st.session_state["llm_provider"] = "azure_openai"

    with patch.multiple(
        "streamlit",
        markdown=MagicMock(),
        chat_message=MagicMock(),
        caption=MagicMock(),
    ) as mocks:
        import streamlit as st2
        st2.chat_message.return_value.__enter__ = MagicMock(return_value=None)
        st2.chat_message.return_value.__exit__ = MagicMock(return_value=None)
        app.render_chat_history()
        assert mocks["caption"].call_count == 0, (
            f"User messages must not render captions; got "
            f"{mocks['caption'].call_count} caption call(s)"
        )


def test_sc4_render_history_no_caption_when_provider_key_missing():
    """SC #4 + Pitfall 11: assistant messages WITHOUT a 'provider' key skip the caption
    (backwards-compat for messages from before Phase 5 / error-return paths)."""
    import app
    import streamlit as st

    st.session_state["messages"] = [
        {"role": "assistant", "content": "old message with no provider", "results": None},
    ]
    st.session_state["llm_provider"] = "azure_openai"

    with patch.multiple(
        "streamlit",
        markdown=MagicMock(),
        chat_message=MagicMock(),
        caption=MagicMock(),
    ) as mocks:
        import streamlit as st2
        st2.chat_message.return_value.__enter__ = MagicMock(return_value=None)
        st2.chat_message.return_value.__exit__ = MagicMock(return_value=None)
        app.render_chat_history()
        assert mocks["caption"].call_count == 0, (
            "Assistant message without 'provider' key must NOT render a caption"
        )


def test_sc4_render_provenance_caption_does_not_read_session_state():
    """SC #4 + RESEARCH Pitfall 11: the _render_provenance_caption helper MUST
    NOT reference st.session_state. Static-source check locks the invariant.
    """
    from app import _render_provenance_caption
    src = inspect.getsource(_render_provenance_caption)
    assert "session_state" not in src, (
        f"_render_provenance_caption MUST NOT reference session_state — "
        f"Phase 5 RESEARCH.md Pitfall 11 violated. Body:\n{src}"
    )


# ===========================================================================
# Pitfall 8 + provider_name on ABC + adapter overrides
# ===========================================================================

def test_provider_name_is_abstract_on_llmclient_abc():
    """Plan 05-01 + Pitfall 8: provider_name is an abstract property on LLMClient."""
    from src.llm.base import LLMClient
    assert "provider_name" in LLMClient.__abstractmethods__, (
        f"provider_name must be in LLMClient.__abstractmethods__; "
        f"got {LLMClient.__abstractmethods__}"
    )


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
    """SC #5 + DOC-01 + DOC-03 + DOC-04: README mentions LLM Provider Selection,
    Anthropic Claude, smoke_llm.py, Hubble/MGTI, and cross-links USER_GUIDE.md.
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
    # MGTI / Hubble pointer — accept either spelling
    assert "Hubble" in text or "hubble.mmc.com" in text, (
        "README.md missing MGTI/Hubble onboarding pointer"
    )


def test_sc5_user_guide_contains_locked_ui_strings_and_required_topics():
    """SC #5 + DOC-02 + DOC-03 + DOC-04 + RESEARCH Pitfall 13: USER_GUIDE quotes
    the EXACT locked UI strings AND covers the four required documentation topics
    (provider selection, MGTI constraint, smoke-test how-to, warning resolution).
    """
    with open("USER_GUIDE.md", encoding="utf-8") as f:
        text = f.read()

    # The 7 locked UI strings (Pitfall 13)
    locked_strings = [
        "LLM provider",                 # selectbox label
        "Azure OpenAI",                 # option 1
        "Anthropic Claude (MGTI)",      # option 2
        "LLM PROVIDER",                 # sidebar section header
        "QUERY DISABLED",               # blocked-input placeholder fragment
        "hubble.mmc.com",               # Hubble link
        "smoke_llm.py",                 # smoke script reference
    ]
    for s in locked_strings:
        assert s in text, f"USER_GUIDE.md missing locked UI string: {s!r}"

    # Four required topic coverage
    required_topics = [
        "LLM Provider Selection",       # section title (DOC-02)
        "MGTI",                         # MGTI constraint coverage (DOC-03)
        "First-Time",                   # First-time setup checklist (DOC-04)
        "Mid-Session",                  # Mid-session switching (SC #2 docs surface)
    ]
    for t in required_topics:
        assert t in text, f"USER_GUIDE.md missing required topic: {t!r}"

    # Warning-resolution table — names each ANTHROPIC_* required var
    for var in ("ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"):
        assert var in text, f"USER_GUIDE.md warning table missing {var}"


# ===========================================================================
# Helper sanity (additive — increases confidence; not strictly required for SC proof)
# ===========================================================================

def test_helper_missing_vars_is_non_raising():
    """Plan 05-01: missing_vars is non-raising and exposed from src.llm."""
    from src.llm import missing_vars
    # Doesn't raise on empty env
    assert isinstance(missing_vars("azure_openai"), list)
    assert isinstance(missing_vars("anthropic_mgti"), list)
    # Doesn't raise on garbage provider
    assert missing_vars("garbage_xyz") == []


def test_helper_provider_options_keys_match_registry():
    """Defensive: PROVIDER_OPTIONS internal keys must match _REGISTRY keys."""
    import app
    from src.llm import _REGISTRY
    assert set(app._PROVIDER_OPTIONS.values()) == set(_REGISTRY.keys()), (
        f"_PROVIDER_OPTIONS internal keys {set(app._PROVIDER_OPTIONS.values())} "
        f"must match _REGISTRY keys {set(_REGISTRY.keys())}. If they diverge, "
        f"the sidebar will set session_state to a key that get_llm() can't resolve."
    )
```

**Run the suite as you write to catch issues early:**

```bash
# After every batch of tests, run the new module to validate
pytest tests/test_phase5_ui.py -v --tb=short
```

Some Streamlit-mock setups are finicky — if a test fails because `render_sidebar` raised inside the patch block, READ the traceback to see which Streamlit primitive needs more patching. Extend the `patch.multiple` list as needed. Do NOT stop until ALL named tests pass.

**Critical: each test's mock setup is independent.** Do not refactor common patch.multiple blocks into a shared fixture unless multiple tests genuinely share the same mock surface — over-DRY'ing mocks makes failures harder to diagnose. Phase 1-4 gates kept setups inline; Phase 5 follows.
  </action>
  <verify>
```bash
# 1. New test file exists
ls -la tests/test_phase5_ui.py
# Expected: file present

# 2. No new fixture files or conftest.py
ls tests/conftest.py tests/fixtures/phase5* 2>/dev/null
# Expected: no matches (matches Phase 1/2/3/4 pattern)

# 3. Run Phase 5 gate ALONE
pytest tests/test_phase5_ui.py -v
# Expected: ~20 tests, ALL PASSING, in <10 seconds

# 4. Run combined Phase 1+2+3+4+5 gate
pytest tests/ -v
# Expected: ~89 tests (69 prior + ~20 Phase 5), ALL PASSING

# 5. Test discovery (sanity)
pytest tests/test_phase5_ui.py --collect-only -q
# Expected: ~20 test ids listed; no collection errors

# 6. All 5 SCs traceable
grep -nE "def test_sc[0-9]_" tests/test_phase5_ui.py
# Expected: SC #1 (≥3), SC #2 (≥3), SC #3 (≥3), SC #4 (≥3), SC #5 (=2)

# 7. Fingerprint privacy test present
grep -nE "def test_sc2_fingerprint" tests/test_phase5_ui.py
# Expected: 1 match

# 8. History-survives-switch test present and covers the LOAD-BEARING assertion
grep -nE "test_sc4_render_history_caption_reads_from_stored_dict" tests/test_phase5_ui.py
# Expected: 1 match

# 9. Helper-static-source test present (Pitfall 11)
grep -nE "test_sc4_render_provenance_caption_does_not_read_session_state" tests/test_phase5_ui.py
# Expected: 1 match

# 10. Docs content tests present
grep -nE "test_sc5_readme|test_sc5_user_guide" tests/test_phase5_ui.py
# Expected: 2 matches

# 11. Only the declared file modified
git diff --stat HEAD -- src/ app.py scripts/ tests/ README.md USER_GUIDE.md
# Expected: ONLY tests/test_phase5_ui.py from this plan (other files were modified
# by Plans 05-01..05-04 in earlier waves)

# 12. Module loads cleanly (no syntax errors)
python -c "import ast; ast.parse(open('tests/test_phase5_ui.py').read()); print('OK')"
# Expected: OK
```
  </verify>
  <done>
`tests/test_phase5_ui.py` exists with ~20 tests covering all 5 Phase 5 SCs, the fingerprint-privacy regression guard (Pitfall 1), the module-level _cache deletion check (Pitfall 6), the provider_name ABC + concrete overrides (Pitfall 8), the helper-static-source invariant (Pitfall 11), the history-survives-switch LOAD-BEARING assertion (SC #4), the chat_input disable wiring (SC #3), and docs-content grep (SC #5 + Pitfall 13). Zero conftest.py. Zero pytest.ini. Zero fixture files in tests/fixtures/phase5*. Zero live HTTP, zero live LLM, zero live Streamlit. Combined Phase 1+2+3+4+5 pytest run is ~89 tests, all passing. Only `tests/test_phase5_ui.py` modified by this plan.
  </done>
</task>

</tasks>

<verification>
Phase-level verification for Plan 05-05 (and Phase 5 overall):

1. **Combined gate green:**
   ```bash
   pytest tests/ -v
   # Expected: ~89 tests pass; 0 failures; <20 seconds wall-clock
   ```

2. **No new fixture infrastructure:**
   ```bash
   ls tests/conftest.py tests/pytest.ini tests/fixtures/phase5* 2>/dev/null
   # Expected: zero output
   ```

3. **Self-contained module count:**
   ```bash
   pytest tests/test_phase5_ui.py --collect-only -q | wc -l
   # Expected: ~21 (20 tests + 1 summary); ±3 tolerance
   ```

4. **All 5 SCs traceable:**
   ```bash
   grep -nE "def test_sc[0-9]_" tests/test_phase5_ui.py
   # Expected:
   #   SC #1: ≥3 tests (selectbox/options/state-init/clamp)
   #   SC #2: ≥3 tests (fingerprint/tuple/switch-different/cache-deleted)
   #   SC #3: ≥3 tests (missing_vars/warning/clear/disabled)
   #   SC #4: ≥3 tests (history-survives-switch/user-msg-guard/no-key-skip/helper-invariant)
   #   SC #5: ≥2 tests (README + USER_GUIDE content)
   ```

5. **Pitfall regression guards present:**
   ```bash
   grep -nE "Pitfall 1|Pitfall 6|Pitfall 8|Pitfall 11|Pitfall 13" tests/test_phase5_ui.py
   # Expected: ≥5 matches (one comment/docstring per regression-locked pitfall)
   ```

6. **Phase 1+2+3+4 gates preserved:**
   ```bash
   pytest tests/test_llm_seam.py tests/test_phase2_parity.py tests/test_phase3_adapter.py tests/test_phase4_strict_tools.py -v
   # Expected: 69 passed (same as before Phase 5)
   ```

7. **Plan 05-05's diff touches ONLY its declared file:**
   ```bash
   git diff --stat HEAD~ -- src/ app.py scripts/ tests/ README.md USER_GUIDE.md
   # Expected: across the whole Phase 5 wave: app.py (Plans 02+03), src/llm/* (Plan 01),
   # README + USER_GUIDE (Plan 04), tests/test_phase5_ui.py (this plan).
   # NO other files.
   ```

8. **Locked UI strings present in BOTH code AND docs:**
   ```bash
   # Code (Plan 05-02 contribution):
   grep -nE '"LLM provider"' app.py
   # Docs (Plan 05-04 contribution):
   grep -nE "LLM provider" USER_GUIDE.md
   # Both: ≥1 match each
   ```

9. **No subprocess/network calls in the gate:**
   ```bash
   grep -nE "subprocess|requests\.(get|post|put|delete)|urllib|httpx" tests/test_phase5_ui.py
   # Expected: ZERO matches (this is a pure-mock module)
   ```

10. **Phase 5 sign-off readiness:**
    - All 5 ROADMAP SCs proven by named tests
    - All 11 requirements (UI-01..07, DOC-01..04) traceable to tests or to docs content
    - Manual operator-run smoke gate against stage gateway is the only remaining surface — documented in 05-04 README/USER_GUIDE smoke-test subsection
</verification>

<success_criteria>
- [ ] `tests/test_phase5_ui.py` exists; `pytest tests/test_phase5_ui.py -v` → all green (~20 tests)
- [ ] No `tests/conftest.py`, no `tests/pytest.ini`, no `tests/fixtures/phase5*` files created
- [ ] Autouse `_clear_factory_cache` (uses `_get_llm_cached.clear()`, NOT old `_cache.clear()`), `_strip_llm_env`, `_clear_streamlit_session_state` fixtures present
- [ ] SC #1 covered: ≥3 tests (PROVIDER_OPTIONS dict shape + selectbox label/options + session-state init from env + clamp-to-known)
- [ ] SC #2 covered: ≥3 tests (fingerprint privacy + _get_llm_cached call-args tuple + switch produces different tuple + _cache dict deleted)
- [ ] SC #3 covered: ≥3 tests (missing_vars return contract + warning content names vars + blocked flag toggles + chat_input disabled=True with swapped placeholder)
- [ ] SC #4 covered: ≥3 tests (history-survives-switch — caption reads stored dict not session_state + user-msg has no caption + no-provider-key skips caption + helper-static-source invariant)
- [ ] SC #5 covered: 2 tests (README content grep + USER_GUIDE locked UI strings + required topics grep)
- [ ] `provider_name` ABC test confirms `__abstractmethods__` membership; concrete adapters return canonical strings
- [ ] Combined `pytest tests/` is ~89 tests, all passing, in <20 seconds; zero live HTTP, zero live LLM, zero live Streamlit
- [ ] Phase 5 (the milestone): all 5 ROADMAP SCs proven; live smoke test against stage gateway remains operator-run per Phase 4 contract (documented in README + USER_GUIDE)
</success_criteria>

<output>
After completion, create `.planning/phases/05-sidebar-ui-toggle-documentation/05-05-SUMMARY.md` documenting:
- Total test count and pass-time
- Mapping from each Phase 5 SC to its proving test function(s) (5 entries)
- Mapping from each tracked RESEARCH.md pitfall to its regression-guard test (Pitfall 1, 6, 8, 11, 13)
- Confirmation: zero live HTTP, zero live LLM, zero live Streamlit; zero conftest.py; zero fixture files
- Combined Phase 1+2+3+4+5 result: e.g. `69 + 20 = 89 passed in 18.x s`
- Phase 5 sign-off statement: "All 5 ROADMAP success criteria proven; sidebar selectbox + missing-creds warning + per-message provenance caption + factory-cache invariants + README/USER_GUIDE documentation shipped. The multi-provider Streamlit toggle is live; operators select Azure OpenAI (default) or Anthropic Claude (MGTI) per session; historical messages keep their original provenance after switches. Phase 5 closes the snow_query multi-provider LLM integration milestone."
- Pending operator action: "Run `python scripts/smoke_llm.py --provider both --verbose` against the stage gateway with valid creds; paste the transcript into the Phase 5 verification PR. The README and USER_GUIDE document this as the operator-only live-credential gate."
</output>
