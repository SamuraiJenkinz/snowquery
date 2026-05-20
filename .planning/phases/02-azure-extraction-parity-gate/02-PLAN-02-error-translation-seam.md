---
phase: 02-azure-extraction-parity-gate
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - src/llm/_compat.py
autonomous: true

must_haves:
  truths:
    - "src/llm/_compat.py exists and exports a single public function: llm_to_query_error() — a contextlib.contextmanager that catches LLMError subclasses and re-raises as QueryError (success criterion #3, ERR-04)"
    - "The LLMError→QueryError translation table appears EXACTLY ONCE in the codebase (CONTEXT.md decision 2)"
    - "LLMConfigError is translated by passing str(e) through as QueryError.message — the compat layer does NOT hardcode 'Azure' or 'Anthropic' in the message (RESEARCH.md OQ-1 — Phase-3-clean)"
    - "LLMAuthError is translated to QueryError with the historic remediation text 'Set the AZURE_OPENAI_API_KEY environment variable.' so users see the same error UI today (success criterion #3 preserves user-visible contract). KNOWN PHASE 3 DEBT: this branch hardcodes Azure-specific remediation text and is intentionally NOT provider-neutral — Phase 3 must update it when AnthropicMGTIClient lands (e.g. dispatch on `e.provider` to emit 'Set the ANTHROPIC_API_KEY environment variable.' for Anthropic). The Azure-specific text is correct and required for Phase 2 byte-identical parity; do not generalize it prematurely."
    - "LLMTimeoutError / LLMTransientError / generic LLMError all translate to QueryError('Azure OpenAI API call failed', str(e)) — same first-arg string the old _call_azure_openai produced"
    - "Translation uses 'raise QueryError(...) from e' to preserve the LLMError as __cause__ for debugging (Python exception-chaining convention)"
  artifacts:
    - path: "src/llm/_compat.py"
      provides: "llm_to_query_error() context manager — the single LLMError→QueryError translation point"
      contains: "@contextlib.contextmanager"
      min_lines: 30
  key_links:
    - from: "src/llm/_compat.py"
      to: "src.utils.QueryError"
      via: "imports QueryError; raises QueryError from the LLMError caught in the context manager"
      pattern: "from src\\.utils import QueryError"
    - from: "src/llm/_compat.py"
      to: "src.llm.errors (LLMError subclasses)"
      via: "catches LLMConfigError / LLMAuthError / LLMTimeoutError / LLMTransientError / LLMError in ordered except clauses"
      pattern: "except LLM(Config|Auth|Timeout|Transient)?Error"
---

<objective>
Create `src/llm/_compat.py` containing `llm_to_query_error()` — a `contextlib.contextmanager` that is the SINGLE place in the codebase where typed `LLMError` subclasses are translated back into `QueryError`. Plan 03's three call sites import this and wrap their `client.complete(...)` calls with `with llm_to_query_error():`.

Purpose: Phase 2 success criterion #3 requires that the user-visible error contract is preserved — Azure timeouts/5xx must surface as `QueryError` (NOT `LLMError`) at the call-site boundary, and the historic remediation text ("Set the AZURE_OPENAI_API_KEY environment variable.") must still reach the user. Without this seam, every call site would need its own translation block, the translation table would drift, and Phase 3 would have to revisit three files to add Anthropic-specific behavior. The context manager pattern collapses the translation to one location.

Output: One new file (`src/llm/_compat.py`) with ~30-50 lines: imports + one decorated function.
</objective>

<execution_context>
@C:\Users\taylo\.claude\get-shit-done\workflows\execute-plan.md
@C:\Users\taylo\.claude\get-shit-done\templates\summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/02-azure-extraction-parity-gate/02-CONTEXT.md
@.planning/phases/02-azure-extraction-parity-gate/02-RESEARCH.md

# The error taxonomy this compat layer translates FROM
@src/llm/errors.py

# The exception class this compat layer translates TO
@src/utils.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create src/llm/_compat.py with the llm_to_query_error() context manager</name>
  <files>src/llm/_compat.py</files>
  <action>
