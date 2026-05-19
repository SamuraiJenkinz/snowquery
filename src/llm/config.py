"""LLM configuration: settings dataclass + per-provider validation (CFG-01, CFG-03, CFG-05).

This module is the single source of truth for which environment variables
each provider requires. Phase 3 extends the Anthropic field set; Phase 5
adds the UI cache-key fields. The top-level `config.py` keeps DB/embedding
config; this module owns LLM-only config.

NOTE: This module does NOT call load_dotenv(). The top-level `config.py`
already calls `load_dotenv()` at import time; we just read `os.environ`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from src.llm.errors import LLMConfigError

# Default provider when neither explicit kwarg nor session state specifies one.
# Locked: must default to azure_openai so existing deployments are byte-identical (CFG-05).
DEFAULT_PROVIDER = "azure_openai"


@dataclass(frozen=True, slots=True)
class LLMSettings:
    """All LLM provider config in one immutable bag.

    `api_key` fields are excluded from repr to satisfy OBS-03 — they will
    not appear in logs that format the Settings object, in tracebacks that
    include locals, or in REPL inspection.
    """
    # Default provider
    provider_default: str = DEFAULT_PROVIDER

    # Azure OpenAI
    azure_endpoint: str = ""
    azure_api_key: str = field(default="", repr=False)
    azure_api_version: str = "2023-05-15"

    # Anthropic MGTI (real values consumed in Phase 3; declared now so the
    # schema is stable and Phase 3 doesn't have to touch this dataclass)
    anthropic_base_url: str = ""
    anthropic_api_key: str = field(default="", repr=False)
    anthropic_model: str = ""
    anthropic_version: str = "bedrock-2023-05-31"
    anthropic_max_tokens: int = 1024
    anthropic_temperature: float = 0.0
    anthropic_timeout_s: int = 30
    anthropic_tools_supported: bool = True


# Per-provider required env vars (CFG-03: validate_config raises with FULL list,
# not fail-on-first).
_REQUIRED_VARS: dict[str, tuple[str, ...]] = {
    "azure_openai": ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"),
    # API_VERSION has a usable default per RESEARCH.md ("2023-05-15") — OPTIONAL.
    "anthropic_mgti": (
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL",
    ),
    # Anthropic optional vars (ANTHROPIC_VERSION, ANTHROPIC_MAX_TOKENS, etc.)
    # have documented defaults in LLMSettings and are NOT required for validation.
}


def load_settings() -> LLMSettings:
    """Read os.environ and build an LLMSettings.

    Pure read; no side effects. Callers that want load_dotenv() must invoke
    it before calling this (the project's top-level config.py already does).
    """
    def _bool(name: str, default: bool) -> bool:
        v = os.getenv(name)
        if v is None:
            return default
        return v.strip().lower() not in ("0", "false", "no", "off", "")

    def _int(name: str, default: int) -> int:
        v = os.getenv(name)
        if not v:
            return default
        try:
            return int(v)
        except ValueError:
            return default

    def _float(name: str, default: float) -> float:
        v = os.getenv(name)
        if not v:
            return default
        try:
            return float(v)
        except ValueError:
            return default

    return LLMSettings(
        provider_default=os.getenv("LLM_PROVIDER_DEFAULT", DEFAULT_PROVIDER),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        azure_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
        azure_api_version=os.getenv("API_VERSION", "2023-05-15"),
        anthropic_base_url=os.getenv("ANTHROPIC_BASE_URL", ""),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", ""),
        anthropic_version=os.getenv("ANTHROPIC_VERSION", "bedrock-2023-05-31"),
        anthropic_max_tokens=_int("ANTHROPIC_MAX_TOKENS", 1024),
        anthropic_temperature=_float("ANTHROPIC_TEMPERATURE", 0.0),
        anthropic_timeout_s=_int("ANTHROPIC_TIMEOUT_S", 30),
        anthropic_tools_supported=_bool("ANTHROPIC_TOOLS_SUPPORTED", True),
    )


def validate_config(provider: str) -> None:
    """Verify all required env vars for `provider` are set.

    Collects ALL missing vars before raising (not fail-on-first) so the
    operator sees the full list in one message — CFG-03 + success criterion #4.

    Raises:
        LLMConfigError: if `provider` is unknown OR any required var is missing/empty.
    """
    if provider not in _REQUIRED_VARS:
        raise LLMConfigError(
            f"Unknown provider: {provider!r}. Known providers: "
            f"{sorted(_REQUIRED_VARS)}",
            provider=provider,
        )

    missing = [name for name in _REQUIRED_VARS[provider] if not os.getenv(name)]
    if missing:
        raise LLMConfigError(
            f"Missing required env vars for {provider}: " + ", ".join(missing),
            provider=provider,
        )
