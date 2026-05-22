"""snow_query LLM abstraction package.

Public API:
    - LLMClient: abstract base class
    - get_llm(provider): factory returning a cached LLMClient instance
    - LLMError + 6 typed subclasses
    - ToolSchema, ToolCall, ClassificationResultV1, IntentResult dataclasses
    - LLMSettings, load_settings, missing_vars, validate_config

Resolution order for get_llm(provider=None):
    1. explicit kwarg (provider="...")
    2. Streamlit session_state["llm_provider"] (if running under Streamlit)
    3. LLM_PROVIDER_DEFAULT env var
    4. fallback "azure_openai" (DEFAULT_PROVIDER)

Phase 5 cache contract: @st.cache_resource keyed on the 4-arg tuple
    (provider, base_url, model, api_key_fingerprint)
so switching ANY of these four re-resolves a fresh adapter instance.
Outside a Streamlit session the decorator falls back to a no-op pass-through
(see _cache_resource below) so get_llm() keeps working in pytest / python -c.
"""
from __future__ import annotations

import hashlib
import importlib
import os
from typing import TYPE_CHECKING

from src.llm.base import LLMClient
from src.llm.config import (
    DEFAULT_PROVIDER,
    LLMSettings,
    load_settings,
    missing_vars,
    validate_config,
)
from src.llm.errors import (
    LLMAuthError,
    LLMConfigError,
    LLMError,
    LLMGuardrailError,
    LLMSchemaError,
    LLMTimeoutError,
    LLMTransientError,
)
from src.llm.types import (
    ClassificationResultV1,
    IntentResult,
    ToolCall,
    ToolSchema,
)

# Lazy string-based imports avoid the circular dep that would arise if
# __init__.py imported the adapter modules at module-load time (the adapter
# modules import LLMClient from src.llm.base, which is fine, but importing
# them eagerly here would also import their future Phase 2/3 dependencies
# — requests, etc. — at package-import time). String-based lazy import
# defers that cost until get_llm() actually needs the class.
_REGISTRY: dict[str, str] = {
    "azure_openai": "src.llm.azure_openai:AzureOpenAIClient",
    "anthropic_mgti": "src.llm.anthropic_mgti:AnthropicMGTIClient",
}


# Streamlit cache_resource decorator with no-op fallback for non-Streamlit
# contexts (pytest, `python -c`, scripts/smoke_llm.py outside a session).
# In real Streamlit, `@_cache_resource` IS `@st.cache_resource` and caches
# the adapter instance keyed on the function's positional args. In the
# fallback, the decorator is a pass-through — each call builds a fresh
# instance, which is fine because tests already isolate per-test via the
# autouse fixture that calls _get_llm_cached.clear() defensively.
try:  # pragma: no cover — exercised live under Streamlit
    import streamlit as st
    _cache_resource = st.cache_resource
except Exception:
    def _cache_resource(func=None, **kwargs):
        """No-op cache_resource for non-Streamlit contexts.

        The wrapped function is returned untouched — no caching, no .clear()
        attribute. Tests defend against the missing .clear() via
        `getattr(..., 'clear', None) + callable(...)`.
        """
        if func is None:
            return lambda f: f
        return func


def _import_class(dotted: str) -> type[LLMClient]:
    """Resolve 'module.path:ClassName' to the actual class."""
    module_path, _, class_name = dotted.partition(":")
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def _fingerprint(api_key: str) -> str:
    """One-way 8-hex-char SHA-256 of the API key for cache-key inclusion.

    Empty key returns "" (the unconfigured-provider cache slot, distinct
    from any real key). Non-empty key returns the first 8 hex characters
    of the SHA-256 digest — sufficient to detect key rotation (32 bits of
    entropy, ~4 billion-way uniqueness), cryptographically infeasible to
    reverse.

    RESEARCH.md Pitfall 1: NEVER use a substring of the raw key (that
    leaks key material). NEVER put the raw key in the @st.cache_resource
    argument list (Streamlit may render arg values in debug output and
    error messages).
    """
    if not api_key:
        return ""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:8]


def _resolve_provider(explicit: str | None) -> str:
    """Resolve provider per the documented order: kwarg > session > env > default.

    Streamlit session_state access is wrapped in try/except Exception because
    `st.session_state` raises outside a Streamlit session (e.g. during pytest
    or `python -c "..."` checks). See RESEARCH.md "Factory + Cache" section.
    """
    if explicit is not None:
        return explicit
    try:  # pragma: no cover — exercised live in Phase 5 UI work
        import streamlit as st
        provider = st.session_state.get("llm_provider")
        if provider:
            return provider
    except Exception:
        pass
    return os.environ.get("LLM_PROVIDER_DEFAULT", DEFAULT_PROVIDER)


