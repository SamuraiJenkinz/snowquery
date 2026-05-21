---
phase: 4
plan: 2
name: classify-with-tool-strict-tools-and-fallback
type: execute
wave: 1
depends_on: []
files_modified:
  - src/llm/anthropic_mgti.py
autonomous: true

must_haves:
  truths:
    - "AnthropicMGTIClient.classify_with_tool no longer raises NotImplementedError"
    - "When self._tools_supported is True, classify_with_tool POSTs a body containing tools=[tool_dict] AND tool_choice={'type':'tool','name':tool_name,'disable_parallel_tool_use':True}"
    - "On HTTP 200 with a valid tool_use block, classify_with_tool returns a ToolCall whose .input is the validated dict"
    - "On HTTP 200 missing a tool_use block matching tool_name, classify_with_tool raises LLMSchemaError"
    - "On HTTP 200 with stop_reason='guardrail_intervened', classify_with_tool raises LLMGuardrailError (BEFORE the missing-tool_use check)"
    - "On HTTP 200 with stop_reason='max_tokens' during tool_use, classify_with_tool raises LLMSchemaError (DIVERGES from complete()'s truncated-as-success semantics — Phase 4 lock per CONTEXT.md error matrix)"
    - "On jsonschema.ValidationError during tool_use input validation, classify_with_tool raises LLMSchemaError with the validation .message embedded"
    - "When self._tools_supported is False, classify_with_tool transparently delegates to _classify_via_text_mode and returns a schema-validated ToolCall whose external shape is INDISTINGUISHABLE from the strict-tools path"
    - "In the text-mode fallback path, the request body does NOT contain 'tools' or 'tool_choice' keys"
    - "Exactly ONE llm_call log event is emitted per classify_with_tool invocation in BOTH paths (strict and text_fallback)"
    - "The llm_call log event has a llm_tool_mode field with value 'strict' (tools-on path) or 'text_fallback' (escape-hatch path)"
    - "The llm_provider_loaded startup log gains a tools_supported: bool field reflecting self._tools_supported"
    - "complete() behaviour is unchanged externally — Phase 3's 21-test acceptance gate (tests/test_phase3_adapter.py) still passes byte-identically"
  artifacts:
    - path: "src/llm/anthropic_mgti.py"
      provides: "classify_with_tool (strict path + text-mode fallback), _classify_via_text_mode helper, _post_messages helper, tools_supported log field"
      contains: "def classify_with_tool"
  key_links:
    - from: "AnthropicMGTIClient.classify_with_tool (strict path)"
      to: "AnthropicMGTIClient._post_messages"
      via: "data = self._post_messages(body, headers, correlation_id, extra)"
      pattern: "self\\._post_messages\\("
    - from: "AnthropicMGTIClient.complete (refactored)"
      to: "AnthropicMGTIClient._post_messages"
      via: "data = self._post_messages(body, headers, correlation_id, extra)"
      pattern: "self\\._post_messages\\("
    - from: "AnthropicMGTIClient.classify_with_tool (fallback path)"
      to: "AnthropicMGTIClient._classify_via_text_mode"
      via: "if not self._tools_supported: return self._classify_via_text_mode(...)"
      pattern: "_classify_via_text_mode"
    - from: "AnthropicMGTIClient._classify_via_text_mode"
      to: "AnthropicMGTIClient.complete (with log suppression)"
      via: "raw = self.complete(enriched, _emit_log=False)"
      pattern: "_emit_log\\s*=\\s*False"
---

<objective>
Replace the Phase 3 `NotImplementedError` stub of `AnthropicMGTIClient.classify_with_tool` with a fully-functional strict-tools implementation, an env-flag-gated text-mode fallback (`ANTHROPIC_TOOLS_SUPPORTED=false` escape hatch), and a shared `_post_messages` helper that both `complete()` and `classify_with_tool()` consume. Add `tools_supported` to the `llm_provider_loaded` startup log and `llm_tool_mode` to the per-call `llm_call` log.

