---
phase: 01-abstraction-seam
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - src/llm/__init__.py
  - src/llm/base.py
  - src/llm/errors.py
  - src/llm/types.py
autonomous: true

must_haves:
  truths:
    - "src/llm/ is a real Python package importable from a REPL inside the project venv (success criterion #1, ABS-01)"
    - "LLMClient ABC enforces the two-method contract at construction time — subclasses missing complete or classify_with_tool raise TypeError on instantiation (success criterion #2, ABS-02)"
    - "All six LLM error classes exist as a flat hierarchy under LLMError (ERR-01)"
    - "ToolSchema, ToolCall, IntentResult, and ClassificationResultV1 are frozen+slots dataclasses available at the adapter boundary (ABS-03, ABS-05, TOOL-01)"
    - "ClassificationResultV1 does NOT contain chart_requested or chart_type fields (locked decision; supports TOOL-03 in Phase 4)"
  artifacts:
    - path: "src/llm/__init__.py"
      provides: "Package marker (factory wiring lands in Plan 02)"
      min_lines: 5
    - path: "src/llm/base.py"
      provides: "LLMClient abstract base class with @abstractmethod complete and classify_with_tool"
      contains: "class LLMClient(abc.ABC)"
    - path: "src/llm/errors.py"
      provides: "LLMError + 6 typed subclasses, all carrying provider/status_code/correlation_id kwargs"
      contains: "class LLMError(Exception)"
    - path: "src/llm/types.py"
      provides: "ToolSchema, ToolCall, IntentResult, ClassificationResultV1 dataclasses (frozen, slots)"
      contains: "ClassificationResultV1"
  key_links:
    - from: "src/llm/base.py"
      to: "src/llm/types.py"
      via: "ToolSchema and ToolCall type hints in classify_with_tool signature"
      pattern: "from src\\.llm\\.types import ToolSchema, ToolCall"
    - from: "src/llm/base.py"
      to: "abc.ABC"
      via: "LLMClient inheritance + @abstractmethod decorators"
      pattern: "@abstractmethod"
---

<objective>
Create the `src/llm/` package skeleton with the abstract `LLMClient` interface, the full error taxonomy, and the dataclass types that future adapters will exchange with call sites.

Purpose: Establish the stable seam — types, interface, errors — that Plan 02's factory and config wire together, and that Phases 2–4 plug adapters into. No call sites change; no behavior change ships.

Output: Four files in `src/llm/` (`__init__.py`, `base.py`, `errors.py`, `types.py`) all importable as a package, with the ABC contract enforced by `abc.ABC` and all six error classes defined ready for Phases 2–4 to raise.
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

# Existing files referenced for style/parity (READ-ONLY in this plan)
@src/utils.py
@src/query_router.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create errors.py with the full LLM error taxonomy</name>
  <files>src/llm/errors.py</files>
  <action>
Create `src/llm/errors.py` with the complete error hierarchy that Phases 1–4 will use. Define LLMError as the base, then six flat subclasses. Only `LLMConfigError` is raised in Phase 1; the rest exist now so Phase 3/4 doesn't have to revisit the seam (locked decision in CONTEXT.md).

Exact shape (from RESEARCH.md Recommended Shapes section 2):

```python
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
```

Requirements:
- Use `from __future__ import annotations` at the top (matches existing project style — `query_router.py:5`, `sql_generator.py:3`).
- Each subclass has a one-line docstring; no extra attributes beyond the inherited ones.
- Do NOT add `retryable: bool` (deferred per RESEARCH.md — no retry logic exists in Phase 1).
- Do NOT include code that imports or logs anything containing keys; this is a pure class-definition module.
- No `__all__` needed.
  </action>
  <verify>
Run from project root:
```
python -c "from src.llm.errors import LLMError, LLMAuthError, LLMTransientError, LLMGuardrailError, LLMSchemaError, LLMTimeoutError, LLMConfigError; e = LLMConfigError('msg', provider='azure_openai', status_code=500, correlation_id='abc'); assert isinstance(e, LLMError); assert e.provider == 'azure_openai'; assert e.status_code == 500; assert e.correlation_id == 'abc'; print('OK')"
```
Must print `OK`.
  </verify>
  <done>
