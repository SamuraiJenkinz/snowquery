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