Purpose: This plan delivers the Anthropic-side strict-tools machinery that the production call site (Plan 01's migrated `classify_intent`) AND the smoke script (Plan 03) both depend on. The HTTP/envelope-parsing logic from Phase 3's `complete()` (lines 268-315) is extracted to an intra-module `_post_messages` helper so both adapter methods reuse it — extracting ~70 lines of duplication intra-module without crossing the adapter boundary (CONTEXT.md §Code structure locks this).

Output: A functional `classify_with_tool` covering all 9 rows of the CONTEXT.md error matrix; a stable text-mode fallback that produces a `ToolCall` indistinguishable from the strict-tools `ToolCall` to downstream consumers; intact Phase 3 `complete()` semantics (zero observable changes from the outside); and structured-log additions that let operators distinguish strict vs fallback paths in dashboards.
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
@.planning/phases/04-strict-tools-smoke-test/04-CONTEXT.md
@.planning/phases/04-strict-tools-smoke-test/04-RESEARCH.md

# Files this plan modifies
@src/llm/anthropic_mgti.py

# Reference patterns (read-only)
@src/llm/azure_openai.py
@src/llm/types.py
@src/llm/errors.py
@requirements.txt
@tests/test_phase3_adapter.py
</context>

<decisions>
## Decisions locked for this plan

1. **Env-flag-only fallback, NO runtime auto-fallback.** `classify_with_tool` checks `self._tools_supported` AT ENTRY. `True` → strict-tools path. `False` → delegate to `_classify_via_text_mode`. There is NO try-strict-then-retry-text logic. CONTEXT.md §Fallback strategy locks this — operators need a loud signal if the proxy regresses on tools, not a quiet downgrade.

2. **`_post_messages` is extracted intra-module to `anthropic_mgti.py`, NOT to `src/llm/_log.py`.** CONTEXT.md §Code structure locks this: "DO NOT extract to src/llm/_log.py — keep within anthropic_mgti.py." The helper owns HTTP + 4xx/5xx envelope parsing + typed-error mapping. It does NOT own timing or log emission — those stay in the caller's try/finally (RESEARCH.md Pattern 3 WARNING).

3. **`max_tokens` during `tool_use` is `LLMSchemaError`, NOT `outcome='truncated'`.** This DIVERGES from `complete()`'s Phase 3 semantics (where `max_tokens` returns the partial text successfully). CONTEXT.md error matrix row 8 + RESEARCH.md Pitfall 2 lock this. The message MUST mention "raise ANTHROPIC_MAX_TOKENS" so operators know the remediation.

4. **Guardrail check runs BEFORE the missing-tool_use check.** Same critical-order rule as `complete()` (RESEARCH.md Pitfall 4). A guardrail intervention has empty content[]; checking for missing tool_use first would surface as `LLMSchemaError "missing tool_use block"` instead of `LLMGuardrailError`. The locked order is: guardrail → max_tokens → tool_use extraction → input validation → schema validation.

5. **Defensive iteration for tool_use blocks even with `disable_parallel_tool_use: True`.** Content may MIX `text` + `tool_use` blocks (RESEARCH.md Pitfall 3 — verified against Anthropic docs). Take the FIRST block whose `type == "tool_use"` AND `name == tool_name`. Indexing `content[0]` is a regression vector.

6. **Text-mode fallback is SELF-CONTAINED inside `AnthropicMGTIClient`** — NO cross-adapter import from `src/llm/azure_openai.py`. Intentional duplication mirrors Phase 2/3 `_log_llm_call` precedent. The injected system-prompt template mirrors `azure_openai.py:254-264` verbatim (RESEARCH.md Q4). The fence-stripping logic mirrors `query_router.py:144-148` verbatim (RESEARCH.md Q4).

7. **Log emission asymmetry — locked by user (orchestration locked_decisions §3): ONE event per call from the wrapper; the delegate's event is suppressed.** Mechanism (planner picks; this plan picks **option A**): add a private keyword-only parameter `_emit_log: bool = True` to `complete()`. When `_classify_via_text_mode` calls `self.complete(enriched, _emit_log=False)`, the delegate's `_log_llm_call(extra)` call is gated by `if _emit_log:`. The wrapper (`classify_with_tool` fallback branch) emits its own ONE event tagged `llm_tool_mode: "text_fallback"`. The strict-tools path emits ONE event tagged `llm_tool_mode: "strict"`. **Rationale for picking option A over a separate `_complete_internal` shim:** smaller diff (~3 lines vs ~30 lines of shim plumbing), self-documenting via the kwarg name, and the underscore-prefix convention signals "internal, don't call from outside" to readers.

8. **`tools_supported` field added at the END of the `llm_provider_loaded` extra dict.** Order-of-definition (RESEARCH.md Q7) — minimizes diff vs `tests/test_phase3_adapter.py:423-440`'s existing log-capture test (which doesn't assert absence of extras).

9. **`requirements.txt` jsonschema version drift is a precondition.** RESEARCH.md Q3 / Pitfall 4: installed `jsonschema` is `4.25.1`, but `requirements.txt:18` pins `>=4.26.0,<5`. Run `pip install -U "jsonschema>=4.26.0,<5"` BEFORE executing this plan's verify step. If the upgrade fails, halt and report — do NOT proceed with a stale version.

10. **No new error types.** `LLMSchemaError`, `LLMGuardrailError`, `LLMAuthError`, `LLMTransientError`, `LLMTimeoutError`, `LLMError`, `LLMConfigError` — all already defined in `src/llm/errors.py` (RESEARCH.md Q12 + STATE.md Phase 1 sign-off). Phase 4 only adds error-RAISE sites.

11. **No edits to `src/llm/_compat.py`.** RESEARCH.md Q9 confirms the catch-all `except LLMError` branch at `_compat.py:111-117` already dispatches `LLMSchemaError(provider="anthropic_mgti")` to `QueryError("Anthropic API call failed", str(e))`. The COMPAT-DISPATCH regression guard lives in Plan 04's acceptance gate.
</decisions>

<tasks>

<task type="auto">
  <name>Task 2.1: Extract _post_messages helper from complete() and add tools_supported log field</name>
  <files>src/llm/anthropic_mgti.py</files>
  <action>
**Precondition (MUST run before any other action in this task):**
```bash
pip install -U "jsonschema>=4.26.0,<5"
```
If this fails, halt and report. RESEARCH.md Pitfall 4: dev box has 4.25.1; pin requires 4.26+.

**Step A — Add `tools_supported` to the startup log.**

Locate the existing `logger.info("llm_provider_loaded", ...)` call in `AnthropicMGTIClient.__init__` (`src/llm/anthropic_mgti.py:178-181`):

```python
logger.info(
    "llm_provider_loaded",
    extra={"provider": "anthropic_mgti", "base_url": self._base_url},
)
```

Change to (append `tools_supported` at the end of the extra dict — RESEARCH.md Q7):

```python
logger.info(
    "llm_provider_loaded",
    extra={
        "provider": "anthropic_mgti",
        "base_url": self._base_url,
        "tools_supported": self._tools_supported,
    },
)
```

**Step B — Extract `_post_messages` helper.**

Add a NEW private method on `AnthropicMGTIClient`. Insert AFTER `__repr__` (line 185) and BEFORE `complete()` (line 187):

