---
phase: 5
plan: 5
name: acceptance-gate
type: execute
wave: 4
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
    - "Test for chat_input disable wiring: when blocked flag True, chat_input is called with disabled=True AND swapped placeholder; when False, disabled=False AND placeholder='ENTER QUERY...'"
    - "Test for docs content: README and USER_GUIDE grep-assert each of the 7 locked UI strings + the 4 required documentation topics; README test asserts MGTI token presence"
    - "Combined Phase 1+2+3+4+5 suite is ~69 + ~21 = ~90 tests, all passing, zero live HTTP"
    - "All Streamlit context-manager mocks built via _build_streamlit_mock_surface() helper — single source of truth; ALL render_sidebar-exercising tests reuse it (no inline broken patch.multiple sidebar mocks)"
  artifacts:
    - path: "tests/test_phase5_ui.py"
      provides: "Phase 5 acceptance gate — pytest module proving all 5 SCs + cache key invariants + caption regression guards + docs-content checks"
      contains: "def test_sc1_"
  key_links:
    - from: "tests/test_phase5_ui.py SC #1 test"
      to: "app.py render_sidebar (via _build_streamlit_mock_surface helper + patch)"
      via: "build correctly-shaped streamlit mocks; call render_sidebar; capture selectbox kwargs"
      pattern: "_build_streamlit_mock_surface|patch\\(.streamlit\\."
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
      via: "open file, read text, assert required tokens present (including MGTI)"
      pattern: "README\\.md|USER_GUIDE\\.md"
---

<objective>
Create `tests/test_phase5_ui.py` — a pytest module proving ALL 5 Phase 5 success criteria PLUS the documented regression guards from RESEARCH.md (Pitfalls 1, 6, 8, 11, 13). A green run on this module IS the Phase 5 gate, just as Phase 1-4 had their dedicated acceptance gates.

Purpose: This is the rate-limiting evidence document for Phase 5 close-out. Following the Phase 1/2/3/4 precedent, the gate is one self-contained pytest module — no conftest.py, no pytest.ini, no fixture files, all mocks inline. Streamlit is mocked via `unittest.mock.patch` against the `streamlit` module (the render functions are called directly; the mocks capture call arguments for assertions). Zero live HTTP, zero live LLM, zero live Streamlit.

Output: `tests/test_phase5_ui.py` (~21 tests) covering: SC #1 (sidebar selectbox label/options/session-state init), SC #2 (cache-key invariant + fingerprint privacy), SC #3 (missing-vars warning + chat_input disable wiring BOTH blocked AND unblocked), SC #4 (per-message caption + history-survives-switch + user-msg guard), SC #5 (docs content grep — README MGTI + USER_GUIDE 7 locked strings). Combined Phase 1+2+3+4+5 run yields approximately 90 tests, all green, in under 20 seconds.
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

# This plan depends on all four prior plans (Plan 03 is now Wave 3, so Plan 05 is Wave 4)
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

1. **Test module is SELF-CONTAINED.** NO `conftest.py`. NO `pytest.ini`. NO new fixture files in `tests/fixtures/`. NO new helpers in `tests/`. Matches Phase 1/2/3/4 acceptance-gate pattern (STATE.md Phase 4-04 decision: "Test module self-contained — no conftest.py, no pytest.ini, no new tests/fixtures/ files").