Create a new file at `src/llm/_compat.py`. The leading underscore signals package-internal: only the three call sites in `query_router.py` and `sql_generator.py` should import it. It is NOT re-exported from `src/llm/__init__.py` (Phase 1's `__init__.py` should remain unchanged by this plan).

Exact file contents (RESEARCH.md "Error Translation Design" + OQ-1 resolution):

```python
"""LLMError → QueryError translation seam (success criterion #3, ERR-04).

This module is the SINGLE place in the codebase that maps the typed
LLMError family back into the legacy QueryError that the existing UI
already knows how to render. Call sites consume this via:

    from src.llm import get_llm
    from src.llm._compat import llm_to_query_error

    client = get_llm()
    with llm_to_query_error():
        content = client.complete(messages, max_tokens=500).strip()

Design notes (locked decisions from CONTEXT.md / RESEARCH.md):

  * The translation table appears here EXACTLY ONCE — if Phase 3 needs
    new behavior for LLMGuardrailError or provider-specific remediation,
    it edits this file and only this file.

  * LLMConfigError is translated by passing str(e) through as the
    QueryError.message. The adapter (Phase 2 AzureOpenAIClient and
    Phase 3 AnthropicMGTIClient) embeds provider-specific remediation
    text in the LLMConfigError message at raise time. This keeps the
    compat layer provider-agnostic — adding Anthropic does NOT require
    editing this file (RESEARCH.md "Phase 3 Compatibility Check").

  * LLMAuthError uses the historic 'Set the AZURE_OPENAI_API_KEY ...'
    remediation text to preserve byte-identical user-visible behavior
    today. Phase 3 may revisit this branch when the Anthropic adapter
    lands — at that point the branch can dispatch on e.provider.

  * All raise statements use 'from e' to preserve the underlying
    LLMError as __cause__ for debugging (PEP 3134).

  * The catch-all 'except LLMError' branch ensures NO LLMError subclass
    can leak past this context manager — even future ones added in
    Phase 3 (LLMGuardrailError, LLMSchemaError) will be caught.
"""
from __future__ import annotations

import contextlib
from typing import Iterator

from src.llm.errors import (
    LLMAuthError,
    LLMConfigError,
    LLMError,
    LLMTimeoutError,
    LLMTransientError,
)
from src.utils import QueryError


@contextlib.contextmanager
def llm_to_query_error() -> Iterator[None]:
    """Translate LLMError subclasses raised inside the block to QueryError.

    Call sites in query_router.py and sql_generator.py wrap their
    client.complete(...) call with this context manager so the existing
    QueryError-based error UI keeps working unchanged.

    The order of except clauses matters: subclasses must come before
    LLMError (Python catches the first matching except).

    Raises:
        QueryError: wrapping whichever LLMError subclass fired inside
            the `with` block. The original exception is attached as
            __cause__ via `raise ... from e`.
    """
    try:
        yield
    except LLMConfigError as e:
        # Provider embeds remediation text in the LLMConfigError message
        # at raise time (see AzureOpenAIClient.complete pre-flight check).
        # Pass str(e) through as the QueryError.message so the user sees
        # the same actionable text today and after Phase 3 adds Anthropic.
        raise QueryError(str(e), "Check your .env configuration.") from e
    except LLMAuthError as e:
        # HTTP 401/403 from the provider — key was present but invalid.
        # The historic remediation text in _call_azure_openai (today) is:
        #   QueryError("Azure OpenAI API key not configured",
        #              "Set the AZURE_OPENAI_API_KEY environment variable.")
        # which is the same user-visible text we want here (the old code
        # didn't actually distinguish missing-key vs invalid-key at the
        # HTTP layer — RequestException covered both).
        raise QueryError(
            "Azure OpenAI API key not configured",
            "Set the AZURE_OPENAI_API_KEY environment variable.",
        ) from e
    except LLMTimeoutError as e:
        raise QueryError("Azure OpenAI API call failed", str(e)) from e
    except LLMTransientError as e:
        raise QueryError("Azure OpenAI API call failed", str(e)) from e
    except LLMError as e:
        # Catch-all for any other LLMError subclass (LLMSchemaError today,
        # LLMGuardrailError in Phase 3, anything new in Phase 4+).
        raise QueryError("Azure OpenAI API call failed", str(e)) from e
```

Requirements:

- **Single file, single function.** Do NOT add other helpers here. The `_log_llm_call` helper lives in each adapter (Plan 01 owns it for Azure; Phase 3 owns it for Anthropic). The compat layer is just the error-translation seam.
- **Catch order is fixed.** `LLMConfigError`, `LLMAuthError`, `LLMTimeoutError`, `LLMTransientError`, then catch-all `LLMError`. Python checks except clauses top-to-bottom; placing `LLMError` first would shadow all subclasses.
- **`raise ... from e`** preserves the chain — `QueryError.__cause__` is the original `LLMError`. Useful for debugging via `traceback.print_exception`.
- **DO NOT modify `src/llm/__init__.py`** to re-export `llm_to_query_error`. The leading underscore is the signal; call sites import directly from `src.llm._compat`. Re-exporting would invite use from app code that should be holding `LLMError` directly.
- **DO NOT add a `provider` parameter** to `llm_to_query_error()`. RESEARCH.md OQ-1 resolved this: provider-specific remediation lives in the adapter's `LLMConfigError` message text; the compat layer stays provider-agnostic. (Phase 3 may revisit `LLMAuthError` if Anthropic needs a different remediation string — but that change happens INSIDE this file, not as a parameter at call sites.)
- **`Iterator[None]` return annotation** — the contextlib idiom. The function is a generator; the decorator wraps it into a context manager. The type hint is `Iterator[None]` because `yield` produces one `None`.
  </action>
  <verify>
Run from project root:

```
python -c "
import contextlib
from src.llm._compat import llm_to_query_error
from src.llm.errors import (
    LLMAuthError, LLMConfigError, LLMError, LLMSchemaError,
    LLMTimeoutError, LLMTransientError,
)
from src.utils import QueryError

# 1. The decorated function is callable as a context manager.
with llm_to_query_error():
    pass  # no exception raised, no translation needed

# 2. LLMConfigError → QueryError(str(e), 'Check your .env configuration.')
try:
    with llm_to_query_error():
        raise LLMConfigError(
            'Azure OpenAI API key not configured. '
            'Set the AZURE_OPENAI_API_KEY environment variable.',
            provider='azure_openai',
        )
    raise AssertionError('expected QueryError to be raised')
except QueryError as e:
    assert 'AZURE_OPENAI_API_KEY' in e.message, f'config remediation missing: {e.message!r}'
    assert e.details == 'Check your .env configuration.', f'details wrong: {e.details!r}'
    assert isinstance(e.__cause__, LLMConfigError), f'cause chain broken: {type(e.__cause__)}'

# 3. LLMAuthError → QueryError('Azure OpenAI API key not configured', 'Set the AZURE_OPENAI_API_KEY environment variable.')
try:
    with llm_to_query_error():
        raise LLMAuthError('HTTP 401', provider='azure_openai', status_code=401)
    raise AssertionError('expected QueryError')
except QueryError as e:
    assert e.message == 'Azure OpenAI API key not configured', f'auth message wrong: {e.message!r}'
    assert e.details == 'Set the AZURE_OPENAI_API_KEY environment variable.', f'auth details wrong: {e.details!r}'

# 4. LLMTimeoutError → QueryError('Azure OpenAI API call failed', str(e))
try:
    with llm_to_query_error():
        raise LLMTimeoutError('request timed out after 30s', provider='azure_openai')
    raise AssertionError('expected QueryError')
except QueryError as e:
    assert e.message == 'Azure OpenAI API call failed', f'timeout message wrong: {e.message!r}'
    assert 'timed out' in e.details, f'timeout details wrong: {e.details!r}'

# 5. LLMTransientError → same first-arg as timeout
try:
    with llm_to_query_error():
        raise LLMTransientError('HTTP 503', provider='azure_openai', status_code=503)
    raise AssertionError('expected QueryError')
except QueryError as e:
    assert e.message == 'Azure OpenAI API call failed', f'transient message wrong: {e.message!r}'

# 6. Catch-all: bare LLMError or future subclass like LLMSchemaError
try:
    with llm_to_query_error():
        raise LLMSchemaError('malformed JSON', provider='azure_openai')
    raise AssertionError('expected QueryError')
except QueryError as e:
    assert e.message == 'Azure OpenAI API call failed', f'catch-all message wrong: {e.message!r}'
    assert isinstance(e.__cause__, LLMSchemaError), f'cause chain broken for schema error: {type(e.__cause__)}'

# 7. Non-LLM exceptions pass through unchanged (e.g. KeyError from call-site logic)
try:
    with llm_to_query_error():
        raise KeyError('not an LLM error')
    raise AssertionError('expected KeyError to pass through')
except KeyError:
    pass  # correct — not our concern
except QueryError:
    raise AssertionError('compat layer wrapped a non-LLMError — leak!')

# 8. QueryError already raised inside the block is NOT wrapped (passes through)
try:
    with llm_to_query_error():
        raise QueryError('something else', 'unrelated to LLM')
    raise AssertionError('expected QueryError to pass through')
except QueryError as e:
    assert e.message == 'something else', f'QueryError got re-wrapped: {e.message!r}'

print('PLAN 02-02 VERIFICATION OK')
"
```

Must print `PLAN 02-02 VERIFICATION OK`.

This proves the eight observable behaviors required by success criterion #3 and ERR-04:
1. Empty block works.
2. `LLMConfigError` → `QueryError` with `str(e)` as message and `__cause__` preserved.
3. `LLMAuthError` → `QueryError` with historic Azure remediation text.
4. `LLMTimeoutError` → `QueryError("Azure OpenAI API call failed", str(e))`.
5. `LLMTransientError` → same.
6. `LLMSchemaError` (catch-all) → `QueryError` with details from `str(e)` and `__cause__` preserved.
7. Non-LLM exceptions pass through unchanged (no over-catching).
8. `QueryError` raised inside the block is NOT re-wrapped (would cause double-wrap if it were).
  </verify>
  <done>
- `src/llm/_compat.py` exists with one public function: `llm_to_query_error()` decorated with `@contextlib.contextmanager`.
- All 5 translation branches present in the correct order: `LLMConfigError`, `LLMAuthError`, `LLMTimeoutError`, `LLMTransientError`, catch-all `LLMError`.
- `LLMConfigError` branch uses `str(e)` for the `QueryError.message` (Phase-3-clean — adapter embeds provider-specific text in the LLMConfigError message).
- `LLMAuthError` branch hardcodes the historic Azure remediation text to preserve user-visible behavior.
- Every translation uses `from e` so the original LLMError is preserved as `__cause__`.
- Non-LLM exceptions and pre-existing `QueryError`s pass through unchanged.
- `src/llm/__init__.py` is NOT modified by this plan — `_compat` is package-internal.
- Phase 1's `tests/test_llm_seam.py` still passes (no surface area changed).
- Satisfies ERR-04 + success criterion #3 (the seam exists; Plan 03 wires the three call sites through it; Plan 04 proves the end-to-end error-path parity).
  </done>
</task>

</tasks>

<verification>
After Task 1, confirm:

```
# 1. File exists and is minimal (one function, ~30-60 lines is the target).
python -c "
import inspect
import src.llm._compat as m
funcs = [n for n in dir(m) if not n.startswith('_') and callable(getattr(m, n))]
# The only PUBLIC name we expect is llm_to_query_error (contextmanager IS a callable but is in dir as 'contextmanager' — that's the stdlib decorator imported, not a public surface).
# Use inspect.getmembers to be precise:
public_funcs = [n for n, obj in inspect.getmembers(m) if inspect.isfunction(obj) and not n.startswith('_') and getattr(obj, '__module__', '') == 'src.llm._compat']
assert public_funcs == ['llm_to_query_error'], f'unexpected public funcs in _compat: {public_funcs}'
print('OK')
"

# 2. Phase 1 acceptance gate still passes
python -m pytest tests/test_llm_seam.py -v
```

Both must succeed. The Phase 1 gate proves we did not accidentally edit any Phase 1 file.

LOCKED files (`src/query_router.py`, `src/sql_generator.py`, `app.py`, top-level `config.py`, `src/llm/__init__.py`, `src/llm/base.py`, `src/llm/errors.py`, `src/llm/types.py`, `src/llm/config.py`) MUST NOT be modified by this plan:

```
git diff --name-only HEAD src/query_router.py src/sql_generator.py app.py config.py src/llm/__init__.py src/llm/base.py src/llm/errors.py src/llm/types.py src/llm/config.py 2>&1 | head
```

Must produce no output.
</verification>

<success_criteria>
- `src/llm/_compat.py` exists with one public function: `llm_to_query_error()`.
- The translation table is complete and ordered correctly (subclasses before `LLMError` catch-all).
- All five LLMError branches translate to `QueryError` with the documented (`message`, `details`) tuples; original exception preserved as `__cause__`.
- Non-LLM exceptions and pre-existing `QueryError`s pass through the context manager unchanged (no over-catching).
- `src/llm/__init__.py` is NOT modified — the seam is package-internal.
- Phase 1 acceptance gate (`tests/test_llm_seam.py`) still 6/6 passing.
- LOCKED files: `src/query_router.py`, `src/sql_generator.py`, `app.py`, top-level `config.py`, and all Phase 1 files in `src/llm/` (except the stub `azure_openai.py` which Plan 01 owns) NOT modified.

Maps to: Success criterion #3 (full — the translation seam EXISTS and is the single point of LLMError→QueryError translation); ERR-04 (full).
</success_criteria>

<output>
After completion, create `.planning/phases/02-azure-extraction-parity-gate/02-02-SUMMARY.md` documenting:
- Final line count of `src/llm/_compat.py`.
- Confirmation that all five `except` branches translate correctly (with the verify script's output captured).
- Confirmation that `src/llm/__init__.py` has zero diff against HEAD (the seam stays package-internal).
- Confirmation that Phase 1 acceptance gate runs green (6/6).
- A note on the Phase 3 evolution path: when Phase 3 adds `LLMGuardrailError` from Anthropic, it can either (a) rely on the catch-all branch (zero edits here) OR (b) add a dedicated `except LLMGuardrailError` branch above the catch-all (one-line edit). Either path is supported by this design.
</output>
</content>
</invoke>