@_cache_resource
def _get_llm_cached(
    provider: str, base_url: str, model: str, api_key_fingerprint: str
) -> LLMClient:
    """Cached adapter resolver — @st.cache_resource keyed on the 4-arg tuple.

    Called by get_llm() with pre-derived cache-key inputs. The cache key is
    (provider, base_url, model, api_key_fingerprint) per ROADMAP SC #2;
    switching ANY of these four re-resolves a fresh adapter instance.

    Args (all positional, all hashable strings — Streamlit cache-key requirement):
        provider: One of _REGISTRY keys.
        base_url: For Azure, the endpoint URL; for Anthropic, the proxy base URL.
        model: Model identifier (Azure deployment name or Anthropic model id).
        api_key_fingerprint: 8-hex-char SHA-256 of the raw API key, or "" if unset.
            NEVER the raw key itself (RESEARCH.md Pitfall 1).

    Returns:
        Cached LLMClient instance for this exact (provider, base_url, model, fingerprint)
        tuple. The cache survives across reruns inside a Streamlit session and is
        cleared automatically when any of the 4 args change.

    Raises:
        LLMConfigError: if `provider` is not in _REGISTRY.
    """
    if provider not in _REGISTRY:
        raise LLMConfigError(
            f"Unknown provider: {provider!r}. Known providers: "
            f"{sorted(_REGISTRY)}",
            provider=provider,
        )
    cls = _import_class(_REGISTRY[provider])
    return cls()


def get_llm(provider: str | None = None) -> LLMClient:
    """Return a cached LLMClient for the resolved provider (ABS-04).

    Resolution order (preserved from Phase 1):
        1. explicit kwarg
        2. Streamlit session_state["llm_provider"] (try/except — safe outside Streamlit)
        3. LLM_PROVIDER_DEFAULT env var
        4. fallback "azure_openai" (DEFAULT_PROVIDER)

    Cache: @_cache_resource on _get_llm_cached, keyed on the 4-arg tuple
    (provider, base_url, model, api_key_fingerprint) per ROADMAP Phase 5 SC #2.
    Cache survives across Streamlit reruns and re-resolves on any key-tuple change.

    Outside a Streamlit session (e.g. pytest, python -c), the @_cache_resource
    decorator falls back to a no-op pass-through — each call builds a fresh
    instance. Tests isolate via _get_llm_cached.clear() in their autouse fixtures
    (defended by getattr+callable for the no-Streamlit fallback).

    Raises:
        LLMConfigError: if the resolved provider is not in _REGISTRY.
    """
    resolved = _resolve_provider(provider)

    # Compute cache-key inputs BEFORE the cached call (the tuple IS the key).
    # We cannot read base_url/model from a constructed instance because the
    # instance doesn't exist yet — that's the whole point of the cache.
    settings = load_settings()
    if resolved == "azure_openai":
        # _extract_model_from_endpoint is module-level in azure_openai.py
        # — importable from outside per Phase 5 Plan 05-01 decision §5.
        from src.llm.azure_openai import _extract_model_from_endpoint
        base_url = settings.azure_endpoint
        model = _extract_model_from_endpoint(settings.azure_endpoint)
        raw_key = settings.azure_api_key
    elif resolved == "anthropic_mgti":
        base_url = settings.anthropic_base_url
        model = settings.anthropic_model
        raw_key = settings.anthropic_api_key
    else:
        # Unknown provider — defer to _get_llm_cached, which raises with the
        # known-providers list (preserves Phase 1 error contract verbatim).
        return _get_llm_cached(resolved, "", "", "")

    fingerprint = _fingerprint(raw_key)
    return _get_llm_cached(resolved, base_url, model, fingerprint)


__all__ = [
    # Interface
    "LLMClient",
    # Factory
    "get_llm",
    # Config
    "LLMSettings",
    "load_settings",
    "missing_vars",
    "validate_config",
    "DEFAULT_PROVIDER",
    # Errors
    "LLMError",
    "LLMAuthError",
    "LLMTransientError",
    "LLMGuardrailError",
    "LLMSchemaError",
    "LLMTimeoutError",
    "LLMConfigError",
    # Types
    "ToolSchema",
    "ToolCall",
    "ClassificationResultV1",
    "IntentResult",
]