- `src/llm/errors.py` exists and imports cleanly.
- All 7 classes (`LLMError`, `LLMAuthError`, `LLMTransientError`, `LLMGuardrailError`, `LLMSchemaError`, `LLMTimeoutError`, `LLMConfigError`) are importable.
- `LLMConfigError(...)` instances carry `provider`, `status_code`, `correlation_id` attributes set from kwargs.
- All subclasses are direct children of `LLMError` (flat hierarchy).
- Satisfies ERR-01.
  </done>
</task>

<task type="auto">
  <name>Task 2: Create types.py with the four boundary dataclasses</name>
  <files>src/llm/types.py</files>
  <action>
Create `src/llm/types.py` with the four `@dataclass(frozen=True, slots=True)` types used at the adapter boundary. These are the only non-primitive shapes that cross the seam (per ABS-05). All four are required in Phase 1 — `ClassificationResultV1` and `IntentResult` are referenced by Phase 4 (TOOL-01); `ToolSchema` and `ToolCall` are referenced by the ABC method signatures in `base.py` (Task 3).

Exact shape (from RESEARCH.md Recommended Shapes section 3):

```python
"""Dataclasses exchanged at the LLM adapter boundary.

All types here are `frozen=True, slots=True` per ABS-03. They are the only
non-primitive shapes that cross the adapter seam (per ABS-05): adapters return
`str` (from `complete`) or `ToolCall` (from `classify_with_tool`), never raw
HTTP/JSON.

Python 3.10+ is required for `slots=True` (dev: 3.13.3, deploy: 3.11.14+).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ToolSchema:
    """Provider-agnostic tool/function-calling schema.

    `input_schema` is a JSON-Schema-shaped dict. The Anthropic adapter
    (Phase 4) passes it directly to `tools[*].input_schema`; the Azure
    adapter uses it for prompt templating.
    """
    name: str
    description: str
    input_schema: dict


@dataclass(frozen=True, slots=True)
class ToolCall:
    """Validated tool invocation returned by `classify_with_tool`.

    `raw_response` is debug-only and excluded from `repr`. Note: with
    `frozen=True` the dict slot cannot be reassigned, but the dict's
    contents are still mutable — acceptable for Phase 1 (debug only).
    """
    tool_name: str
    input: dict
    raw_response: dict = field(default_factory=dict, repr=False)


@dataclass(frozen=True, slots=True)
class ClassificationResultV1:
    """Single source of truth for intent-classification LLM output (TOOL-01).

    Phase 4's `INTENT_TOOL` schema is derived programmatically from these
    fields (TOOL-02). `chart_requested` and `chart_type` are intentionally
    NOT included here — they are populated by the heuristic
    `_detect_chart_request()` in query_router.py and merged AFTER the LLM
    call (TOOL-03 / TOOL-04). The LLM cannot overwrite the heuristic.
    """
    version: str  # literal "v1" for schema-versioning (Phase 4)
    intent: str  # "structured" | "semantic" | "hybrid"
    confidence: float  # 0.0-1.0
    reasoning: str
    detected_filters: dict  # {"priority", "assignment_group", "date_range"}


@dataclass(frozen=True, slots=True)
class IntentResult:
    """Final intent shape returned to call sites (post-merge).

    Carries the LLM fields from `ClassificationResultV1` PLUS the heuristic
    `chart_requested` / `chart_type`. Phase 4's `classify_intent` builds this
    by merging the LLM result with `_detect_chart_request()` output.
    """
    intent: str
    confidence: float
    reasoning: str
    detected_filters: dict
    chart_requested: bool  # heuristic, NOT from LLM
    chart_type: str | None  # heuristic, NOT from LLM
```

