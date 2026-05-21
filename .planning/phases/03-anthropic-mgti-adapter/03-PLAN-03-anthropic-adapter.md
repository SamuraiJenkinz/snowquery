---
phase: 03-anthropic-mgti-adapter
plan: 03
type: execute
wave: 2
depends_on: ["03-01"]
files_modified:
  - src/llm/anthropic_mgti.py
  - tests/manual/observe_correlation_echo.py
autonomous: true

must_haves:
  truths:
    - "AnthropicMGTIClient.complete(messages, ...) performs `requests.post(f'{base_url.rstrip(\"/\")}/model/{model}/messages', headers={'X-Api-Key': key, 'Content-Type': 'application/json', 'X-Correlation-Id': uuid}, json=body, timeout=...)` with a FRESH uuid.uuid4() per call (SC #1)"
    - "AnthropicMGTIClient.__init__ raises LLMConfigError when ANTHROPIC_MODEL is non-empty AND does not start with 'eu.anthropic.claude-' (e.g. 'gpt-4o' raises); empty model does NOT raise at __init__ (preserves Phase 1 no-op pattern — empty config is caught at HTTP time in complete() like Azure does) — SC #2 first half"
    - "AnthropicMGTIClient.complete() request body OMITS `temperature`, `top_p`, and `top_k` when self._model starts with 'eu.anthropic.claude-opus-4-7'; for other eu.anthropic.claude-* models the body INCLUDES `temperature` (sourced from self._temperature or call kwarg) and OMITS `top_p`/`top_k` unless explicitly passed (SC #2 second half)"
    - "AnthropicMGTIClient.complete() maps MGTI HTTP responses to typed errors per SC #3: 401/403 → LLMAuthError; 429/5xx → LLMTransientError; requests.Timeout → LLMTimeoutError; HTTP 200 with stop_reason=='guardrail_intervened' → LLMGuardrailError (even though content is empty — guardrail check BEFORE content-emptiness check per RESEARCH.md Pitfall 4); HTTP 200 with empty content AND non-guardrail stop_reason → LLMSchemaError"
    - "AnthropicMGTIClient.complete() extracts system messages by FILTERING ALL `role='system'` entries from input messages, concatenating their `content` with '\\n\\n', and setting the result as the top-level `system` request-body field; when NO system messages present the `system` key is OMITTED entirely from the body (NOT sent as empty string — Anthropic Messages API treats absent and empty differently per CONTEXT.md)"
    - "AnthropicMGTIClient.complete() concatenates ALL `content[*].text` blocks (in order) for the success-path return value; multiple text blocks join into one string with no separator; no .strip() is applied to the return value (mirrors Phase 2 Pitfall 1 — call sites strip)"
    - "Each AnthropicMGTIClient.complete() call emits exactly one logger.info('llm_call', extra={...}) event with provider='anthropic_mgti', model=<full eu.anthropic.claude-* string>, latency_ms (wall-clock around requests.post), outcome ∈ {success, truncated, guardrail, auth_error, transient_error, timeout, schema_error, error}, prompt_tokens (normalized from usage.input_tokens), completion_tokens (normalized from usage.output_tokens), correlation_id (the sent UUID), stop_reason (present on both success and error paths) — log fields ALL use the llm_ prefix (llm_provider, llm_model, …) consistent with Phase 2 _log_llm_call, EXCEPT correlation_id which is populated for Anthropic (Azure leaves it None)"
    - "AnthropicMGTIClient.__init__ emits exactly one logger.info('llm_provider_loaded', extra={'provider': 'anthropic_mgti', 'base_url': self._base_url}) event at construction — matches the Azure pattern added in Plan 01 (SC #5 — Anthropic half)"
    - "classify_with_tool stub UNCHANGED — Phase 4 owns it (RESEARCH.md Pitfall 7); the existing `raise NotImplementedError('AnthropicMGTIClient.classify_with_tool is implemented in Phase 4')` body MUST remain"
    - "tests/manual/observe_correlation_echo.py exists as a manual-only script (docstring marks it 'manual only — requires live ANTHROPIC_API_KEY') that constructs AnthropicMGTIClient, sends one real request, and prints whether MGTI echoes the X-Correlation-Id header back; resolves the STATE.md blocker 'MGTI X-Correlation-Id echo unverified' as an observation step, not a runtime dependency (OQ-3 decision)"
  artifacts:
    - path: "src/llm/anthropic_mgti.py"
      provides: "Full AnthropicMGTIClient implementation: __init__ with model-prefix validation and startup log, complete() with MGTI body+headers, correlation UUID, response/error mapping, structured log event; classify_with_tool stub PRESERVED"
      contains: "class AnthropicMGTIClient(LLMClient)"
      min_lines: 200
      exports: ["AnthropicMGTIClient", "_log_llm_call", "_build_request_body"]
    - path: "tests/manual/observe_correlation_echo.py"
      provides: "Manual observation script — captures whether MGTI echoes X-Correlation-Id header on a real request; documented as the resolution of the STATE.md blocker; not in pytest collection"
      min_lines: 30
  key_links:
    - from: "src/llm/anthropic_mgti.py"
      to: "requests.post"
      via: "POST {base_url}/model/{model}/messages with headers={Content-Type, X-Api-Key, X-Correlation-Id} and json=<body with anthropic_version+max_tokens+messages+optional system/temperature>"
      pattern: "requests\\.post"
    - from: "src/llm/anthropic_mgti.py"
      to: "src.utils.logger"
      via: "logger.info('llm_call', extra={...}) inside try/finally; logger.info('llm_provider_loaded', extra={...}) inside __init__"
      pattern: "logger\\.info.*(llm_call|llm_provider_loaded)"
    - from: "src/llm/anthropic_mgti.py"
      to: "src.llm.errors"
      via: "raises LLMConfigError (init-time model validation + pre-flight) / LLMAuthError / LLMTransientError / LLMTimeoutError / LLMGuardrailError / LLMSchemaError"
      pattern: "raise LLM(Config|Auth|Transient|Timeout|Guardrail|Schema)Error"
    - from: "src/llm/anthropic_mgti.py"
      to: "src.llm.config.load_settings"
      via: "AnthropicMGTIClient.__init__ calls load_settings() and reads the 8 anthropic_* fields"
      pattern: "load_settings\\(\\)"
---

<objective>
Replace the Phase 1 stub `src/llm/anthropic_mgti.py` (47 lines, raises `NotImplementedError`) with a full real adapter that talks to the MGTI Apigee proxy, maps responses to typed errors, emits the OBS-02 structured log event per call, and validates the model name at construction. Also produce a manual-only observation script that resolves the STATE.md "X-Correlation-Id echo unverified" blocker.

Purpose: This is the centerpiece of Phase 3 — once it lands, `get_llm("anthropic_mgti").complete(...)` is fully functional (no UI yet — that is Phase 5). The body construction, response parsing, and error mapping are all order-sensitive (RESEARCH.md Pitfall 4 — guardrail check BEFORE content-emptiness check is the single biggest source of latent bugs); the action sections below encode that order explicitly. The `classify_with_tool` stub MUST remain unchanged — Phase 4 owns it.

