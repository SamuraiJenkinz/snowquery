"""snow_query LLM abstraction package.

Public API:
    - LLMClient: abstract base class
    - get_llm(provider): factory returning a cached LLMClient instance
    - LLMError + 6 typed subclasses
    - ToolSchema, ToolCall, ClassificationResultV1, IntentResult dataclasses
    - LLMSettings, load_settings, validate_config

Resolution order for get_llm(provider=None):
    1. explicit kwarg (provider="...")
    2. Streamlit session_state["llm_provider"] (if running under Streamlit)
    3. LLM_PROVIDER_DEFAULT env var
    4. fallback "azure_openai" (DEFAULT_PROVIDER)

Cache key in Phase 1 is the provider string only (no api_key fingerprint
yet — that lands in Phase 5 if mid-session key reload is needed).
"""
from __future__ import annotations

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

# Module-level cache. Plan 03 verifies idempotence; Phase 5 may wrap this
# with @st.cache_resource and clear() this dict before the decorator takes over.
_cache: dict[str, LLMClient] = {}


def _import_class(dotted: str) -> type[LLMClient]:
    """Resolve 'module.path:ClassName' to the actual class."""
    module_path, _, class_name = dotted.partition(":")
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


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


def get_llm(provider: str | None = None) -> LLMClient:
    """Return a cached LLMClient for the resolved provider (ABS-04).

    Args:
        provider: Optional explicit provider name. If None, resolution falls
            through to Streamlit session state, then LLM_PROVIDER_DEFAULT,
            then "azure_openai".

    Returns:
        Cached LLMClient instance. Subsequent calls with the same resolved
        provider return the SAME instance.

    Raises:
        LLMConfigError: if the resolved provider is not in _REGISTRY.
    """
    resolved = _resolve_provider(provider)
    if resolved in _cache:
        return _cache[resolved]
    if resolved not in _REGISTRY:
        raise LLMConfigError(
            f"Unknown provider: {resolved!r}. Known providers: "
            f"{sorted(_REGISTRY)}",
            provider=resolved,
        )
    cls = _import_class(_REGISTRY[resolved])
    instance = cls()
    _cache[resolved] = instance
    return instance


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
