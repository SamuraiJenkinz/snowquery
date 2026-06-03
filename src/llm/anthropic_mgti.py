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


def _build_request_body(
    model: str,
    version: str,
    max_tokens: int,
    temperature: float,
    messages: list[dict],
    direct_mode: bool = False,
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

    if direct_mode:
        # Native Anthropic API: model in body, no anthropic_version (sent as header).
        body: dict = {
            "model": model,
            "messages": non_system,
            "max_tokens": max_tokens,
        }
    else:
        body = {
            "anthropic_version": version,
            "messages": non_system,
            "max_tokens": max_tokens,
        }

    # 2. system key OMITTED entirely when no system messages present
    if system_parts:
        body["system"] = "\n\n".join(system_parts)

    # 3. Sampling params: opus-4-7 omits ALL; other Claude models send temperature only.
    #    Match both eu.anthropic.claude-opus-4-7* (MGTI/Bedrock) and claude-opus-4-7*
    #    (direct API) — same family, different namespace.
    opus_47 = (
        model.startswith("eu.anthropic.claude-opus-4-7")
        or (direct_mode and model.startswith("claude-opus-4-7"))
    )
    if not opus_47:
        body["temperature"] = temperature

    return body


class AnthropicMGTIClient(LLMClient):
    """Real Anthropic MGTI adapter (Phase 3 / Phase 4).

    Talks to the MMC Apigee proxy at POST {base_url}/model/{model}/messages.
    Provides complete() for text-mode and classify_with_tool() for strict-tools
    intent classification (Phase 4).

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
        self._direct_mode: bool = settings.anthropic_direct_mode

        # SC #2 first half: a NON-EMPTY model name MUST start with
        # 'eu.anthropic.claude-' (Claude 4.5+ on EU Bedrock). Empty model
        # is allowed at __init__ — the no-op pattern from Phase 1 lets the
        # factory cache store the instance even when config is missing.
        # Direct mode skips the eu.* prefix check (native API uses
        # claude-haiku-4-5-20251001 / claude-sonnet-4-5-* / etc.).
        if (
            self._model
            and not self._direct_mode
            and not self._model.startswith("eu.anthropic.claude-")
        ):
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
            extra={
                "provider": "anthropic_mgti",
                "base_url": self._base_url,
                "tools_supported": self._tools_supported,
            },
        )

    def __repr__(self) -> str:
        # OBS-03 — never include self._api_key in repr.
        return "AnthropicMGTIClient()"

    @property
    def provider_name(self) -> str:
        return "anthropic_mgti"

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
        if self._direct_mode:
            url = f"{self._base_url.rstrip('/')}/messages"
        else:
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

    def complete(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 500,
        temperature: float = 0.1,
        _emit_log: bool = True,
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
            "Accept": "application/json",
            "X-Api-Key": self._api_key,
            "X-Correlation-Id": correlation_id,
        }
        if self._direct_mode:
            # Native Anthropic API requires the version as a header (not in body).
            headers["anthropic-version"] = self._version if self._version and not self._version.startswith("bedrock-") else "2023-06-01"
        body = _build_request_body(
            model=self._model,
            version=self._version,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
            direct_mode=self._direct_mode,
        )

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
            data = self._post_messages(body, headers, correlation_id, extra)

            # ---- HTTP 200 success path ----
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

        finally:
            extra["llm_latency_ms"] = int((time.monotonic() - t0) * 1000)
            if _emit_log:
                _log_llm_call(extra)

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
            "Accept": "application/json",
            "X-Api-Key": self._api_key,
            "X-Correlation-Id": correlation_id,
        }
        if self._direct_mode:
            headers["anthropic-version"] = self._version if self._version and not self._version.startswith("bedrock-") else "2023-06-01"

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
            direct_mode=self._direct_mode,
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
