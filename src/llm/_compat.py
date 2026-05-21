"""LLMError -> QueryError translation seam (success criterion #3, ERR-04).

This module is the SINGLE place in the codebase that maps the typed
LLMError family back into the legacy QueryError that the existing UI
already knows how to render. Call sites consume this via:

    from src.llm import get_llm
    from src.llm._compat import llm_to_query_error

    client = get_llm()
    with llm_to_query_error():
        content = client.complete(messages, max_tokens=500).strip()

Design notes (locked decisions from CONTEXT.md / RESEARCH.md):

  * The translation table appears here EXACTLY ONCE -- if Phase 3 needs
    new behavior for LLMGuardrailError or provider-specific remediation,
    it edits this file and only this file.

  * LLMConfigError is translated by passing str(e) through as the
    QueryError.message. The adapter (Phase 2 AzureOpenAIClient and
    Phase 3 AnthropicMGTIClient) embeds provider-specific remediation
    text in the LLMConfigError message at raise time. This keeps the
    compat layer provider-agnostic -- adding Anthropic does NOT require
    editing this file (RESEARCH.md "Phase 3 Compatibility Check").

  * LLMAuthError / LLMTimeoutError / LLMTransientError / catch-all
    LLMError dispatch on e.provider so Anthropic errors get
    Anthropic-named remediation. The Azure path (and unknown-provider
    path) preserves the exact Phase 2 wording byte-identically. See the
    if-branches below.

  * All raise statements use 'from e' to preserve the underlying
    LLMError as __cause__ for debugging (PEP 3134).

  * The catch-all 'except LLMError' branch ensures NO LLMError subclass
    can leak past this context manager -- even future ones added in
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
        # (the Phase 2 acceptance gate at tests/test_phase2_parity.py
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