```python
def _post_messages(
    self,
    body: dict,
    headers: dict,
    correlation_id: str,
    extra: dict,
) -> dict:
    """POST to /messages, parse envelope, raise typed errors on 4xx/5xx, return JSON dict on 2xx.

    Shared by complete() and classify_with_tool(). Owns:
      - requests.post with timeout
      - requests.Timeout → LLMTimeoutError (with correlation_id)
      - requests.RequestException → LLMTransientError (with correlation_id)
      - MGTI error envelope parsing ({error: {title, detail, status}})
      - 401/403 → LLMAuthError; 429/5xx → LLMTransientError; other → LLMError

    Does NOT own:
      - Response-body parsing beyond error-envelope lookup (caller-specific:
        complete() extracts text blocks; classify_with_tool extracts tool_use)
      - Timing (caller's try/finally owns t0/latency)
      - Log emission (caller's try/finally calls _log_llm_call)

    `extra` is mutated in-place for log enrichment (llm_outcome, llm_error_type)
    so the caller's finally block sees the right values when emitting llm_call.
    """
    url = f"{self._base_url.rstrip('/')}/model/{self._model}/messages"

    try:
        response = requests.post(
            url,
            headers=headers,
            json=body,
            timeout=self._timeout_s,
        )
    except requests.exceptions.Timeout as e:
        extra["llm_error_type"] = "LLMTimeoutError"
        extra["llm_outcome"] = "timeout"
        raise LLMTimeoutError(
            f"Anthropic MGTI request timed out after {self._timeout_s}s: {e}",
            provider="anthropic_mgti",
            correlation_id=correlation_id,
        ) from e
    except requests.exceptions.RequestException as e:
        # Connection errors, DNS, etc. — transient. Does NOT catch HTTPError
        # (we never call raise_for_status; MGTI 4xx/5xx handled below).
        extra["llm_error_type"] = "LLMTransientError"
        extra["llm_outcome"] = "transient_error"
        raise LLMTransientError(
            f"Anthropic MGTI request failed: {e}",
            provider="anthropic_mgti",
            correlation_id=correlation_id,
        ) from e

    # HTTP error path (4xx/5xx). Per RESEARCH.md Pitfall 1 / Phase 3 lock:
    # do NOT call response.raise_for_status() — must parse MGTI envelope first.
    if not response.ok:
        status = response.status_code
        try:
            err = response.json().get("error", {}) or {}
            title = err.get("title", "unknown")
            detail = err.get("detail", response.text[:200])
            msg = f"{title}: {detail}"
        except (ValueError, AttributeError):
            msg = response.text[:200] if response.text else "unknown error"

        if status in (401, 403):
            extra["llm_error_type"] = "LLMAuthError"
            extra["llm_outcome"] = "auth_error"
            raise LLMAuthError(
                f"Anthropic MGTI auth failed (HTTP {status}): {msg}",
                provider="anthropic_mgti",
                status_code=status,
                correlation_id=correlation_id,
            )
        if status == 429 or (500 <= status < 600):
            extra["llm_error_type"] = "LLMTransientError"
            extra["llm_outcome"] = "transient_error"
            raise LLMTransientError(
                f"Anthropic MGTI transient failure (HTTP {status}): {msg}",
                provider="anthropic_mgti",
                status_code=status,
                correlation_id=correlation_id,
            )
        # Any other HTTP error (400, 404, 422) — surface as generic LLMError
        extra["llm_error_type"] = "LLMError"
        raise LLMError(
            f"Anthropic MGTI HTTP error (HTTP {status}): {msg}",
            provider="anthropic_mgti",
            status_code=status,
            correlation_id=correlation_id,
        )

    return response.json()
```

**Step C — Refactor `complete()` to call `_post_messages` (preserve external behavior).**

In `complete()` (`src/llm/anthropic_mgti.py:187-428`), find the block at lines 268-315 (the entire `try: response = requests.post(...)` through the final HTTP-error `raise LLMError(...)`). Replace ONLY the HTTP+error portion with a call to `self._post_messages(body, headers, correlation_id, extra)` while keeping the rest of the body parsing (200-path, guardrail, content checks, text-block extraction, etc.) intact.

**Concretely, the refactored `complete()` body should look like:**

```python
        t0 = time.monotonic()
        extra: dict = {
            # ... existing extra dict initialization unchanged (lines 257-267) ...
        }
        try:
            data = self._post_messages(body, headers, correlation_id, extra)

            # ---- HTTP 200 success path ---- (lines 317-403 unchanged)
            usage = data.get("usage", {}) or {}
            extra["llm_prompt_tokens"] = usage.get("input_tokens")
            # ... rest of the 200-path body parsing unchanged ...
            # ... including: guardrail check, empty-content check, text-block
            #     extraction, tool_use stop_reason rejection (complete()'s
            #     "wrong-call-site" error at line 369-380), max_tokens
            #     truncated outcome, end_turn/stop_sequence success, unknown
            #     stop_reason error ...
            # ... final return: "".join(b.get("text", "") for b in text_blocks)

        # NOTE: The Timeout and RequestException except-branches that USED to
        # live here (lines 405-424) are now INSIDE _post_messages. Remove them
        # from complete()'s try/except — they will never fire from here again.

        finally:
            extra["llm_latency_ms"] = int((time.monotonic() - t0) * 1000)
            if _emit_log:  # See Task 2.2 — add this kwarg in next task
                _log_llm_call(extra)
```

