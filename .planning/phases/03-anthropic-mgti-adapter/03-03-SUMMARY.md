---
phase: 03-anthropic-mgti-adapter
plan: 03
subsystem: api
tags: [anthropic, mgti, bedrock, adapter, llm, requests, uuid, correlation-id, guardrail, observability]

# Dependency graph
requires:
  - phase: 01-abstraction-seam
    provides: "LLMClient ABC, factory cache, six typed LLMError subclasses, ToolSchema/ToolCall types"
  - phase: 02-azure-extraction-parity-gate
    provides: "Locked _log_llm_call signature (COPIED VERBATIM into anthropic_mgti.py per intentional duplication decision); NO .strip() return-value convention; LLMConfigError-embeds-remediation pattern"
  - phase: 03-anthropic-mgti-adapter (wave 1)
    provides: "Plan 01 — .env.example with 9 Anthropic vars + Azure llm_provider_loaded pattern to mirror; Plan 02 — _compat.py dispatches on e.provider so Anthropic-provider LLMErrors translate to Anthropic-specific QueryError text"
provides:
  - "AnthropicMGTIClient full implementation (Phase 1 stub 47 lines → real adapter 442 lines)"
  - "Init-time validation: non-empty ANTHROPIC_MODEL that does NOT start with 'eu.anthropic.claude-' raises LLMConfigError; empty model preserves Phase 1 no-op pattern (factory cache stores instance)"
  - "complete() POSTs to {base_url}/model/{model}/messages with X-Api-Key + Content-Type + fresh X-Correlation-Id UUID per call"
  - "_build_request_body helper: filter ALL role='system' messages to top-level system key (OMIT key entirely when none); always send anthropic_version + max_tokens; OMIT temperature/top_p/top_k for eu.anthropic.claude-opus-4-7* models"
  - "Typed-error mapping (response.ok-based, NOT raise_for_status): 401/403 → LLMAuthError, 429/5xx → LLMTransientError, Timeout → LLMTimeoutError, other RequestException → LLMTransientError, other HTTP non-ok → LLMError"
  - "HTTP 200 stop_reason dispatcher in locked order: guardrail_intervened → LLMGuardrailError (BEFORE empty-content check — Pitfall 4); empty content non-guardrail → LLMSchemaError; no text blocks → LLMSchemaError; tool_use → LLMSchemaError; max_tokens → success with outcome='truncated'; end_turn/stop_sequence → success; unknown → LLMSchemaError"
  - "Per-call llm_call structured log event with 9 llm_* extra fields (provider, model, latency_ms, outcome, error_type, prompt_tokens normalized from input_tokens, completion_tokens normalized from output_tokens, correlation_id populated, stop_reason on both success and error paths)"
  - "One llm_provider_loaded event at __init__ (Anthropic half of SC #5; symmetric with Azure pattern from Plan 01)"
  - "classify_with_tool stub PRESERVED — Phase 4 territory (NotImplementedError unchanged)"
  - "__repr__ returns 'AnthropicMGTIClient()' — OBS-03 regression guard symmetric with Azure"
  - "tests/manual/observe_correlation_echo.py — one-shot diagnostic for the STATE.md blocker 'MGTI X-Correlation-Id echo unverified', NOT collected by pytest"
affects: [03-04-acceptance-gate, 04-tool-classification, 05-ui-cache-key]

# Tech tracking
tech-stack:
  added: []  # uuid is stdlib; requests/jsonschema already in tree
  patterns:
    - "Init-time vs HTTP-time config validation split: bad-prefix model name raises at __init__ (catches typos before factory cache fills); missing fields raise at complete() time (preserves no-op factory pattern with provider-specific remediation text)"
    - "Order-sensitive stop_reason dispatcher with explicit numbered comment block — guardrail BEFORE empty-content (RESEARCH.md Pitfall 4); locked order documented inline so future reorders are obvious bugs"
    - "Field-name normalization at log boundary: Anthropic's usage.input_tokens/output_tokens become extra['llm_prompt_tokens']/extra['llm_completion_tokens'] (matches Azure's prompt_tokens/completion_tokens semantics) — dashboards can aggregate across providers"
    - "Manual-only diagnostic scripts live in tests/manual/ (no test_ prefix, no pytest collection); fail-fast exit 2 on missing env so a future CI matrix could gate on them without smoke risk"