Requirements:
- `from __future__ import annotations` at the top.
- All four classes are `@dataclass(frozen=True, slots=True)`.
- `ClassificationResultV1` MUST NOT contain `chart_requested` or `chart_type` (locked decision; see CONTEXT.md + TOOL-03).
- `ToolCall.raw_response` MUST have `repr=False` so debug payloads don't appear in error messages.
- No `__all__` needed.
  </action>
  <verify>
Run from project root:
```
python -c "from dataclasses import is_dataclass, FrozenInstanceError; from src.llm.types import ToolSchema, ToolCall, ClassificationResultV1, IntentResult; assert all(is_dataclass(t) for t in [ToolSchema, ToolCall, ClassificationResultV1, IntentResult]); ts = ToolSchema(name='x', description='y', input_schema={}); 
try:
    ts.name = 'z'; raise AssertionError('frozen violated')
except FrozenInstanceError: pass
assert hasattr(ToolSchema, '__slots__'); fields = {f for f in ClassificationResultV1.__dataclass_fields__}; assert 'chart_requested' not in fields and 'chart_type' not in fields, f'chart fields leaked into ClassificationResultV1: {fields}'; tc = ToolCall(tool_name='n', input={'k':'v'}, raw_response={'big': 'payload'}); assert 'big' not in repr(tc) and 'payload' not in repr(tc), f'raw_response leaked into repr: {repr(tc)}'; print('OK')"
```
Must print `OK`. The verification confirms: (a) all four are dataclasses, (b) frozen is enforced, (c) `__slots__` is set, (d) `ClassificationResultV1` does NOT contain chart fields, (e) `ToolCall.raw_response` is excluded from `repr`.
  </verify>
  <done>
- `src/llm/types.py` exists and all four classes import cleanly.
- `ToolSchema`, `ToolCall`, `ClassificationResultV1`, `IntentResult` are all `frozen=True, slots=True` dataclasses.
- `ClassificationResultV1` does NOT contain `chart_requested` or `chart_type`.
- `ToolCall.raw_response` is excluded from `repr()` output.
- Satisfies ABS-03, ABS-05 (preparatory), TOOL-01.
  </done>
</task>

<task type="auto">
  <name>Task 3: Create base.py with LLMClient ABC, and __init__.py as a minimal package marker</name>
  <files>src/llm/base.py, src/llm/__init__.py</files>
  <action>
Create two files:

**File 1: `src/llm/base.py`** — the `LLMClient` ABC. Two methods (`complete`, `classify_with_tool`) declared with `@abstractmethod`. Signatures match RESEARCH.md Recommended Shapes section 3 exactly — these are tuned so that (a) Phase 2's Azure extraction is a zero-diff at call sites, and (b) Phase 3's Anthropic adapter handles the `system`-extraction internally.