Output:
- `src/llm/anthropic_mgti.py` rewritten from 47-line stub to a ~200-300 line real adapter with `__init__` (model validation + startup log), `complete()` (MGTI HTTP + response/error mapping + log), preserved `classify_with_tool` stub, `_log_llm_call` (copied verbatim from `azure_openai.py`), and `_build_request_body` helper.
- `tests/manual/observe_correlation_echo.py` new file — manual script for the X-Correlation-Id echo observation step.

DO NOT:
- Touch `src/llm/__init__.py`, `src/llm/azure_openai.py` (Plan 01 owns the Azure startup-log edit; Plan 02 may have already shipped — adapter for Anthropic is independent), `src/llm/_compat.py` (Plan 02 owns), `src/llm/config.py` (no changes needed — settings already declared), `src/llm/base.py`, `src/llm/errors.py`, `src/llm/types.py`.
- Implement `classify_with_tool` (Phase 4 owns it — keep stub).
- Add `response.raise_for_status()` (RESEARCH.md Pitfall 1 — MGTI error envelope must be parsed BEFORE raising; use `if not response.ok:` pattern).
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

# The Phase 1 stub this plan replaces (47 lines, raises NotImplementedError)
@src/llm/anthropic_mgti.py

# The pattern to mirror line-for-line (Phase 2 locked code)
@src/llm/azure_openai.py

# The settings dataclass providing all 8 anthropic_* fields + load_settings()
@src/llm/config.py

# The seam this adapter plugs into (READ-ONLY here)
@src/llm/base.py
@src/llm/errors.py
@src/llm/types.py

# Plan 01 summary — confirms .env.example has the 9 vars and Azure __init__ logs
@.planning/phases/03-anthropic-mgti-adapter/03-01-SUMMARY.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Implement AnthropicMGTIClient with __init__ (model validation + startup log), complete() (MGTI HTTP + response/error mapping + structured log), preserved classify_with_tool stub</name>
  <files>src/llm/anthropic_mgti.py</files>
  <action>
Rewrite `src/llm/anthropic_mgti.py`. Keep the file-level docstring style consistent with `azure_openai.py`. The skeleton below is the locked structure — implement each block exactly as described.

**1. Module docstring** (replace the stub docstring):
```python
"""Anthropic MGTI adapter — Phase 3 real implementation.

Replaces the Phase 1 stub with a fully functional adapter against the MGTI
Apigee proxy. Provides text-mode complete() only; classify_with_tool stays
as a NotImplementedError stub until Phase 4 wires strict-tools.

Key differences vs the Azure adapter:
  (a) Endpoint path is /model/{model}/messages (not Azure's /chat/completions);
      the /messages suffix is mandatory.
  (b) Auth header is X-Api-Key, NOT Authorization: Bearer or api-key.
  (c) X-Correlation-Id is sent as a fresh uuid.uuid4() per call (SC #1).
  (d) System messages are extracted out of the messages list and placed as a
      top-level `system` body field (Anthropic Messages API shape).
  (e) Sampling params (temperature/top_p/top_k) are OMITTED entirely for
      models matching eu.anthropic.claude-opus-4-7* (per SC #2).
  (f) Error envelope from MGTI is {"error": {"title", "detail", "status"}} —
      NOT the native Anthropic SDK {"type":"error", "error":{...}} shape.
  (g) HTTP 200 + empty content with stop_reason != "guardrail_intervened"
      is NOT a success — it's an LLMSchemaError. The guardrail check runs
      BEFORE the content-emptiness check (order matters — RESEARCH.md Pitfall 4).

The _log_llm_call helper is COPIED VERBATIM from azure_openai.py per the
Phase 2 decision (intentional duplication; no premature extraction). If
both adapters are ever unified, the helper extracts to src/llm/_log.py.
"""
```

**2. Module imports** (top of file after docstring):
```python
from __future__ import annotations

import time
import uuid
from typing import Any

import requests

from src.llm.base import LLMClient
from src.llm.config import load_settings
from src.llm.errors import (
    LLMAuthError,
    LLMConfigError,
    LLMError,
    LLMGuardrailError,
    LLMSchemaError,
    LLMTimeoutError,
    LLMTransientError,
)
from src.llm.types import ToolCall, ToolSchema
from src.utils import logger
```

Notes:
- `uuid` is stdlib; no requirements.txt change.
- All six typed error classes are imported (LLMConfigError, LLMAuthError, LLMTransientError, LLMTimeoutError, LLMGuardrailError, LLMSchemaError); LLMError stays for the generic-fallback raise.
- `logger` from `src.utils` — same name as Azure; downstream handlers / dashboards see one `snow_query` logger emitting from both adapters.

**3. Module-level helper `_log_llm_call(extra: dict) -> None`** (COPY VERBATIM from `azure_openai.py:52-64` — Phase 2 decision):

```python
def _log_llm_call(extra: dict) -> None:
    """Emit one structured log event per LLM call (OBS-02).

    The 'msg' is the fixed tag 'llm_call'; all structured fields live in extra.
    The existing snow_query logger uses a plain-text formatter, so the structured
    fields are not visible in default console output — but they are accessible
    to any downstream handler (e.g. a JSON formatter could be added later in
    setup_logging() without touching this code).

    This function is duplicated verbatim from src/llm/azure_openai.py per the
    Phase 2 decision (intentional duplication; no premature extraction). If
    both adapters are ever unified, extract here.
    """
    logger.info("llm_call", extra=extra)
```

**4. Module-level helper `_build_request_body(model, version, max_tokens, temperature, messages) -> dict`** (extracted helper — keeps `complete()` readable):

```python
def _build_request_body(
    model: str,
    version: str,
    max_tokens: int,
    temperature: float,
    messages: list[dict],
) -> dict:
    """Build the MGTI request body from text-mode inputs.

    Implementation rules (each maps to a locked CONTEXT.md decision):

    1. System extraction: filter ALL role='system' messages out of the input;
       concatenate their content strings with '\\n\\n'; set as top-level
       `system` body field. If NO system messages present, OMIT the `system`
       key from the body entirely (do NOT send system='' — Anthropic Messages
       API treats absent and empty differently).

    2. Remaining messages: pass through as the `messages` array with role and
       content preserved verbatim. No reordering. Non-system roles only.

    3. anthropic_version: always sent (Bedrock-required constant per CONTEXT.md).

    4. max_tokens: always sent (Anthropic API requires it — unlike OpenAI).

    5. Sampling params:
       - Model starts with 'eu.anthropic.claude-opus-4-7'? OMIT temperature,
         top_p, AND top_k from body.
       - Otherwise: SEND temperature. top_p and top_k are NOT sent (caller can
         add them via kwargs in future; out of Phase 3 scope).

    Returns the dict ready to pass as json=body to requests.post.
    """
    # 1. System extraction — defensive: filter ALL system, not first-wins
    system_parts = [
        str(m["content"])
        for m in messages
        if m.get("role") == "system" and isinstance(m.get("content"), str)
    ]
    non_system = [m for m in messages if m.get("role") != "system"]

    body: dict = {
        "anthropic_version": version,
        "messages": non_system,
        "max_tokens": max_tokens,
    }

    # 2. system key OMITTED entirely when no system messages present
    if system_parts:
        body["system"] = "\n\n".join(system_parts)

    # 3. Sampling params: opus-4-7 omits ALL; other eu.anthropic.claude-* sends temperature only
    if not model.startswith("eu.anthropic.claude-opus-4-7"):
        body["temperature"] = temperature

    return body
```

