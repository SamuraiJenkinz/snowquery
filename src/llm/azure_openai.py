"""Azure OpenAI adapter — Phase 2 real implementation.

Replaces the Phase 1 stub with a fully functional adapter that wraps the same
Azure OpenAI HTTP call shape used by today's _call_azure_openai, plus typed-error
mapping, a structured logging hook, and the classify_with_tool prompt-based JSON
path required by ADP-02.

Key differences vs the old _call_azure_openai:
  (a) Typed errors raised at the HTTP boundary (ERR-02).
  (b) max_tokens is a per-call kwarg — was hardcoded 500/1000 in two duplicated places.
  (c) One structured log event per complete() call (OBS-02).
"""
from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlparse

import requests

from src.llm.base import LLMClient
from src.llm.config import load_settings
from src.llm.errors import (
    LLMAuthError,
    LLMConfigError,
    LLMError,
    LLMSchemaError,
    LLMTimeoutError,
    LLMTransientError,
)
from src.llm.types import ToolCall, ToolSchema
from src.utils import logger


def _extract_model_from_endpoint(endpoint: str) -> str:
    """Extract Azure deployment name (proxy for 'model') from the endpoint URL.

    Azure endpoints look like:
        https://xxx.openai.azure.com/openai/deployments/<deployment>/chat/completions

    Returns the deployment name, or 'unknown' if the URL doesn't fit that shape.
    Called once at adapter construction; cached on the instance as self._model.
    """
    try:
        parts = urlparse(endpoint).path.split("/")
        idx = parts.index("deployments")
        return parts[idx + 1]
    except (ValueError, IndexError):
        return "unknown"


def _log_llm_call(extra: dict) -> None:
    """Emit one structured log event per LLM call (OBS-02).

    The 'msg' is the fixed tag 'llm_call'; all structured fields live in extra.
    The existing snow_query logger uses a plain-text formatter, so the structured
    fields are not visible in default console output — but they are accessible
    to any downstream handler (e.g. a JSON formatter could be added later in
    setup_logging() without touching this code).

    Phase 3's AnthropicMGTIClient copies this function verbatim into
    src/llm/anthropic_mgti.py. If both adapters are ever unified, extract here.
    """
    logger.info("llm_call", extra=extra)


