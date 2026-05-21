"""Dataclasses exchanged at the LLM adapter boundary.

All types here are `frozen=True, slots=True` per ABS-03. They are the only
non-primitive shapes that cross the adapter seam (per ABS-05): adapters return
`str` (from `complete`) or `ToolCall` (from `classify_with_tool`), never raw
HTTP/JSON.

Python 3.10+ is required for `slots=True` (dev: 3.13.3, deploy: 3.11.14+).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


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

    version: str  # literal "v1" for schema-versioning (Phase 4) — see Plan 01 decision §2
    intent: Literal["structured", "semantic", "hybrid"]  # was `str` pre-Phase 4
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


# ---------------------------------------------------------------------------
# Phase 4: INTENT_TOOL — programmatically derived from ClassificationResultV1
# per TOOL-02 (single source of truth). Adding/removing a field on the
# dataclass automatically propagates to the LLM schema; chart_requested /
# chart_type are absent from the dataclass by design (TOOL-03) so they
# cannot leak into the LLM contract.
#
# CRITICAL: dataclasses.fields(cls)[i].type returns STRINGS under
# `from __future__ import annotations` (line 10 of this file). Use
# typing.get_type_hints(cls) to get real type objects.
# ---------------------------------------------------------------------------
import typing
from dataclasses import MISSING, fields

_PRIMITIVE_TO_JSON_SCHEMA: dict[type, dict] = {
    str: {"type": "string"},
    int: {"type": "integer"},
    float: {"type": "number"},
    bool: {"type": "boolean"},
    dict: {"type": "object"},
    list: {"type": "array"},
}


def _py_type_to_json_schema(py_type: typing.Any) -> dict:
    """Map a resolved Python type to its JSON-schema fragment.

    Handles primitives, dict, list, typing.Literal[...] (string-enum), and
    Optional[X] / X | None (nullable). Raises NotImplementedError on
    unsupported shapes — keep the surface deliberately narrow so v2 needs a
    deliberate extension, not a silent regression.
    """
    origin = typing.get_origin(py_type)
    args = typing.get_args(py_type)

    if origin is typing.Literal:
        return {"type": "string", "enum": list(args)}

    # Optional[X] / X | None → expand into nullable type-array
    if origin is typing.Union or py_type.__class__.__name__ == "UnionType":
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1 and len(args) == 2:
            inner = _py_type_to_json_schema(non_none[0])
            t = inner.get("type")
            if isinstance(t, str):
                inner["type"] = [t, "null"]
            return inner

    if py_type in _PRIMITIVE_TO_JSON_SCHEMA:
        return dict(_PRIMITIVE_TO_JSON_SCHEMA[py_type])  # copy

    raise NotImplementedError(
        f"_py_type_to_json_schema: unsupported type {py_type!r}; extend "
        f"_PRIMITIVE_TO_JSON_SCHEMA or add a branch."
    )


def _build_intent_tool_schema(cls: type) -> dict:
    """Reflect cls's @dataclass fields into a JSON Schema 'object'.

    Returns: {"type": "object", "properties": {...}, "required": [...],
              "additionalProperties": False}

    additionalProperties=False mirrors Anthropic strict-mode best practice
    and locks the LLM out of injecting chart_requested / chart_type.
    """
    hints = typing.get_type_hints(cls)
    properties: dict[str, dict] = {}
    required: list[str] = []
    for f in fields(cls):
        properties[f.name] = _py_type_to_json_schema(hints[f.name])
        # In v1, no field has a default — all are required.
        if f.default is MISSING and f.default_factory is MISSING:
            required.append(f.name)
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


# Top-level constant — single source of truth for intent-classification
# strict-tools schema (TOOL-02). Description kept SHORT per Anthropic
# tool-use guide ("overly long descriptions reduce model accuracy").
INTENT_TOOL: ToolSchema = ToolSchema(
    name="classify_intent",
    description=(
        "Classify a user query about ServiceNow incidents into structured, "
        "semantic, or hybrid. Extract priority/group/date filters and a "
        "confidence score."
    ),
    input_schema=_build_intent_tool_schema(ClassificationResultV1),
)
