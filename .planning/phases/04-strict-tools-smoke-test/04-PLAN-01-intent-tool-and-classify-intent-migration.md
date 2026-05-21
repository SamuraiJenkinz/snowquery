---
phase: 4
plan: 1
name: intent-tool-and-classify-intent-migration
type: execute
wave: 1
depends_on: []
files_modified:
  - src/llm/types.py
  - src/query_router.py
autonomous: true

must_haves:
  truths:
    - "INTENT_TOOL is importable from src.llm.types as a top-level ToolSchema constant"
    - "INTENT_TOOL.input_schema['properties'] contains exactly {version, intent, confidence, reasoning, detected_filters}"
    - "INTENT_TOOL.input_schema['properties'] does NOT contain chart_requested or chart_type"
    - "INTENT_TOOL.input_schema['properties']['intent'] is {'type': 'string', 'enum': ['structured', 'semantic', 'hybrid']}"
    - "INTENT_TOOL.input_schema['properties']['version'] is {'type': 'string'} (plain string, no const/enum)"
    - "classify_intent calls client.classify_with_tool(messages, INTENT_TOOL, tool_name='classify_intent') instead of client.complete() + json.loads()"
    - "classify_intent's returned dict's chart_requested/chart_type fields come from the heuristic locals, NEVER from the LLM ToolCall.input"
    - "The runtime intent-allowlist check (current query_router.py:157-158) is REMOVED (now enforced by jsonschema via INTENT_TOOL.input_schema enum)"
    - "The markdown fence-stripping logic (current query_router.py:144-148) is REMOVED (ToolCall.input is already a dict)"
    - "The json.loads + JSONDecodeError fallback (current query_router.py:150-154) is REMOVED (LLMSchemaError now translates to QueryError via _compat.py, caught by the existing except Exception fallback at 173-175)"
  artifacts:
    - path: "src/llm/types.py"
      provides: "INTENT_TOOL: ToolSchema top-level constant + _build_intent_tool_schema + _py_type_to_json_schema helpers; ClassificationResultV1.intent re-typed to Literal['structured', 'semantic', 'hybrid']"
      contains: "INTENT_TOOL: ToolSchema"
    - path: "src/query_router.py"
      provides: "classify_intent migrated to classify_with_tool with heuristic merge AFTER LLM result"
      contains: "classify_with_tool"
  key_links:
    - from: "src/query_router.py::classify_intent"
      to: "src/llm/anthropic_mgti.py::classify_with_tool (or Azure equivalent)"
      via: "client = get_llm(); call = client.classify_with_tool(messages, INTENT_TOOL, tool_name='classify_intent')"
      pattern: "classify_with_tool\\(.*INTENT_TOOL"
    - from: "src/llm/types.py::INTENT_TOOL"
      to: "src/llm/types.py::ClassificationResultV1"
      via: "_build_intent_tool_schema(ClassificationResultV1) reflection helper"
      pattern: "_build_intent_tool_schema\\(ClassificationResultV1\\)"
    - from: "src/query_router.py::classify_intent return dict"
      to: "heuristic locals chart_requested, chart_type (line 121)"
      via: "final dict construction reads from local variables, NOT from call.input"
      pattern: "\"chart_requested\":\\s*chart_requested"
---

<objective>
Land `INTENT_TOOL` as a top-level constant in `src/llm/types.py` (derived programmatically from `ClassificationResultV1` per TOOL-02) and migrate `src/query_router.py::classify_intent` from the current prompt-based JSON-parse path to `client.classify_with_tool(...)` while preserving the heuristic-populated `chart_requested`/`chart_type` merge (TOOL-04).

Purpose: This plan is the **schema foundation** for the entire phase. Plan 02 (`AnthropicMGTIClient.classify_with_tool`) takes any `ToolSchema` as a parameter — but the production call site (`classify_intent`) and the smoke script (Plan 03) BOTH need `INTENT_TOOL` to exist as a stable, importable constant. Deriving it from the dataclass (vs hand-writing JSON) is TOOL-02's single-source-of-truth lock: changing a field on `ClassificationResultV1` automatically propagates to the LLM schema.

Output: A reflective schema-derivation helper, the `INTENT_TOOL` constant, a tightened `intent` enum on `ClassificationResultV1`, and a 30-line surgical edit to `classify_intent` that swaps `complete() + json.loads()` for `classify_with_tool()` while keeping the heuristic-merge dict-construction shape verbatim.
</objective>

