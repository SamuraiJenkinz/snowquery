---
phase: 01-abstraction-seam
plan: 02
type: execute
wave: 2
depends_on: ["01-01"]
files_modified:
  - src/llm/config.py
  - src/llm/__init__.py
  - src/llm/azure_openai.py
  - src/llm/anthropic_mgti.py
  - requirements.txt
autonomous: true

must_haves:
  truths:
    - "get_llm(provider) returns a cached LLMClient, resolving provider per explicit-kwarg > st.session_state > LLM_PROVIDER_DEFAULT env (default azure_openai) (success criterion #3, ABS-04, CFG-05)"
    - "validate_config(provider) raises LLMConfigError listing EVERY missing required env var for that provider (success criterion #4, CFG-03)"
    - "LLMSettings dataclass has Azure AND Anthropic fields all defined, with api_key fields excluded from repr (CFG-01, OBS-03)"
    - "Adapter stub files exist and raise NotImplementedError on instantiation/call so the factory can register them without circular imports (ABS-01 final)"
    - "jsonschema>=4.26.0,<5 is listed in requirements.txt (CFG-06)"
  artifacts:
    - path: "src/llm/config.py"
      provides: "LLMSettings dataclass (Azure + Anthropic fields, api_keys with repr=False) + validate_config(provider)"
      contains: "def validate_config"
    - path: "src/llm/__init__.py"
      provides: "get_llm factory with module-level _cache + lazy-import _REGISTRY"
      contains: "def get_llm"
    - path: "src/llm/azure_openai.py"
      provides: "AzureOpenAIClient stub — class extending LLMClient, methods raise NotImplementedError (real impl is Phase 2)"
      contains: "class AzureOpenAIClient(LLMClient)"
    - path: "src/llm/anthropic_mgti.py"
      provides: "AnthropicMGTIClient stub — class extending LLMClient, methods raise NotImplementedError (real impl is Phase 3)"
      contains: "class AnthropicMGTIClient(LLMClient)"
    - path: "requirements.txt"
      provides: "jsonschema dependency"
      contains: "jsonschema"
  key_links:
    - from: "src/llm/__init__.py"
      to: "src/llm/azure_openai.py and src/llm/anthropic_mgti.py"
      via: "lazy string-based import inside get_llm via importlib.import_module"
      pattern: "importlib\\.import_module"
    - from: "src/llm/__init__.py"
      to: "streamlit.session_state"
      via: "wrapped in try/except Exception for pytest/CLI safety"
      pattern: "try:\\s*\\n\\s*import streamlit"
    - from: "src/llm/config.py"
      to: "os.environ"
      via: "validate_config reads required vars per provider"
      pattern: "os\\.(getenv|environ)"
---

<objective>
Wire the package's runtime entry points: the configuration layer (`LLMSettings` + `validate_config`), the `get_llm` factory with module-level cache, and the two adapter stub files that the factory registers via lazy imports. Add `jsonschema` to `requirements.txt`.

Purpose: Plan 01 built the static seam (types, errors, ABC). This plan makes the seam *usable* — call sites in future phases will type `from src.llm import get_llm; client = get_llm()` and get a real instance. No call sites change in this plan either; Phase 2 wires `app.py` and the call sites.

Output: 5 files touched (4 new, 1 modified) that together complete the Phase 1 deliverable.
</objective>

<execution_context>
@C:\Users\taylo\.claude\get-shit-done\workflows\execute-plan.md
@C:\Users\taylo\.claude\get-shit-done\templates\summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/01-abstraction-seam/01-CONTEXT.md
@.planning/phases/01-abstraction-seam/01-RESEARCH.md
@.planning/phases/01-abstraction-seam/01-01-SUMMARY.md

# Plan 01 outputs we build on
@src/llm/base.py
@src/llm/errors.py
@src/llm/types.py

# Existing project files for style reference (READ-ONLY)
@config.py
@requirements.txt
@src/utils.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create src/llm/config.py with LLMSettings + validate_config</name>
  <files>src/llm/config.py</files>
  <action>