**Important deletions from `complete()`:**
- Lines 269-315 (the `requests.post(url, ...)` call AND the entire 4xx/5xx envelope-parsing block AND the three `raise LLMAuthError/LLMTransientError/LLMError` blocks): MOVED to `_post_messages`. Replace with `data = self._post_messages(body, headers, correlation_id, extra)`.
- Lines 405-424 (the two `except requests.exceptions.Timeout` and `except requests.exceptions.RequestException` branches on complete's outer try): DELETED — they're now inside `_post_messages`.

**Lines PRESERVED in `complete()`:**
- All pre-flight config checks (lines 217-235).
- The `correlation_id = str(uuid.uuid4())` (line 240) and `headers = {...}` (lines 242-246) and `_build_request_body(...)` call (lines 247-253).
- `t0 = time.monotonic()` (line 256) and `extra: dict = {...}` (lines 257-267).
- The ENTIRE 200-path response parsing (lines 318-403) — guardrail check, empty-content check, text-block extraction, tool_use rejection, max_tokens outcome, end_turn/stop_sequence success, unknown-stop_reason raise, the final `return "".join(...)`.
- The `finally:` block (lines 426-428) — though Task 2.2 adds the `if _emit_log:` gate.

**The `complete()` signature does NOT change in this task.** Task 2.2 adds the `_emit_log` kwarg.

**WARNING (RESEARCH.md Pattern 3 WARNING):** The `t0` timing and `finally:` log emission MUST stay in the caller (`complete()`), NOT inside `_post_messages`. Moving them would break the timing for the 200-path (which does additional work after `_post_messages` returns).
  </action>
  <verify>
```bash
# 1. Confirm _post_messages exists at the right place
grep -n "def _post_messages" src/llm/anthropic_mgti.py
# Expected: one match between __repr__ and complete()

# 2. Confirm tools_supported in startup log
grep -n "tools_supported" src/llm/anthropic_mgti.py
# Expected: at least 2 matches (the dict entry + self._tools_supported reference)

# 3. Confirm complete() no longer has the moved Timeout/RequestException branches
#    at its OUTER try/except (they should be GONE — caught inside _post_messages now)
grep -nB1 "except requests.exceptions.Timeout" src/llm/anthropic_mgti.py
# Expected: ONE match (inside _post_messages) — NOT TWO

grep -nB1 "except requests.exceptions.RequestException" src/llm/anthropic_mgti.py
# Expected: ONE match (inside _post_messages) — NOT TWO

# 4. Confirm complete() now invokes the helper
grep -n "self._post_messages(" src/llm/anthropic_mgti.py
# Expected: one match (will become two after Task 2.2 adds the strict-tools call)

# 5. CRITICAL: Phase 3 acceptance gate MUST still pass byte-identically.
#    The refactor must preserve external complete() behavior.
pytest tests/test_phase3_adapter.py -v
# Expected: 21 passed, 0 failed (same as STATE.md baseline)

# 6. Combined regression sanity-check
pytest tests/ -q
# Expected: 39 passed (Phase 1+2+3 + Plan 01's changes — no Plan 04 tests yet)
```

If the Phase 3 acceptance gate regresses, ROLL BACK this task and inspect — the refactor preserved external behavior wrong somewhere (most likely the `extra` mutation timing or the 200-path control flow).
  </verify>
  <done>
`_post_messages` private method exists on `AnthropicMGTIClient`. `complete()` calls it instead of inlining the HTTP+error-mapping logic. `complete()` no longer contains the moved Timeout/RequestException except-branches at its outer try. `tools_supported` appears in the `llm_provider_loaded` startup-log `extra` dict. Phase 3's `tests/test_phase3_adapter.py` (21 tests) passes byte-identically — the refactor is observably a no-op from outside.
  </done>
</task>

<task type="auto">
  <name>Task 2.2: Implement classify_with_tool (strict path) + _classify_via_text_mode (escape hatch) + complete() log-suppression kwarg</name>
  <files>src/llm/anthropic_mgti.py</files>
  <action>
**Step A — Add `_emit_log` kwarg to `complete()` for log-suppression.**

Modify `complete()`'s signature (currently at `src/llm/anthropic_mgti.py:187-194`) to add a keyword-only parameter:

```python
def complete(
    self,
    messages: list[dict],
    *,
    max_tokens: int = 500,
    temperature: float = 0.1,
    _emit_log: bool = True,
    **kwargs: Any,
) -> str:
```

In `complete()`'s `finally:` block (lines ~426-428 after Task 2.1's edits), gate the `_log_llm_call(extra)` call:

```python
finally:
    extra["llm_latency_ms"] = int((time.monotonic() - t0) * 1000)
    if _emit_log:
        _log_llm_call(extra)
```

The default `True` preserves all existing call-site behavior (production code never passes the kwarg). Only `_classify_via_text_mode` will pass `_emit_log=False`. The underscore prefix + keyword-only positioning signals "internal mechanism, do not call from outside the module."

**Step B — Implement `classify_with_tool` (replacing the Phase 3 NotImplementedError stub).**

Replace lines 430-442 (the entire `classify_with_tool` stub including docstring placeholder and the `raise NotImplementedError(...)` line) with the full implementation:

```python
    def classify_with_tool(
        self,
        messages: list[dict],
        tool: ToolSchema,
        *,
        tool_name: str,
        **kwargs: Any,
    ) -> ToolCall:
        """Strict-tools intent classification with env-flag-gated text fallback.

        Sends Anthropic's `tools` + `tool_choice` strict-mode request body
        (TOOL-02/TOOL-06). On HTTP 200, extracts the first tool_use block
        matching `tool_name`, validates its `.input` against
        `tool.input_schema` via jsonschema (defence-in-depth), and returns
        a ToolCall. When `self._tools_supported is False`, delegates
        transparently to `_classify_via_text_mode` — the returned ToolCall
        is INDISTINGUISHABLE downstream from the strict-tools path
        (CONTEXT.md §Fallback strategy).

        Raises:
            LLMConfigError: missing ANTHROPIC_API_KEY/BASE_URL/MODEL.
            LLMAuthError: HTTP 401/403.
            LLMTransientError: HTTP 429/5xx or connection-level errors.
            LLMTimeoutError: requests.Timeout.
            LLMGuardrailError: stop_reason == 'guardrail_intervened'.
            LLMSchemaError: any of the 6 structural failures in the error
                matrix — missing tool_use block, wrong tool name, malformed
                input (not dict), schema-validation failure, max_tokens
                during tool_use (DIVERGES from complete()'s truncated-success
                semantics — Phase 4 lock per CONTEXT.md error matrix), or
                unknown stop_reason.
            LLMError: any other unexpected HTTP error.
        """
        import json as _json
        import jsonschema

        # Pre-flight config checks — IDENTICAL to complete() (lines 217-235).
        # Duplicated (not extracted) because the helper boundary is HTTP, not
        # config. Keeps each method's pre-conditions explicit.
        if not self._api_key:
            raise LLMConfigError(
                "Anthropic API key not configured. "
                "Set the ANTHROPIC_API_KEY environment variable.",
                provider="anthropic_mgti",
            )
        if not self._base_url:
            raise LLMConfigError(
                "Anthropic base URL not configured. "
                "Set the ANTHROPIC_BASE_URL environment variable.",
                provider="anthropic_mgti",
            )
        if not self._model:
            raise LLMConfigError(
                "Anthropic model not configured. "
                "Set the ANTHROPIC_MODEL environment variable to a "
                "Claude 4.5+ EU Bedrock model (eu.anthropic.claude-*).",
                provider="anthropic_mgti",
            )

        # Branch on env-flag — CONTEXT.md §Fallback strategy: env-flag-only,
        # NO runtime auto-fallback. Operator flips ANTHROPIC_TOOLS_SUPPORTED
        # to disable strict-tools entirely.
        if not self._tools_supported:
            return self._classify_via_text_mode(messages, tool, tool_name=tool_name)

        # --- Strict-tools path ---
        correlation_id = str(uuid.uuid4())  # RESEARCH.md Pitfall 5: before try
        headers = {
            "Content-Type": "application/json",
            "X-Api-Key": self._api_key,
            "X-Correlation-Id": correlation_id,
        }

        # Body shape: complete()'s baseline body PLUS tools + tool_choice.
        # max_tokens uses kwargs override OR self._max_tokens default
        # (NOT the 500 hardcode from complete() — classify needs enough
        # room for a small structured object, ~256 tokens; default is fine).
        max_tokens = kwargs.get("max_tokens", self._max_tokens)
        temperature = kwargs.get("temperature", self._temperature)
        body = _build_request_body(
            model=self._model,
            version=self._version,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
        )
        # Anthropic tool definition shape — verified verbatim against
        # platform.claude.com/docs/en/api/messages (RESEARCH.md "Anthropic
        # strict-tools request body").
        body["tools"] = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
        ]
        body["tool_choice"] = {
            "type": "tool",
            "name": tool_name,
            "disable_parallel_tool_use": True,
        }

        t0 = time.monotonic()
        extra: dict = {
            "llm_provider": "anthropic_mgti",
            "llm_model": self._model,
            "llm_latency_ms": 0,
            "llm_outcome": "error",
            "llm_error_type": None,
            "llm_prompt_tokens": None,
            "llm_completion_tokens": None,
            "llm_correlation_id": correlation_id,
            "llm_stop_reason": None,
            "llm_tool_mode": "strict",  # CONTEXT.md §classify_with_tool log
            "llm_tool_name": tool_name,
        }
        try:
            data = self._post_messages(body, headers, correlation_id, extra)

            usage = data.get("usage", {}) or {}
            extra["llm_prompt_tokens"] = usage.get("input_tokens")
            extra["llm_completion_tokens"] = usage.get("output_tokens")
            stop_reason = data.get("stop_reason")
            extra["llm_stop_reason"] = stop_reason
            content_blocks = data.get("content") or []

            # CRITICAL ORDER (mirrors complete()'s order + adds tool_use-
            # specific checks) — RESEARCH.md Pitfall 4 + locked decision §4:
            #   1. guardrail (BEFORE missing-tool_use — guardrails have
            #      empty content[], would otherwise surface as schema error)
            #   2. max_tokens during tool_use → schema error (DIVERGES from
            #      complete()'s truncated-success semantics — locked decision §3)
            #   3. defensive iteration to find first tool_use block matching
            #      tool_name (RESEARCH.md Pitfall 3 — content may be mixed
            #      text+tool_use)
            #   4. missing tool_use block / wrong name → schema error
            #   5. malformed input (not dict) → schema error
            #   6. jsonschema.validate → schema error on failure

            # 1. Guardrail
            if stop_reason == "guardrail_intervened":
                extra["llm_error_type"] = "LLMGuardrailError"
                extra["llm_outcome"] = "guardrail"
                raise LLMGuardrailError(
                    "Anthropic guardrail intervened on this request.",
                    provider="anthropic_mgti",
                    correlation_id=correlation_id,
                )

            # 2. max_tokens during tool_use — LOCKED DIVERGENCE FROM complete()
            if stop_reason == "max_tokens":
                extra["llm_error_type"] = "LLMSchemaError"
                extra["llm_outcome"] = "schema_error"
                raise LLMSchemaError(
                    "max_tokens reached during tool_use — input likely "
                    "truncated and unreliable; raise ANTHROPIC_MAX_TOKENS.",
                    provider="anthropic_mgti",
                    correlation_id=correlation_id,
                )

            # 3. Find first tool_use block matching tool_name (defensive
            #    iteration even with disable_parallel_tool_use=True per
            #    locked decision §5)
            tool_use_block = None
            wrong_name_seen = None  # track for better error msg
            for block in content_blocks:
                if block.get("type") == "tool_use":
                    if block.get("name") == tool_name:
                        tool_use_block = block
                        break
                    else:
                        wrong_name_seen = block.get("name")

            # 4. Missing tool_use (or only wrong-name tool_use blocks)
            if tool_use_block is None:
                extra["llm_error_type"] = "LLMSchemaError"
                extra["llm_outcome"] = "schema_error"
                if wrong_name_seen is not None:
                    msg = (
                        f"wrong tool name returned: expected {tool_name!r}, "
                        f"got {wrong_name_seen!r}"
                    )
                else:
                    types = [b.get("type") for b in content_blocks]
                    msg = (
                        f"missing tool_use block in content "
                        f"(stop_reason={stop_reason!r}, content_types={types!r})"
                    )
                raise LLMSchemaError(
                    msg,
                    provider="anthropic_mgti",
                    correlation_id=correlation_id,
                )

            # 5. Malformed input
            input_dict = tool_use_block.get("input")
            if not isinstance(input_dict, dict):
                extra["llm_error_type"] = "LLMSchemaError"
                extra["llm_outcome"] = "schema_error"
                raise LLMSchemaError(
                    f"malformed tool_use input: expected dict, got "
                    f"{type(input_dict).__name__}",
                    provider="anthropic_mgti",
                    correlation_id=correlation_id,
                )

            # 6. Defence-in-depth jsonschema validation (TOOL-06)
            try:
                jsonschema.validate(input_dict, tool.input_schema)
            except jsonschema.ValidationError as e:
                extra["llm_error_type"] = "LLMSchemaError"
                extra["llm_outcome"] = "schema_error"
                raise LLMSchemaError(
                    f"tool_use input failed schema validation: {e.message}",
                    provider="anthropic_mgti",
                    correlation_id=correlation_id,
                ) from e

            # Unknown / missing stop_reason — defensive (Anthropic should
            # always return stop_reason="tool_use" on a successful tool call).
            # Accept tool_use; treat anything else (after guardrail/max_tokens
            # already handled above) as schema error.
            if stop_reason not in ("tool_use", "end_turn", "stop_sequence"):
                extra["llm_error_type"] = "LLMSchemaError"
                extra["llm_outcome"] = "schema_error"
                raise LLMSchemaError(
                    f"unknown stop_reason: {stop_reason!r}",
                    provider="anthropic_mgti",
                    correlation_id=correlation_id,
                )

            # Success
            extra["llm_outcome"] = "success"
            return ToolCall(
                tool_name=tool_name,
                input=input_dict,
                raw_response=data,
            )

        finally:
            extra["llm_latency_ms"] = int((time.monotonic() - t0) * 1000)
            _log_llm_call(extra)
```