<execution_context>
@C:\Users\taylo\.claude/get-shit-done/workflows/execute-plan.md
@C:\Users\taylo\.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/04-strict-tools-smoke-test/04-CONTEXT.md
@.planning/phases/04-strict-tools-smoke-test/04-RESEARCH.md

# Existing code this plan modifies
@src/llm/types.py
@src/query_router.py

# Reference patterns (read-only — do NOT modify)
@src/llm/azure_openai.py
@src/llm/_compat.py
</context>

<decisions>
## Decisions locked for this plan

1. **`intent: str` becomes `intent: Literal["structured", "semantic", "hybrid"]`** on `ClassificationResultV1`. This is locked by the user (orchestration locked_decisions §1). The derived `INTENT_TOOL.input_schema['properties']['intent']` MUST be `{"type": "string", "enum": ["structured", "semantic", "hybrid"]}`. This REPLACES the current runtime allowlist at `src/query_router.py:157-158` — which Plan 01 deletes.

2. **`version: str` STAYS as plain string** — no `Literal["v1"]`, no `const`, no `enum`. Locked by user (orchestration locked_decisions §2). The derived schema is `{"type": "string"}`. Future v2 work updates both the dataclass annotation AND the derivation helper together — Phase 4 ships v1 only.

3. **Schema derivation uses `typing.get_type_hints()` NOT `dataclasses.fields(...).type`** — RESEARCH.md Pitfall 1 + Q1. `src/llm/types.py:10` uses `from __future__ import annotations` which makes `f.type` return strings; `get_type_hints()` resolves forward references to real type objects. Use `fields()` for ordering and required-detection; use `get_type_hints()` for type lookup.

4. **`additionalProperties: false`** on the derived schema — mirrors Anthropic strict-mode best practice (RESEARCH.md "Anthropic strict-tools request body (verified shape)"). Combined with all-required fields (v1 has no defaults), this means the LLM CANNOT add `chart_requested` or `chart_type` even by accident.

5. **Heuristic merge runs AFTER LLM result, not before** — RESEARCH.md Pattern 5 + Pitfall (TOOL-04 lock). The `_detect_chart_request()` call at `src/query_router.py:121` produces locals `chart_requested, chart_type` BEFORE the LLM call. The final dict construction at lines 162-169 reads from those locals — Phase 4 must NOT regress by reading `call.input.get("chart_requested")` (which would return `None` since the schema has no such field, but the lookup itself is the regression vector).

6. **The fence-stripping (lines 144-148), `json.loads` (150), JSONDecodeError fallback (151-154), and intent-allowlist (157-158) blocks are DELETED.** Schema validation now happens inside the adapter via `jsonschema.validate(input_dict, tool.input_schema)`; the `enum` constraint on `intent` handles allowlisting; the `LLMSchemaError → QueryError` translation via `_compat.py` is caught by the existing `except Exception` at `query_router.py:173-175`, routing to `_heuristic_classify` exactly as JSONDecodeError did.

7. **The outer try/except heuristic-fallback (lines 171-175) STAYS UNCHANGED.** `except QueryError: raise` and `except Exception: return _heuristic_classify(user_query)` already handle `LLMSchemaError → QueryError` correctly via `_compat.py:111-117`'s catch-all branch (locked in Phase 3). No edits to the fallback shape.

8. **NO new file `src/llm/_intent_tool.py`** — keep the helpers in `src/llm/types.py` to minimize import surface. `ClassificationResultV1` already lives there; the derivation helpers + `INTENT_TOOL` constant naturally co-locate. CONTEXT.md §Claude's Discretion permits either; co-location is simpler.
</decisions>

<tasks>

<task type="auto">
  <name>Task 1.1: Add schema-derivation helpers + INTENT_TOOL constant + tighten intent to Literal in src/llm/types.py</name>
  <files>src/llm/types.py</files>
  <action>
Edit `src/llm/types.py` to:

**(a) Tighten `ClassificationResultV1.intent`** from `str` to `Literal["structured", "semantic", "hybrid"]`:

```python
# Add to the top of the file, AFTER `from __future__ import annotations`
from typing import Literal

# Modify the existing ClassificationResultV1 dataclass — change ONLY the intent line
@dataclass(frozen=True, slots=True)
class ClassificationResultV1:
    """... (keep existing docstring verbatim) ..."""
    version: str  # literal "v1" for schema-versioning (Phase 4) — see Plan 01 decision §2
    intent: Literal["structured", "semantic", "hybrid"]  # was `str` pre-Phase 4
    confidence: float
    reasoning: str
    detected_filters: dict
```

