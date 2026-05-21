---
phase: 03-anthropic-mgti-adapter
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - src/llm/_compat.py
autonomous: true

must_haves:
  truths:
    - "src/llm/_compat.py llm_to_query_error() context manager dispatches the LLMAuthError / LLMTimeoutError / LLMTransientError / catch-all LLMError branches on `e.provider` so an Anthropic-provider error surfaces with Anthropic-specific user-visible text (resolves Phase 2 KNOWN DEBT recorded in STATE.md and the docstring of the file — 'Phase 3 may revisit this branch when the Anthropic adapter lands')"
    - "LLMConfigError branch UNCHANGED — provider embeds its own remediation text at raise time, str(e) is passed through verbatim, Plan 03 keeps the same pattern for AnthropicMGTIClient pre-flight checks (the 'Phase-3-clean path' from Phase 2 OQ-1)"
    - "For LLMAuthError with provider='azure_openai': QueryError(\"Azure OpenAI API key not configured\", \"Set the AZURE_OPENAI_API_KEY environment variable.\") — BYTE-IDENTICAL to Phase 2's hardcoded text (the Phase 2 acceptance gate at tests/test_phase2_parity.py:660-663 grep-asserts these exact strings; must not break)"
    - "For LLMAuthError with provider='anthropic_mgti': QueryError(\"Anthropic API key not configured or not authorised\", \"Check ANTHROPIC_API_KEY and ANTHROPIC_BASE_URL in your .env.\") — distinct, actionable, gives the operator the two most likely fixes"
    - "For LLMTimeoutError / LLMTransientError / catch-all LLMError with provider='anthropic_mgti': QueryError uses provider-named message ('Anthropic API call failed' instead of 'Azure OpenAI API call failed'); for provider='azure_openai' OR unknown provider, falls back to the existing 'Azure OpenAI API call failed' wording (preserves the Phase 2 acceptance gate at tests/test_phase2_parity.py:641,651,693,703 which asserts exactly that string for Azure)"
    - "Phase 2 acceptance gate (tests/test_phase2_parity.py — all 12 tests) still passes byte-identically after this change; Phase 1 acceptance gate (tests/test_llm_seam.py — 6 tests) still passes; combined 18 tests green is the regression guard"
  artifacts:
    - path: "src/llm/_compat.py"
      provides: "llm_to_query_error context manager with per-provider dispatch on LLMAuthError, LLMTimeoutError, LLMTransientError, and the catch-all LLMError branch"
      contains: "anthropic_mgti"
  key_links:
    - from: "src/llm/_compat.py"
      to: "LLMError.provider attribute (set at raise time by AzureOpenAIClient and AnthropicMGTIClient)"
      via: "getattr(e, 'provider', None) == 'anthropic_mgti' check before raising QueryError"
      pattern: "getattr\\(e,\\s*['\\\"]provider['\\\"]"
    - from: "src/llm/_compat.py"
      to: "src.utils.QueryError"
      via: "raise QueryError(message, details) from e — with per-provider message/details"
      pattern: "raise QueryError"
---

<objective>
Pay down the Phase 2 KNOWN DEBT recorded in STATE.md ("LLMAuthError branch in _compat.py CURRENTLY hardcodes Azure text — Phase 3 known debt: revisit when Anthropic lands to dispatch on e.provider") AND extend the dispatch to `LLMTimeoutError`, `LLMTransientError`, and the catch-all `LLMError` branch so the user-visible "Azure OpenAI API call failed" wording does not appear when the active provider is Anthropic.

Purpose: Without this change, a Phase 3 Anthropic timeout shows the user "Azure OpenAI API call failed" — wrong product label, useless remediation hint. The fix is a 4-branch provider dispatch in a single file. The Phase 2 acceptance gate explicitly asserts the Azure wording (`tests/test_phase2_parity.py` lines 641, 651, 660-663, 693, 703) so the dispatch MUST preserve the Azure path byte-identically. The Anthropic path adds new, provider-named wording that Plan 04 will grep-assert.

Output: One file edited (`src/llm/_compat.py`) — replace the four bare-Azure branches with provider-dispatched branches. No other file touched.