Notes:
- `isinstance(m.get("content"), str)` guard: Phase 3 is text-mode only. If a system message has list-typed content (structured Anthropic content blocks), Phase 3 skips it. RESEARCH.md Pitfall 3 calls this out — Phase 5 may need to revisit if structured system content becomes load-bearing.
- The `top_p`/`top_k` "send only if caller passes" rule is INTENTIONALLY not implemented as kwargs in Phase 3; the LLMClient `complete()` interface only accepts `max_tokens` and `temperature` as named kwargs (matches `LLMClient.complete` signature in `src/llm/base.py`).
- Phase 4 will revisit this helper to add `tools` and `tool_choice` keys for strict-tools mode. Keep the helper signature stable.

**5. `AnthropicMGTIClient` class** — replace the existing stub body. Structure:

```python
class AnthropicMGTIClient(LLMClient):
    """Real Anthropic MGTI adapter (Phase 3).

    Talks to the MMC Apigee proxy at POST {base_url}/model/{model}/messages.
    Provides complete() only; classify_with_tool is a Phase 4 stub.

    Construction:
      - Reads 8 anthropic_* fields from LLMSettings (src/llm/config.py).
      - Validates ANTHROPIC_MODEL when non-empty: must start with
        'eu.anthropic.claude-' (Claude 4.5+ on EU Bedrock). Empty model
        does NOT raise (preserves Phase 1 no-op pattern — empty config
        is caught at HTTP time in complete(), matching the Azure precedent).
      - Emits exactly one `llm_provider_loaded` log event for SC #5.

    Per-call:
      - Generates a fresh UUID for X-Correlation-Id.
      - Builds request body via _build_request_body (system extraction,
        opus-4-7 sampling-param omission, anthropic_version, max_tokens).
      - POSTs with X-Api-Key + Content-Type: application/json headers.
      - On HTTP 4xx/5xx: parses MGTI error envelope and raises the typed
        error per the SC #3 mapping table.
      - On HTTP 200: checks stop_reason BEFORE content emptiness — guardrail
        responses have empty content[] but must surface as LLMGuardrailError,
        not LLMSchemaError (RESEARCH.md Pitfall 4).
      - Emits exactly one llm_call event per call (success or error path).
    """

    def __init__(self) -> None:
        # Read settings (no-op pattern preserved from Phase 1 for the empty-
        # config case; non-empty bad model name still raises at __init__ per
        # SC #2 first half).
        settings = load_settings()
        self._base_url: str = settings.anthropic_base_url
        self._api_key: str = settings.anthropic_api_key
        self._model: str = settings.anthropic_model
        self._version: str = settings.anthropic_version
        self._max_tokens: int = settings.anthropic_max_tokens
        self._temperature: float = settings.anthropic_temperature
        self._timeout_s: int = settings.anthropic_timeout_s
        self._tools_supported: bool = settings.anthropic_tools_supported

        # SC #2 first half: a NON-EMPTY model name MUST start with
        # 'eu.anthropic.claude-' (Claude 4.5+ on EU Bedrock). Empty model
        # is allowed at __init__ — the no-op pattern from Phase 1 lets the
        # factory cache store the instance even when config is missing.
        if self._model and not self._model.startswith("eu.anthropic.claude-"):
            raise LLMConfigError(
                f"ANTHROPIC_MODEL must start with 'eu.anthropic.claude-' "
                f"(Claude 4.5+ on EU Bedrock region). Got: {self._model!r}. "
                f"Update ANTHROPIC_MODEL in your .env.",
                provider="anthropic_mgti",
            )

        # SC #5 (Anthropic half): one llm_provider_loaded event per loadable
        # provider. The factory cache guarantees at-most-once per process.
        # Matches the Azure pattern in src/llm/azure_openai.py (Plan 01 edit).
        logger.info(
            "llm_provider_loaded",
            extra={"provider": "anthropic_mgti", "base_url": self._base_url},
        )

    def __repr__(self) -> str:
        # OBS-03 — never include self._api_key in repr.
        return "AnthropicMGTIClient()"

    def complete(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 500,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> str:
        """Send a chat-completion request to MGTI and return the assistant text.

        Returns the concatenated content[*].text blocks WITHOUT .strip() — call
        sites already strip (mirrors Phase 2 Pitfall 1 for symmetric provider
        behavior). Multiple text blocks are joined in order with no separator.

        Raises:
            LLMConfigError: Missing ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, or
                ANTHROPIC_MODEL — caught at HTTP time (init-time check covers
                only the bad-prefix model name per SC #2 first half).
            LLMAuthError: HTTP 401 or 403.
            LLMTransientError: HTTP 429 or 5xx, or connection-level errors.
            LLMTimeoutError: requests.Timeout.
            LLMGuardrailError: HTTP 200 with stop_reason == 'guardrail_intervened'.
            LLMSchemaError: HTTP 200 with empty content (non-guardrail), or no
                text blocks in content, or stop_reason 'tool_use' (Phase 4 path
                reached complete()), or unknown/missing stop_reason.
            LLMError: any other unexpected HTTP error.
        """
        # Pre-flight config check — embed provider-specific remediation in the
        # LLMConfigError message so _compat.py's LLMConfigError branch passes
        # str(e) through (Phase 2 OQ-1 lock — adapter owns remediation text).
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

        # RESEARCH.md Pitfall 5: correlation_id MUST be generated BEFORE the
        # try block so it's available in finally's _log_llm_call even if
        # requests.post raises immediately.
        correlation_id = str(uuid.uuid4())

        headers = {
            "Content-Type": "application/json",
            "X-Api-Key": self._api_key,
            "X-Correlation-Id": correlation_id,
        }
        body = _build_request_body(
            model=self._model,
            version=self._version,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
        )
        url = f"{self._base_url.rstrip('/')}/model/{self._model}/messages"

        t0 = time.monotonic()
        extra: dict = {
            "llm_provider": "anthropic_mgti",
            "llm_model": self._model,
            "llm_latency_ms": 0,
            "llm_outcome": "error",          # overwritten on success / truncated / guardrail
            "llm_error_type": None,
            "llm_prompt_tokens": None,       # normalized from usage.input_tokens
            "llm_completion_tokens": None,   # normalized from usage.output_tokens
            "llm_correlation_id": correlation_id,
            "llm_stop_reason": None,         # populated on both success and error paths when available
        }
        try:
            response = requests.post(
                url,
                headers=headers,
                json=body,
                timeout=self._timeout_s,
            )

            # ---- HTTP error path (4xx/5xx) ----
            # Per RESEARCH.md Pitfall 1: do NOT call response.raise_for_status().
            # The MGTI error envelope must be parsed BEFORE raising, to extract
            # {title, detail}. Use `if not response.ok:` instead.
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
                # Any other HTTP error (e.g. 400, 404, 422) — surface as generic LLMError
                extra["llm_error_type"] = "LLMError"
                raise LLMError(
                    f"Anthropic MGTI HTTP error (HTTP {status}): {msg}",
                    provider="anthropic_mgti",
                    status_code=status,
                    correlation_id=correlation_id,
                )

            # ---- HTTP 200 success path ----
            data = response.json()
            usage = data.get("usage", {}) or {}
            extra["llm_prompt_tokens"] = usage.get("input_tokens")
            extra["llm_completion_tokens"] = usage.get("output_tokens")
            stop_reason = data.get("stop_reason")
            extra["llm_stop_reason"] = stop_reason
            content_blocks = data.get("content") or []

            # CRITICAL ORDER (RESEARCH.md Pitfall 4):
            #   1. guardrail check (BEFORE content-emptiness — guardrails ALWAYS
            #      have empty content[], but must surface as LLMGuardrailError)
            #   2. content-emptiness check
            #   3. text-blocks check
            #   4. unexpected stop_reason (tool_use, unknown)
            #   5. max_tokens (success-with-truncated outcome)
            #   6. end_turn / stop_sequence (plain success)

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
                    f"(stop_reason={stop_reason!r}). HTTP 200 + empty content "
                    f"does NOT count as success.",
                    provider="anthropic_mgti",
                    correlation_id=correlation_id,
                )

            # 3. No text blocks in (non-empty) content
            text_blocks = [b for b in content_blocks if b.get("type") == "text"]
            if not text_blocks:
                extra["llm_error_type"] = "LLMSchemaError"
                extra["llm_outcome"] = "schema_error"
                raise LLMSchemaError(
                    f"Anthropic MGTI returned content with no text blocks "
                    f"(types: {[b.get('type') for b in content_blocks]!r}).",
                    provider="anthropic_mgti",
                    correlation_id=correlation_id,
                )

            # 4. tool_use reaching complete()'s text-mode path = wrong call site
            if stop_reason == "tool_use":
                extra["llm_error_type"] = "LLMSchemaError"
                extra["llm_outcome"] = "schema_error"
                raise LLMSchemaError(
                    "Unexpected tool_use stop_reason in complete() text-mode "
                    "path. Phase 4 owns the tool-use flow via "
                    "classify_with_tool — calling complete() should not "
                    "produce tool_use.",
                    provider="anthropic_mgti",
                    correlation_id=correlation_id,
                )

            # 5. max_tokens truncation — SUCCESS with outcome='truncated'
            #    (caller chose max_tokens; truncation is a known outcome,
            #    do NOT raise — CONTEXT.md decision).
            if stop_reason == "max_tokens":
                extra["llm_outcome"] = "truncated"
            elif stop_reason in ("end_turn", "stop_sequence"):
                # 6. Normal success
                extra["llm_outcome"] = "success"
            else:
                # Unknown / missing stop_reason
                extra["llm_error_type"] = "LLMSchemaError"
                extra["llm_outcome"] = "schema_error"
                raise LLMSchemaError(
                    f"Anthropic MGTI returned unknown stop_reason: {stop_reason!r}.",
                    provider="anthropic_mgti",
                    correlation_id=correlation_id,
                )

            # Concatenate all text blocks in order (no separator, no .strip()).
            # NOTE: NO .strip() — call sites strip; double-strip is idempotent
            # but breaks the symmetric provider behavior locked in Phase 2.
            return "".join(b.get("text", "") for b in text_blocks)

        except requests.exceptions.Timeout as e:
            extra["llm_error_type"] = "LLMTimeoutError"
            extra["llm_outcome"] = "timeout"
            raise LLMTimeoutError(
                f"Anthropic MGTI request timed out after {self._timeout_s}s: {e}",
                provider="anthropic_mgti",
                correlation_id=correlation_id,
            ) from e

        except requests.exceptions.RequestException as e:
            # Connection errors, DNS, etc. — treat as transient. This branch
            # does NOT catch HTTPError because we never call raise_for_status();
            # MGTI 4xx/5xx is handled in the `if not response.ok:` block above.
            extra["llm_error_type"] = "LLMTransientError"
            extra["llm_outcome"] = "transient_error"
            raise LLMTransientError(
                f"Anthropic MGTI request failed: {e}",
                provider="anthropic_mgti",
                correlation_id=correlation_id,
            ) from e

        finally:
            extra["llm_latency_ms"] = int((time.monotonic() - t0) * 1000)
            _log_llm_call(extra)

    def classify_with_tool(
        self,
        messages: list[dict],
        tool: ToolSchema,
        *,
        tool_name: str,
        **kwargs: Any,
    ) -> ToolCall:
        # PRESERVED from Phase 1 stub — Phase 4 owns the strict-tools flow
        # (RESEARCH.md Pitfall 7). Do NOT implement in Phase 3.
        raise NotImplementedError(
            "AnthropicMGTIClient.classify_with_tool is implemented in Phase 4"
        )
```