```python
"""Provider-agnostic LLM client interface (ABS-02).

The ABC enforces the two-method contract at construction time — instantiating
a subclass missing either method raises TypeError. This is the Phase 1 seam:
Phase 2 introduces AzureOpenAIClient, Phase 3 introduces AnthropicMGTIClient,
both implementing this interface.

Method signatures are chosen so that:
  - `complete` accepts `messages: list[dict]` (Azure-native shape including
    {"role": "system", ...} entries) for zero-diff Phase 2 parity. The
    Anthropic adapter (Phase 3) is responsible for extracting the system
    message and promoting it to the top-level `system` field internally.
  - `max_tokens` is a per-call kwarg (the only difference between the two
    duplicated `_call_azure_openai` definitions today is max_tokens 500 vs
    1000 — see RESEARCH.md "Codebase Reconnaissance").
"""
from __future__ import annotations

import abc
from typing import Any

from src.llm.types import ToolCall, ToolSchema


class LLMClient(abc.ABC):
    """Abstract LLM provider interface.

    Concrete adapters (AzureOpenAIClient, AnthropicMGTIClient) implement
    both methods. Adapters return only `str` or `ToolCall` — raw HTTP JSON
    never crosses this boundary (ABS-05).
    """

    @abc.abstractmethod
    def complete(
        self,
        messages: list[dict],
        *,
        max_tokens: int = 500,
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> str:
        """Send a chat-completion request and return the assistant text.

        Args:
            messages: List of {"role", "content"} dicts; the first entry
                may have role "system" (Azure-native shape). The Anthropic
                adapter extracts/promotes system internally.
            max_tokens: Per-call ceiling; default 500 (query_router.py),
                callers override to 1000 for SQL generation (sql_generator.py).
            temperature: Sampling temperature; current code uses 0.1.
            **kwargs: Reserved for adapter-specific overrides.

        Returns:
            The raw assistant text content (caller may JSON-parse it).
        """

    @abc.abstractmethod
    def classify_with_tool(
        self,
        messages: list[dict],
        tool: ToolSchema,
        *,
        tool_name: str,
        **kwargs: Any,
    ) -> ToolCall:
        """Invoke the provider's tool/function-calling path for intent classification.

        Phase 2: Azure adapter uses prompt-based JSON parsing (existing pattern).
        Phase 4: Anthropic adapter uses native strict-tools.
        Both wrap the validated result in `ToolCall`.

        Args:
            messages: Same shape as `complete`.
            tool: Tool schema definition.
            tool_name: Name of the tool to invoke (used for `tool_choice`).
            **kwargs: Reserved for adapter-specific overrides.

        Returns:
            A `ToolCall` carrying the validated tool input dict.

        Raises:
            LLMSchemaError: If the provider returns a malformed/missing
                tool_use response (Phase 4 raises this).
        """
```