**Step C — Implement `_classify_via_text_mode` private helper.**

Add a NEW private method on `AnthropicMGTIClient`, placed immediately AFTER `classify_with_tool`:

```python
    def _classify_via_text_mode(
        self,
        messages: list[dict],
        tool: ToolSchema,
        *,
        tool_name: str,
    ) -> ToolCall:
        """Text-mode escape hatch when ANTHROPIC_TOOLS_SUPPORTED=false.

        Mirrors the strict-tools path's external shape: produces a ToolCall
        whose `input` passes the same jsonschema.validate(input, tool.input_schema)
        check. Downstream code cannot distinguish which path produced the result.

        Mechanism:
          1. Inject a system message instructing the LLM to respond with ONLY
             a JSON object matching `tool.input_schema`. Mirror Azure's
             pattern verbatim (azure_openai.py:254-264) — intentional
             duplication per CONTEXT.md §Fallback strategy ("Text-mode helper
             is INTERNAL to AnthropicMGTIClient — does NOT import from
             src/llm/azure_openai.py").
          2. Call self.complete(enriched, _emit_log=False). The kwarg
             suppresses complete()'s llm_call event because the wrapper
             emits its own event tagged llm_tool_mode='text_fallback'
             (locked decision §7).
          3. Strip markdown fences (mirror query_router.py:144-148 verbatim).
          4. json.loads → jsonschema.validate → return ToolCall.

        ALL error cases raise LLMSchemaError (no JSONDecodeError leaks past
        this boundary). Both paths through classify_with_tool produce
        EXACTLY ONE llm_call log event.
        """
        import json as _json
        import jsonschema

        # Build the system-prompt addendum. Mirror azure_openai.py:254-264
        # verbatim (CONTEXT.md §Fallback strategy "intentional duplication,
        # symmetric with Phase 2/3 _log_llm_call precedent").
        enriched = list(messages) + [
            {
                "role": "system",
                "content": (
                    f"You are calling the tool `{tool.name}`. "
                    f"Respond ONLY with a JSON object matching this schema:\n"
                    f"{_json.dumps(tool.input_schema)}\n"
                    f"Do not include markdown code fences or commentary."
                ),
            }
        ]

        # Set up the per-call log envelope for the wrapper's ONE event.
        # The delegate (self.complete) is called with _emit_log=False so
        # it does NOT emit its own llm_call event — we emit one event
        # here tagged with llm_tool_mode='text_fallback' (locked decision §7).
        correlation_id = str(uuid.uuid4())
        t0 = time.monotonic()
        extra: dict = {
            "llm_provider": "anthropic_mgti",
            "llm_model": self._model,
            "llm_latency_ms": 0,
            "llm_outcome": "error",
            "llm_error_type": None,
            "llm_prompt_tokens": None,  # not available in text-mode wrapper
            "llm_completion_tokens": None,
            "llm_correlation_id": correlation_id,
            "llm_stop_reason": None,
            "llm_tool_mode": "text_fallback",
            "llm_tool_name": tool_name,
        }
        try:
            # Delegate to complete() with log suppression. complete() generates
            # its own correlation_id and headers internally; the one above
            # belongs to the wrapper's log event (operator can correlate
            # via wall-clock proximity if needed).
            raw = self.complete(enriched, _emit_log=False)

            # Fence-stripping — mirror query_router.py:144-148 verbatim
            # (CONTEXT.md §Specifics: "mirror query_router.py:144-148")
            content = raw.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            try:
                parsed = _json.loads(content)
            except _json.JSONDecodeError as e:
                extra["llm_error_type"] = "LLMSchemaError"
                extra["llm_outcome"] = "schema_error"
                raise LLMSchemaError(
                    f"Anthropic MGTI text-mode returned invalid JSON for "
                    f"tool {tool.name!r}: {e}",
                    provider="anthropic_mgti",
                    correlation_id=correlation_id,
                ) from e

            try:
                jsonschema.validate(parsed, tool.input_schema)
            except jsonschema.ValidationError as e:
                extra["llm_error_type"] = "LLMSchemaError"
                extra["llm_outcome"] = "schema_error"
                raise LLMSchemaError(
                    f"Anthropic MGTI text-mode response failed schema "
                    f"validation for {tool.name!r}: {e.message}",
                    provider="anthropic_mgti",
                    correlation_id=correlation_id,
                ) from e

            extra["llm_outcome"] = "success"
            return ToolCall(
                tool_name=tool_name,
                input=parsed,
                raw_response={"content": raw},
            )

        finally:
            extra["llm_latency_ms"] = int((time.monotonic() - t0) * 1000)
            _log_llm_call(extra)
```