key-files:
  created:
    - "tests/manual/observe_correlation_echo.py (97 lines)"
  modified:
    - "src/llm/anthropic_mgti.py (47 → 442 lines; full rewrite — Phase 1 stub → real adapter)"

key-decisions:
  - "Init-time model-prefix check raises ONLY when ANTHROPIC_MODEL is non-empty (empty preserves Phase 1 no-op so factory cache can still store the instance); the missing-model case is caught at HTTP time in complete() with remediation text"
  - "Sampling-param omission key match uses startswith('eu.anthropic.claude-opus-4-7') — NOT a regex. Per CONTEXT.md ('matching eu.anthropic.claude-opus-4-7*'), startswith is correct and simpler; matches eu.anthropic.claude-opus-4-7-20251201-v1:0 and any future opus-4-7 variants"
  - "System extraction filters ALL role='system' entries (not first-wins) and joins with '\\n\\n' — defensive against multi-system prompts; isinstance(content, str) guard skips structured content blocks (Phase 5 may revisit if list-typed system content becomes load-bearing)"
  - "system key OMITTED ENTIRELY when no system messages present — not sent as empty string. Anthropic Messages API treats absent and empty differently"
  - "_log_llm_call COPIED VERBATIM from src/llm/azure_openai.py — intentional duplication per Phase 2 decision 02-01; no premature extraction. If both adapters are ever unified the helper extracts to src/llm/_log.py"
  - "response.ok-based dispatch (NOT raise_for_status) so the MGTI error envelope {error: {title, detail, status}} can be parsed BEFORE raising the typed error — title/detail embed in the LLMError message (RESEARCH.md Pitfall 1)"
  - "correlation_id generated BEFORE the try block so the finally's _log_llm_call has it even if requests.post raises immediately (DNS failure, etc.) — Pitfall 5"
  - "max_tokens stop_reason returns text WITH outcome='truncated' (does NOT raise) — caller chose max_tokens, truncation is a known outcome, not a failure"
  - "X-Correlation-Id echo verification deferred to OPERATOR (manual script) — observation step, not a runtime dependency. Script output gets pasted into commit message / summary; resolves STATE.md blocker as observation, not as code change (OQ-3)"

patterns-established:
  - "Init-time validation split: typo-style errors (bad prefix) raise at __init__; absence-style errors (missing env) raise at first complete(). Preserves factory cache; surfaces typos early; gives missing-config a remediation-rich error path"
  - "Locked stop_reason ordering documented as inline numbered comment block — order is load-bearing; reorders are visible in diff"
  - "Provider-side field normalization at the log boundary so dashboards can aggregate across providers without per-provider field maps"
  - "Manual-only diagnostic scripts in tests/manual/ — pytest skips them by directory; operator runs by hand; exit codes (0 success / 1 HTTP non-2xx / 2 missing env) allow future automation"

# Metrics
duration: 8min
completed: 2026-05-21
---

# Phase 3 Plan 03: Anthropic MGTI Adapter Summary

**Replaced the Phase 1 47-line NotImplementedError stub with a full ~440-line AnthropicMGTIClient that POSTs to {base_url}/model/{model}/messages with a fresh X-Correlation-Id UUID per call, validates ANTHROPIC_MODEL prefix at __init__, maps MGTI responses to six typed LLMErrors (with the critical guardrail-before-empty-content ordering locked in), normalizes usage fields into llm_prompt_tokens/llm_completion_tokens at the log boundary, and emits one llm_provider_loaded + one llm_call event — while preserving classify_with_tool as a Phase 4 stub.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-05-21T15:06:30Z
- **Completed:** 2026-05-21T15:14:35Z
- **Tasks:** 2/2
- **Files modified:** 2 (1 rewrite, 1 new)

## Accomplishments

