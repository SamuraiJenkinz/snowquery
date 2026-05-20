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

  * LLMAuthError uses the historic 'Set the AZURE_OPENAI_API_KEY ...'
    remediation text to preserve byte-identical user-visible behavior
    today. Phase 3 may revisit this branch when the Anthropic adapter
    lands -- at that point the branch can dispatch on e.provider.

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
        # Provider embeds remediation text in the LLMConfigError message
        # at raise time (see AzureOpenAIClient.complete pre-flight check).
        # Pass str(e) through as the QueryError.message so the user sees
        # the same actionable text today and after Phase 3 adds Anthropic.
        raise QueryError(str(e), "Check your .env configuration.") from e
    except LLMAuthError as e:
        # HTTP 401/403 from the provider -- key was present but invalid.
        # The historic remediation text in _call_azure_openai (today) is:
        #   QueryError("Azure OpenAI API key not configured",
        #              "Set the AZURE_OPENAI_API_KEY environment variable.")
        # which is the same user-visible text we want here (the old code
        # didn't actually distinguish missing-key vs invalid-key at the
        # HTTP layer -- RequestException covered both).
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