Create `src/llm/config.py` housing:
1. `LLMSettings` — a frozen dataclass holding ALL provider config fields (Azure today + Anthropic for Phase 3) read from environment variables. `api_key` fields use `field(repr=False)` so OBS-03 is enforced by construction.
2. `_REQUIRED_VARS` — a per-provider dict listing the env vars that `validate_config` must require.
3. `validate_config(provider)` — collects ALL missing vars (NOT fail-on-first per locked decision in CONTEXT.md), then raises `LLMConfigError` with the full list.
4. `load_settings()` — convenience factory that reads `os.environ` and returns an `LLMSettings`. No side-effects (no `load_dotenv()` here; `app.py` and top-level `config.py` already call it — we just read `os.environ`).

Exact shape:

```python
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
```

Requirements:
- `LLMSettings` MUST be `frozen=True, slots=True`.
- `azure_api_key` and `anthropic_api_key` MUST use `field(default="", repr=False)`.
- `validate_config` MUST collect all missing vars before raising (NOT fail-on-first).
- The error message format is exactly `"Missing required env vars for {provider}: VAR1, VAR2, ..."` per locked decision in CONTEXT.md.
- Do NOT call `load_dotenv()` here.
- Do NOT modify the top-level `config.py` (LOCKED).
  </action>
  <verify>
Run from project root (after ensuring AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY are temporarily unset for the test):
```
python -c "
import os
# Strip Azure vars to force validation failure
for k in ('AZURE_OPENAI_ENDPOINT', 'AZURE_OPENAI_API_KEY'):
    os.environ.pop(k, None)
from src.llm.config import LLMSettings, load_settings, validate_config, DEFAULT_PROVIDER
from src.llm.errors import LLMConfigError

# CFG-05: default is azure_openai
assert DEFAULT_PROVIDER == 'azure_openai'

# OBS-03: api_key never appears in repr
s = LLMSettings(azure_api_key='SECRET_DO_NOT_LEAK_123', anthropic_api_key='SECRET_DO_NOT_LEAK_456')
r = repr(s)
assert 'SECRET_DO_NOT_LEAK_123' not in r, f'azure_api_key leaked: {r}'
assert 'SECRET_DO_NOT_LEAK_456' not in r, f'anthropic_api_key leaked: {r}'

# CFG-03 / success criterion #4: validate_config lists ALL missing vars
try:
    validate_config('azure_openai')
    raise AssertionError('expected LLMConfigError')
except LLMConfigError as e:
    msg = str(e)
    assert 'AZURE_OPENAI_ENDPOINT' in msg and 'AZURE_OPENAI_API_KEY' in msg, f'missing vars not in message: {msg}'

# Unknown provider
try:
    validate_config('mystery_provider')
    raise AssertionError('expected LLMConfigError for unknown provider')
except LLMConfigError as e:
    assert 'mystery_provider' in str(e)

print('OK')
"
```
Must print `OK`.
  </verify>
  <done>
- `src/llm/config.py` exists with `LLMSettings`, `_REQUIRED_VARS`, `load_settings`, `validate_config`, `DEFAULT_PROVIDER`.
- `LLMSettings` is `frozen=True, slots=True`; `azure_api_key` and `anthropic_api_key` have `repr=False`.
- `validate_config("azure_openai")` with both vars missing raises `LLMConfigError` whose message contains BOTH `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY`.
- `validate_config("unknown_provider")` raises `LLMConfigError`.
- `repr(LLMSettings(azure_api_key="X"))` does NOT contain `"X"`.
- Top-level `config.py` is NOT modified.
- Satisfies CFG-01, CFG-03, CFG-05, OBS-03 (mechanism in place; verified by Plan 03).
  </done>
</task>

<task type="auto">
  <name>Task 2: Create adapter stubs (azure_openai.py, anthropic_mgti.py) and wire the factory into __init__.py</name>
  <files>src/llm/azure_openai.py, src/llm/anthropic_mgti.py, src/llm/__init__.py</files>
  <action>
This task does three things atomically because they form one logical unit (the factory registers the two stub classes via lazy import — if any one is missing, the other two are useless):

**File 1: `src/llm/azure_openai.py`** — stub that registers as `LLMClient` but raises `NotImplementedError` on every method. Phase 2 replaces this with the real implementation.