- `src/llm/anthropic_mgti.py` — full real adapter (442 lines). __init__ reads 8 anthropic_* settings, validates non-empty model has `eu.anthropic.claude-` prefix, emits one `llm_provider_loaded` log event. `complete()` constructs MGTI URL `/model/{model}/messages`, sends X-Api-Key + fresh X-Correlation-Id UUID per call, builds body via `_build_request_body` (system extraction, opus-4-7 sampling-param omission), parses MGTI error envelope `{error: {title, detail}}` BEFORE raising typed errors, dispatches HTTP 200 by stop_reason in the locked order (guardrail → empty-content → no-text-blocks → tool_use → max_tokens-truncated → end_turn-success → unknown), emits one `llm_call` structured event per call with 9 `llm_*` extra fields including the correlation_id and stop_reason.
- `tests/manual/observe_correlation_echo.py` — 97-line one-shot diagnostic that resolves the STATE.md blocker "MGTI `X-Correlation-Id` echo unverified" as an observation step. Reads env vars, POSTs one request, prints whether MGTI echoed the correlation header (case-insensitive lookup) plus the `usage` block and `stop_reason`. Exit codes 0/1/2 for success/HTTP-error/missing-env. Verified NOT collected by pytest (exit 5 = "no tests collected" on `pytest --collect-only tests/manual/observe_correlation_echo.py`).
- Phase 1 + Phase 2 acceptance gates: **18 passed in 8.28s** — zero regression. The off-limits files list (`.env.example`, `src/llm/__init__.py`, `src/llm/azure_openai.py`, `src/llm/_compat.py`, `src/llm/config.py`, `src/llm/base.py`, `src/llm/errors.py`, `src/llm/types.py`, `src/query_router.py`, `src/sql_generator.py`, `app.py`, `config.py`, `tests/test_llm_seam.py`, `tests/test_phase2_parity.py`, `tests/fixtures/`) — `git diff HEAD~2 HEAD --` against that list produces zero output.

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement AnthropicMGTIClient** — `c2a1d2a` (feat)
2. **Task 2: Manual X-Correlation-Id echo observation script** — `b101451` (test)

_Phase 4 will revisit `_build_request_body` to add `tools`/`tool_choice` keys for strict-tools mode; signature stays stable._

## Files Created/Modified

### `src/llm/anthropic_mgti.py` (47 → 442 lines — full rewrite)

- **Module docstring** rewritten to flag all 7 key differences vs Azure (endpoint path, auth header, correlation ID, system extraction, opus sampling-param omission, MGTI error envelope shape, guardrail-before-empty-content ordering).
- **Module imports**: `time`, `uuid`, `requests`, plus all six `LLMError` subclasses (`LLMAuthError`, `LLMConfigError`, `LLMError`, `LLMGuardrailError`, `LLMSchemaError`, `LLMTimeoutError`, `LLMTransientError`), `LLMClient` ABC, `load_settings`, `ToolCall`/`ToolSchema`, and `logger`.
- **`_log_llm_call(extra)`** — module-level; COPIED VERBATIM from `src/llm/azure_openai.py:52-64` per Phase 2 decision (intentional duplication; comment in docstring explicitly references the no-premature-extraction lock).
- **`_build_request_body(model, version, max_tokens, temperature, messages)`** — module-level helper. Filters ALL `role='system'` entries (joined with `\n\n` and set as top-level `system` key; OMITTED entirely when none). Always sets `anthropic_version`, `messages` (non-system), `max_tokens`. Sets `temperature` ONLY if `not model.startswith('eu.anthropic.claude-opus-4-7')`. `top_p`/`top_k` NOT sent in Phase 3 (`LLMClient.complete` signature only accepts `max_tokens` and `temperature` named kwargs).
- **`AnthropicMGTIClient.__init__`** — reads 8 `anthropic_*` fields from `load_settings()`. Validates `if self._model and not self._model.startswith("eu.anthropic.claude-"): raise LLMConfigError(...)` — the `self._model and` guard makes empty model an allowed no-op (factory cache contract). Emits `logger.info("llm_provider_loaded", extra={"provider": "anthropic_mgti", "base_url": self._base_url})` unconditionally.
- **`__repr__`** — returns `"AnthropicMGTIClient()"` (OBS-03 — no API key leak, symmetric with `AzureOpenAIClient.__repr__`).
- **`complete(messages, *, max_tokens=500, temperature=0.1, **kwargs)`**:
  - Pre-flight raises `LLMConfigError` with provider-specific remediation text if `_api_key` / `_base_url` / `_model` is empty (Phase 2 OQ-1 lock — adapter owns remediation text).
  - `correlation_id = str(uuid.uuid4())` BEFORE `try:` so it's available in `finally` even if `requests.post` raises (Pitfall 5).
  - Headers: `Content-Type: application/json`, `X-Api-Key: <key>`, `X-Correlation-Id: <uuid>`.
  - URL: `f"{self._base_url.rstrip('/')}/model/{self._model}/messages"`.
  - `requests.post(url, headers=headers, json=body, timeout=self._timeout_s)`.
  - HTTP error path uses `if not response.ok:` (NOT `raise_for_status()` — Pitfall 1). Parses MGTI envelope `{error: {title, detail}}` and embeds in the message. 401/403 → `LLMAuthError`; 429 or 5xx → `LLMTransientError`; other → `LLMError`.
  - HTTP 200 path dispatcher (LOCKED ORDER per Pitfall 4): guardrail_intervened → `LLMGuardrailError`; empty content → `LLMSchemaError`; no text blocks → `LLMSchemaError`; tool_use → `LLMSchemaError`; max_tokens → outcome='truncated' (success); end_turn/stop_sequence → outcome='success'; anything else → `LLMSchemaError`.
  - Return value: `"".join(b.get("text", "") for b in text_blocks)` — NO `.strip()` (call sites strip; Phase 2 Pitfall 1).
  - `requests.exceptions.Timeout` → `LLMTimeoutError`; other `RequestException` → `LLMTransientError` (connection/DNS failures; HTTPError is NOT in this branch because we never call `raise_for_status`).
  - `finally:` populates `llm_latency_ms = int((time.monotonic() - t0) * 1000)` and calls `_log_llm_call(extra)`.
