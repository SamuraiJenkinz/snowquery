"""Typed errors raised at the LLM adapter boundary.

All adapter exceptions inherit from LLMError so call sites can catch the
whole family with `except LLMError`. Subclasses are flat (not grouped) so
call sites can also catch specific kinds by name (e.g. `except LLMAuthError`).

Only LLMConfigError is raised in Phase 1; the other classes are wired in
Phases 2-4. Defining them now prevents revisiting the seam.
"""
from __future__ import annotations


class LLMError(Exception):
    """Base class for all LLM adapter errors."""

    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        status_code: int | None = None,
        correlation_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code
        self.correlation_id = correlation_id


class LLMAuthError(LLMError):
    """HTTP 401/403 from the LLM provider."""


class LLMTransientError(LLMError):
    """HTTP 429 or 5xx — provider-side transient failure."""


class LLMGuardrailError(LLMError):
    """Provider returned a policy/guardrail intervention (not retryable)."""


class LLMSchemaError(LLMError):
    """Provider response did not match the expected/declared schema."""


class LLMTimeoutError(LLMError):
    """requests.Timeout or equivalent transport-level timeout."""


class LLMConfigError(LLMError):
    """Missing or invalid configuration (env vars, model name, etc.)."""
