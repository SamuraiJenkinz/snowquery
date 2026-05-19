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