class AzureOpenAIClient(LLMClient):
    """Real Azure OpenAI adapter (Phase 2).

    Wraps the same HTTP call shape as the old _call_azure_openai. The only
    differences are: (a) typed errors at the boundary, (b) max_tokens is a
    per-call kwarg (was hardcoded 500/1000 in two duplicated places), (c) one
    structured log event per call.
    """

    def __init__(self) -> None:
        # No-op pattern preserved from Phase 1: construction must NOT raise so
        # the factory cache can store the instance. Missing config is caught at
        # HTTP time in complete() with provider-specific remediation text.
        settings = load_settings()
        self._endpoint: str = settings.azure_endpoint
        self._api_key: str = settings.azure_api_key
        self._api_version: str = settings.azure_api_version
        self._model: str = _extract_model_from_endpoint(self._endpoint)

    def __repr__(self) -> str:
        # OBS-03: never include self._api_key in repr.
        return "AzureOpenAIClient()"

    def complete(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 500,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> str:
        """Send a chat-completion request and return the assistant text.

        Returns the raw content string with NO .strip() — call sites already
        strip; double-strip is idempotent but not byte-identical to the old path
        (Pitfall 1 from RESEARCH.md).

        Raises:
            LLMConfigError: Missing AZURE_OPENAI_API_KEY or AZURE_OPENAI_ENDPOINT
                with provider-specific remediation text embedded in the message
                (RESEARCH.md OQ-1: Phase-3-clean path so the compat layer can
                pass str(e) through as QueryError.message without hardcoding
                Azure text in _compat.py).
            LLMAuthError: HTTP 401 or 403.
            LLMTransientError: HTTP 429 or 5xx, or connection-level errors.
            LLMTimeoutError: requests.Timeout.
            LLMError: Any other HTTP error not covered above.
        """
        # Pre-flight config check — embed provider-specific remediation in the
        # LLMConfigError message so the error translation seam (Plan 02) can pass
        # str(e) through as QueryError.message without hardcoding Azure text in
        # the compat layer (RESEARCH.md OQ-1: Phase-3-clean path).
        if not self._api_key:
            raise LLMConfigError(
                "Azure OpenAI API key not configured. "
                "Set the AZURE_OPENAI_API_KEY environment variable.",
                provider="azure_openai",
            )
        if not self._endpoint:
            raise LLMConfigError(
                "Azure OpenAI endpoint not configured. "
                "Set the AZURE_OPENAI_ENDPOINT environment variable.",
                provider="azure_openai",
            )

        headers = {
            "Content-Type": "application/json",
            "api-key": self._api_key,
        }
        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        t0 = time.monotonic()
        extra: dict = {
            "llm_provider": "azure_openai",
            "llm_model": self._model,
            "llm_latency_ms": 0,
            "llm_outcome": "error",  # overwritten on success
            "llm_error_type": None,
            "llm_prompt_tokens": None,
            "llm_completion_tokens": None,
            "llm_correlation_id": None,  # Azure has no correlation ID; Phase 3 populates this
        }
        try:
            response = requests.post(
                f"{self._endpoint}?api-version={self._api_version}",
                headers=headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {}) or {}
            extra["llm_prompt_tokens"] = usage.get("prompt_tokens")
            extra["llm_completion_tokens"] = usage.get("completion_tokens")
            extra["llm_outcome"] = "success"
            return text  # NO .strip() — call sites already strip; double-strip is idempotent but is not byte-identical to the old path

        except requests.exceptions.Timeout as e:
            extra["llm_error_type"] = "LLMTimeoutError"
            raise LLMTimeoutError(
                f"Azure OpenAI request timed out: {e}",
                provider="azure_openai",
            ) from e

        except requests.exceptions.HTTPError as e:
            status = getattr(e.response, "status_code", None)
            extra["llm_error_type"] = (
                "LLMAuthError" if status in (401, 403)
                else "LLMTransientError" if status == 429 or (status is not None and 500 <= status < 600)
                else "LLMError"
            )
            if status in (401, 403):
                raise LLMAuthError(
                    f"Azure OpenAI authentication failed (HTTP {status}): {e}",
                    provider="azure_openai",
                    status_code=status,
                ) from e
            if status == 429 or (status is not None and 500 <= status < 600):
                raise LLMTransientError(
                    f"Azure OpenAI transient failure (HTTP {status}): {e}",
                    provider="azure_openai",
                    status_code=status,
                ) from e
            # Any other HTTP error falls through to the generic LLMError
            raise LLMError(
                f"Azure OpenAI HTTP error (HTTP {status}): {e}",
                provider="azure_openai",
                status_code=status,
            ) from e

        except requests.exceptions.RequestException as e:
            # Connection errors, DNS, etc. — treat as transient.
            extra["llm_error_type"] = "LLMTransientError"
            raise LLMTransientError(
                f"Azure OpenAI request failed: {e}",
                provider="azure_openai",
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
        """Prompt-based JSON classification for Azure (ADP-02).

        Phase 4 reserves provider-side strict-tools for the Anthropic adapter
        only. The Azure path stays on prompt + JSON parse to preserve existing
        behavior; this keeps the parity gate scoped to complete() alone.

        Builds a system-prompt addendum instructing the model to respond as
        JSON matching tool.input_schema, calls complete(), strips markdown
        code fences if present, json.loads(), validates via jsonschema, and
        returns a ToolCall.

        Raises:
            LLMSchemaError: response was not valid JSON, or did not match
                tool.input_schema.
        """
        import json

        import jsonschema

        # Append a strict JSON-mode instruction as a system message. Existing
        # CLASSIFICATION_PROMPT in query_router.py already instructs the model
        # to "Respond with JSON" — this is the same pattern, generalized.
        enriched = list(messages) + [
            {
                "role": "system",
                "content": (
                    f"You are calling the tool `{tool.name}`. "
                    f"Respond ONLY with a JSON object matching this schema:\n"
                    f"{json.dumps(tool.input_schema)}\n"
                    f"Do not include markdown code fences or commentary."
                ),
            }
        ]
        raw = self.complete(enriched, **kwargs)

        # Strip markdown code fences if the model included them anyway.
        content = raw.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            raise LLMSchemaError(
                f"Azure OpenAI did not return valid JSON for tool {tool.name!r}: {e}",
                provider="azure_openai",
            ) from e

        try:
            jsonschema.validate(parsed, tool.input_schema)
        except jsonschema.ValidationError as e:
            raise LLMSchemaError(
                f"Azure OpenAI tool response failed schema validation for {tool.name!r}: {e.message}",
                provider="azure_openai",
            ) from e

        return ToolCall(
            tool_name=tool_name,
            input=parsed,
            raw_response={"content": raw},
        )