2. **Streamlit mocking strategy — `_build_streamlit_mock_surface()` helper + `patch.multiple` with PRE-BUILT mocks (Blocker 3 fix).**

   **What was BROKEN in the earlier draft:**
   ```python
   # WRONG — do NOT do this:
   with patch.multiple(
       "streamlit",
       sidebar=MagicMock().__enter__.return_value,  # ← not a usable context manager
       ...
   ) as mocks:
       mocks["sidebar"] = MagicMock()              # ← does NOT change the patch
       mocks["sidebar"].__enter__ = MagicMock(...)
   ```

   Why it was wrong:
   - `MagicMock().__enter__.return_value` is a Mock instance, NOT a context-manager-shaped object.
   - Re-assigning `mocks["sidebar"]` AFTER `patch.multiple` entered does NOT change what was patched on `streamlit` — only mutates the local dict.
   - `with st.sidebar:` then fails to behave correctly.

   **The corrected pattern (USE THIS — single source of truth via helper):**

   Define a module-level helper at the TOP of `tests/test_phase5_ui.py`:

   ```python
   def _build_streamlit_mock_surface() -> dict:
       """Build a complete dict of correctly-shaped Streamlit primitive mocks.

       Returns a dict keyed by streamlit-primitive name, ready to splat into
       patch.multiple("streamlit", **surface). Context managers (sidebar,
       expander, chat_message, spinner, columns elements) are built BEFORE
       patch.multiple is entered, so their __enter__/__exit__ are real mocks
       that work with `with` statements.

       DRY rationale: at least 4 tests exercise render_sidebar() and need this
       same surface. Pasting a 15-line patch.multiple block into each test
       drifts over time and obscures what each test is really asserting.
       Centralize it here; each test overrides only the 1-2 primitives it
       asserts on.
       """
       # Build each context-manager mock once, with proper __enter__/__exit__
       sidebar_cm = MagicMock()
       sidebar_cm.__enter__ = MagicMock(return_value=None)
       sidebar_cm.__exit__ = MagicMock(return_value=None)

       expander_cm = MagicMock()
       expander_cm.__enter__ = MagicMock(return_value=None)
       expander_cm.__exit__ = MagicMock(return_value=None)

       chat_message_cm = MagicMock()
       chat_message_cm.__enter__ = MagicMock(return_value=None)
       chat_message_cm.__exit__ = MagicMock(return_value=None)

       spinner_cm = MagicMock()
       spinner_cm.__enter__ = MagicMock(return_value=None)
       spinner_cm.__exit__ = MagicMock(return_value=None)

       return {
           # Context managers — pre-built with working __enter__/__exit__
           "sidebar": sidebar_cm,
           "expander": MagicMock(return_value=expander_cm),  # st.expander() returns a CM
           "chat_message": MagicMock(return_value=chat_message_cm),
           "spinner": MagicMock(return_value=spinner_cm),
           # Layout
           "columns": MagicMock(return_value=(MagicMock(), MagicMock(), MagicMock())),
           "divider": MagicMock(),
           "markdown": MagicMock(),
           # Inputs (default-returns chosen to keep render functions on the happy path)
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
           # Data display
           "metric": MagicMock(),
           "dataframe": MagicMock(),
       }
   ```

   **Per-test usage pattern:**

   ```python
   def test_some_render_sidebar_behavior(some_env):
       import app
       import streamlit as st

       # Build the surface, override the 1-2 primitives this test cares about
       surface = _build_streamlit_mock_surface()
       surface["selectbox"] = MagicMock(return_value="Anthropic Claude (MGTI)")

       with patch.multiple("streamlit", **surface):
           # Seed any session_state this test depends on
           st.session_state["upload_authenticated"] = True
           app.render_sidebar()

           # Assert on the mock that this test focused on
           assert surface["selectbox"].call_args.args[0] == "LLM provider"
           ...
   ```

   This pattern:
   - Builds context-manager mocks BEFORE `patch.multiple` is entered (so `with st.sidebar:` actually works).
   - Re-uses the same correctly-shaped dict across every render_sidebar / render_main_content / render_chat_history test.
   - Lets each test override only what it asserts on — minimal noise.
   - The mocks ARE the same MagicMock instances accessible to the test (via `surface[name]`) — assertions on `call_args` / `call_count` work.

3. **Autouse `_clear_factory_cache` fixture** mirrors prior phases but uses the Plan 05-01-renamed `_get_llm_cached.clear()`:
   ```python
   @pytest.fixture(autouse=True)
   def _clear_factory_cache():
       import src.llm as llm_pkg
       clear_fn = getattr(llm_pkg._get_llm_cached, "clear", None)
       if callable(clear_fn):
           clear_fn()
       yield
       clear_fn = getattr(llm_pkg._get_llm_cached, "clear", None)
       if callable(clear_fn):
           clear_fn()
   ```