```python
"""Azure OpenAI adapter — Phase 1 stub.

Real implementation lands in Phase 2 (Azure Extraction + Parity Gate).
Existing here so src/llm/__init__.py's get_llm factory can register it
without a circular import.
"""
from __future__ import annotations

from typing import Any

from src.llm.base import LLMClient
from src.llm.types import ToolCall, ToolSchema


class AzureOpenAIClient(LLMClient):
    """Phase 1 stub. Real implementation in Phase 2."""

    def __init__(self) -> None:
        # No-op constructor; Phase 2 will read AZURE_* env vars via
        # src.llm.config.load_settings(). Construction must NOT raise in
        # Phase 1 so the factory cache can store the instance.
        pass

    def complete(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 500,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> str:
        raise NotImplementedError(
            "AzureOpenAIClient.complete is implemented in Phase 2"
        )

    def classify_with_tool(
        self,
        messages: list[dict],
        tool: ToolSchema,
        *,
        tool_name: str,
        **kwargs: Any,
    ) -> ToolCall:
        raise NotImplementedError(
            "AzureOpenAIClient.classify_with_tool is implemented in Phase 2"
        )
```

**File 2: `src/llm/anthropic_mgti.py`** — same stub pattern. Phase 3 replaces this with the real MGTI implementation.

```python
"""Anthropic MGTI adapter — Phase 1 stub.

Real implementation lands in Phase 3 (Anthropic MGTI Adapter), with strict-tools
wired in Phase 4. Existing here so src/llm/__init__.py's get_llm factory can
register it without a circular import.
"""
from __future__ import annotations

from typing import Any

from src.llm.base import LLMClient
from src.llm.types import ToolCall, ToolSchema


class AnthropicMGTIClient(LLMClient):
    """Phase 1 stub. Real implementation in Phase 3, tools in Phase 4."""

    def __init__(self) -> None:
        # No-op constructor; Phase 3 reads ANTHROPIC_* env vars via
        # src.llm.config.load_settings() and validates the model name
        # (must start with eu.anthropic.claude-). For Phase 1, construction
        # must NOT raise so the factory cache can store the instance.
        pass

    def complete(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 500,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> str:
        raise NotImplementedError(
            "AnthropicMGTIClient.complete is implemented in Phase 3"
        )

    def classify_with_tool(
        self,
        messages: list[dict],
        tool: ToolSchema,
        *,
        tool_name: str,
        **kwargs: Any,
    ) -> ToolCall:
        raise NotImplementedError(
            "AnthropicMGTIClient.classify_with_tool is implemented in Phase 4"
        )
```

**File 3: `src/llm/__init__.py`** — REPLACE the Plan-01 minimal version with the full factory. Keep all the existing re-exports (LLMClient, errors, types) AND add `get_llm`, `_resolve_provider`, `_REGISTRY`, `_cache`.

Read the current `src/llm/__init__.py` first (created in Plan 01 Task 3), then replace it with:

```python
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
```

Critical requirements:
- The `try/except Exception` wrapper around `st.session_state` access is REQUIRED per RESEARCH.md "Streamlit-safety issue" — it's the verified pattern for pytest/CLI compatibility. Do NOT use `hasattr(st, "session_state")` (insufficient).
- `_REGISTRY` uses `"module.path:ClassName"` string format with `importlib.import_module` lazy resolution — avoids circular imports between `__init__.py` and the adapter modules.
- Cache key in `_cache` is the resolved provider string ONLY (no fingerprinting — locked decision).
- The factory MUST NOT call `validate_config()` itself — that's an explicit call at the top of `app.py` (Phase 5 wiring), per locked decision in RESEARCH.md Open Question #1.
- DO NOT modify the top-level `config.py`, `app.py`, `src/query_router.py`, or `src/sql_generator.py` (LOCKED for Phase 1).
  </action>
  <verify>