Keep `version: str` (plain) per locked decision §2. Keep `confidence: float`, `reasoning: str`, `detected_filters: dict` unchanged.

**(b) Add the schema-derivation helpers and INTENT_TOOL constant** at the BOTTOM of `src/llm/types.py` (after `IntentResult`):

```python
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
```

**(c) Do NOT add `INTENT_TOOL` to `src/llm/__init__.py` re-exports** — call sites import directly via `from src.llm.types import INTENT_TOOL`. Minimizes import-surface churn.

**Verification while you work:** After this edit, opening a Python REPL with `python -c "from src.llm.types import INTENT_TOOL; import json; print(json.dumps(INTENT_TOOL.input_schema, indent=2))"` MUST produce a dict whose `properties` keys are exactly `{version, intent, confidence, reasoning, detected_filters}`, where `intent.enum` is `["structured", "semantic", "hybrid"]`, and `additionalProperties` is `false`.
  </action>
  <verify>
Run from the repo root:

```bash
python -c "
from src.llm.types import INTENT_TOOL, ClassificationResultV1
import json
schema = INTENT_TOOL.input_schema
print('name:', INTENT_TOOL.name)
print('properties:', sorted(schema['properties']))
print('required:', sorted(schema['required']))
print('additionalProperties:', schema.get('additionalProperties'))
print('intent schema:', schema['properties']['intent'])
print('version schema:', schema['properties']['version'])
print('chart_requested absent:', 'chart_requested' not in schema['properties'])
print('chart_type absent:', 'chart_type' not in schema['properties'])
"
```

Expected output:
```
name: classify_intent
properties: ['confidence', 'detected_filters', 'intent', 'reasoning', 'version']
required: ['confidence', 'detected_filters', 'intent', 'reasoning', 'version']
additionalProperties: False
intent schema: {'type': 'string', 'enum': ['structured', 'semantic', 'hybrid']}
version schema: {'type': 'string'}
chart_requested absent: True
chart_type absent: True
```
  </verify>
  <done>
INTENT_TOOL constant exists at `src/llm/types.py` top-level; reflects all 5 ClassificationResultV1 fields; `intent` schema has the 3-value enum; `version` schema is plain string; chart_requested/chart_type absent; `additionalProperties: false` set. `ClassificationResultV1.intent` annotation is `Literal["structured", "semantic", "hybrid"]`. No other dataclasses changed. No imports added to `src/llm/__init__.py`.
  </done>
</task>

<task type="auto">
  <name>Task 1.2: Migrate src/query_router.py::classify_intent from complete() + json.loads to classify_with_tool() with heuristic merge AFTER LLM</name>
  <files>src/query_router.py</files>
  <action>
Edit `src/query_router.py` to migrate `classify_intent` (lines 101-175) from the current prompt-based JSON-parse path to `client.classify_with_tool(messages, INTENT_TOOL, tool_name='classify_intent')`. The heuristic merge for `chart_requested`/`chart_type` MUST run AFTER the LLM call (TOOL-04). The outer try/except heuristic-fallback shape stays unchanged.

**Step A — Add the INTENT_TOOL import.** Find the existing `from src.llm` imports near the top of the file (currently around `from src.llm import get_llm` and `from src.llm._compat import llm_to_query_error`). Add:

```python
from src.llm.types import INTENT_TOOL
```

If `json` is no longer used ANYWHERE else in `src/query_router.py` after this edit (grep before removing), remove the `import json` line at the top. **Caution:** other functions in the file (e.g. `generate_executive_summary`) may still use `json`. Run `grep -n "json\." src/query_router.py` AFTER your edits but BEFORE removing the import; only remove if zero matches remain.

**Step B — Replace lines 137-169 (the LLM-call-through-final-return-dict block) with this exact shape.** Preserve indentation level (one level inside the outer `try:` at line 123):

```python
        client = get_llm()
        with llm_to_query_error():
            call = client.classify_with_tool(
                messages,
                INTENT_TOOL,
                tool_name="classify_intent",
            )

        result = call.input  # dict matching ClassificationResultV1 fields
        # Schema validation happened inside the adapter via jsonschema —
        # `intent` is guaranteed to be one of structured/semantic/hybrid
        # (enum constraint from INTENT_TOOL.input_schema), and all 5 fields
        # are present (required-by-default in the derived schema).

        logger.info(
            f"Classified as: {result['intent']} "
            f"(confidence: {result.get('confidence', 0)})"
        )

        # CRITICAL (TOOL-04): heuristic merge AFTER LLM result. The
        # chart_requested / chart_type values come from the heuristic
        # locals computed at line 121 (_detect_chart_request) — NEVER
        # from call.input. INTENT_TOOL.input_schema has no such fields,
        # so call.input.get('chart_requested') would return None anyway,
        # but reading from it is the regression vector this comment guards.
        return {
            "intent": result["intent"],
            "confidence": result.get("confidence", 0.5),
            "reasoning": result.get("reasoning", ""),
            "detected_filters": result.get("detected_filters", {}),
            "chart_requested": chart_requested,  # from heuristic at line 121
            "chart_type": chart_type,             # from heuristic at line 121
        }
```