- **`classify_with_tool`** — body UNCHANGED from Phase 1 stub: `raise NotImplementedError("AnthropicMGTIClient.classify_with_tool is implemented in Phase 4")`. Phase 4 territory (RESEARCH.md Pitfall 7).

### `tests/manual/observe_correlation_echo.py` (NEW — 97 lines)

- Reads `ANTHROPIC_BASE_URL` / `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` / `ANTHROPIC_VERSION` directly from env (does NOT go through `load_settings()` — allows one-off env overrides without touching `.env`).
- Generates fresh `uuid.uuid4()`, POSTs `{anthropic_version, messages: [{role:user, content:"Reply with just the word 'ok'."}], max_tokens: 16}` to `{base_url}/model/{model}/messages`, timeout=30.
- Case-insensitive scan of `response.headers` for `x-correlation-id`. Prints one of three outcomes: "MGTI did NOT echo X-Correlation-Id" / "MGTI echoed exactly. value=..." / "MGTI returned a DIFFERENT correlation id. sent=... returned=...".
- Also prints the `usage` block and `stop_reason` on HTTP 2xx (the other half of the STATE.md blocker — `usage` pass-through observation).
- Exit codes: 0 (HTTP 2xx), 1 (HTTP non-2xx), 2 (missing env). Verified `pytest --collect-only tests/manual/observe_correlation_echo.py` returns exit 5 (no tests collected).

## Confirmation Checklist (per plan `<output>` section)

- **Final line count of `src/llm/anthropic_mgti.py`:** 442 (up from 47 stub). Range expected by plan: 200-300+; actual 442 reflects the locked stop_reason dispatcher with explicit comments + the six init/HTTP error branches + the two module-level helpers + the docstrings.
- **All required signals present in module source** (verified by `inspect.getsource(src.llm.anthropic_mgti)`): `requests.post`, `X-Correlation-Id`, `X-Api-Key`, `uuid.uuid4`, `eu.anthropic.claude-`, `/messages`, `guardrail_intervened`, `input_tokens`, `output_tokens`, `llm_provider_loaded`, `llm_call`.
- **All six typed-error classes imported and raised**: `LLMConfigError` (init-time prefix + pre-flight missing-config), `LLMAuthError` (401/403), `LLMTransientError` (429/5xx + RequestException), `LLMTimeoutError` (requests.Timeout), `LLMGuardrailError` (stop_reason=='guardrail_intervened'), `LLMSchemaError` (empty content / no text blocks / tool_use / unknown stop_reason).
- **Does NOT call `response.raise_for_status()`** (RESEARCH.md Pitfall 1) — confirmed: `grep raise_for_status src/llm/anthropic_mgti.py` returns zero matches.
- **Does NOT call `.strip()` on the return value** (Phase 2 Pitfall 1) — confirmed: return statement is `"".join(b.get("text", "") for b in text_blocks)` with no surrounding strip.
- **`classify_with_tool` stub byte-identical to Phase 1**: same message text "AnthropicMGTIClient.classify_with_tool is implemented in Phase 4".