4. **Autouse `_strip_llm_env` fixture** mirrors prior phases verbatim — strips all LLM env vars between tests so each test sees a clean slate. Same var list as Phase 4 gate (`tests/test_phase4_strict_tools.py:226-244`).

5. **Realistic env constants** match prior phases:
   - `_AZURE_ENDPOINT = "https://example.openai.azure.com/openai/deployments/gpt-4o-mini/chat/completions"`
   - `_AZURE_MODEL = "gpt-4o-mini"`
   - `_AZURE_KEY = "azure-test-key-not-real"`
   - `_BASE_URL = "https://stage.int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1"`
   - `_API_KEY = "test-key-not-real"`
   - `_MODEL_SONNET = "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"`

6. **Streamlit session_state seeding pattern:** Streamlit's `session_state` is a special object. In tests, after `import streamlit as st`, we can write to it directly: `st.session_state["llm_provider"] = "azure_openai"`. Between tests, clear it via an autouse fixture.

7. **SC #2 cache-key test strategy:** use `unittest.mock.patch.object` to wrap `_get_llm_cached` and capture call args:
   ```python
   real_cached = llm_pkg._get_llm_cached
   with patch.object(llm_pkg, "_get_llm_cached", wraps=real_cached) as spy:
       get_llm("azure_openai")
       assert spy.call_args == call("azure_openai", _AZURE_ENDPOINT, "gpt-4o-mini", expected_fp)
   ```

8. **SC #3 warning test strategy:**
   - Strip env so `missing_vars("anthropic_mgti")` returns the full list of 3 names.
   - Seed `st.session_state["llm_provider"] = "anthropic_mgti"`.
   - Use `_build_streamlit_mock_surface()`; override `selectbox` to return the Anthropic option.
   - Call `app.render_sidebar()`.
   - Assert `surface["warning"].call_count >= 1` and the captured warning text contains all three var names AND the recovery-path phrase.
   - Assert `st.session_state["_llm_provider_blocked"] is True`.

9. **SC #3 chat_input disable test strategy — BOTH BLOCKED AND UNBLOCKED (Warning 5 fix):**

   The earlier draft had ONLY the BLOCKED case. A regression that always sets `disabled=True` would still pass that test. The unblocked case is mandatory for the disable-wiring contract.

   **Blocked case (`_llm_provider_blocked = True`):**
   - Set `st.session_state["_llm_provider_blocked"] = True`.
   - Use `_build_streamlit_mock_surface()`; override `chat_input` to capture invocations.
   - Call `app.render_main_content()`.
   - Assert `surface["chat_input"].call_args.kwargs.get("disabled") is True`.
   - Assert the placeholder argument is `"QUERY DISABLED — see sidebar warning"`.

   **Unblocked case (`_llm_provider_blocked = False`) — NEW per Warning 5:**
   - Set `st.session_state["_llm_provider_blocked"] = False`.
   - Use `_build_streamlit_mock_surface()`; override `chat_input` to capture invocations.
   - Call `app.render_main_content()`.
   - Assert `surface["chat_input"].call_args.kwargs.get("disabled") is False`.
   - Assert the placeholder argument is EXACTLY `"ENTER QUERY..."` (Warning 7 fix — lock the default string against drift).