**Lines DELETED in this edit (must be removed verbatim):**
- Lines 141-148: the `try:` block opening, the markdown-fence-stripping comment, and the 4 fence-stripping lines (`if content.startswith("```"):` through `content = content.strip()`).
- Line 150: `result = json.loads(content)`
- Lines 151-154: the `except json.JSONDecodeError as e:` branch (logger.error + fallback to `_heuristic_classify`).
- Lines 156-158: the intent-allowlist runtime check (`if result.get("intent") not in [...]`). This validation now lives in the JSON-schema `enum` constraint.

**Lines PRESERVED unchanged:**
- Lines 101-136: function signature, docstring, logger.info, `_detect_chart_request` call, schema_text setup, messages list construction.
- Lines 171-175: the outer `except QueryError: raise` and `except Exception as e: ... return _heuristic_classify(user_query)`. These ALREADY handle `LLMSchemaError → QueryError` translation via `_compat.py:111-117` (Phase 3 locked the catch-all `except LLMError` dispatch — `LLMSchemaError` is a subclass of `LLMError`, so it's routed correctly).

**Step C — Use `result["intent"]` not `result.get("intent", "structured")` in the return dict.** The schema's `required` list guarantees `intent` presence; the `enum` guarantees its value. Defaulting to `"structured"` would silently mask an upstream contract violation. Keep `.get(...)` with default ONLY for `confidence`, `reasoning`, `detected_filters` to preserve current default-on-missing behavior for fields that aren't load-bearing (the logger.info line and the return dict).

  **WAIT — schema makes them required too.** Since `additionalProperties: false` AND all 5 fields are in `required`, the LLM cannot return any of them missing without the adapter raising `LLMSchemaError` (caught by `except Exception` → `_heuristic_classify`). The `.get(..., default)` calls are defensive belt-and-braces; keeping them does no harm and protects against future schema relaxation. **Decision: keep .get(..., default) for confidence/reasoning/detected_filters; use direct `result["intent"]` for intent.**
  </action>
  <verify>
Run from the repo root:

```bash
# 1. Confirm INTENT_TOOL import landed
grep -n "from src.llm.types import INTENT_TOOL" src/query_router.py
# Expected: one match

# 2. Confirm classify_with_tool call site exists
grep -n "client.classify_with_tool(" src/query_router.py
# Expected: one match inside classify_intent

# 3. Confirm deleted blocks are GONE
grep -n "json.JSONDecodeError" src/query_router.py
# Expected: ZERO matches (the only one was the deleted block)

grep -n 'result.get("intent") not in' src/query_router.py
# Expected: ZERO matches

grep -nE 'content\.startswith\("```"\)' src/query_router.py
# Expected: ZERO matches

# 4. Confirm heuristic merge stayed correct (uses LOCALS, not call.input)
grep -nE '"chart_requested":\s*chart_requested' src/query_router.py
grep -nE '"chart_type":\s*chart_type' src/query_router.py
# Expected: one match each, INSIDE classify_intent's return dict

# 5. Confirm classify_intent return dict does NOT read chart_requested/chart_type from LLM
grep -n 'call.input.get.*chart' src/query_router.py
grep -n 'result.get.*chart' src/query_router.py
# Expected: ZERO matches each

# 6. Module imports cleanly
python -c "from src.query_router import classify_intent; print('import OK')"
# Expected: "import OK" (NO ImportError, NO NameError on INTENT_TOOL)

# 7. Sanity-check Phase 1+2+3 tests still pass (Plan 01 should not break any prior phase tests)
pytest tests/test_llm_seam.py tests/test_phase2_parity.py tests/test_phase3_adapter.py -q
# Expected: 39 passed (same baseline as STATE.md). Note: tests that mock the adapter
# at .complete(...) will still pass because Plan 01 only changes classify_intent's
# call to .classify_with_tool(); tests that mock .complete directly won't trigger it.
# If a Phase 2 or 3 test asserts classify_intent calls .complete(), update the
# test in this task — but inventory first: grep for "classify_intent" in tests/
# and confirm zero tests directly invoke classify_intent (they likely test the
# adapter layer only).
```
  </verify>
  <done>
`classify_intent` calls `client.classify_with_tool(messages, INTENT_TOOL, tool_name="classify_intent")` (NOT `client.complete()`). The fence-stripping, `json.loads`, JSONDecodeError fallback, and intent-allowlist code blocks are removed. The final return dict's `chart_requested`/`chart_type` values come from the heuristic locals at line 121, NEVER from `call.input`. The outer try/except heuristic-fallback shape is unchanged. `import json` removed from query_router.py top-level IF and ONLY IF no other function in the file still uses it. Module imports cleanly. Existing Phase 1+2+3 tests still pass.
  </done>
</task>

</tasks>

<verification>
Phase-level verification for Plan 01:

1. **Schema derivation is single-source-of-truth (TOOL-02):**
   ```bash
   python -c "
   from src.llm.types import INTENT_TOOL, ClassificationResultV1
   from dataclasses import fields
   dc_field_names = {f.name for f in fields(ClassificationResultV1)}
   schema_props = set(INTENT_TOOL.input_schema['properties'])
   assert dc_field_names == schema_props, f'mismatch: dc={dc_field_names} schema={schema_props}'
   print('OK: dataclass fields == schema properties')
   "
   ```

2. **chart_requested/chart_type cannot leak (TOOL-03):**
   ```bash
   python -c "
   from src.llm.types import INTENT_TOOL
   for forbidden in ['chart_requested', 'chart_type']:
       assert forbidden not in INTENT_TOOL.input_schema['properties'], forbidden
   print('OK: heuristic-only fields absent from LLM schema')
   "
   ```

3. **Migration touched only the 2 declared files:**
   ```bash
   git diff --stat HEAD -- src/ scripts/ tests/
   # Expected: ONLY src/llm/types.py and src/query_router.py appear
   ```

4. **No regression on prior phases:**
   ```bash
   pytest tests/ -q
   # Expected: 39 passed (Phase 1+2+3 baseline preserved)
   ```
</verification>

<success_criteria>
- [ ] `from src.llm.types import INTENT_TOOL` works and returns a `ToolSchema` with `name="classify_intent"`
- [ ] `INTENT_TOOL.input_schema['properties']` has exactly 5 keys: `version, intent, confidence, reasoning, detected_filters`
- [ ] `INTENT_TOOL.input_schema['properties']['intent'] == {"type": "string", "enum": ["structured", "semantic", "hybrid"]}`
- [ ] `INTENT_TOOL.input_schema['properties']['version'] == {"type": "string"}`
- [ ] `INTENT_TOOL.input_schema['additionalProperties'] is False`
- [ ] `INTENT_TOOL.input_schema['required']` includes all 5 field names
- [ ] `chart_requested` and `chart_type` are absent from `INTENT_TOOL.input_schema['properties']`
- [ ] `ClassificationResultV1.__dataclass_fields__['intent'].type` (or via `get_type_hints`) resolves to `Literal["structured", "semantic", "hybrid"]`
- [ ] `src/query_router.py::classify_intent` invokes `client.classify_with_tool(messages, INTENT_TOOL, tool_name="classify_intent")` exactly once
- [ ] `grep -nE 'json\.JSONDecodeError|result\.get\("intent"\) not in|content\.startswith\("```"\)' src/query_router.py` returns ZERO matches
- [ ] The return dict's `chart_requested`/`chart_type` values reference the LOCAL variables (line 121 origin), not `call.input` or `result`
- [ ] Combined Phase 1+2+3 test suite still passes (39 tests)
- [ ] Only `src/llm/types.py` and `src/query_router.py` modified in this plan's git diff
</success_criteria>

<output>
After completion, create `.planning/phases/04-strict-tools-smoke-test/04-01-SUMMARY.md` documenting:
- What was changed in `src/llm/types.py` (helpers added, `INTENT_TOOL` constant, `intent` enum tightening)
- What was changed in `src/query_router.py` (call-site migration, deletions, heuristic-merge preservation)
- Confirmation of the 6 success-criteria asserts above
- Any deviations from the locked decisions (should be zero — flag if not)
- Any test that needed adjustment in `tests/` (should be zero based on grep — flag if not)
- Note for Plan 02: `INTENT_TOOL` is now importable; Plan 02 does NOT need it (takes `tool: ToolSchema` as a param), but Plan 03 (smoke script) WILL import it
</output>
</content>
</invoke>