**File 2: `src/llm/__init__.py`** — a minimal package marker. The full factory (`get_llm`, `_resolve_provider`, `_cache`, `_REGISTRY`) lands in Plan 02. For now, we only re-export the public names so `from src.llm import LLMClient` works from the REPL (satisfies success criterion #1).

```python
"""snow_query LLM abstraction package.

Phase 1 (this commit): types, errors, and the LLMClient ABC.
Phase 1 Plan 02: get_llm factory + LLMSettings + adapter stubs.
Phase 2: AzureOpenAIClient real implementation + call-site rewrite.
Phase 3: AnthropicMGTIClient real implementation.
Phase 4: Strict-tools wiring in classify_with_tool.
Phase 5: Streamlit UI toggle and @st.cache_resource integration.
"""
from src.llm.base import LLMClient
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

__all__ = [
    "LLMClient",
    "LLMError",
    "LLMAuthError",
    "LLMTransientError",
    "LLMGuardrailError",
    "LLMSchemaError",
    "LLMTimeoutError",
    "LLMConfigError",
    "ToolSchema",
    "ToolCall",
    "ClassificationResultV1",
    "IntentResult",
]
```

Notes:
- DO NOT add `get_llm` or `_cache` here — Plan 02 owns those.
- DO NOT import `azure_openai` or `anthropic_mgti` from `__init__.py` — Plan 02 wires them via the lazy-import registry.
- Keep imports absolute (`from src.llm.base import ...`) to match project style (utils.py, query_router.py both use absolute imports).
  </action>
  <verify>
Run from project root:
```
python -c "from src.llm import LLMClient, ToolSchema, ToolCall, LLMConfigError; import abc; assert issubclass(LLMClient, abc.ABC); assert LLMClient.__abstractmethods__ == frozenset({'complete', 'classify_with_tool'}), f'abstract methods mismatch: {LLMClient.__abstractmethods__}'; 
# Confirm ABC enforcement: a subclass missing methods cannot be instantiated
class Incomplete(LLMClient): pass
try:
    Incomplete(); raise AssertionError('should have raised TypeError')
except TypeError as e:
    assert 'complete' in str(e) and 'classify_with_tool' in str(e), f'TypeError did not mention both methods: {e}'
# Confirm a complete subclass CAN instantiate
class Concrete(LLMClient):
    def complete(self, messages, *, max_tokens=500, temperature=0.1, **kwargs): return ''
    def classify_with_tool(self, messages, tool, *, tool_name, **kwargs): return ToolCall(tool_name=tool_name, input={})
Concrete()
print('OK')"
```
Must print `OK`. This proves: (a) `LLMClient` is an ABC, (b) both `complete` and `classify_with_tool` are abstract, (c) instantiating an incomplete subclass raises `TypeError` mentioning both methods (success criterion #2), (d) a complete subclass instantiates fine.
  </verify>
  <done>
- `src/llm/base.py` exists with `LLMClient(abc.ABC)` and two `@abstractmethod` methods (`complete`, `classify_with_tool`) with the exact signatures from RESEARCH.md.
- `src/llm/__init__.py` exists and re-exports `LLMClient` + all 7 error classes + all 4 types.
- The package is importable: `from src.llm import LLMClient` works from a REPL inside the project venv.
- Instantiating a `LLMClient` subclass missing either method raises `TypeError` at construction time.
- Satisfies ABS-01 (partially — full satisfaction in Plan 02), ABS-02, ABS-05 (interface declaration).
  </done>
</task>

</tasks>

<verification>
After all three tasks, run from project root:

```
python -c "
# Importability (success criterion #1)
from src.llm import (
    LLMClient,
    LLMError, LLMAuthError, LLMTransientError, LLMGuardrailError,
    LLMSchemaError, LLMTimeoutError, LLMConfigError,
    ToolSchema, ToolCall, ClassificationResultV1, IntentResult,
)
import abc
from dataclasses import is_dataclass

# ABS-02: LLMClient is an ABC with exactly two abstract methods
assert issubclass(LLMClient, abc.ABC)
assert LLMClient.__abstractmethods__ == frozenset({'complete', 'classify_with_tool'})

# ABS-03: types are frozen+slots dataclasses
for t in [ToolSchema, ToolCall, ClassificationResultV1, IntentResult]:
    assert is_dataclass(t)
    assert hasattr(t, '__slots__'), f'{t.__name__} missing __slots__'

# TOOL-03 (Phase 4 prep): chart fields NOT in ClassificationResultV1
fields = set(ClassificationResultV1.__dataclass_fields__)
assert 'chart_requested' not in fields
assert 'chart_type' not in fields

# ERR-01: full error hierarchy, all inherit from LLMError
for cls in [LLMAuthError, LLMTransientError, LLMGuardrailError,
            LLMSchemaError, LLMTimeoutError, LLMConfigError]:
    assert issubclass(cls, LLMError)

print('PLAN 01 VERIFICATION OK')
"
```

Must print `PLAN 01 VERIFICATION OK`.
</verification>

<success_criteria>
- All 4 files (`__init__.py`, `base.py`, `errors.py`, `types.py`) exist under `src/llm/`.
- `from src.llm import LLMClient` works from a REPL inside the project venv.
- `LLMClient.__abstractmethods__ == frozenset({'complete', 'classify_with_tool'})`.
- Instantiating `LLMClient` subclass missing either method raises `TypeError`.
- All 7 error classes import cleanly and inherit from `LLMError`.
- All 4 types are `frozen=True, slots=True` dataclasses.
- `ClassificationResultV1` does not contain `chart_requested` or `chart_type`.
- `ToolCall.raw_response` is excluded from `repr()`.
- No file in `src/llm/` imports from `src/query_router.py`, `src/sql_generator.py`, or `app.py` (LOCKED — Phase 2/5 concerns).
- Top-level `config.py` is NOT modified.

Maps to: Success criteria #1, #2 (full); #5 (partial — `repr` safety on `ToolCall.raw_response`). Requirements ABS-01 (partial), ABS-02, ABS-03, ABS-05, ERR-01, TOOL-01.
</success_criteria>

<output>
After completion, create `.planning/phases/01-abstraction-seam/01-01-SUMMARY.md` documenting:
- Files created (4) with line counts
- Confirmation that ABC contract is enforced
- Confirmation that `ClassificationResultV1` is chart-field-free
- Confirmation that all 7 error classes exist
- Any deviations from RESEARCH.md recommended shapes (expect: none)
</output>