10. **SC #4 history-survives-switch test strategy (the LOAD-BEARING test of this plan):**
    - Seed `st.session_state["messages"]` with two messages: one assistant message with `provider="anthropic_mgti"`, `model="eu.anthropic.claude-sonnet-4-5-20250929-v1:0"`, and a user message (no provider key).
    - Set `st.session_state["llm_provider"] = "azure_openai"` (the OPPOSITE provider — simulating a switch after the message was written).
    - Use `_build_streamlit_mock_surface()`; assert on `surface["caption"]`.
    - Call `app.render_chat_history()`.
    - Assert `surface["caption"]` was called with a string containing `"Anthropic Claude (MGTI)"` AND `"eu.anthropic.claude-sonnet-4-5"` (the ORIGINAL provider's name + model — NOT the currently selected Azure OpenAI).
    - Also assert `surface["caption"]` was NOT called for the user message (guard from Pitfall 11).

11. **SC #4 helper invariant test:** open `app.py`, find `_render_provenance_caption`, parse with `ast`, and assert its body does NOT reference `session_state`. This is a static check — the helper must NEVER read session_state. Plan 05-03 documented this invariant; this test locks it in CI.

12. **SC #5 docs-content test strategy (Warning 6 fix — README MGTI assertion):**

    **README test (`test_sc5_readme_contains_required_topics`):**
    - Open `README.md`. Read into a string.
    - Assert each of: `"LLM Provider Selection"`, `"Anthropic Claude"`, `"smoke_llm.py"`, `"USER_GUIDE.md"`, AND `"MGTI"` (Warning 6 — assert the constraint reference is present, not just `"Hubble"`).
    - Docstring note: the warning-resolution topic is intentionally covered via the README→USER_GUIDE cross-link (README is short; deep walkthrough lives in USER_GUIDE).

    **USER_GUIDE test (`test_sc5_user_guide_contains_locked_ui_strings_and_required_topics`):**
    - Open `USER_GUIDE.md`. Read into a string.
    - Assert each of the 7 locked UI strings: `"LLM provider"`, `"Azure OpenAI"`, `"Anthropic Claude (MGTI)"`, `"LLM PROVIDER"` (uppercase header), `"QUERY DISABLED"`, `"hubble.mmc.com"`, `"smoke_llm.py"`.
    - Assert each of the 4 required topics: `"LLM Provider Selection"`, `"MGTI"`, `"First-Time"`, `"Mid-Session"`.
    - Assert the warning-resolution table names all three Anthropic vars: `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`.
    - Use case-sensitive matching.

13. **NO live Streamlit run.** All tests run under pytest with `streamlit` mocked via the helper-built surface. The `streamlit` package IS imported (it's a dependency), but every primitive is patched per-test via `patch.multiple("streamlit", **surface)`.

14. **NO `pytest.importorskip("streamlit")`.** Streamlit is a hard dependency of the app — `requirements.txt:1`. If pytest is running without streamlit, that's a setup error worth surfacing as an ImportError, not a SKIP.

15. **Test count target ~21**, structured by SC:
    - SC #1 (sidebar selectbox label/options/state-init/clamp): 4 tests
    - SC #2 (cache-key tuple + fingerprint + cache-deleted): 4 tests
    - SC #3 (warning content + chat_input disable BLOCKED + chat_input enabled UNBLOCKED + clear flag): 4 tests (Warning 5: added the unblocked case)
    - SC #4 (caption render + history-survives-switch + user-msg guard + helper invariant): 4 tests
    - SC #5 (README + USER_GUIDE content): 2 tests
    - Helper sanity / Plan 05-01 surface (`_fingerprint`, `missing_vars`, provider_name ABC, PROVIDER_OPTIONS=REGISTRY): ~3 tests
    - Total: ~21 tests

16. **`provider_name` on ABC test:** since Plan 05-01 added `provider_name` as `@property @abc.abstractmethod`, add ONE test verifying the ABC's `__abstractmethods__` contains `provider_name` AND both adapters return their canonical strings.

17. **Static-source assertion approach for helper invariant** (locked decision §11 / RESEARCH Pitfall 11):
    ```python
    def test_render_provenance_caption_does_not_read_session_state():
        from app import _render_provenance_caption
        src = inspect.getsource(_render_provenance_caption)
        assert "session_state" not in src, (
            f"_render_provenance_caption MUST NOT reference session_state — "
            f"Phase 5 RESEARCH.md Pitfall 11 violated. Body:\n{src}"
        )
    ```

18. **No new dependencies.** `unittest.mock`, `os`, `pytest`, `inspect`, `ast`, `hashlib` are all stdlib or already installed (`pytest` from prior phases).

19. **Wave 4 placement.** Plan 05-03 moved to Wave 3 (depends on Plan 05-02's `_PROVIDER_LABELS` and import line — see Plan 05-03 decision §16). Plan 05-05 therefore moves from Wave 3 → Wave 4, with `depends_on: [1, 2, 3, 4]` (Plan 05-04 docs still need to land before the SC #5 docs-content tests can pass).
</decisions>

<tasks>

<task type="auto">
  <name>Task 5.1: Write tests/test_phase5_ui.py — full acceptance gate (~21 tests) using _build_streamlit_mock_surface helper for all render_sidebar / render_main_content / render_chat_history tests</name>
  <files>tests/test_phase5_ui.py</files>
  <action>
**Write `tests/test_phase5_ui.py`.** Use the skeleton below; flesh out each test per the SC breakdown in locked decision §15. Write all test bodies verbatim — no `# TODO` markers, no `...` placeholders.

**CRITICAL: every test that calls `app.render_sidebar()`, `app.render_main_content()`, or `app.render_chat_history()` MUST use `_build_streamlit_mock_surface()` — do NOT paste inline `patch.multiple` blocks with broken `MagicMock().__enter__.return_value` patterns.**

**MODULE HEADER + IMPORTS + HELPER + AUTOUSE FIXTURES + ENV CONSTANTS:**

```python
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
# Streamlit mock surface helper — single source of truth for ALL render_*
# tests. Builds context-manager mocks BEFORE patch.multiple is entered so
# `with st.sidebar:` / `with st.chat_message(...)` / `with st.spinner(...)`
# all behave correctly. (DRY across 4+ tests; corrects the earlier draft's
# `MagicMock().__enter__.return_value` mis-pattern.)
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
    sidebar_cm = MagicMock()
    sidebar_cm.__enter__ = MagicMock(return_value=None)
    sidebar_cm.__exit__ = MagicMock(return_value=None)

    expander_cm = MagicMock()
    expander_cm.__enter__ = MagicMock(return_value=None)
    expander_cm.__exit__ = MagicMock(return_value=None)

    chat_message_cm = MagicMock()
    chat_message_cm.__enter__ = MagicMock(return_value=None)
    chat_message_cm.__exit__ = MagicMock(return_value=None)

    spinner_cm = MagicMock()
    spinner_cm.__enter__ = MagicMock(return_value=None)
    spinner_cm.__exit__ = MagicMock(return_value=None)

    return {
        # Context managers (pre-built with __enter__/__exit__)
        "sidebar": sidebar_cm,
        "expander": MagicMock(return_value=expander_cm),
        "chat_message": MagicMock(return_value=chat_message_cm),
        "spinner": MagicMock(return_value=spinner_cm),
        # Layout
        "columns": MagicMock(return_value=(MagicMock(), MagicMock(), MagicMock())),
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
```

**Continue writing the test functions.** Group by SC. Each test function has a one-line docstring referencing the SC or pitfall it proves. **Every render_sidebar / render_main_content / render_chat_history test MUST use `_build_streamlit_mock_surface()` — no inline broken patch.multiple blocks.**

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


def test_sc1_session_state_initialized_from_env_default(azure_env, monkeypatch):
    """SC #1: st.session_state['llm_provider'] is initialized from LLM_PROVIDER_DEFAULT."""
    import app
    import streamlit as st

    monkeypatch.setenv("LLM_PROVIDER_DEFAULT", "anthropic_mgti")
    st.session_state["upload_authenticated"] = True
    st.session_state["data_loaded"] = False

    surface = _build_streamlit_mock_surface()
    surface["selectbox"] = MagicMock(return_value="Anthropic Claude (MGTI)")

    with patch.multiple("streamlit", **surface):
        app.render_sidebar()

    # Session state was initialized from env, then updated by selectbox return
    assert st.session_state["llm_provider"] == "anthropic_mgti"


def test_sc1_session_state_clamps_unknown_env_to_azure(monkeypatch):
    """SC #1 + RESEARCH Pitfall 2: unknown LLM_PROVIDER_DEFAULT falls back to azure_openai."""
    import app
    import streamlit as st

    monkeypatch.setenv("LLM_PROVIDER_DEFAULT", "anthropic_typo_oops")
    st.session_state["upload_authenticated"] = True

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
    README→USER_GUIDE cross-link (README is short; deep walkthrough lives in
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
```

**Run the suite as you write to catch issues early:**

```bash
pytest tests/test_phase5_ui.py -v --tb=short
```

If a test fails because `render_sidebar`/`render_main_content`/`render_chat_history` raised inside `patch.multiple`, READ the traceback to see which Streamlit primitive needs to be added to `_build_streamlit_mock_surface()`. Extend the helper, not the individual tests — keep the surface DRY.

**Critical: do NOT replace the helper-based mocks with inline `patch.multiple` blocks.** The earlier draft of this plan had a broken inline pattern (`MagicMock().__enter__.return_value` for context managers). The helper is the corrected, central pattern.
  </action>
  <verify>
```bash
# 1. New test file exists
ls -la tests/test_phase5_ui.py
# Expected: file present

# 2. No new fixture files or conftest.py
ls tests/conftest.py tests/fixtures/phase5* 2>/dev/null
# Expected: no matches

# 3. Helper present at module scope
grep -nE "^def _build_streamlit_mock_surface" tests/test_phase5_ui.py
# Expected: 1 match

# 4. ALL render_* tests use the helper (no inline broken patch.multiple sidebar mocks)
# Check that no test contains the broken pattern:
grep -nE "MagicMock\(\)\.__enter__\.return_value" tests/test_phase5_ui.py
# Expected: 0 matches (the broken pattern from the earlier draft is GONE)

# 5. The helper is called by multiple tests
grep -cE "_build_streamlit_mock_surface\(\)" tests/test_phase5_ui.py
# Expected: ≥4 calls (SC #1 render, SC #1 init, SC #1 clamp, SC #3 warning, SC #3 blocked, SC #3 unblocked, SC #4 history etc.)

# 6. Run Phase 5 gate ALONE
pytest tests/test_phase5_ui.py -v
# Expected: ~21 tests, ALL PASSING, in <10 seconds

# 7. Run combined Phase 1+2+3+4+5 gate
pytest tests/ -v
# Expected: ~90 tests (69 prior + ~21 Phase 5), ALL PASSING

# 8. SC #3 has BOTH the blocked AND unblocked chat_input tests
grep -nE "test_sc3_chat_input_disabled_when_blocked|test_sc3_chat_input_enabled_when_not_blocked" tests/test_phase5_ui.py
# Expected: 2 matches

# 9. Default placeholder string locked in the unblocked test
grep -nE 'placeholder == "ENTER QUERY\.\.\."' tests/test_phase5_ui.py
# Expected: ≥1 match

# 10. README MGTI assertion present
grep -nE 'assert "MGTI" in text' tests/test_phase5_ui.py
# Expected: 1 match (in the README test)

# 11. All 5 SCs traceable
grep -nE "def test_sc[0-9]_" tests/test_phase5_ui.py
# Expected: SC #1 (≥3), SC #2 (≥3), SC #3 (≥4 — note: blocked + unblocked + warning + missing_vars), SC #4 (≥3), SC #5 (=2)

# 12. Module loads cleanly
python -c "import ast; ast.parse(open('tests/test_phase5_ui.py').read()); print('OK')"
# Expected: OK
```
  </verify>
  <done>
`tests/test_phase5_ui.py` exists with ~21 tests covering all 5 Phase 5 SCs, the fingerprint-privacy regression guard (Pitfall 1), the module-level _cache deletion check (Pitfall 6), the provider_name ABC + concrete overrides (Pitfall 8), the helper-static-source invariant (Pitfall 11), the history-survives-switch LOAD-BEARING assertion (SC #4), the chat_input disable wiring (SC #3 — BOTH blocked AND unblocked, with the default placeholder string locked), and docs-content grep (SC #5 + Pitfall 13 — README MGTI assertion present). The `_build_streamlit_mock_surface()` helper is the SINGLE source of truth for Streamlit mocks; the broken `MagicMock().__enter__.return_value` pattern from the earlier draft is GONE. Zero conftest.py. Zero pytest.ini. Zero fixture files. Zero live HTTP, zero live LLM, zero live Streamlit. Combined Phase 1+2+3+4+5 pytest run is ~90 tests, all passing. Only `tests/test_phase5_ui.py` modified by this plan.
  </done>
</task>

</tasks>

<verification>
Phase-level verification for Plan 05-05 (and Phase 5 overall):

1. **Combined gate green:**
   ```bash
   pytest tests/ -v
   # Expected: ~90 tests pass; 0 failures; <20 seconds wall-clock
   ```

2. **No new fixture infrastructure:**
   ```bash
   ls tests/conftest.py tests/pytest.ini tests/fixtures/phase5* 2>/dev/null
   # Expected: zero output
   ```

3. **Self-contained module count:**
   ```bash
   pytest tests/test_phase5_ui.py --collect-only -q | wc -l
   # Expected: ~22 (21 tests + 1 summary); ±3 tolerance
   ```

4. **All 5 SCs traceable:**
   ```bash
   grep -nE "def test_sc[0-9]_" tests/test_phase5_ui.py
   # Expected:
   #   SC #1: ≥3 tests
   #   SC #2: ≥3 tests
   #   SC #3: ≥4 tests (including BOTH blocked AND unblocked chat_input)
   #   SC #4: ≥3 tests
   #   SC #5: ≥2 tests (with README MGTI + USER_GUIDE 7-string + 4-topic assertions)
   ```

5. **Helper is single source of truth:**
   ```bash
   grep -cE "_build_streamlit_mock_surface\(\)" tests/test_phase5_ui.py
   # Expected: ≥4 (called by every render_* exercising test)
   grep -nE "MagicMock\(\)\.__enter__\.return_value" tests/test_phase5_ui.py
   # Expected: 0 (the broken pattern is GONE)
   ```

6. **Pitfall regression guards present:**
   ```bash
   grep -nE "Pitfall 1|Pitfall 6|Pitfall 8|Pitfall 11|Pitfall 13" tests/test_phase5_ui.py
   # Expected: ≥5 matches
   ```

7. **Phase 1+2+3+4 gates preserved:**
   ```bash
   pytest tests/test_llm_seam.py tests/test_phase2_parity.py tests/test_phase3_adapter.py tests/test_phase4_strict_tools.py -v
   # Expected: 69 passed (same as before Phase 5)
   ```

8. **Plan 05-05's diff touches ONLY its declared file:**
   ```bash
   git diff --stat HEAD~ -- src/ app.py scripts/ tests/ README.md USER_GUIDE.md
   # Expected: across the whole Phase 5 wave: app.py (Plans 02+03), src/llm/* (Plan 01),
   # tests/test_llm_seam.py, tests/test_phase2_parity.py, tests/test_phase3_adapter.py,
   # tests/test_phase4_strict_tools.py (Plan 01's test rewires),
   # README + USER_GUIDE (Plan 04), tests/test_phase5_ui.py (this plan).
   # NO other files.
   ```

9. **Locked UI strings present in BOTH code AND docs:**
   ```bash
   grep -nE '"LLM provider"' app.py
   grep -nE "LLM provider" USER_GUIDE.md
   # Both: ≥1 match each
   ```

10. **No subprocess/network calls in the gate:**
    ```bash
    grep -nE "subprocess|requests\.(get|post|put|delete)|urllib|httpx" tests/test_phase5_ui.py
    # Expected: ZERO matches (this is a pure-mock module)
    ```

11. **Phase 5 sign-off readiness:**
    - All 5 ROADMAP SCs proven by named tests
    - All 11 requirements (UI-01..07, DOC-01..04) traceable to tests or to docs content
    - chat_input BOTH branches asserted (no false-pass against an always-disabled regression)
    - README MGTI token explicitly asserted (Warning 6 closed)
    - Helper-based Streamlit mocks (Blocker 3 closed)
    - Manual operator-run smoke gate against stage gateway remains the only live surface — documented in 05-04 README/USER_GUIDE smoke-test subsection
</verification>

<success_criteria>
- [ ] `tests/test_phase5_ui.py` exists; `pytest tests/test_phase5_ui.py -v` → all green (~21 tests)
- [ ] `_build_streamlit_mock_surface()` helper defined at module scope; ALL render_sidebar / render_main_content / render_chat_history exercising tests use it
- [ ] The broken `MagicMock().__enter__.return_value` pattern is ABSENT from the file (Blocker 3 closed)
- [ ] No `tests/conftest.py`, no `tests/pytest.ini`, no `tests/fixtures/phase5*` files created
- [ ] Autouse `_clear_factory_cache` (uses `_get_llm_cached.clear()` via `getattr + callable`), `_strip_llm_env`, `_clear_streamlit_session_state` fixtures present
- [ ] SC #1 covered: ≥3 tests
- [ ] SC #2 covered: ≥3 tests
- [ ] SC #3 covered: ≥4 tests (missing_vars return + warning content + chat_input BLOCKED branch + chat_input UNBLOCKED branch — Warning 5 closed)
- [ ] SC #3 unblocked test asserts `placeholder == "ENTER QUERY..."` exactly (Warning 7 closed)
- [ ] SC #4 covered: ≥3 tests (history-survives-switch + user-msg-guard + no-provider-key skips + helper-static-source invariant)
- [ ] SC #5 covered: 2 tests; README test asserts `"MGTI" in text` (Warning 6 closed); USER_GUIDE test asserts all 7 locked UI strings + 4 required topics + 3 ANTHROPIC_* warning-table vars
- [ ] `provider_name` ABC test confirms `__abstractmethods__` membership; concrete adapters return canonical strings
- [ ] Combined `pytest tests/` is ~90 tests, all passing, in <20 seconds; zero live HTTP, zero live LLM, zero live Streamlit
- [ ] Phase 5 (the milestone): all 5 ROADMAP SCs proven; live smoke test against stage gateway remains operator-run per Phase 4 contract (documented in README + USER_GUIDE)
</success_criteria>

<output>
After completion, create `.planning/phases/05-sidebar-ui-toggle-documentation/05-05-SUMMARY.md` documenting:
- Total test count (~21) and pass-time
- Mapping from each Phase 5 SC to its proving test function(s) (5 entries)
- Mapping from each tracked RESEARCH.md pitfall to its regression-guard test (Pitfall 1, 6, 8, 11, 13)
- Confirmation: `_build_streamlit_mock_surface()` is the single source of truth for Streamlit mocks (Blocker 3 closure)
- Confirmation: SC #3 covers BOTH blocked AND unblocked chat_input branches (Warning 5 closure)
- Confirmation: default placeholder `"ENTER QUERY..."` locked by test (Warning 7 closure)
- Confirmation: README test asserts `"MGTI"` token presence (Warning 6 closure)
- Confirmation: zero live HTTP, zero live LLM, zero live Streamlit; zero conftest.py; zero fixture files
- Combined Phase 1+2+3+4+5 result: e.g. `69 + 21 = 90 passed in 18.x s`
- Phase 5 sign-off statement: "All 5 ROADMAP success criteria proven; sidebar selectbox + missing-creds warning + per-message provenance caption + factory-cache invariants + README/USER_GUIDE documentation shipped. The multi-provider Streamlit toggle is live; operators select Azure OpenAI (default) or Anthropic Claude (MGTI) per session; historical messages keep their original provenance after switches. Phase 5 closes the snow_query multi-provider LLM integration milestone."
- Pending operator action: "Run `python scripts/smoke_llm.py --provider both --verbose` against the stage gateway with valid creds; paste the transcript into the Phase 5 verification PR."
</output>