**Step D — Verify imports at top of `anthropic_mgti.py` include `jsonschema` lazily.**

The above code uses `import jsonschema` inside the methods (matches `azure_openai.py:249`'s lazy-import pattern). Do NOT add `jsonschema` to the top-of-module imports — keep it method-local to avoid forcing the import on `complete()`-only consumers.

**Step E — Verify the imports of `LLMSchemaError` and `LLMGuardrailError` from `src/llm/errors` exist at the top of `anthropic_mgti.py`.** These were imported in Phase 3 already (used in `complete()`). Sanity-check with `grep -nE "LLMSchemaError|LLMGuardrailError" src/llm/anthropic_mgti.py` — both should appear in the `from src.llm.errors import (...)` block near the top.
  </action>
  <verify>
```bash
# 1. classify_with_tool is no longer NotImplementedError
grep -n "NotImplementedError" src/llm/anthropic_mgti.py
# Expected: ZERO matches (or only in unrelated places)

grep -n "def classify_with_tool" src/llm/anthropic_mgti.py
grep -n "def _classify_via_text_mode" src/llm/anthropic_mgti.py
# Expected: one match each

# 2. _emit_log kwarg landed in complete()
grep -n "_emit_log" src/llm/anthropic_mgti.py
# Expected: at least 3 matches (signature, finally gate, text-mode call)

# 3. Strict-tools body shape correct
grep -nE 'body\["tools"\]|body\["tool_choice"\]' src/llm/anthropic_mgti.py
# Expected: one each

grep -n "disable_parallel_tool_use" src/llm/anthropic_mgti.py
# Expected: one match (in tool_choice dict)

# 4. Log tagging
grep -n '"llm_tool_mode"' src/llm/anthropic_mgti.py
# Expected: 2 matches (strict, text_fallback)

# 5. Quick smoke — adapter constructs and classify_with_tool method is callable
python -c "
from unittest.mock import patch, MagicMock
import os
os.environ['ANTHROPIC_BASE_URL'] = 'https://stage.example.com/coreapi/llm/anthropic/v1'
os.environ['ANTHROPIC_API_KEY'] = 'test'
os.environ['ANTHROPIC_MODEL'] = 'eu.anthropic.claude-sonnet-4-5-20250929-v1:0'
from src.llm.anthropic_mgti import AnthropicMGTIClient
from src.llm.types import INTENT_TOOL
c = AnthropicMGTIClient()
print('classify_with_tool:', c.classify_with_tool)
print('_classify_via_text_mode:', c._classify_via_text_mode)
print('_post_messages:', c._post_messages)
# Now invoke with a mocked _post_messages returning a valid tool_use response
mock_data = {
    'content': [
        {'type': 'tool_use', 'id': 'toolu_xxx', 'name': 'classify_intent',
         'input': {'version': 'v1', 'intent': 'structured', 'confidence': 0.9,
                   'reasoning': 'test', 'detected_filters': {}}}
    ],
    'stop_reason': 'tool_use',
    'usage': {'input_tokens': 50, 'output_tokens': 10},
    'model': os.environ['ANTHROPIC_MODEL'],
}
with patch.object(c, '_post_messages', return_value=mock_data):
    result = c.classify_with_tool(
        [{'role': 'user', 'content': 'test'}],
        INTENT_TOOL,
        tool_name='classify_intent',
    )
    print('result.tool_name:', result.tool_name)
    print('result.input:', result.input)
print('OK')
"
# Expected: prints method refs, then result.tool_name='classify_intent',
# then result.input with the 5 fields, then OK.

# 6. CRITICAL: Phase 3 acceptance gate MUST still pass byte-identically
pytest tests/test_phase3_adapter.py -v
# Expected: 21 passed
# (NotImplementedError test test_classify_with_tool_stub at the bottom of
#  test_phase3_adapter.py would now FAIL because the stub is gone — that
#  test must be DELETED in this task or marked as expected-to-fail. Check
#  what the test name is:
grep -n "NotImplementedError" tests/test_phase3_adapter.py
#  If a test asserts the stub raises NotImplementedError, that test is
#  intentionally being invalidated by Phase 4 — DELETE it from
#  test_phase3_adapter.py. The Phase 3 sign-off in STATE.md anticipated this:
#  "classify_with_tool stub body BYTE-IDENTICAL to Phase 1 — Phase 4 territory".

# 7. Combined regression sanity-check
pytest tests/ -q
# Expected: all green (Phase 1+2+3 + Plan 01 + Plan 02 changes; Plan 04 tests
# not yet present).
```
  </verify>
  <done>
`AnthropicMGTIClient.classify_with_tool` is implemented end-to-end: strict-tools path with correct body shape (tools + tool_choice), defensive tool_use extraction, all 6+ error matrix rows raising `LLMSchemaError`/`LLMGuardrailError` correctly, jsonschema validation, success returns `ToolCall`. `_classify_via_text_mode` mirrors Azure's text-mode shape and produces an indistinguishable `ToolCall`. `complete()`'s `_emit_log: bool = True` kwarg suppresses the delegate's log event when called from text-mode wrapper; exactly ONE `llm_call` event per `classify_with_tool` invocation in BOTH paths. `tools_supported` field in `llm_provider_loaded` log. Phase 3 acceptance gate (21 tests) still passes; any NotImplementedError-asserting test in Phase 3 is removed since the stub is now implemented.
  </done>
</task>

</tasks>

<verification>
Phase-level verification for Plan 02:

1. **Method surface complete:**
   ```bash
   python -c "
   from src.llm.anthropic_mgti import AnthropicMGTIClient
   assert callable(getattr(AnthropicMGTIClient, 'classify_with_tool', None))
   assert callable(getattr(AnthropicMGTIClient, '_classify_via_text_mode', None))
   assert callable(getattr(AnthropicMGTIClient, '_post_messages', None))
   import inspect
   sig = inspect.signature(AnthropicMGTIClient.complete)
   assert '_emit_log' in sig.parameters, sig
   print('OK: surface complete')
   "
   ```

2. **`_post_messages` is shared by both methods:**
   ```bash
   grep -c "self._post_messages(" src/llm/anthropic_mgti.py
   # Expected: 2 (one in complete, one in classify_with_tool)
   ```

3. **Phase 3 acceptance gate preserved:**
   ```bash
   pytest tests/test_phase3_adapter.py -v
   # Expected: 21 passed (minus any deleted NotImplementedError test)
   ```

4. **No new error types or compat edits:**
   ```bash
   git diff --stat HEAD -- src/llm/errors.py src/llm/_compat.py
   # Expected: zero lines changed
   ```

5. **Only the declared file is modified:**
   ```bash
   git diff --stat HEAD -- src/ tests/ scripts/
   # Expected: ONLY src/llm/anthropic_mgti.py (plus possibly one test deletion
   # in tests/test_phase3_adapter.py for the NotImplementedError-asserting test).
   ```
</verification>

<success_criteria>
- [ ] `AnthropicMGTIClient.classify_with_tool` does NOT raise `NotImplementedError`
- [ ] Strict-tools path POSTs body containing exactly: `body["tools"][0] == {"name": tool.name, "description": tool.description, "input_schema": tool.input_schema}` AND `body["tool_choice"] == {"type": "tool", "name": tool_name, "disable_parallel_tool_use": True}`
- [ ] On valid `tool_use` response, returns `ToolCall(tool_name=tool_name, input={...validated dict...}, raw_response=data)`
- [ ] All 9 CONTEXT.md error matrix rows raise the correct typed error (guardrail → LLMGuardrailError; missing tool_use, wrong name, malformed input, schema-validate failure, max_tokens-during-tool_use, unknown stop_reason → LLMSchemaError; HTTP 401/403 → LLMAuthError; HTTP 429/5xx → LLMTransientError; Timeout → LLMTimeoutError)
- [ ] Guardrail check runs BEFORE missing-tool_use check (locked decision §4)
- [ ] `max_tokens` during tool_use raises `LLMSchemaError` (NOT outcome='truncated' — locked decision §3)
- [ ] Mixed `text`+`tool_use` content blocks handled via defensive iteration; first matching `name` wins
- [ ] `_classify_via_text_mode` runs when `self._tools_supported is False`; returns `ToolCall` indistinguishable from strict path (downstream `result = call.input` works identically)
- [ ] Text-mode path's request body has NO `tools` and NO `tool_choice` keys
- [ ] Exactly ONE `llm_call` log event per `classify_with_tool` invocation in BOTH paths (delegate's log suppressed via `_emit_log=False`)
- [ ] `llm_call` log has `llm_tool_mode: "strict"` or `"text_fallback"` and `llm_tool_name: <tool_name>`
- [ ] `llm_provider_loaded` log has `tools_supported: <bool>` field
- [ ] `_post_messages` is the single owner of HTTP + 4xx/5xx → typed-error mapping; called by BOTH `complete()` and `classify_with_tool()`
- [ ] Phase 3's `tests/test_phase3_adapter.py` (21 tests) still passes byte-identically; any test asserting the NotImplementedError stub is deleted
- [ ] `src/llm/errors.py`, `src/llm/_compat.py` unchanged
- [ ] Plan 02's diff touches ONLY `src/llm/anthropic_mgti.py` (plus possibly one deletion in `tests/test_phase3_adapter.py`)
</success_criteria>

<output>
After completion, create `.planning/phases/04-strict-tools-smoke-test/04-02-SUMMARY.md` documenting:
- `_post_messages` helper extraction: line counts before/after in `complete()`
- `classify_with_tool` strict-tools implementation: which error matrix rows are exercised and where (line refs)
- `_classify_via_text_mode` fallback: mirror points to Azure / query_router with line refs
- `_emit_log` kwarg mechanism: where suppression happens; confirmation that exactly one log event fires per call in both paths
- `tools_supported` log field addition
- Any Phase 3 test deletion (e.g. the NotImplementedError-asserting test) — note name and reason
- Confirmation: Phase 3 acceptance gate (21 tests) green; combined Phase 1+2+3 + Plan 01+02 suite green
- Note for Plan 04: this implementation covers the 9 error-matrix rows; Plan 04's acceptance gate should add one test per row
</output>
</content>
</invoke>