Decisions resolved here:
- **OQ-2** (per orchestrator planning_context): YES, fix `LLMTimeoutError` and `LLMTransientError` too — consistent and additive; no Phase 2 test asserts those exact texts for non-Azure providers; defer-is-acceptable per RESEARCH.md OQ-2, but doing it now blocks a real Phase 5 UX regression where the user sees "Azure OpenAI API call failed" on an Anthropic timeout. The dispatch lines are ~3 each — total ~12 additional lines.

DO NOT: touch `LLMConfigError` branch (Phase 2 OQ-1 path is the locked pattern). Touch any file other than `src/llm/_compat.py`.
</objective>

<execution_context>
@C:\Users\taylo\.claude\get-shit-done\workflows\execute-plan.md
@C:\Users\taylo\.claude\get-shit-done\templates\summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/03-anthropic-mgti-adapter/03-CONTEXT.md
@.planning/phases/03-anthropic-mgti-adapter/03-RESEARCH.md

# The file this plan edits
@src/llm/_compat.py

# The error class the dispatch reads .provider from
@src/llm/errors.py

# Phase 2 acceptance gate — its hardcoded-Azure assertions are what makes the regression guard load-bearing
@tests/test_phase2_parity.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add provider dispatch to LLMAuthError, LLMTimeoutError, LLMTransientError, and catch-all LLMError branches in llm_to_query_error()</name>
  <files>src/llm/_compat.py</files>
  <action>
Edit `src/llm/_compat.py`. The file has ONE context manager `llm_to_query_error()` with FIVE except branches. Modify the LLMAuthError, LLMTimeoutError, LLMTransientError, and the catch-all LLMError branches to dispatch on `e.provider`. Leave the LLMConfigError branch unchanged.

**Current shape** (lines 70-97, Phase 2 locked):
```python
try:
    yield
except LLMConfigError as e:
    raise QueryError(str(e), "Check your .env configuration.") from e
except LLMAuthError as e:
    raise QueryError(
        "Azure OpenAI API key not configured",
        "Set the AZURE_OPENAI_API_KEY environment variable.",
    ) from e
except LLMTimeoutError as e:
    raise QueryError("Azure OpenAI API call failed", str(e)) from e
except LLMTransientError as e:
    raise QueryError("Azure OpenAI API call failed", str(e)) from e
except LLMError as e:
    raise QueryError("Azure OpenAI API call failed", str(e)) from e
```

**New shape** (provider dispatch in the four branches that need it):

```python
try:
    yield
except LLMConfigError as e:
    # UNCHANGED — provider embeds remediation text at raise time; str(e) is
    # passed through verbatim. This is the "Phase-3-clean" pattern from
    # Phase 2 OQ-1: adding a new provider does NOT require editing this
    # branch (the new adapter just constructs LLMConfigError with its own
    # remediation text — see AnthropicMGTIClient.complete pre-flight check
    # in Phase 3 Plan 03).
    raise QueryError(str(e), "Check your .env configuration.") from e

except LLMAuthError as e:
    # Phase 3: dispatch on e.provider so each provider's HTTP 401/403
    # surfaces its own remediation. Azure path is BYTE-IDENTICAL to Phase 2
    # (the Phase 2 acceptance gate at tests/test_phase2_parity.py:660-663
    # asserts these exact strings).
    if getattr(e, "provider", None) == "anthropic_mgti":
        raise QueryError(
            "Anthropic API key not configured or not authorised",
            "Check ANTHROPIC_API_KEY and ANTHROPIC_BASE_URL in your .env.",
        ) from e
    # Azure path (and any unknown / None provider — preserves Phase 2 behavior)
    raise QueryError(
        "Azure OpenAI API key not configured",
        "Set the AZURE_OPENAI_API_KEY environment variable.",
    ) from e

except LLMTimeoutError as e:
    # Phase 3: provider-named message so an Anthropic timeout does not show
    # "Azure OpenAI API call failed" in the UI. Azure path UNCHANGED.
    if getattr(e, "provider", None) == "anthropic_mgti":
        raise QueryError("Anthropic API call failed", str(e)) from e
    raise QueryError("Azure OpenAI API call failed", str(e)) from e

except LLMTransientError as e:
    # Phase 3: provider-named message (matches LLMTimeoutError pattern).
    if getattr(e, "provider", None) == "anthropic_mgti":
        raise QueryError("Anthropic API call failed", str(e)) from e
    raise QueryError("Azure OpenAI API call failed", str(e)) from e

except LLMError as e:
    # Catch-all for any LLMError subclass not caught above (LLMSchemaError,
    # LLMGuardrailError, future additions). Phase 3: dispatch by provider
    # so guardrail / schema errors get the right product label too.
    if getattr(e, "provider", None) == "anthropic_mgti":
        raise QueryError("Anthropic API call failed", str(e)) from e
    raise QueryError("Azure OpenAI API call failed", str(e)) from e
```