### Guardrail-before-empty-content ordering excerpt (lines 326-355)

```python
            # CRITICAL ORDER (RESEARCH.md Pitfall 4):
            #   1. guardrail check (BEFORE content-emptiness — guardrails ALWAYS
            #      have empty content[], but must surface as LLMGuardrailError)
            #   2. content-emptiness check
            #   3. text-blocks check
            ...
            # 1. Guardrail — HTTP 200 + empty content + stop_reason guardrail
            if stop_reason == "guardrail_intervened":
                extra["llm_error_type"] = "LLMGuardrailError"
                extra["llm_outcome"] = "guardrail"
                raise LLMGuardrailError(
                    "Anthropic guardrail intervened on this request.",
                    provider="anthropic_mgti",
                    correlation_id=correlation_id,
                )

            # 2. Empty content (and NOT guardrail — already handled above)
            if not content_blocks:
                extra["llm_error_type"] = "LLMSchemaError"
                extra["llm_outcome"] = "schema_error"
                raise LLMSchemaError(
                    f"Anthropic MGTI returned HTTP 200 with empty content "
                    ...
```

Guardrail check at line 336 precedes empty-content check at line 346 — locked order verified.

## Decisions Made

(See frontmatter `key-decisions`; the load-bearing ones recap here.)

1. **Init-time validation split** — non-empty bad-prefix raises at `__init__`; absent fields raise at `complete()`. Preserves factory cache for the empty case; surfaces typos before HTTP latency.
2. **`startswith('eu.anthropic.claude-opus-4-7')` not regex** — CONTEXT.md says "matching opus-4-7*"; startswith covers the full version-suffix family.
3. **`_log_llm_call` copied verbatim** — intentional duplication per Phase 2 decision 02-01. No premature extraction.
4. **`response.ok` not `raise_for_status`** — MGTI envelope `{error: {title, detail, status}}` is parsed BEFORE raising so the title/detail land in the typed error message.
5. **`correlation_id` generated before `try:`** — Pitfall 5; `finally`'s log call always has it.
6. **`system` key OMITTED, not empty-string** — Anthropic API distinguishes absent from empty.
7. **`max_tokens` → outcome='truncated', not error** — caller chose max_tokens; truncation is a known outcome.
8. **X-Correlation-Id echo verification deferred to operator** — OQ-3; manual diagnostic script resolves the STATE.md blocker via observation, not code.

## Deviations from Plan