Run from project root:
```
python -c "
import os
# Ensure LLM_PROVIDER_DEFAULT is unset to test the fallback path
os.environ.pop('LLM_PROVIDER_DEFAULT', None)
from src.llm import get_llm, LLMClient
from src.llm.errors import LLMConfigError

# ABS-04: get_llm returns LLMClient instance
c1 = get_llm('azure_openai')
assert isinstance(c1, LLMClient), f'not an LLMClient: {type(c1)}'

# Cached: same call returns SAME instance
c2 = get_llm('azure_openai')
assert c1 is c2, 'cache miss — get_llm did not return cached instance'

# CFG-05: default fallback is azure_openai
c3 = get_llm()  # no explicit, no env, no st — should resolve to azure_openai
assert c3 is c1, f'default resolution did not hit azure_openai cache: {c3} vs {c1}'

# Resolution order: env var overrides default
os.environ['LLM_PROVIDER_DEFAULT'] = 'anthropic_mgti'
c4 = get_llm()  # should now resolve anthropic_mgti
from src.llm.anthropic_mgti import AnthropicMGTIClient
assert isinstance(c4, AnthropicMGTIClient), f'env override failed: {type(c4)}'
os.environ.pop('LLM_PROVIDER_DEFAULT', None)

# Explicit kwarg beats env
os.environ['LLM_PROVIDER_DEFAULT'] = 'anthropic_mgti'
c5 = get_llm('azure_openai')
assert c5 is c1, 'explicit kwarg did not override env'
os.environ.pop('LLM_PROVIDER_DEFAULT', None)

# Unknown provider raises
try:
    get_llm('mystery')
    raise AssertionError('expected LLMConfigError')
except LLMConfigError as e:
    assert 'mystery' in str(e)

# Stubs raise NotImplementedError on method call (Phase 2/3 fill these in)
try:
    c1.complete([{'role': 'user', 'content': 'hi'}])
    raise AssertionError('expected NotImplementedError')
except NotImplementedError as e:
    assert 'Phase 2' in str(e), f'stub message did not mention Phase 2: {e}'

print('OK')
"
```
Must print `OK`. This verifies: (a) factory returns `LLMClient`, (b) cache works (same instance), (c) default fallback is `azure_openai` (CFG-05), (d) env var overrides default, (e) explicit kwarg overrides env (ABS-04 resolution order), (f) unknown provider raises `LLMConfigError`, (g) stubs raise `NotImplementedError` mentioning the phase they ship in.
  </verify>
  <done>
- `src/llm/azure_openai.py` exists with `AzureOpenAIClient(LLMClient)` whose methods raise `NotImplementedError` mentioning Phase 2.
- `src/llm/anthropic_mgti.py` exists with `AnthropicMGTIClient(LLMClient)` whose methods raise `NotImplementedError` mentioning Phase 3 (or Phase 4 for `classify_with_tool`).
- `src/llm/__init__.py` exports `get_llm`, `LLMClient`, `LLMSettings`, `load_settings`, `validate_config`, all 7 error classes, all 4 types.
- `get_llm("azure_openai")` returns an `AzureOpenAIClient` instance; second call returns the SAME instance.
- `get_llm()` with no env vars set defaults to `azure_openai` (CFG-05).
- `get_llm("unknown")` raises `LLMConfigError`.
- `_resolve_provider` wraps `streamlit` access in `try/except Exception` (verified by Plan 03 outside-Streamlit run).
- Files NOT modified: `src/query_router.py`, `src/sql_generator.py`, `app.py`, top-level `config.py`.
- Satisfies ABS-01 (full), ABS-04.
  </done>
</task>

<task type="auto">
  <name>Task 3: Add jsonschema dependency to requirements.txt</name>
  <files>requirements.txt</files>
  <action>
Add `jsonschema>=4.26.0,<5` to `requirements.txt`. Currently the file ends with the `transformers` line (line 14). Append a new section for LLM tool-schema validation.

Read the current file first, then append the new dependency. The exact addition (place after the `transformers>=4.51.0` line, before EOF):

```
# LLM tool schema validation (Phase 4 strict-tools defence-in-depth, TOOL-06)
jsonschema>=4.26.0,<5
```

Requirements:
- Use the version pin EXACTLY as specified: `jsonschema>=4.26.0,<5` (CFG-06).
- Add a comment explaining the phase context so future readers understand why it's there even though Phase 1 doesn't use it yet.
- Do NOT install the package as part of this task (installation is environment-side; the file change is the deliverable). The next operator running `pip install -r requirements.txt` will pick it up.
- Do NOT touch any other line in `requirements.txt`.
  </action>
  <verify>
Run from project root:
```
python -c "
content = open('requirements.txt').read()
assert 'jsonschema>=4.26.0,<5' in content, f'jsonschema pin missing or wrong: see requirements.txt'
# Sanity: file is still readable line-by-line as pip would parse it
lines = [l.strip() for l in content.splitlines() if l.strip() and not l.strip().startswith('#')]
assert any('jsonschema' in l for l in lines)
print('OK')
"
```
Must print `OK`. Also verify the existing dependencies are intact:
```
python -c "
content = open('requirements.txt').read()
for needed in ('streamlit', 'duckdb', 'pandas', 'python-dotenv', 'chromadb', 'sentence-transformers', 'requests', 'jsonschema'):
    assert needed in content, f'{needed} missing from requirements.txt'
print('all-present')
"
```
Must print `all-present`.
  </verify>
  <done>