Implementation notes (each maps to a Phase 2 regression-guard the change MUST preserve):

- **`getattr(e, "provider", None)` (not `e.provider`)**: `LLMError.provider` is always set by the adapters today, but using `getattr(... None)` is defensive against any future LLMError raised by a third-party / external library that did not pass `provider=...`. Three lines, no cost.
- **Azure path is the fallback in every dispatch**: the `if provider == "anthropic_mgti": ...` then unconditional Azure path means Azure (and any unknown provider — covers the future where a Phase 5 adapter does not get its own dispatch yet) always falls through to the Phase 2 wording. This is the explicit regression guard for the Phase 2 acceptance gate (`tests/test_phase2_parity.py:641,651,660-663,693,703` — those tests inject errors with `provider="azure_openai"`).
- **`LLMConfigError` branch UNCHANGED**: Phase 2 OQ-1 locked the "provider embeds remediation in the message, compat layer passes str(e) through" pattern. Plan 03 follows that pattern for AnthropicMGTIClient's pre-flight check — so no dispatch needed here. (Editing this branch in Phase 3 would re-open Phase 2's OQ-1; do not do it.)
- **Module docstring**: the existing docstring's "Phase 3 may revisit this branch when the Anthropic adapter lands" note should be UPDATED to "Phase 3 dispatches on e.provider — see the if-branches below" (one-line edit), so a future reader does not think the debt is still open.
- **No new imports needed**: `getattr` is builtin; `QueryError` is already imported; the error classes are already imported.
- **Method shape (one try with five excepts) preserved**: Don't refactor into a helper; the file's value is exactly that it's a single, readable translation table.
- **Order of except clauses preserved**: subclasses before LLMError (Python catches the first match). The order today is `LLMConfigError → LLMAuthError → LLMTimeoutError → LLMTransientError → LLMError`. Keep that order — `LLMConfigError`, `LLMAuthError`, `LLMTimeoutError`, `LLMTransientError` are sibling subclasses of `LLMError`, so the catch-all `LLMError` MUST stay last.

**Docstring update**: change the bullet about the LLMAuthError branch (lines 27-31 in current file) from:
> * LLMAuthError uses the historic 'Set the AZURE_OPENAI_API_KEY ...' remediation text to preserve byte-identical user-visible behavior today. Phase 3 may revisit this branch when the Anthropic adapter lands -- at that point the branch can dispatch on e.provider.

to:
> * LLMAuthError / LLMTimeoutError / LLMTransientError / catch-all LLMError dispatch on e.provider so Anthropic errors get Anthropic-named remediation. The Azure path (and unknown-provider path) preserves the exact Phase 2 wording byte-identically. See the if-branches below.
  </action>
  <verify>
Run from project root:

```
python -c "
from contextlib import suppress
from src.llm._compat import llm_to_query_error
from src.llm.errors import LLMAuthError, LLMTimeoutError, LLMTransientError, LLMConfigError, LLMSchemaError, LLMGuardrailError
from src.utils import QueryError

# ------- LLMAuthError dispatch -------

# Azure path — must be BYTE-IDENTICAL to Phase 2
try:
    with llm_to_query_error():
        raise LLMAuthError('HTTP 401', provider='azure_openai', status_code=401)
except QueryError as e:
    assert e.message == 'Azure OpenAI API key not configured', f'Azure auth message regressed: {e.message!r}'
    assert e.details == 'Set the AZURE_OPENAI_API_KEY environment variable.', f'Azure auth details regressed: {e.details!r}'

# Anthropic path — new wording
try:
    with llm_to_query_error():
        raise LLMAuthError('HTTP 401', provider='anthropic_mgti', status_code=401)
except QueryError as e:
    assert e.message == 'Anthropic API key not configured or not authorised', f'Anthropic auth message wrong: {e.message!r}'
    assert e.details == 'Check ANTHROPIC_API_KEY and ANTHROPIC_BASE_URL in your .env.', f'Anthropic auth details wrong: {e.details!r}'

# Unknown provider — falls back to Azure wording (regression guard for any future adapter)
try:
    with llm_to_query_error():
        raise LLMAuthError('HTTP 401', provider='some_new_provider', status_code=401)
except QueryError as e:
    assert e.message == 'Azure OpenAI API key not configured', f'unknown provider should fall back to Azure: {e.message!r}'

# ------- LLMTimeoutError dispatch -------

try:
    with llm_to_query_error():
        raise LLMTimeoutError('timed out', provider='azure_openai')
except QueryError as e:
    assert e.message == 'Azure OpenAI API call failed', f'Azure timeout message regressed: {e.message!r}'
    assert 'timed out' in (e.details or ''), f'timeout details lost: {e.details!r}'

try:
    with llm_to_query_error():
        raise LLMTimeoutError('timed out after 30s', provider='anthropic_mgti')
except QueryError as e:
    assert e.message == 'Anthropic API call failed', f'Anthropic timeout message wrong: {e.message!r}'
    assert 'timed out after 30s' in (e.details or ''), f'timeout details lost: {e.details!r}'

# ------- LLMTransientError dispatch -------

try:
    with llm_to_query_error():
        raise LLMTransientError('HTTP 503', provider='azure_openai', status_code=503)
except QueryError as e:
    assert e.message == 'Azure OpenAI API call failed', f'Azure transient message regressed: {e.message!r}'

try:
    with llm_to_query_error():
        raise LLMTransientError('HTTP 503', provider='anthropic_mgti', status_code=503)
except QueryError as e:
    assert e.message == 'Anthropic API call failed', f'Anthropic transient message wrong: {e.message!r}'

# ------- Catch-all LLMError dispatch (LLMSchemaError, LLMGuardrailError) -------

try:
    with llm_to_query_error():
        raise LLMSchemaError('bad json', provider='azure_openai')
except QueryError as e:
    assert e.message == 'Azure OpenAI API call failed', f'Azure schema-error fall-through regressed: {e.message!r}'

try:
    with llm_to_query_error():
        raise LLMGuardrailError('guardrail intervened', provider='anthropic_mgti')
except QueryError as e:
    assert e.message == 'Anthropic API call failed', f'Anthropic guardrail message wrong: {e.message!r}'

try:
    with llm_to_query_error():
        raise LLMSchemaError('empty content', provider='anthropic_mgti')
except QueryError as e:
    assert e.message == 'Anthropic API call failed', f'Anthropic schema-error message wrong: {e.message!r}'

# ------- LLMConfigError UNCHANGED (Phase 2 OQ-1 lock — adapter embeds remediation) -------

try:
    with llm_to_query_error():
        raise LLMConfigError(
            'Anthropic model must start with eu.anthropic.claude-',
            provider='anthropic_mgti',
        )
except QueryError as e:
    assert e.message == 'Anthropic model must start with eu.anthropic.claude-', f'config-error message lost: {e.message!r}'
    assert e.details == 'Check your .env configuration.'

print('TASK 1 OK')
"
```

Must print `TASK 1 OK`. Then confirm zero regression on Phase 1 + Phase 2:

```
python -m pytest tests/test_llm_seam.py tests/test_phase2_parity.py -v
```

Expected: 18 tests pass. If `test_error_translation_at_call_site` fails, the Azure-path fallback regressed — re-check that the `if provider == 'anthropic_mgti':` branch is INSIDE each except and the Azure raise is OUTSIDE the if.
  </verify>
  <done>
- `src/llm/_compat.py` `llm_to_query_error()` has four updated branches (`LLMAuthError`, `LLMTimeoutError`, `LLMTransientError`, catch-all `LLMError`), each dispatching on `getattr(e, "provider", None) == "anthropic_mgti"` to a provider-named QueryError; Azure path (and any unknown provider) preserves the exact Phase 2 wording.
- `LLMConfigError` branch UNCHANGED (Phase 2 OQ-1 lock).
- Module docstring updated to reflect that Phase 3 paid down the LLMAuthError debt and extended dispatch to Timeout/Transient/catch-all.
- Phase 1 + Phase 2 acceptance gates (18 tests) still pass byte-identically.
- Plan 04 has the foundation to add Anthropic-specific error-translation assertions on top of the existing Azure assertions.
- Satisfies the regression-prevention half of SC #3 (the typed-error mapping AT THE ADAPTER lands in Plan 03; the user-visible QueryError shape lands here).
  </done>