None — plan executed exactly as written. All 11 verification steps in Task 1 passed first try; Task 2 verification needed a one-line tweak (pytest exit code 5 = "no tests collected" — the verify block's `check_output` raised on non-zero exit, switched to `subprocess.run` to inspect rc directly; the script behavior was correct, the verify-shell was overly strict).

## Issues Encountered

- **pytest exit code 5 from `--collect-only` on a no-test file** — the Task 2 verify block as written used `subprocess.check_output` which raises on non-zero rc. pytest exit 5 IS the desired result ("no tests collected"). Adjusted the verification to use `subprocess.run` and check rc explicitly. No code change to the manual script — its behavior was correct from the first write.

## User Setup Required

None — no external service configuration required by THIS plan. (The `tests/manual/observe_correlation_echo.py` script DOES require a live `ANTHROPIC_API_KEY` to produce useful output, but that is an operator-discretion observation step, not a runtime requirement.)

## Observed Behavior (X-Correlation-Id echo — STATE.md blocker)

**Live observation deferred to Phase 4 smoke test per ROADMAP.md.** No live stage `ANTHROPIC_API_KEY` was available during this plan's execution window, so the manual script was verified to construct correctly and fail fast on missing env (exit 2) but not run against a real MGTI endpoint. When the operator runs `python tests/manual/observe_correlation_echo.py` with a live key, the output should be pasted into this section as a follow-up (or recorded in the Phase 4 smoke-test summary). The STATE.md blocker is RESOLVED-BY-OBSERVATION-STEP — the script exists, the path is documented, and no code change in `src/llm/anthropic_mgti.py` depends on a particular echo outcome (the field is logged unconditionally as `llm_correlation_id` regardless of whether MGTI echoes it back).

## SC Mapping

This plan satisfies the following Phase 3 success criteria at the adapter level. The acceptance-gate proof (Plan 04) is the regression contract.

- **SC #1 — Fresh X-Correlation-Id per call + correct URL + correct headers + correct body shape.** Lines 270-291 (`headers` dict with `Content-Type`/`X-Api-Key`/`X-Correlation-Id`), 287 (`url = f"{...rstrip('/')}/model/{self._model}/messages"`), 282 (`correlation_id = str(uuid.uuid4())`), `_build_request_body` (lines 70-122). Verified at runtime: two consecutive `complete()` calls produced two distinct UUIDs in `headers['X-Correlation-Id']`.
- **SC #2 first half — `__init__` validates non-empty `ANTHROPIC_MODEL` prefix.** Lines 178-185. Verified: `os.environ['ANTHROPIC_MODEL']='gpt-4o'; AnthropicMGTIClient()` raises `LLMConfigError` with `eu.anthropic.claude-` in the remediation text; empty model does NOT raise.
- **SC #2 second half — opus-4-7 OMITS temperature/top_p/top_k.** Line 119 (`if not model.startswith("eu.anthropic.claude-opus-4-7")`). Verified: with `ANTHROPIC_MODEL='eu.anthropic.claude-opus-4-7-20251201-v1:0'`, the body sent via `requests.post` had `'temperature' not in body`, `'top_p' not in body`, `'top_k' not in body` even when the call passed `temperature=0.7`.
- **SC #3 — typed-error mapping.** Verified all six branches at runtime: 401 → `LLMAuthError` (with envelope `title`/`detail` parsed into the message), 403 → `LLMAuthError`, 429 → `LLMTransientError`, 503 → `LLMTransientError`, `requests.Timeout` → `LLMTimeoutError`, `stop_reason='guardrail_intervened'` → `LLMGuardrailError`, `stop_reason='end_turn'` + empty content → `LLMSchemaError`. **The critical guardrail-before-empty-content ordering** (the single biggest source of latent bugs per RESEARCH.md Pitfall 4) is verified: guardrail check at line 336 precedes empty-content check at line 346; the runtime test `_make_resp(text='', stop_reason='guardrail_intervened')` raises `LLMGuardrailError` (not `LLMSchemaError`).
- **SC #5 Anthropic half — `llm_provider_loaded` event at `__init__`.** Line 188 emits `logger.info("llm_provider_loaded", extra={"provider": "anthropic_mgti", "base_url": self._base_url})`. Verified at runtime: one record with `record.provider == 'anthropic_mgti'` and `record.base_url == os.environ['ANTHROPIC_BASE_URL']` captured per `__init__` invocation.
- **SC #4 (config template)** — owned by Plan 01; this plan does not touch `.env.example`.
- **SC #5 "no tool wrapping reachable"** — owned by Plan 04 acceptance gate (`classify_with_tool` stub is preserved here as required; the gate verifies call sites don't reach it).

## Next Phase Readiness

- **For 03-04-acceptance-gate (final Phase 3 plan):** AnthropicMGTIClient is fully wired. Plan 04 can now build a test module that covers all five SCs end-to-end (the same way `test_phase2_parity.py` covers Phase 2). The 18-test Phase-1+2 regression contract is intact (verified `pytest tests/test_llm_seam.py tests/test_phase2_parity.py -q` → 18 passed in 8.28s after both this plan's commits).
- **For Phase 4 (strict-tools):** `_build_request_body` signature is stable; Phase 4 extends it to accept `tools` / `tool_choice` keys. `classify_with_tool` stub is in place with the locked Phase 4 message. `_tools_supported` is read from settings at `__init__` (currently unused; Phase 4 will branch on it if MGTI capability negotiation lands).
- **For Phase 5 (UI cache key):** `__repr__` is hardened so the API key cannot leak when Streamlit logs `st.session_state` or component repr. `llm_provider_loaded` is the operator-visible "I configured this provider" signal Phase 5 dashboards can latch onto.
- **STATE.md blocker resolution:** "MGTI `usage` block pass-through and `X-Correlation-Id` echo unverified" — RESOLVED-BY-OBSERVATION-STEP. The manual script exists; live observation deferred to Phase 4 smoke test (no live stage key was available during execution). No code change in the adapter depends on a particular echo outcome.

---
*Phase: 03-anthropic-mgti-adapter*
*Plan: 03*
*Completed: 2026-05-21*