- `requirements.txt` contains the exact line `jsonschema>=4.26.0,<5` (with no version typos).
- A short comment above it identifies the Phase 4 / TOOL-06 purpose.
- All pre-existing dependencies (streamlit, duckdb, pandas, python-dotenv, chromadb, sentence-transformers, requests, onnxruntime, altair, python-certifi-win32, torch, transformers) are untouched.
- Satisfies CFG-06.
  </done>
</task>

</tasks>

<verification>
After all three tasks, run from project root with all Azure/Anthropic env vars unset:

```
python -c "
import os
for k in list(os.environ):
    if k.startswith(('AZURE_OPENAI_', 'ANTHROPIC_', 'LLM_PROVIDER_')):
        del os.environ[k]

# 1. Package importable (success criterion #1, ABS-01 final)
from src.llm import (
    get_llm, LLMClient, LLMSettings, load_settings, validate_config,
    DEFAULT_PROVIDER, LLMError, LLMConfigError,
    ToolSchema, ToolCall, ClassificationResultV1, IntentResult,
)
from src.llm.azure_openai import AzureOpenAIClient
from src.llm.anthropic_mgti import AnthropicMGTIClient

# 2. CFG-05: default provider is azure_openai
assert DEFAULT_PROVIDER == 'azure_openai'

# 3. ABS-04: factory + cache + resolution order
c1 = get_llm()  # falls all the way through to azure_openai
assert isinstance(c1, AzureOpenAIClient)
c2 = get_llm('azure_openai')
assert c1 is c2  # cache hit

# 4. Success criterion #4 / CFG-03: validate_config lists ALL missing vars
try:
    validate_config('azure_openai')
    raise AssertionError('should have raised')
except LLMConfigError as e:
    m = str(e)
    assert 'AZURE_OPENAI_ENDPOINT' in m and 'AZURE_OPENAI_API_KEY' in m

try:
    validate_config('anthropic_mgti')
    raise AssertionError('should have raised')
except LLMConfigError as e:
    m = str(e)
    assert 'ANTHROPIC_BASE_URL' in m
    assert 'ANTHROPIC_API_KEY' in m
    assert 'ANTHROPIC_MODEL' in m

# 5. OBS-03 / Success criterion #5: api_key fields excluded from repr
s = LLMSettings(azure_api_key='LEAK_ME_1', anthropic_api_key='LEAK_ME_2')
assert 'LEAK_ME_1' not in repr(s)
assert 'LEAK_ME_2' not in repr(s)

# 6. CFG-06: jsonschema pin present
assert 'jsonschema>=4.26.0,<5' in open('requirements.txt').read()

print('PLAN 02 VERIFICATION OK')
"
```

Must print `PLAN 02 VERIFICATION OK`.
</verification>

<success_criteria>
- `src/llm/config.py`, `src/llm/azure_openai.py`, `src/llm/anthropic_mgti.py` all created.
- `src/llm/__init__.py` upgraded from Plan 01's minimal version to include the factory.
- `requirements.txt` modified to add `jsonschema>=4.26.0,<5`.
- `get_llm(provider=None)` resolves provider via kwarg > session_state > env > "azure_openai" and caches by provider string.
- `validate_config(provider)` raises `LLMConfigError` listing EVERY missing required env var (not fail-on-first).
- `LLMSettings` repr does NOT contain API key values (`field(repr=False)` mechanism).
- Adapter stubs raise `NotImplementedError` on method calls but instantiate cleanly.
- LOCKED files untouched: `app.py`, top-level `config.py`, `src/query_router.py`, `src/sql_generator.py`.

Maps to: Success criteria #3 (full), #4 (full), #5 (mechanism in place). Requirements ABS-01 (full), ABS-04, CFG-01, CFG-03, CFG-05, CFG-06, OBS-03.
</success_criteria>

<output>
After completion, create `.planning/phases/01-abstraction-seam/01-02-SUMMARY.md` documenting:
- 5 files touched (list with line counts)
- Confirmation that `get_llm` resolution order works (kwarg / env / default tested)
- Confirmation that `validate_config` lists ALL missing vars for both providers
- Confirmation that `repr(LLMSettings(...))` does not expose api_key values
- Confirmation that `jsonschema>=4.26.0,<5` is in `requirements.txt`
- Any deviations from RESEARCH.md (expect: none)
</output>