Notes encoded as task-level guards (each maps to a specific CONTEXT.md / RESEARCH.md decision the implementer easily inverts):

- **`response.ok` (not `raise_for_status()`)** — RESEARCH.md Pitfall 1. The MGTI error envelope MUST be parsed before raising the typed error (we need `title`/`detail` for the message), and `raise_for_status()` raises `HTTPError` which is caught by `RequestException` below — wrong dispatch.
- **`stop_reason` check BEFORE content-emptiness check** — RESEARCH.md Pitfall 4. Guardrail responses ALWAYS have empty content[], but they must surface as `LLMGuardrailError`, not `LLMSchemaError`. The order in the action block above is the locked sequence: guardrail → empty-content → no-text-blocks → tool_use → unknown stop_reason → max_tokens (truncated success) → end_turn/stop_sequence (success). DO NOT reorder.
- **`system` key OMITTED when no system messages present** — CONTEXT.md "No system messages present: Omit `system` key from the body entirely. Do NOT send `system: ""`." The `if system_parts:` guard in `_build_request_body` enforces this.
- **Log fields use `llm_*` prefix** — same convention as Phase 2 `_log_llm_call`. Field `llm_correlation_id` is populated (Azure leaves None); `llm_prompt_tokens` / `llm_completion_tokens` are NORMALIZED Azure field names (NOT `input_tokens`/`output_tokens` — RESEARCH.md "Log event field naming"). `llm_stop_reason` is added (Anthropic-only; not present in Azure logs — that is acceptable, the field is extra-only).
- **`correlation_id` is generated BEFORE the try block** — RESEARCH.md Pitfall 5. Set on `extra["llm_correlation_id"]` before `t0 = time.monotonic()` so the `finally`'s log call has it even if `requests.post(...)` itself raises (e.g. a DNS failure that fires `RequestException` before the response is even created).
- **`__repr__` override** — OBS-03 regression guard symmetric with Azure. Returns `"AnthropicMGTIClient()"` so the API key cannot leak via repr.
- **`classify_with_tool` body is UNCHANGED** — same `raise NotImplementedError(...)` text as the Phase 1 stub. Phase 4 owns it (RESEARCH.md Pitfall 7).
- **Empty model at `__init__` does NOT raise** — `if self._model and not self._model.startswith(...)`. The `self._model and` guard is the load-bearing distinction: empty (env not set yet) is allowed at construction; non-empty invalid is not (SC #2 first half).
- **Sampling-param omission key match**: `model.startswith("eu.anthropic.claude-opus-4-7")` — covers `eu.anthropic.claude-opus-4-7`, `eu.anthropic.claude-opus-4-7-20251201-v1:0`, etc. (per CONTEXT.md "for any model name matching `eu.anthropic.claude-opus-4-7*`"). Do NOT use a regex; `startswith` is correct and simpler.
  </action>
  <verify>
Run from project root (PowerShell or Bash). This verification is end-to-end against `requests.post` mock and exercises SC #1, #2, #3, #5 (the Anthropic half) at the adapter level. The full pytest acceptance gate lands in Plan 04.

```
python -c "
import os
import logging
from unittest.mock import patch, MagicMock

# Step 1: strip env and confirm empty model does NOT raise at __init__ (no-op pattern preserved)
for k in ('ANTHROPIC_BASE_URL','ANTHROPIC_API_KEY','ANTHROPIC_MODEL','ANTHROPIC_VERSION','ANTHROPIC_MAX_TOKENS','ANTHROPIC_TEMPERATURE','ANTHROPIC_TIMEOUT_S','ANTHROPIC_TOOLS_SUPPORTED','LLM_PROVIDER_DEFAULT'):
    os.environ.pop(k, None)
from src.llm.anthropic_mgti import AnthropicMGTIClient
from src.llm.errors import LLMConfigError, LLMAuthError, LLMTransientError, LLMTimeoutError, LLMGuardrailError, LLMSchemaError, LLMError

c = AnthropicMGTIClient()  # MUST NOT raise (empty model)
assert repr(c) == 'AnthropicMGTIClient()', f'repr regressed: {repr(c)!r}'

# Step 2: SC #2 first half — non-eu-prefixed model at __init__ MUST raise LLMConfigError
os.environ['ANTHROPIC_MODEL'] = 'gpt-4o'
try:
    AnthropicMGTIClient()
    raise AssertionError('SC #2 BROKEN: bad model name did not raise at __init__')
except LLMConfigError as e:
    assert 'eu.anthropic.claude-' in str(e), f'remediation text missing eu.anthropic.claude- mention: {e}'
    assert e.provider == 'anthropic_mgti'

# Step 3: valid eu.anthropic.claude- prefix constructs cleanly
os.environ['ANTHROPIC_BASE_URL'] = 'https://stage.example.com/coreapi/llm/anthropic/v1'
os.environ['ANTHROPIC_API_KEY'] = 'test-key-not-real'
os.environ['ANTHROPIC_MODEL'] = 'eu.anthropic.claude-sonnet-4-5-20250929-v1:0'
captured = []
class _H(logging.Handler):
    def emit(self, record):
        captured.append(record)
import src.utils as u
u.logger.addHandler(_H())

c = AnthropicMGTIClient()
# SC #5 Anthropic half: one llm_provider_loaded event per construction
load_events = [r for r in captured if r.getMessage() == 'llm_provider_loaded']
assert len(load_events) == 1, f'expected 1 llm_provider_loaded event, got {len(load_events)}'
assert load_events[0].provider == 'anthropic_mgti'
assert load_events[0].base_url == os.environ['ANTHROPIC_BASE_URL']

# Step 4: SC #1 happy path — URL, headers (including fresh UUID), body shape
def _make_resp(text='Hello.', stop_reason='end_turn', input_tokens=25, output_tokens=10):
    r = MagicMock()
    r.status_code = 200
    r.ok = True
    r.json.return_value = {
        'id':'msg_test','type':'message','role':'assistant',
        'model':'eu.anthropic.claude-sonnet-4-5-20250929-v1:0',
        'content': [{'type':'text','text':text}] if text else [],
        'stop_reason': stop_reason,
        'usage': {'input_tokens': input_tokens, 'output_tokens': output_tokens},
    }
    return r

captured.clear()
with patch('requests.post', return_value=_make_resp(text='Hi there.')) as mp:
    out = c.complete([
        {'role':'system','content':'You are a helpful assistant.'},
        {'role':'user','content':'Greet me.'},
    ], max_tokens=128, temperature=0.5)
assert out == 'Hi there.', f'extraction wrong: {out!r}'

call_args = mp.call_args
url = call_args.args[0] if call_args.args else call_args.kwargs.get('url')
assert url.endswith('/model/eu.anthropic.claude-sonnet-4-5-20250929-v1:0/messages'), f'URL wrong: {url!r}'

headers = call_args.kwargs['headers']
assert headers['Content-Type'] == 'application/json'
assert headers['X-Api-Key'] == 'test-key-not-real'
assert 'X-Correlation-Id' in headers, 'missing X-Correlation-Id header'
import uuid
uuid.UUID(headers['X-Correlation-Id'])  # must parse as valid UUID — raises if not

# Body shape: system extracted to top-level; messages has no system; temperature present (not opus-4-7)
body = call_args.kwargs['json']
assert body['anthropic_version'] == 'bedrock-2023-05-31', f'version wrong: {body}'
assert body['max_tokens'] == 128, f'max_tokens not honored: {body}'
assert body['system'] == 'You are a helpful assistant.', f'system extraction failed: {body}'
assert body['messages'] == [{'role':'user','content':'Greet me.'}], f'messages not filtered: {body}'
assert body['temperature'] == 0.5, f'temperature should be sent for non-opus model: {body}'
assert 'top_p' not in body, f'top_p should not be sent: {body}'
assert 'top_k' not in body, f'top_k should not be sent: {body}'

# Step 5: SC #1 — fresh UUID per call (two calls -> two different correlation IDs)
ids = []
with patch('requests.post', side_effect=lambda *a, **kw: (ids.append(kw['headers']['X-Correlation-Id']), _make_resp(text='x'))[1]):
    c.complete([{'role':'user','content':'a'}])
    c.complete([{'role':'user','content':'b'}])
assert len(set(ids)) == 2, f'X-Correlation-Id repeated across calls: {ids}'

# Step 6: SC #2 second half — opus-4-7 model OMITS temperature/top_p/top_k
os.environ['ANTHROPIC_MODEL'] = 'eu.anthropic.claude-opus-4-7-20251201-v1:0'
import src.llm
src.llm._cache.clear()
c_opus = AnthropicMGTIClient()
with patch('requests.post', return_value=_make_resp()) as mp:
    c_opus.complete([{'role':'user','content':'x'}], temperature=0.7)
body = mp.call_args.kwargs['json']
assert 'temperature' not in body, f'opus-4-7 SHOULD OMIT temperature: {body}'
assert 'top_p' not in body
assert 'top_k' not in body

# Step 7: SC #1 + body — system OMITTED when no system messages
with patch('requests.post', return_value=_make_resp()) as mp:
    c_opus.complete([{'role':'user','content':'just user'}])
body = mp.call_args.kwargs['json']
assert 'system' not in body, f'system key should be OMITTED when no system msgs: {body}'

# Step 8: SC #3 — typed error mapping
def _err_resp(code, title='Err', detail='detail'):
    r = MagicMock()
    r.status_code = code
    r.ok = False
    r.json.return_value = {'error':{'title':title,'detail':detail,'status':code}}
    r.text = f'{title}: {detail}'
    return r

# 401 -> LLMAuthError
with patch('requests.post', return_value=_err_resp(401, 'Unauthorized', 'Invalid API key')):
    try:
        c_opus.complete([{'role':'user','content':'x'}])
        raise AssertionError('expected LLMAuthError on 401')
    except LLMAuthError as e:
        assert e.provider == 'anthropic_mgti'
        assert e.status_code == 401
        assert 'Unauthorized' in str(e) or 'Invalid API key' in str(e), f'envelope not parsed: {e}'

# 403 -> LLMAuthError
with patch('requests.post', return_value=_err_resp(403, 'Forbidden', 'no access')):
    try:
        c_opus.complete([{'role':'user','content':'x'}])
        raise AssertionError('expected LLMAuthError on 403')
    except LLMAuthError:
        pass

# 429 -> LLMTransientError
with patch('requests.post', return_value=_err_resp(429, 'TooMany', 'rate limited')):
    try:
        c_opus.complete([{'role':'user','content':'x'}])
        raise AssertionError('expected LLMTransientError on 429')
    except LLMTransientError as e:
        assert e.status_code == 429

# 503 -> LLMTransientError
with patch('requests.post', return_value=_err_resp(503, 'Service Unavailable', 'down')):
    try:
        c_opus.complete([{'role':'user','content':'x'}])
        raise AssertionError('expected LLMTransientError on 503')
    except LLMTransientError:
        pass

# requests.Timeout -> LLMTimeoutError
import requests
with patch('requests.post', side_effect=requests.exceptions.Timeout('simulated')):
    try:
        c_opus.complete([{'role':'user','content':'x'}])
        raise AssertionError('expected LLMTimeoutError')
    except LLMTimeoutError as e:
        assert e.provider == 'anthropic_mgti'

# stop_reason=guardrail_intervened (HTTP 200, empty content) -> LLMGuardrailError
with patch('requests.post', return_value=_make_resp(text='', stop_reason='guardrail_intervened')):
    try:
        c_opus.complete([{'role':'user','content':'x'}])
        raise AssertionError('expected LLMGuardrailError on guardrail stop')
    except LLMGuardrailError as e:
        assert e.provider == 'anthropic_mgti'

# HTTP 200 + empty content + NON-guardrail stop_reason -> LLMSchemaError
# (CRITICAL: this proves the guardrail-check-BEFORE-content-emptiness ordering is correct.
# If the order were reversed, guardrail responses would also raise LLMSchemaError instead.)
with patch('requests.post', return_value=_make_resp(text='', stop_reason='end_turn')):
    try:
        c_opus.complete([{'role':'user','content':'x'}])
        raise AssertionError('expected LLMSchemaError on 200+empty-content+non-guardrail')
    except LLMSchemaError as e:
        assert 'empty content' in str(e).lower() or 'does NOT count as success' in str(e), f'wrong schema-error msg: {e}'

# Step 9: max_tokens stop_reason -> SUCCESS with outcome='truncated' (do NOT raise)
captured.clear()
with patch('requests.post', return_value=_make_resp(text='partial answer', stop_reason='max_tokens')):
    out = c_opus.complete([{'role':'user','content':'x'}])
assert out == 'partial answer', f'truncation should still return text: {out!r}'
call_events = [r for r in captured if r.getMessage() == 'llm_call']
assert len(call_events) == 1
assert call_events[0].llm_outcome == 'truncated', f'expected outcome=truncated, got {call_events[0].llm_outcome!r}'

# Step 10: log event shape on success
captured.clear()
with patch('requests.post', return_value=_make_resp(text='ok', input_tokens=42, output_tokens=7)):
    c_opus.complete([{'role':'user','content':'x'}])
ev = [r for r in captured if r.getMessage() == 'llm_call'][-1]
assert ev.llm_provider == 'anthropic_mgti'
assert ev.llm_model.startswith('eu.anthropic.claude-opus-4-7')
assert ev.llm_outcome == 'success'
assert ev.llm_error_type is None
assert ev.llm_prompt_tokens == 42  # normalized from input_tokens
assert ev.llm_completion_tokens == 7  # normalized from output_tokens
assert ev.llm_correlation_id is not None
import uuid
uuid.UUID(ev.llm_correlation_id)  # valid UUID
assert ev.llm_stop_reason == 'end_turn'
assert isinstance(ev.llm_latency_ms, int) and ev.llm_latency_ms >= 0

# Step 11: classify_with_tool stub PRESERVED (Phase 4 territory)
from src.llm.types import ToolSchema
tool = ToolSchema(name='x', description='x', input_schema={'type':'object'})
try:
    c_opus.classify_with_tool([{'role':'user','content':'x'}], tool, tool_name='x')
    raise AssertionError('classify_with_tool should still raise NotImplementedError')
except NotImplementedError as e:
    assert 'Phase 4' in str(e), f'stub message changed: {e}'

print('TASK 1 OK — adapter fully wired')
"
```

Must print `TASK 1 OK — adapter fully wired`.

Also confirm Phase 1 + Phase 2 (and Plan 01 + Plan 02 if those have shipped) still green:

```
python -m pytest tests/test_llm_seam.py tests/test_phase2_parity.py -v
```

Expected: 18 tests pass.
  </verify>
  <done>
- `src/llm/anthropic_mgti.py` no longer raises `NotImplementedError` from `complete()` — full real implementation present.
- `__init__` reads 8 anthropic_* fields from `load_settings()`, validates `ANTHROPIC_MODEL` prefix (non-empty + non-eu.anthropic.claude- → `LLMConfigError`), and emits one `llm_provider_loaded` event.
- `__repr__` returns `"AnthropicMGTIClient()"` (OBS-03 regression guard symmetric with Azure).
- `complete()` posts to `{base_url}/model/{model}/messages` with `X-Api-Key` + `Content-Type: application/json` + fresh `X-Correlation-Id` UUID per call.
- `_build_request_body` extracts system messages, OMITS `system` key when no system messages, OMITS `temperature`/`top_p`/`top_k` for opus-4-7 models, always sends `anthropic_version` and `max_tokens`.
- HTTP error path: parses MGTI `{error: {title, detail}}` envelope BEFORE raising; 401/403→LLMAuthError, 429/5xx→LLMTransientError, requests.Timeout→LLMTimeoutError, other RequestException→LLMTransientError.
- HTTP 200 path order: guardrail → empty-content → no-text-blocks → tool_use → max_tokens (truncated success) → end_turn/stop_sequence (success) → unknown stop_reason (LLMSchemaError).
- `_log_llm_call` COPIED VERBATIM from azure_openai.py (intentional duplication per Phase 2 decision).
- Each `complete()` call emits exactly one `llm_call` event with full `llm_*` extra fields (provider, model, latency_ms, outcome, error_type, prompt_tokens, completion_tokens, correlation_id, stop_reason).
- `classify_with_tool` body UNCHANGED — still raises `NotImplementedError("AnthropicMGTIClient.classify_with_tool is implemented in Phase 4")`.
- Phase 1 + Phase 2 acceptance gates (18 tests) still pass.
- Satisfies: SC #1 (URL + headers + fresh UUID), SC #2 (model validation + opus sampling-param omission), SC #3 (typed-error mapping including guardrail and empty-content), SC #5 (Anthropic half — startup log and no tool wrapping reachable). SC #4 owned by Plan 01 (`.env.example`). The acceptance-gate proof of all 5 is Plan 04.
  </done>
</task>

<task type="auto">
  <name>Task 2: Create tests/manual/observe_correlation_echo.py — manual observation script for the X-Correlation-Id echo (OQ-3, resolves STATE.md blocker)</name>
  <files>tests/manual/observe_correlation_echo.py</files>
  <action>
Create the `tests/manual/` directory (if missing) and write `observe_correlation_echo.py`. This is a manual-only script (NOT collected by pytest) that the operator runs against a real stage `ANTHROPIC_API_KEY` to observe whether MGTI echoes the `X-Correlation-Id` header on the response. The output of this observation goes into the Phase 3 commit message and SUMMARY — it resolves the STATE.md blocker "MGTI X-Correlation-Id echo unverified" through observation rather than a code change.

Per the OQ-3 decision recorded in planning_context: this script is small, satisfies the CONTEXT.md observation requirement, and is gated by a `--run-manual` flag (or simply documented "manual only — pytest does NOT collect this file").

**File contents** (`tests/manual/observe_correlation_echo.py`):

```python
"""Manual observation script — does MGTI echo our X-Correlation-Id?

Resolves the STATE.md blocker:
    "MGTI `usage` block pass-through and `X-Correlation-Id` echo unverified —
     capture a real stage response during Phase 3 to inform observability design"

Usage (requires a working stage .env):
    python tests/manual/observe_correlation_echo.py

This script:
  1. Constructs AnthropicMGTIClient from env vars.
  2. Sends ONE real text-mode request with a known X-Correlation-Id.
  3. Prints whether the response headers echo back the same correlation ID
     and what the usage block looked like.

The output is recorded in 03-03-SUMMARY.md and the commit message, so a
future Phase 5 work-item can decide whether to promote X-Correlation-Id echo
to a load-bearing log field.

NOT collected by pytest (this directory has no test_ prefix; pytest collection
is `tests/test_*.py` only). Safe to leave in the repo as a one-shot diagnostic.
"""
from __future__ import annotations

import os
import sys
import uuid

import requests


def main() -> int:
    base_url = os.getenv("ANTHROPIC_BASE_URL", "").rstrip("/")
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    model = os.getenv("ANTHROPIC_MODEL", "")
    version = os.getenv("ANTHROPIC_VERSION", "bedrock-2023-05-31")

    if not (base_url and api_key and model):
        print(
            "ERROR: set ANTHROPIC_BASE_URL, ANTHROPIC_API_KEY, and "
            "ANTHROPIC_MODEL in your environment first. Aborting.",
            file=sys.stderr,
        )
        return 2

    correlation_id = str(uuid.uuid4())
    url = f"{base_url}/model/{model}/messages"
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": api_key,
        "X-Correlation-Id": correlation_id,
    }
    body = {
        "anthropic_version": version,
        "messages": [{"role": "user", "content": "Reply with just the word 'ok'."}],
        "max_tokens": 16,
    }

    print(f"[observe_correlation_echo] sending POST {url}")
    print(f"[observe_correlation_echo] X-Correlation-Id sent: {correlation_id}")
    response = requests.post(url, headers=headers, json=body, timeout=30)
    print(f"[observe_correlation_echo] HTTP {response.status_code}")
    print(f"[observe_correlation_echo] response headers: {dict(response.headers)}")

    # Echo check — case-insensitive header lookup
    echoed = None
    for k, v in response.headers.items():
        if k.lower() == "x-correlation-id":
            echoed = v
            break

    if echoed is None:
        print("[observe_correlation_echo] RESULT: MGTI did NOT echo X-Correlation-Id.")
    elif echoed == correlation_id:
        print(f"[observe_correlation_echo] RESULT: MGTI echoed exactly. value={echoed}")
    else:
        print(
            f"[observe_correlation_echo] RESULT: MGTI returned a DIFFERENT correlation "
            f"id. sent={correlation_id} returned={echoed}"
        )

    # Usage block observation
    if response.ok:
        try:
            data = response.json()
            print(f"[observe_correlation_echo] usage block: {data.get('usage')}")
            print(f"[observe_correlation_echo] stop_reason: {data.get('stop_reason')}")
        except ValueError:
            print("[observe_correlation_echo] response body not JSON.")
    else:
        print(f"[observe_correlation_echo] error body: {response.text[:300]}")

    return 0 if response.ok else 1


if __name__ == "__main__":
    sys.exit(main())
```

Notes:
- This file lives in `tests/manual/`, NOT `tests/`. The default `pytest tests/` collection picks up `tests/test_*.py` only — `tests/manual/observe_correlation_echo.py` is NOT collected. Run as `python tests/manual/observe_correlation_echo.py`.
- No assertion / no `def test_*`; explicitly NOT a test. Output is print-only for the operator's eyes.
- Reads env vars directly (does NOT go through `src.llm.config.load_settings()`) so a developer can run this with a one-off env override without touching `.env`.
- Exit codes: 0 on HTTP 2xx, 1 on HTTP non-2xx, 2 on missing env. Allows a future CI matrix job to gate on this if desired.
- The output of running this with a live key is what goes into the Phase 3 commit message and into the 03-03-SUMMARY.md "Observed Behavior" section.
  </action>
  <verify>
Run from project root:

```
# 1. File exists at the manual path
python -c "
import os
p = os.path.join('tests', 'manual', 'observe_correlation_echo.py')
assert os.path.exists(p), f'missing: {p}'

# 2. pytest does NOT collect it (it's not in tests/ root and has no test_ prefix)
import subprocess
out = subprocess.check_output(['python','-m','pytest','--collect-only','-q','tests/manual/observe_correlation_echo.py'], stderr=subprocess.STDOUT).decode()
# Allow either 'no tests collected' or 'collected 0 items'
assert 'no tests' in out.lower() or 'collected 0' in out.lower(), f'pytest collected the manual script: {out}'

# 3. Script aborts cleanly with exit 2 when env vars are missing (does NOT try to run live)
import os, subprocess
env = {k: v for k, v in os.environ.items() if not k.startswith('ANTHROPIC_')}
proc = subprocess.run(['python','tests/manual/observe_correlation_echo.py'], env=env, capture_output=True, text=True)
assert proc.returncode == 2, f'expected exit 2 on missing env, got {proc.returncode}; stderr={proc.stderr!r}'
assert 'ANTHROPIC_BASE_URL' in proc.stderr or 'ANTHROPIC_BASE_URL' in proc.stdout, f'error message did not mention required vars: {proc.stderr!r}'

print('TASK 2 OK — manual observation script present, not pytest-collected, fails fast on missing env')
"
```

Must print `TASK 2 OK ...`. This proves the script exists, is NOT pytest-collected (so it never runs in CI by accident), and fails fast when env is missing.

NOTE: this verify block does NOT actually call the MGTI proxy. The live-credential observation step happens when the operator manually runs `python tests/manual/observe_correlation_echo.py` with a real stage key — the script's output is then pasted into 03-03-SUMMARY.md. If a real key is not available during this phase, document "live observation deferred to Phase 4 smoke test" in the summary; Phase 4 owns live-credential testing per ROADMAP.md.
  </verify>
  <done>
- `tests/manual/observe_correlation_echo.py` exists, ~50-70 lines, with a clear "manual only" docstring referencing the STATE.md blocker it resolves.
- The script reads `ANTHROPIC_BASE_URL` / `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` / `ANTHROPIC_VERSION` from env, generates a fresh UUID, POSTs to MGTI, prints whether the response echoes the `X-Correlation-Id` header (case-insensitive), and prints the `usage` block + `stop_reason`.
- pytest collection does NOT pick up this file (verified with `pytest --collect-only`).
- Exit codes: 0 (success), 1 (HTTP non-2xx), 2 (missing env).
- Operator can paste the script's output into 03-03-SUMMARY.md to resolve the STATE.md blocker "MGTI X-Correlation-Id echo unverified" through observation. If live observation is deferred to Phase 4, that fact is documented in the summary.
- Satisfies the OQ-3 decision and the CONTEXT.md observation requirement.
  </done>
</task>

</tasks>

<verification>
End-of-plan verification — adapter is fully wired plus the manual observation script is present:

```
# 1. Adapter is no longer a stub
python -c "
import inspect
from src.llm.anthropic_mgti import AnthropicMGTIClient
from src.llm.base import LLMClient

# Class still satisfies the ABC
assert issubclass(AnthropicMGTIClient, LLMClient)
assert AnthropicMGTIClient.__abstractmethods__ == frozenset()

# complete() is no longer NotImplementedError
src_complete = inspect.getsource(AnthropicMGTIClient.complete)
assert 'NotImplementedError' not in src_complete, 'complete() still a stub'

# classify_with_tool MUST still be NotImplementedError (Phase 4)
src_classify = inspect.getsource(AnthropicMGTIClient.classify_with_tool)
assert 'NotImplementedError' in src_classify, 'classify_with_tool wrongly implemented in Phase 3'
assert 'Phase 4' in src_classify

# Required signals are in the source
for needle in ['requests.post', 'X-Correlation-Id', 'X-Api-Key', 'uuid.uuid4', 'eu.anthropic.claude-', '/messages',
               'guardrail_intervened', 'input_tokens', 'output_tokens', 'llm_provider_loaded', 'llm_call']:
    assert needle in src_complete or needle in inspect.getsource(__import__('src.llm.anthropic_mgti', fromlist=['*'])), \
        f'missing in module: {needle!r}'

print('PLAN 03-03 ADAPTER VERIFICATION OK')
"

# 2. Phase 1 + Phase 2 acceptance gates still green (18 tests)
python -m pytest tests/test_llm_seam.py tests/test_phase2_parity.py -v

# 3. Manual observation script exists and is NOT pytest-collected
ls tests/manual/observe_correlation_echo.py
python -m pytest --collect-only tests/manual/ 2>&1 | grep -i 'no tests\|collected 0' || echo 'WARN: manual script unexpectedly collected'
```

The pytest run MUST show 18 passing.

Files this plan modifies:
- `src/llm/anthropic_mgti.py` (full rewrite — 47-line stub → 200-300 line real adapter)
- `tests/manual/observe_correlation_echo.py` (NEW)

Files NOT touched by this plan (verify diff is empty):
```
git diff --name-only HEAD .env.example src/llm/__init__.py src/llm/azure_openai.py src/llm/_compat.py src/llm/config.py src/llm/base.py src/llm/errors.py src/llm/types.py src/query_router.py src/sql_generator.py app.py config.py tests/test_llm_seam.py tests/test_phase2_parity.py tests/fixtures/ 2>&1 | head
```

Must produce no output. NOTE: Plan 01 may have already modified `.env.example` and `src/llm/azure_openai.py`; Plan 02 may have modified `src/llm/_compat.py`. Those are sibling-Wave-1 plans this plan depends on (Plan 01 explicit dependency for env + Azure startup-log pattern). If running this plan in isolation, those modifications are expected to already be in HEAD.
</verification>

<success_criteria>
- `src/llm/anthropic_mgti.py` no longer raises `NotImplementedError` from `complete()`; full real implementation present (~200-300 lines).
- `AnthropicMGTIClient.__init__` validates non-empty `ANTHROPIC_MODEL` prefix and emits `llm_provider_loaded` log event (SC #2 first half + SC #5 Anthropic half).
- `AnthropicMGTIClient.complete()` POSTs to `{base_url}/model/{model}/messages` with `X-Api-Key`, `Content-Type: application/json`, and a fresh `X-Correlation-Id` UUID per call (SC #1).
- Request body OMITS `temperature`/`top_p`/`top_k` for `eu.anthropic.claude-opus-4-7*` models; OMITS `system` key entirely when no system messages present; always sends `anthropic_version` and `max_tokens` (SC #2 second half).
- Response/error mapping per SC #3: 401/403→LLMAuthError, 429/5xx→LLMTransientError, Timeout→LLMTimeoutError, guardrail_intervened→LLMGuardrailError, empty-content-non-guardrail→LLMSchemaError. **CRITICAL: guardrail check BEFORE content-emptiness check** (RESEARCH.md Pitfall 4).
- One `llm_call` log event per complete() call with full `llm_*` extra fields (Anthropic field names normalized to Azure: `input_tokens`→`llm_prompt_tokens`, `output_tokens`→`llm_completion_tokens`); `llm_correlation_id` populated; `llm_outcome` ∈ {success, truncated, guardrail, auth_error, transient_error, timeout, schema_error, error}.
- `_log_llm_call` is byte-identical to the Azure copy (intentional duplication).
- `classify_with_tool` stub UNCHANGED — still raises `NotImplementedError("AnthropicMGTIClient.classify_with_tool is implemented in Phase 4")` (RESEARCH.md Pitfall 7).
- `tests/manual/observe_correlation_echo.py` exists and is NOT pytest-collected.
- Phase 1 + Phase 2 acceptance gates (18 tests) still pass.

Maps to: SC #1 (full — URL construction, headers, fresh UUID). SC #2 (full — model validation at __init__ + opus-4-7 sampling-param omission). SC #3 (full — adapter-level typed-error mapping including guardrail and empty-content; user-visible QueryError translation is Plan 02). SC #5 (Anthropic half — startup log; "no tool wrapping" half is already true in call sites — Plan 04 verifies). The acceptance-gate proof that all 5 SCs work end-to-end is Plan 04. Requirements: ADP-03, ADP-04, ADP-05, ADP-06, ADP-08, ERR-02, ERR-03, OBS-01, OBS-04, TOOL-07 (the not-yet-wired stub aspect).
</success_criteria>

<output>
After completion, create `.planning/phases/03-anthropic-mgti-adapter/03-03-SUMMARY.md` documenting:
- Final line count of `src/llm/anthropic_mgti.py` (stub was 47; expect ~250-350 lines).
- Confirmation that `requests.post`, `X-Correlation-Id`, `X-Api-Key`, `uuid.uuid4`, `eu.anthropic.claude-`, `/messages`, `guardrail_intervened`, `input_tokens`, `output_tokens`, `llm_provider_loaded`, `llm_call`, all six typed-error classes (LLMConfigError / LLMAuthError / LLMTransientError / LLMTimeoutError / LLMGuardrailError / LLMSchemaError) are all present.
- Confirmation that the adapter does NOT call `response.raise_for_status()` (RESEARCH.md Pitfall 1) and does NOT call `.strip()` on the return value (Phase 2 Pitfall 1 — symmetric provider behavior).
- Confirmation that `classify_with_tool` stub is byte-identical to the Phase 1 stub (Phase 4 territory).
- Confirmation that the guardrail stop_reason check precedes the content-emptiness check in `complete()` (paste the relevant 10-line excerpt showing the order).
- Confirmation that Phase 1 + Phase 2 acceptance gates (18 tests) still pass.
- "Observed Behavior" section: paste the output of `python tests/manual/observe_correlation_echo.py` (if a live key was available); otherwise note "live correlation-echo observation deferred to Phase 4 smoke test per ROADMAP.md".
- Line-by-line summary of which SC each part of the implementation satisfies.
</output>