</task>

</tasks>

<verification>
End-of-plan verification:

```
# 1. Provider dispatch is in place — grep for the anthropic_mgti string in the four branches
grep -c "anthropic_mgti" src/llm/_compat.py
# Expected: at least 4 (one per dispatched branch)

# 2. LLMConfigError branch is unchanged — must NOT mention anthropic_mgti dispatch
grep -A 6 "except LLMConfigError" src/llm/_compat.py
# Expected output shows: raise QueryError(str(e), "Check your .env configuration.") from e

# 3. Phase 1 + Phase 2 acceptance gates still green (18 tests)
python -m pytest tests/test_llm_seam.py tests/test_phase2_parity.py -v
```

The third command MUST show 18 passing. The Phase 2 acceptance gate's
`test_error_translation_at_call_site` is the critical regression guard — it injects `LLMAuthError(provider="azure_openai")` and `LLMTimeoutError(provider="azure_openai")` and `LLMTransientError(provider="azure_openai")` and asserts the exact Phase 2 Azure wording.

Files NOT touched by this plan (verify diff is empty):
```
git diff --name-only HEAD .env.example src/llm/__init__.py src/llm/azure_openai.py src/llm/anthropic_mgti.py src/llm/config.py src/llm/base.py src/llm/errors.py src/llm/types.py src/query_router.py src/sql_generator.py app.py config.py tests/ 2>&1 | head
```

Must produce no output (Plan 01 may have already modified `.env.example` and `src/llm/azure_openai.py`; if so the above command should be run BEFORE Plan 01 OR adjusted to exclude those two files).

Plan-level surface: exactly ONE file — `src/llm/_compat.py`.
</verification>

<success_criteria>
- `src/llm/_compat.py` `llm_to_query_error()` dispatches on `e.provider` in the LLMAuthError, LLMTimeoutError, LLMTransientError, and catch-all LLMError branches.
- For `provider == "anthropic_mgti"`: produces Anthropic-named QueryError wording ("Anthropic API key not configured or not authorised" / "Anthropic API call failed").
- For `provider == "azure_openai"` OR unknown provider: produces exactly the Phase 2 wording byte-identically ("Azure OpenAI API key not configured" / "Azure OpenAI API call failed").
- `LLMConfigError` branch UNCHANGED.
- Module docstring updated to reflect Phase 3 dispatch.
- Phase 1 + Phase 2 acceptance gates (18 tests) still pass.

Maps to: SC #3 (foundational layer — adapter-level typed-error raises land in Plan 03; this plan ensures those typed errors surface as Anthropic-named QueryError at the call site instead of being mislabeled "Azure OpenAI API call failed"). Resolves the known Phase 2 debt recorded in STATE.md. Requirements: ERR-02, ERR-03 (the call-site translation half — adapter-level mapping is Plan 03).
</success_criteria>

<output>
After completion, create `.planning/phases/03-anthropic-mgti-adapter/03-02-SUMMARY.md` documenting:
- A diff snippet of `src/llm/_compat.py` showing the four updated branches (LLMAuthError, LLMTimeoutError, LLMTransientError, catch-all LLMError).
- Confirmation that the LLMConfigError branch is byte-identical to Phase 2 (paste lines 70-77 from HEAD vs after).
- Confirmation that Phase 1 + Phase 2 acceptance gates (18 tests) pass — paste the pytest summary line.
- Confirmation that only `src/llm/_compat.py` was modified — paste `git diff --name-only HEAD` output (filtered to exclude `.env.example` and `src/llm/azure_openai.py` if Plan 01 already committed those).
- One-line note: "Phase 2 known debt resolved: LLMAuthError + LLMTimeoutError + LLMTransientError + catch-all LLMError now dispatch on e.provider. Phase 5 UI is unblocked from showing wrong product names on Anthropic errors."
</output>
