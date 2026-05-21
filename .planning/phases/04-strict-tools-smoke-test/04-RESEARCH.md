# Phase 4: Strict-Tools + Smoke Test — Research

**Researched:** 2026-05-21
**Domain:** Anthropic strict-tools / programmatic JSON-schema derivation / operator-run live-credential smoke script
**Confidence:** HIGH (all 12 research questions answered with file:line refs from the active codebase + verified Anthropic Messages API docs)

---

## Summary

Phase 4 is a focused, dependency-heavy phase that lands one new endpoint adapter method (`AnthropicMGTIClient.classify_with_tool`) on top of pre-built infrastructure: `ANTHROPIC_TOOLS_SUPPORTED` is already loaded (`anthropic_mgti.py:161` → `self._tools_supported`), `jsonschema>=4.26.0,<5` is already pinned (`requirements.txt:18`), `ClassificationResultV1` is already frozen with the exact 5-field shape (`src/llm/types.py:44-58`), the `_compat.py` per-provider dispatch already covers `LLMSchemaError`/`LLMGuardrailError` via the catch-all `except LLMError` branch (`_compat.py:111-117`), and `requirements.txt` is the only file that owns `jsonschema` dependency wiring. The work is mostly mechanical translation of the Phase 3 `complete()` HTTP+envelope-parsing pattern into a tool-use-aware twin (`_post_messages` helper extraction), plus a clean reflective schema generator and one net-new operator-run script.

The Anthropic Messages API `tool_use` response shape is fully documented and HIGH-confidence: `stop_reason: "tool_use"` accompanies a `content` array that may MIX `text` and `tool_use` blocks (verified against the official Anthropic docs example which shows both). The `tool_use` block has fields `type`, `id` (opaque `toolu_...`), `name`, `input` (dict). The `tool_choice` shape `{"type":"tool","name":"...","disable_parallel_tool_use":true}` is officially supported and the field name spellings are correct (verified verbatim against `platform.claude.com/docs/en/api/messages`). The MGTI proxy passes these through unchanged per Phase 3 STATE.md decisions.

The smoke script is a standalone `scripts/smoke_llm.py` operator-tool. The `scripts/` directory does NOT yet exist (verified via `Glob scripts/**/*`); planner must create it. The script must call `load_dotenv()` directly (root `config.py` already does so, but `scripts/` is outside its import path and importing `config.py` has side effects — creates `data/` and `db/` directories). Pattern to mirror: `tests/manual/observe_correlation_echo.py` (single-file, `def main() -> int`, `if __name__ == "__main__": sys.exit(main())`).

**Primary recommendation:** Split into 4 plans matching Phase 3's rhythm — (1) `INTENT_TOOL` derivation + `classify_intent` heuristic-merge migration; (2) `AnthropicMGTIClient.classify_with_tool` + `_classify_via_text_mode` + `_post_messages` helper extraction + `tools_supported` log field; (3) `scripts/smoke_llm.py`; (4) `tests/test_phase4_strict_tools.py` acceptance gate. Wave assignment: 1 and 2 in parallel are RISKY (Plan 2 also touches `anthropic_mgti.py`); recommend serial Wave 1 = Plan 1 + Plan 3 (no file overlap), Wave 2 = Plan 2 (depends on Plan 1's `INTENT_TOOL` import), Wave 3 = Plan 4 (depends on all three).

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `jsonschema` | `>=4.26.0,<5` (pinned in `requirements.txt:18`) | Validate `tool_use.input` against `tool.input_schema` (defence-in-depth even with proxy strict-mode) | Already used by `AzureOpenAIClient.classify_with_tool` (`src/llm/azure_openai.py:284-289`); proven pattern |
| `requests` | `>=2.31.0` (pinned in `requirements.txt:7`) | Both `POST /messages` and `GET /` service-info in smoke script | All adapter HTTP is `requests`-based; zero new deps |
| `python-dotenv` | `>=1.0.0` (pinned in `requirements.txt:4`) | `load_dotenv()` in smoke script | Already used by root `config.py:7,13` |
| `dataclasses` (stdlib) | Python 3.11+ | `dataclasses.fields()` for `INTENT_TOOL` derivation | `ClassificationResultV1` is `@dataclass(frozen=True, slots=True)` (`src/llm/types.py:43`) |
| `typing.get_type_hints` (stdlib) | Python 3.11+ | Resolve forward-reference annotations under `from __future__ import annotations` | **MANDATORY** — `dataclasses.fields(...).type` returns strings under future-annotations; `get_type_hints()` returns real types (verified empirically) |

### Installed version vs pin (PLANNER ACTION REQUIRED)

Current installed `jsonschema` is **4.25.1** (verified via `pip show jsonschema`). `requirements.txt:18` pins `>=4.26.0,<5`. First task of Plan 02 (or the acceptance gate) MUST `pip install -U "jsonschema>=4.26.0,<5"` before any test run, or the gate fails on import-time version mismatch. Add this to plan preconditions.

### Supporting (already in tree, no install)
| Library | Use | Where Used |
|---------|-----|------------|
| `uuid` (stdlib) | `X-Correlation-Id` per call | `anthropic_mgti.py:240` |
| `time.monotonic` (stdlib) | Latency timing | `anthropic_mgti.py:256` |
| `argparse` (stdlib) | `--provider`/`--verbose` flags | New for smoke script; stdlib pattern |
| `sys` (stdlib) | `sys.exit(0/1)` from smoke main | `tests/manual/observe_correlation_echo.py:97` |
| `py_compile` (stdlib) | SC #5 syntax check (acceptance gate) | New test pattern |

### Alternatives Rejected (per CONTEXT.md locks)
| Instead of | Could Use | Why NOT |
|------------|-----------|---------|
| `dataclasses.fields()` + manual type map | `pydantic` BaseModel + `.model_json_schema()` | CONTEXT.md §Claude's Discretion: "pydantic is NOT a dependency and should not be added solely for this" |
| Runtime auto-fallback to text-mode | Try-tools, on-error try-text | CONTEXT.md §Fallback strategy: explicit "env-flag-only fallback, NO runtime auto-fallback" |
| `anthropic` SDK | Direct `requests.post` | `.planning/research/STACK.md:180` — SDK uses `Authorization: Bearer`/SigV4 incompatible with MGTI's `X-Api-Key` |
| `--json` flag on smoke | Operator-eye human output only | CONTEXT.md §Smoke output: explicit deferral |
| Shared `_post_messages` extraction to `src/llm/_log.py` | Intra-module helper inside `anthropic_mgti.py` | CONTEXT.md §Code structure: explicit "DO NOT extract to src/llm/_log.py — keep within anthropic_mgti.py" |

---

## Architecture Patterns

### Project Structure After Phase 4

```
src/
├── llm/
│   ├── anthropic_mgti.py   # MODIFY: add classify_with_tool, _classify_via_text_mode, _post_messages
│   ├── azure_openai.py     # NO CHANGES (text-mode classify_with_tool already correct since Phase 2)
│   ├── base.py             # NO CHANGES
│   ├── config.py           # NO CHANGES (tools_supported already loaded)
│   ├── errors.py           # NO CHANGES
│   ├── types.py            # NO CHANGES; ADD: top-level INTENT_TOOL constant via reflection helper
│   ├── _compat.py          # NO CHANGES (catch-all LLMError branch already dispatches by provider)
│   └── __init__.py         # OPTIONAL: re-export INTENT_TOOL (defer unless needed by call sites)
├── query_router.py         # MODIFY: classify_intent migrates complete() → classify_with_tool + heuristic-merge
scripts/                    # NEW directory
└── smoke_llm.py            # NEW operator-run script (single file, ~250 lines)
tests/
└── test_phase4_strict_tools.py  # NEW acceptance gate (~25 tests)
```

### Pattern 1: Reflective schema derivation from `ClassificationResultV1`

**What:** Generate `INTENT_TOOL.input_schema` programmatically by walking `dataclasses.fields()` and mapping each Python type to its JSON-schema equivalent.

**Why this pattern:** Single source of truth — adding/removing a field in `ClassificationResultV1` automatically propagates to `INTENT_TOOL.input_schema['properties']`. This is the explicit lock of TOOL-02 / SC #1.

**Critical detail (`from __future__ import annotations`):** `src/llm/types.py:10` uses `from __future__ import annotations`, which makes `dataclasses.fields(cls)[i].type` return STRINGS instead of resolved type objects. The planner MUST use `typing.get_type_hints(cls)` to get real type objects. Verified empirically:

```python
# Source: codebase smoke-test (verified 2026-05-21)
from dataclasses import fields
from src.llm.types import ClassificationResultV1
# WRONG — under future-annotations, .type is the string "str"
for f in fields(ClassificationResultV1):
    print(f.name, type(f.type).__name__)  # all str
# RIGHT — resolves through forward-references
import typing
hints = typing.get_type_hints(ClassificationResultV1)
for name, t in hints.items():
    print(name, t)  # str, str, float, str, dict
```

**Recommended type-mapping table:**

| Python type | JSON-schema type | Notes |
|-------------|------------------|-------|
| `str` | `{"type": "string"}` | Primary case for `version`, `intent`, `reasoning` |
| `float` | `{"type": "number"}` | For `confidence` (0.0-1.0) |
| `int` | `{"type": "integer"}` | Not used in v1 but document for v2 |
| `bool` | `{"type": "boolean"}` | Not in v1; deny-list candidate for `chart_requested` if anyone tries to add it |
| `dict` | `{"type": "object"}` | For `detected_filters` — value-shape is `{}` (any-shape) in v1 |
| `list` | `{"type": "array"}` | Not in v1 |
| `typing.Literal["v1"]` | `{"type": "string", "enum": ["v1"]}` | OPTIONAL — see Open Question 1 |
| `Optional[X]` / `X \| None` | Add `"null"` to type array (`{"type": ["string", "null"]}`) | Not in v1; document for v2 |

**Source for `Literal` detection (verified empirically):**
```python
from typing import get_type_hints, get_origin, get_args, Literal
# get_origin(Literal["v1"]) returns typing.Literal sentinel
# get_args(Literal["v1"]) returns ("v1",)
```

**Recommended helper signature (planner picks exact name):**
```python
# In src/llm/types.py (or a new src/llm/_intent_tool.py)
def _build_intent_tool_schema(cls: type) -> dict:
    """Derive a JSON Schema 'object' schema from a dataclass type.

    Walks `typing.get_type_hints(cls)` to resolve forward-references that
    `dataclasses.fields(cls)[i].type` would otherwise return as strings
    (the dataclass module uses `from __future__ import annotations`).

    Returns: {"type": "object", "properties": {...}, "required": [...]}
    """
    import typing
    from dataclasses import MISSING, fields

    hints = typing.get_type_hints(cls)
    properties: dict[str, dict] = {}
    required: list[str] = []
    for f in fields(cls):
        properties[f.name] = _py_type_to_json_schema(hints[f.name])
        # In v1, no field has a default — all are required
        if f.default is MISSING and f.default_factory is MISSING:
            required.append(f.name)
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,  # mirrors Anthropic strict-mode best practice
    }

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

**`chart_requested`/`chart_type` filtering:** No deny-list needed in v1 — those fields are absent from `ClassificationResultV1` by design (`src/llm/types.py:44-58`, locked at TOOL-03). Derivation just walks the dataclass; what's not declared can't leak. The SC #1 test explicitly verifies absence.

### Pattern 2: `classify_with_tool` strict-tools path

**What:** Mirror `complete()` structure but with tool_use-block extraction and schema validation.

**Skeleton (planner uses as-is, adapt field names):**
```python
# In AnthropicMGTIClient — sibling of complete() at anthropic_mgti.py:187
def classify_with_tool(
    self,
    messages: list[dict],
    tool: ToolSchema,
    *,
    tool_name: str,
    **kwargs: Any,
) -> ToolCall:
    # Pre-flight checks identical to complete() (lines 217-235)
    # ...

    # Branch on env flag (CONTEXT.md §Fallback strategy)
    if not self._tools_supported:
        return self._classify_via_text_mode(messages, tool, tool_name=tool_name)

    correlation_id = str(uuid.uuid4())
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": self._api_key,
        "X-Correlation-Id": correlation_id,
    }
    # Same body as complete(), PLUS tools + tool_choice
    body = _build_request_body(...)
    body["tools"] = [_tool_schema_to_anthropic(tool)]
    body["tool_choice"] = {
        "type": "tool",
        "name": tool_name,
        "disable_parallel_tool_use": True,
    }

    # _post_messages handles HTTP + 4xx/5xx → typed errors + returns data dict
    data = self._post_messages(body, headers, correlation_id, extra)

    # Extract tool_use block from content[] (defensive iteration even with
    # disable_parallel_tool_use=True per CONTEXT.md §Specifics)
    content_blocks = data.get("content") or []
    stop_reason = data.get("stop_reason")

    # Guardrail check FIRST (matches complete() order at line 336)
    if stop_reason == "guardrail_intervened":
        raise LLMGuardrailError(...)

    # max_tokens during tool_use is a SCHEMA error (CONTEXT.md error matrix)
    if stop_reason == "max_tokens":
        raise LLMSchemaError(
            "max_tokens reached during tool_use — input likely truncated "
            "and unreliable; raise ANTHROPIC_MAX_TOKENS",
            ...
        )

    tool_use_block = None
    for block in content_blocks:
        if block.get("type") == "tool_use" and block.get("name") == tool_name:
            tool_use_block = block
            break

    if tool_use_block is None:
        raise LLMSchemaError(
            f"missing tool_use block in content (stop_reason={stop_reason!r}, "
            f"content_types={[b.get('type') for b in content_blocks]!r})",
            ...
        )

    input_dict = tool_use_block.get("input")
    if not isinstance(input_dict, dict):
        raise LLMSchemaError(
            f"malformed tool_use input: expected dict, got {type(input_dict).__name__}",
            ...
        )

    try:
        jsonschema.validate(input_dict, tool.input_schema)
    except jsonschema.ValidationError as e:
        raise LLMSchemaError(
            f"tool_use input failed schema validation: {e.message}",
            ...,
        ) from e

    return ToolCall(
        tool_name=tool_name,
        input=input_dict,
        raw_response=data,
    )
```

### Pattern 3: `_post_messages` helper extraction (intra-module)

**What:** Extract the HTTP + 4xx/5xx envelope parsing + typed-error mapping from `complete()` (currently lines 268-315 of `anthropic_mgti.py`) into a private method so `classify_with_tool` reuses it without copy-pasting.

**Why intra-module (NOT to `src/llm/_log.py`):** CONTEXT.md §Code structure explicitly locks this. The duplication is ~70 lines IN ONE FILE — comparable to `_build_request_body` (already extracted at line 65). Cross-adapter extraction is Phase-5+ territory.

**Recommended signature:**
```python
def _post_messages(
    self,
    body: dict,
    headers: dict,
    correlation_id: str,
    extra: dict,
) -> dict:
    """POST to /messages, parse envelope, raise typed errors on 4xx/5xx, return JSON dict on 2xx.

    Shared by complete() and classify_with_tool(). Owns: requests.post,
    Timeout/RequestException mapping, MGTI error-envelope parsing
    (lines 282-288), 401/403/429/5xx dispatch (lines 290-307), generic
    LLMError catch-all (lines 309-315). Does NOT own response-body parsing
    beyond the error-envelope lookup — that's caller-specific (complete()
    extracts text blocks; classify_with_tool extracts tool_use blocks).

    The `extra` dict is mutated in-place for log enrichment (llm_outcome,
    llm_error_type) — caller's finally block emits the llm_call event.
    """
    url = f"{self._base_url.rstrip('/')}/model/{self._model}/messages"
    try:
        response = requests.post(url, headers=headers, json=body, timeout=self._timeout_s)
    except requests.exceptions.Timeout as e:
        extra["llm_error_type"] = "LLMTimeoutError"
        extra["llm_outcome"] = "timeout"
        raise LLMTimeoutError(
            f"Anthropic MGTI request timed out after {self._timeout_s}s: {e}",
            provider="anthropic_mgti", correlation_id=correlation_id,
        ) from e
    except requests.exceptions.RequestException as e:
        extra["llm_error_type"] = "LLMTransientError"
        extra["llm_outcome"] = "transient_error"
        raise LLMTransientError(
            f"Anthropic MGTI request failed: {e}",
            provider="anthropic_mgti", correlation_id=correlation_id,
        ) from e

    if not response.ok:
        # ... lines 281-315 of complete() moved here verbatim
        ...

    return response.json()
```

**Both call sites then look like:**
```python
# complete() — replaces lines 269-315 with one helper call
try:
    data = self._post_messages(body, headers, correlation_id, extra)
    # ... lines 318-403 (response parsing) unchanged
finally:
    extra["llm_latency_ms"] = int((time.monotonic() - t0) * 1000)
    _log_llm_call(extra)

# classify_with_tool() — same try/finally structure with its own response parsing
```

**WARNING:** The current `complete()` has the `t0` and `finally:` block AROUND the `try` that contains `requests.post`. Moving the post into `_post_messages` means the `finally` and timing must stay in the CALLER. The helper does NOT own timing or log emission — only HTTP + error mapping. This is the load-bearing detail to preserve symmetry between the two call sites.

### Pattern 4: Text-mode fallback (`_classify_via_text_mode`)

**What:** Internal method called when `self._tools_supported is False`. Mirrors Azure's `classify_with_tool` (`azure_openai.py:224-295`) but stays inside `AnthropicMGTIClient` (no cross-adapter import).

**Recommended skeleton:**
```python
def _classify_via_text_mode(
    self,
    messages: list[dict],
    tool: ToolSchema,
    *,
    tool_name: str,
) -> ToolCall:
    """Text-mode escape hatch: injects schema as system prompt, parses JSON.

    Triggered ONLY by self._tools_supported is False (CONTEXT.md
    §Fallback strategy: env-flag-only, no runtime auto-fallback).

    Produces a ToolCall identical to the strict-tools path — downstream
    cannot tell which path produced the result. Both paths run
    jsonschema.validate on the parsed dict.
    """
    import json
    import jsonschema

    # Pattern mirrors azure_openai.py:254-264 (intentional duplication
    # per CONTEXT.md — keep self-contained)
    enriched = list(messages) + [
        {
            "role": "system",
            "content": (
                f"You are calling the tool `{tool.name}`. "
                f"Respond ONLY with a JSON object matching this schema:\n"
                f"{json.dumps(tool.input_schema)}\n"
                f"Do not include markdown code fences or commentary."
            ),
        }
    ]
    raw = self.complete(enriched)  # delegates to text-mode complete()

    # Markdown-fence stripping — MIRROR query_router.py:144-148 exactly
    content = raw.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e:
        raise LLMSchemaError(
            f"Anthropic MGTI text-mode returned invalid JSON for tool "
            f"{tool.name!r}: {e}",
            provider="anthropic_mgti",
        ) from e

    try:
        jsonschema.validate(parsed, tool.input_schema)
    except jsonschema.ValidationError as e:
        raise LLMSchemaError(
            f"Anthropic MGTI text-mode response failed schema validation "
            f"for {tool.name!r}: {e.message}",
            provider="anthropic_mgti",
        ) from e

    return ToolCall(tool_name=tool_name, input=parsed, raw_response={"content": raw})
```

### Pattern 5: `classify_intent` migration (heuristic-merge AFTER LLM)

**What:** Migrate `src/query_router.py:101-175` from `client.complete()` + `json.loads` to `client.classify_with_tool(INTENT_TOOL)` + heuristic merge.

**Current code to replace (lines 137-169):**
```python
client = get_llm()
with llm_to_query_error():
    content = client.complete(messages, max_tokens=500).strip()

# Parse JSON response
try:
    # Handle markdown code blocks
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()

    result = json.loads(content)
except json.JSONDecodeError as e:
    logger.error(f"Failed to parse classification response: {content}")
    # Fallback to heuristic classification
    return _heuristic_classify(user_query)

# Validate intent
if result.get("intent") not in ["structured", "semantic", "hybrid"]:
    result["intent"] = _heuristic_classify(user_query)["intent"]

logger.info(f"Classified as: {result['intent']} (confidence: {result.get('confidence', 0)})")

return {
    "intent": result.get("intent", "structured"),
    "confidence": result.get("confidence", 0.5),
    "reasoning": result.get("reasoning", ""),
    "detected_filters": result.get("detected_filters", {}),
    "chart_requested": chart_requested,    # ← heuristic-populated (line 121)
    "chart_type": chart_type               # ← heuristic-populated (line 121)
}
```

**Post-Phase-4 target:**
```python
client = get_llm()
with llm_to_query_error():
    call = client.classify_with_tool(messages, INTENT_TOOL, tool_name="classify_intent")

result = call.input  # dict matching ClassificationResultV1 fields

logger.info(f"Classified as: {result['intent']} (confidence: {result.get('confidence', 0)})")

# CRITICAL: heuristic-merge AFTER LLM (TOOL-04 — LLM cannot overwrite)
return {
    "intent": result.get("intent", "structured"),
    "confidence": result.get("confidence", 0.5),
    "reasoning": result.get("reasoning", ""),
    "detected_filters": result.get("detected_filters", {}),
    "chart_requested": chart_requested,    # from heuristic at line 121 (unchanged)
    "chart_type": chart_type,              # from heuristic at line 121 (unchanged)
}
```

**Heuristic-fallback try/except at lines 171-175 (`except QueryError: raise` + `except Exception`) STAYS UNCHANGED** — it already correctly routes LLM failures (now including `LLMSchemaError` translated to `QueryError`) to `_heuristic_classify`. The `LLMSchemaError → QueryError` translation happens via `_compat.py:111-117`'s catch-all branch (Phase 3 already locked this).

### Pattern 6: Smoke script structure

**What:** `scripts/smoke_llm.py` — single-file operator-run script.

**Skeleton (mirror `tests/manual/observe_correlation_echo.py:1-97`):**
```python
"""scripts/smoke_llm.py — live-credential smoke test gate for Phase 5.

Usage:
    python scripts/smoke_llm.py --provider both       # default; SKIPs missing creds
    python scripts/smoke_llm.py --provider azure_openai
    python scripts/smoke_llm.py --provider anthropic_mgti  # FAIL if creds missing
    python scripts/smoke_llm.py --provider both --verbose

Exit codes:
    0 = all configured providers passed all checks
    1 = at least one CONFIGURED provider's check failed

CONTINUE ON FAILURE: runs all checks for all selected providers regardless
of intermediate failures; aggregates final tally.

Operator-run only — NOT in CI (live credentials cannot live in CI per
.planning/phases/04-strict-tools-smoke-test/04-CONTEXT.md §Smoke script
credential & provider model).
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from typing import Callable

import requests
from dotenv import load_dotenv

# load_dotenv() must be called BEFORE importing src.llm modules so
# load_settings() picks up the env. The root config.py also calls
# load_dotenv() but scripts/ is outside its import path and importing
# config.py has side effects (creates data/ and db/ dirs).
load_dotenv()

# Import AFTER load_dotenv so adapter __init__ sees env vars
from src.llm import get_llm
from src.llm.config import load_settings
from src.llm.types import INTENT_TOOL  # added in Plan 01

REDACT_HEADERS = {"X-Api-Key", "Authorization", "api-key"}
BENIGN_COMPLETE_PROMPT = "Reply with the single word OK."
BENIGN_CLASSIFY_QUERY = "how many incidents are open"


@dataclass
class CheckResult:
    provider: str
    check_name: str
    status: str  # "PASS" | "FAIL" | "SKIP"
    latency_ms: int | None
    detail: str  # one-line summary including shape={...}
    error: str | None = None


def _redact_headers(headers: dict) -> dict:
    return {k: ("***" if k in REDACT_HEADERS else v) for k, v in headers.items()}


def _shape(d: dict) -> str:
    return "{" + ", ".join(sorted(d.keys())) + "}"


def _check_anthropic_service_info(settings, verbose: bool) -> CheckResult:
    """GET {base_url}/ — service-info diagnostic per SC #5."""
    url = settings.anthropic_base_url.rstrip("/") + "/"
    headers = {"X-Api-Key": settings.anthropic_api_key}
    t0 = time.monotonic()
    try:
        resp = requests.get(url, headers=headers, timeout=settings.anthropic_timeout_s)
        latency = int((time.monotonic() - t0) * 1000)
        # ... build CheckResult with shape={...}; print redacted headers if verbose
    except Exception as e:
        return CheckResult(..., status="FAIL", ...)


def _check_anthropic_complete(client, verbose: bool) -> CheckResult:
    ...  # similar pattern with client.complete([{"role":"user","content": BENIGN_COMPLETE_PROMPT}])


def _check_anthropic_classify(client, verbose: bool) -> CheckResult:
    ...  # client.classify_with_tool([{"role":"user","content": BENIGN_CLASSIFY_QUERY}], INTENT_TOOL, tool_name="classify_intent")


def _check_azure_complete(client, verbose: bool) -> CheckResult:
    ...


def _check_azure_classify(client, verbose: bool) -> CheckResult:
    ...


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--provider",
        choices=["azure_openai", "anthropic_mgti", "both"],
        default="both",
    )
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    settings = load_settings()
    selected = {"azure_openai", "anthropic_mgti"} if args.provider == "both" else {args.provider}

    results: list[CheckResult] = []

    # Anthropic
    if "anthropic_mgti" in selected:
        if settings.anthropic_base_url and settings.anthropic_api_key and settings.anthropic_model:
            client = get_llm("anthropic_mgti")
            results.append(_check_anthropic_service_info(settings, args.verbose))
            results.append(_check_anthropic_complete(client, args.verbose))
            results.append(_check_anthropic_classify(client, args.verbose))
        else:
            reason = "ANTHROPIC_BASE_URL/API_KEY/MODEL not all set"
            if args.provider == "anthropic_mgti":
                # Explicit selection — SKIP becomes FAIL (CONTEXT.md §Smoke credential)
                results.append(CheckResult("anthropic_mgti", "creds", "FAIL", None, reason))
            else:
                results.append(CheckResult("anthropic_mgti", "creds", "SKIP", None, reason))

    # Azure — symmetric pattern
    # ...

    # Print per-check lines, then summary; return 0 or 1
    for r in results:
        print(f"[{r.status}] {r.provider:14s} / {r.check_name:18s} → {r.detail}")
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    skipped = sum(1 for r in results if r.status == "SKIP")
    exit_code = 1 if failed > 0 else 0
    print(f"\nSummary: {passed} passed, {failed} failed, {skipped} skipped — exit {exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
```

### Anti-Patterns to Avoid

- **Calling `dataclasses.fields(cls)[i].type` directly under `from __future__ import annotations`** — returns strings, not types. ALWAYS use `typing.get_type_hints(cls)`.
- **Heuristic merge BEFORE LLM call** — TOOL-04 lock. The `_detect_chart_request()` at `query_router.py:121` already runs first; the merge happens at the final-dict construction (lines 162-169) which uses the locals, NOT the LLM result. Phase 4 must NOT regress by reading `result.get("chart_requested")`.
- **Importing `config.py` (root) from `scripts/smoke_llm.py`** — has side effects (creates `data/`, `db/` dirs). Call `load_dotenv()` directly.
- **Cross-adapter import of text-mode helper** — DO NOT import `AzureOpenAIClient.classify_with_tool` body from `anthropic_mgti.py`. Intentional duplication per CONTEXT.md.
- **`response.raise_for_status()` in Anthropic path** — would prevent MGTI envelope parsing. Use `if not response.ok:` (Phase 3 already locked this at `anthropic_mgti.py:280`).
- **Asserting on service-info response shape** — CONTEXT.md §Service-info: "Status code 200 is sufficient. Response shape captured to stdout (top-level keys) but NOT asserted — the MGTI service-info schema is undocumented and asserting fields would break on proxy upgrades."
- **Adding a `--json` flag** — CONTEXT.md explicit deferral.
- **Bare `except Exception:` in smoke checks** — CONTEXT.md §CONTINUE ON FAILURE requires each check to capture its own error and continue. Catch `Exception` per check, NOT once around the loop.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON-schema validation of tool_use input | Custom dict-shape walker | `jsonschema.validate(input_dict, tool.input_schema)` | Already pinned (`requirements.txt:18`); Azure path already uses this (`azure_openai.py:284`); raises `jsonschema.ValidationError` with `.message` attribute |
| Markdown-fence stripping from text-mode JSON | Regex | Literal `content.split("```")[1]` then check `if content.startswith("json"): content = content[4:]` (mirror `query_router.py:144-148`) | Already-validated pattern in Azure path (`azure_openai.py:268-273`) + current `classify_intent` |
| Derived JSON schema from Python dataclass | Pydantic `BaseModel.model_json_schema()` | Hand-rolled walk over `typing.get_type_hints()` + small type-map | CONTEXT.md explicitly forbids pydantic dep; `ClassificationResultV1` is small (5 fields, all primitives + 1 dict) |
| HTTP timeout/retry/error mapping in `classify_with_tool` | New impl | Extract `_post_messages` helper from `complete()` (lines 268-315) | CONTEXT.md §Code structure mandates intra-module helper |
| Loading `.env` from script | Manual file parse | `from dotenv import load_dotenv; load_dotenv()` | Already pinned (`requirements.txt:4`); used by root `config.py:7` |
| Service-info GET vs `complete()` shared error handling | Reuse adapter helper | Use `requests.get` directly in smoke; do NOT add `get_service_info()` to adapter | Adapter has no such method today; smoke is operator-run and should be self-contained (CONTEXT.md §Pytest tests stay 100% mocked) |
| Per-check error capture in smoke | Try-once-around-loop | Try inside each `_check_*` returning `CheckResult` | CONTINUE-ON-FAILURE invariant requires per-check isolation |

**Key insight:** All the "smart" derivation, fallback, retry, and parsing logic already exists somewhere in the tree — Phase 4 is mostly composition. The single net-new mechanical piece is the `dataclass → JSON-schema` reflection helper, which is ~30 lines.

---

## Common Pitfalls

### Pitfall 1: Forward-reference annotations break `dataclasses.fields(...).type`

**What goes wrong:** Planner writes `for f in fields(ClassificationResultV1): if f.type is str:` — every `f.type` is the string `"str"` not the type `str`, so the dispatch never matches, and the derived schema has empty `properties`.

**Why it happens:** `src/llm/types.py:10` uses `from __future__ import annotations` (PEP 563), which makes ALL annotations forward references (strings). `dataclasses.fields()` doesn't resolve them. Easy to miss because in a REPL without future-annotations it Just Works.

**How to avoid:** Always use `typing.get_type_hints(ClassificationResultV1)` to get real type objects keyed by field name. Then iterate `fields(cls)` for ordering / required-detection, and look up types in the hints dict.

**Warning signs:** Test for SC #1 (`assert 'intent' in INTENT_TOOL.input_schema['properties']`) fails; `properties` dict is empty.

### Pitfall 2: `max_tokens` truncation during tool_use is silently accepted

**What goes wrong:** Planner copies the Phase 3 `complete()` `stop_reason == "max_tokens"` semantics (truncation as `outcome="truncated"`, NOT an error) into `classify_with_tool`. A partial `tool_use.input` dict then passes the `name == tool_name` check, fails `jsonschema.validate` with a confusing "missing required field" message, and the operator can't tell whether the model rejected the schema or just ran out of tokens.

**Why it happens:** Symmetry temptation — copy-paste the entire `complete()` response-parsing block.

**How to avoid:** CONTEXT.md error matrix explicitly locks `max_tokens during tool_use = LLMSchemaError`. Phase 4 must DIVERGE from `complete()` here. The error message must mention "raise ANTHROPIC_MAX_TOKENS" so the operator knows the remediation.

**Warning signs:** Acceptance gate test for max_tokens-during-tool_use case fails because adapter returns successfully instead of raising.

### Pitfall 3: Mixed `text`+`tool_use` content blocks

**What goes wrong:** Planner assumes `content[0].type == "tool_use"`. The Anthropic API docs explicitly show a mixed response (`platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls`, verified 2026-05-21):
```json
"content": [
  {"type": "text", "text": "I'll check the current weather in San Francisco for you."},
  {"type": "tool_use", "id": "toolu_...", "name": "get_weather", "input": {...}}
]
```
Indexing `content[0]` and asserting `type == "tool_use"` would surface as a spurious `LLMSchemaError`.

**Why it happens:** Easy to assume tool_use is the only block; defensive iteration is rarely modeled in docs examples.

**How to avoid:** ALWAYS iterate `content_blocks` and pick the FIRST block whose `type == "tool_use"` AND `name == tool_name`. The `disable_parallel_tool_use=True` flag prevents multiple `tool_use` blocks but does NOT prevent preceding `text` blocks.

**Warning signs:** Sporadic strict-tools failures when the model decides to explain itself before calling the tool.

### Pitfall 4: `jsonschema 4.25` vs `>=4.26` mismatch

**What goes wrong:** Acceptance gate import fails with `ImportError: cannot import name X from jsonschema` because the project's installed version is `4.25.1` (verified via `pip show jsonschema` 2026-05-21) but `requirements.txt:18` pins `>=4.26.0,<5`.

**Why it happens:** Phase 1 added `jsonschema>=4.26.0,<5` to `requirements.txt` but the dev environment wasn't upgraded.

**How to avoid:** Plan 04 (acceptance gate) MUST include a precondition: `pip install -U "jsonschema>=4.26.0,<5"`. Phase 2's `jsonschema.validate` call in `AzureOpenAIClient.classify_with_tool` (`azure_openai.py:284`) is generic enough to work on either version, so the bug only surfaces if Plan 04 uses 4.26+-only API.

**Warning signs:** Acceptance gate red on first run; `pip list | grep jsonschema` shows 4.25.

### Pitfall 5: Smoke script imports happen BEFORE `load_dotenv()`

**What goes wrong:** Smoke script does `from src.llm import get_llm` at the top of the file, then `load_dotenv()` inside `main()`. `load_settings()` reads `os.environ` at first call; on the first `get_llm()` call all env vars are still empty, so the adapter raises `LLMConfigError` even though `.env` is present.

**Why it happens:** Standard "imports at top" Python style conflicts with the need for env loading before module-level adapter construction. The root `config.py:7,13` already does this correctly (imports `load_dotenv` at top of file, calls it BEFORE constants are defined).

**How to avoid:** In `scripts/smoke_llm.py`, call `load_dotenv()` at module top-level (BEFORE `from src.llm import get_llm`). The `load_dotenv` import itself is from `python-dotenv` which has no side effects.

**Warning signs:** Smoke script always reports "ANTHROPIC_BASE_URL not set" even when `.env` has it set.

### Pitfall 6: `classify_with_tool` log event drops `stop_reason`

**What goes wrong:** Planner adds the `llm_tool_mode: "strict" | "text_fallback"` field (CONTEXT.md §classify_with_tool log) but forgets that text-mode goes through `complete()` (which already logs). Result: ONE call produces TWO `llm_call` log events (text-mode's complete() + classify_with_tool's wrapper), confusing dashboards.

**Why it happens:** Easy to add log emission to both paths without realizing the text-mode path delegates to `complete()`.

**How to avoid:** Only emit `llm_call` from the strict-tools path (where `_post_messages` is the entry); the text-mode path delegates to `complete()` and inherits its log. Document this asymmetry in the docstring of `_classify_via_text_mode`. Alternatively: add a kwarg to `complete()` like `_log_emit: bool = True` and pass `False` from text-mode wrapper, then have the wrapper emit one event with `llm_tool_mode: "text_fallback"`.

**Warning signs:** Phase 4 acceptance gate test counts log events and finds 2 where 1 expected; or operator dashboards show 2x call volume for text-mode operators.

### Pitfall 7: Acceptance gate executes the smoke script

**What goes wrong:** Plan 04 author writes a test that runs `subprocess.run(["python", "scripts/smoke_llm.py"])` to "really verify it works." Test depends on live network OR fails because credentials aren't set in the test environment.

**Why it happens:** Natural temptation when testing a script.

**How to avoid:** CONTEXT.md §Verification strategy SC #5 explicitly locks the verification surface: "File-existence check on `scripts/smoke_llm.py`; syntax check via `py_compile`. NO execution from pytest (operator-run gate). Optionally: import the script's `main()` and call with a mocked `requests` session to verify the check-orchestration logic." Plan 04 acceptance test for SC #5 must NOT invoke the script. Use `os.path.exists` + `py_compile.compile(path, doraise=True)`.

**Warning signs:** Acceptance gate fails in CI/sandbox because creds missing; OR gate makes real HTTP calls.

---

## Code Examples

### Schema derivation helper (production-ready)

```python
# In src/llm/types.py (add at the bottom; or new src/llm/_intent_tool.py)
# Source: derived from CONTEXT.md §Claude's Discretion + verified empirically 2026-05-21
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
    """Map a Python type (resolved via get_type_hints) to its JSON schema fragment.

    Handles primitives, dict, list. Literal[...] becomes string-enum.
    Optional / Union with None becomes nullable. Raises NotImplementedError
    on unsupported shapes — keep the surface deliberately narrow so v2 needs
    a deliberate extension, not a silent regression.
    """
    origin = typing.get_origin(py_type)
    args = typing.get_args(py_type)

    if origin is typing.Literal:
        # All literal args must be the same primitive type
        return {"type": "string", "enum": list(args)}

    # Optional[X] / X | None → expand into nullable
    if origin in (typing.Union,) or (
        py_type.__class__.__name__ == "UnionType"
    ):
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
    """Reflect cls's @dataclass fields into a JSON Schema 'object'."""
    hints = typing.get_type_hints(cls)
    properties: dict[str, dict] = {}
    required: list[str] = []
    for f in fields(cls):
        properties[f.name] = _py_type_to_json_schema(hints[f.name])
        if f.default is MISSING and f.default_factory is MISSING:
            required.append(f.name)
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


# Top-level constant — single source of truth (TOOL-02)
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

### Anthropic strict-tools request body (verified shape)

```python
# Source: platform.claude.com/docs/en/api/messages (verified 2026-05-21)
{
    "anthropic_version": "bedrock-2023-05-31",
    "messages": [{"role": "user", "content": "how many incidents are open"}],
    "max_tokens": 1024,
    "tools": [
        {
            "name": "classify_intent",
            "description": "Classify a user query...",
            "input_schema": {
                "type": "object",
                "properties": {
                    "version": {"type": "string"},
                    "intent": {"type": "string"},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": "string"},
                    "detected_filters": {"type": "object"},
                },
                "required": ["version", "intent", "confidence", "reasoning", "detected_filters"],
                "additionalProperties": False,
            },
        }
    ],
    "tool_choice": {
        "type": "tool",
        "name": "classify_intent",
        "disable_parallel_tool_use": True,
    },
}
```

### Anthropic strict-tools response shape (HIGH-confidence — official)

```json
// Source: platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls
// (verified 2026-05-21)
{
  "id": "msg_01Aq9w938a90dw8q",
  "model": "claude-sonnet-4-5-...",
  "stop_reason": "tool_use",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "I'll classify this query for you."
    },
    {
      "type": "tool_use",
      "id": "toolu_01A09q90qw90lq917835lq9",
      "name": "classify_intent",
      "input": {
        "version": "v1",
        "intent": "structured",
        "confidence": 0.95,
        "reasoning": "...",
        "detected_filters": {}
      }
    }
  ],
  "usage": {"input_tokens": 500, "output_tokens": 30}
}
```

Verified facts:
- Field name is `name` (NOT `tool_name`) ✓
- Field name is `input` (NOT `arguments`) ✓
- `stop_reason` value is `"tool_use"` (NOT `"end_turn"`) when tool called ✓
- `id` is opaque `toolu_...` ✓
- `content` may contain MIXED `text` + `tool_use` blocks ✓
- `disable_parallel_tool_use: true` prevents MULTIPLE `tool_use` blocks but NOT preceding `text` blocks

### `jsonschema.validate` usage (canonical pattern)

```python
# Source: python-jsonschema.readthedocs.io (verified 2026-05-21) + azure_openai.py:283-289
import jsonschema

try:
    jsonschema.validate(input_dict, tool.input_schema)
except jsonschema.ValidationError as e:
    # e.message — short human-readable error
    # e.path — deque of keys leading to the failure (rarely needed for logs)
    raise LLMSchemaError(
        f"tool_use input failed schema validation: {e.message}",
        provider="anthropic_mgti",
    ) from e
```

### Smoke script check-result printing

```python
# CONTEXT.md §Smoke output reference output
[PASS] anthropic_mgti  / service-info       → 200 in 312ms  shape={api_version, supported_models}
[PASS] anthropic_mgti  / complete           → 200 in 412ms  model=eu.anthropic.claude-sonnet-4-5-...  shape={id, type, role, content, model, stop_reason, usage}
[PASS] anthropic_mgti  / classify_with_tool → 200 in 521ms  intent=structured  shape={id, type, role, content[tool_use], model, stop_reason, usage}
[PASS] azure_openai    / complete           → 200 in 287ms  model=gpt-4o-mini  shape={id, object, choices, usage}
[PASS] azure_openai    / classify_with_tool → 200 in 311ms  intent=structured  shape={id, object, choices, usage}

Summary: 5 passed, 0 failed, 0 skipped — exit 0
```

---

## Answers to the 12 Research Questions

### Q1: Schema derivation mechanics

**Answer:** Use `typing.get_type_hints(ClassificationResultV1)` (NOT `dataclasses.fields(...).type` which returns strings under `from __future__ import annotations`). Walk `fields(cls)` for ordering and required-detection (a field without `default` AND without `default_factory` is required). Map primitives via a small dict: `str→string`, `float→number`, `int→integer`, `bool→boolean`, `dict→object`, `list→array`. Handle `Literal[...]` via `typing.get_origin(t) is typing.Literal` + `typing.get_args(t)` → `{"type": "string", "enum": list(args)}`. Handle `Optional[X]` / `X | None` via `Union` detection → nullable. No deny-list needed — `chart_requested`/`chart_type` aren't in the dataclass by design (TOOL-03 lock). For v1, `version: str` stays `{"type": "string"}` (NOT enum/const — see Open Question 1 below).

### Q2: Anthropic tool_use response anatomy

**Answer (HIGH confidence — verified against `platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls`):**
- `stop_reason: "tool_use"` is returned when a tool is called (NOT `end_turn`)
- `content` is an array that may contain MIXED block types — `text` blocks may precede `tool_use` blocks
- `tool_use` block fields: `type` (== `"tool_use"`), `id` (opaque `toolu_...`), `name` (matches the tool name), `input` (dict matching `input_schema`)
- Field name is `name` (NOT `tool_name`) and `input` (NOT `arguments`) — verified verbatim
- With `disable_parallel_tool_use: true`, exactly ONE `tool_use` block; without it, multiple are possible
- Defensive iteration: planner must iterate `content_blocks` finding first block where `type=="tool_use"` AND `name==tool_name`

### Q3: `jsonschema` library

**Answer:** Already pinned in `requirements.txt:18` as `jsonschema>=4.26.0,<5`. Already used in `src/llm/azure_openai.py:284-289` so the pattern is established. **Installed version on dev box is 4.25.1** (verified via `pip show jsonschema` 2026-05-21) — Plan 04 must include `pip install -U "jsonschema>=4.26.0,<5"` precondition. Canonical pattern: `jsonschema.validate(instance_dict, schema_dict)` raises `jsonschema.ValidationError` which has `.message` (short string) and `.path` (deque of keys) attributes. Use `e.message` in `LLMSchemaError` body (mirror Azure path).

### Q4: Text-mode fallback prompt construction

**Answer:** Mirror `src/llm/azure_openai.py:254-264` exactly (intentional duplication per CONTEXT.md §Fallback strategy):
```python
enriched = list(messages) + [
    {
        "role": "system",
        "content": (
            f"You are calling the tool `{tool.name}`. "
            f"Respond ONLY with a JSON object matching this schema:\n"
            f"{json.dumps(tool.input_schema)}\n"
            f"Do not include markdown code fences or commentary."
        ),
    }
]
```
The fence-stripping pattern at `src/query_router.py:144-148` is:
```python
if content.startswith("```"):
    content = content.split("```")[1]
    if content.startswith("json"):
        content = content[4:]
    content = content.strip()
```
This is also duplicated in `azure_openai.py:268-273`. Phase 4 should use this same literal pattern in `_classify_via_text_mode` (CONTEXT.md §Specifics: "mirror query_router.py:144-148").

### Q5: Smoke script HTTP plumbing

**Answer:**
- For Anthropic `complete()` smoke: call `get_llm("anthropic_mgti").complete(...)` directly — the adapter owns the HTTP shape; smoke script doesn't reconstruct it.
- For `classify_with_tool()` smoke: same — call `client.classify_with_tool(messages, INTENT_TOOL, tool_name="classify_intent")`.
- For Anthropic `GET /coreapi/llm/anthropic/v1/` service-info: **smoke script constructs the URL itself** by reading `settings.anthropic_base_url` and calling `requests.get(base_url.rstrip("/") + "/", headers={"X-Api-Key": api_key}, timeout=settings.anthropic_timeout_s)`. There is NO `get_service_info()` helper on `AnthropicMGTIClient` and one should NOT be added — service-info is operator-tooling, not production code path.
- Timeout: use `settings.anthropic_timeout_s` (default 30s per `src/llm/config.py:107`) for symmetry with Phase 3 `complete()`.
- Redact-headers pattern: `{k: ("***" if k in {"X-Api-Key", "Authorization", "api-key"} else v) for k, v in headers.items()}`. Only print in `--verbose` mode (CONTEXT.md §Smoke output: "Default (non-verbose) mode never prints headers").

### Q6: `load_dotenv()` integration

**Answer:** Root-level `config.py:7,13` is the ONLY place in the codebase that calls `load_dotenv()`. `app.py` (project root, NOT `src/app.py`) imports from `src/query_router` which transitively imports `src/llm/config.py` — but **`src/llm/config.py:8-10` explicitly does NOT call `load_dotenv()`** because the root `config.py` already did. The smoke script lives outside both `config.py`'s import chain AND the Streamlit lifecycle, so it MUST call `load_dotenv()` itself. Pattern: `from dotenv import load_dotenv` at top of `scripts/smoke_llm.py`, then `load_dotenv()` at module level BEFORE the `from src.llm import get_llm` import (so the first `load_settings()` call sees the env). DO NOT import root `config.py` — it has side effects (`DATA_DIR.mkdir(exist_ok=True)`, `DB_DIR.mkdir(exist_ok=True)` at lines 30-31).

### Q7: `tools_supported` log field placement

**Answer:** Phase 3 adapter `__init__` log site is at `src/llm/anthropic_mgti.py:178-181`:
```python
logger.info(
    "llm_provider_loaded",
    extra={"provider": "anthropic_mgti", "base_url": self._base_url},
)
```
Phase 4 adds `tools_supported: bool`:
```python
logger.info(
    "llm_provider_loaded",
    extra={
        "provider": "anthropic_mgti",
        "base_url": self._base_url,
        "tools_supported": self._tools_supported,
    },
)
```
Order is operator's choice (CONTEXT.md §Claude's Discretion: "alphabetical, order-of-definition, etc."). Recommend keeping existing field order and appending `tools_supported` at the end — minimizes diff and matches order-of-definition. The acceptance gate's existing log-capture test `test_startup_log_anthropic_provider` (`tests/test_phase3_adapter.py:423-440`) DOES NOT assert the absence of extra fields, so this is backward-compatible. Phase 4 may want to ADD an assertion `assert getattr(ev, 'tools_supported') is True` in a new test.

### Q8: Existing `classify_intent` call site (current code captured verbatim)

**Answer:** See "Pattern 5" above for the EXACT current-vs-target diff. Key load-bearing details:
- Line 121 (`_detect_chart_request(user_query)`) runs FIRST, producing locals `chart_requested, chart_type`.
- Lines 137-139: `client = get_llm()` + `with llm_to_query_error(): content = client.complete(messages, max_tokens=500).strip()` — replaced with `call = client.classify_with_tool(messages, INTENT_TOOL, tool_name="classify_intent")` (no `.strip()` needed — `ToolCall.input` is a dict).
- Lines 144-148 (fence stripping) DELETED — the `ToolCall.input` dict is already-validated against `tool.input_schema`.
- Lines 150-154 (`json.loads` + JSONDecodeError fallback to `_heuristic_classify`) DELETED — schema-validation errors now propagate as `LLMSchemaError` → `QueryError` → caught by `except Exception` at line 173 → routed to `_heuristic_classify`.
- Lines 157-158 (intent-validation against allowed values) DELETED — schema enforces `intent` is one of `structured|semantic|hybrid` (consider adding an `enum` constraint to `intent`'s schema definition, although currently `ClassificationResultV1.intent` is plain `str`).
- Lines 162-169 (final dict construction with heuristic merge) STAYS structurally identical: read LLM fields from `call.input.get(...)` instead of `result.get(...)`; `chart_requested`/`chart_type` continue to come from the heuristic locals.
- Lines 171-175 (try/except/heuristic-fallback) STAYS UNCHANGED — already handles `QueryError` correctly.

### Q9: `_compat.py` dispatch for `classify_with_tool` errors

**Answer:** Phase 3's `_compat.py:111-117` catch-all `except LLMError` branch already dispatches by `e.provider`:
```python
except LLMError as e:
    if getattr(e, "provider", None) == "anthropic_mgti":
        raise QueryError("Anthropic API call failed", str(e)) from e
    raise QueryError("Azure OpenAI API call failed", str(e)) from e
```
This catches `LLMSchemaError`, `LLMGuardrailError`, and any future `LLMError` subclass with NO changes required for Phase 4. The COMPAT-DISPATCH test pattern from `tests/test_phase3_adapter.py:519-552` should be mirrored for Phase 4:
- `test_anthropic_schema_error_translates_to_anthropic_query_error` — verifies `LLMSchemaError(provider="anthropic_mgti")` raised from `classify_with_tool` surfaces as `QueryError("Anthropic API call failed", ...)`.
- `test_anthropic_guardrail_error_translates_to_anthropic_query_error` — same for guardrail.

These tests exercise the catch-all branch path and ensure no regression. NO `_compat.py` edits needed in Phase 4.

### Q10: `scripts/` directory convention

**Answer:** `scripts/` directory does NOT yet exist (verified via `Glob scripts/**/*` — no files found). Phase 4 Plan 03 must create it. There are no sibling scripts to mirror. The closest analog is `tests/manual/observe_correlation_echo.py` (Phase 3 deliverable):
- shebang NOT used (Windows-friendly; invoked as `python scripts/smoke_llm.py`)
- module docstring (8-20 lines) at top with Usage section
- `from __future__ import annotations` first import
- stdlib imports, third-party imports, local imports (PEP 8 grouping)
- `def main() -> int:` returning exit code
- `if __name__ == "__main__": sys.exit(main())` at bottom
- Single file, single class (or just functions). CONTEXT.md §Claude's Discretion: "Single-file is simpler; planner picks."

### Q11: Plan breakdown sanity-check

**Answer:** Recommend the 4-plan split from CONTEXT.md §Claude's Discretion. File overlap analysis:

| Plan | Files touched |
|------|---------------|
| 01 INTENT_TOOL + heuristic merge | `src/llm/types.py` (or `src/llm/_intent_tool.py`), `src/query_router.py` |
| 02 `classify_with_tool` + helpers | `src/llm/anthropic_mgti.py` |
| 03 smoke script | `scripts/smoke_llm.py` (new file) |
| 04 acceptance gate | `tests/test_phase4_strict_tools.py` (new file) |

**Dependency graph:**
- Plan 02 depends on Plan 01 (imports `INTENT_TOOL` for `classify_with_tool` test fixtures? No — Plan 02 takes `tool: ToolSchema` as a param; doesn't need `INTENT_TOOL` specifically. But Plan 01 also migrates `query_router.classify_intent` which calls `client.classify_with_tool(...)` — if Plan 01 lands first, `classify_intent` calls the NotImplementedError stub until Plan 02 lands.)
- Plan 03 depends on Plan 01 (imports `INTENT_TOOL` from `src.llm.types`).
- Plan 03 ALSO depends on Plan 02 (smoke script calls `client.classify_with_tool()` which is `NotImplementedError` until Plan 02).
- Plan 04 depends on ALL three.

**Recommended wave assignment:**
- **Wave 1: Plan 01 ONLY** — establishes `INTENT_TOOL` as a stable import; `query_router.classify_intent` now invokes the NotImplementedError stub, but tests for SC #1 (derivation) pass.
- **Wave 2: Plan 02 + Plan 03 IN PARALLEL** — both depend on Plan 01's `INTENT_TOOL`. Plan 02 touches `anthropic_mgti.py`; Plan 03 creates new `scripts/smoke_llm.py`. ZERO file overlap. After Wave 2, `classify_intent` works end-to-end and smoke script can be run by operators.
- **Wave 3: Plan 04 ONLY** — acceptance gate verifies all 5 SCs + 9 error-matrix rows + COMPAT-DISPATCH.

**Alternative (more conservative, matches Phase 3's 4-wave rhythm):** Plans 01 → 02 → 03 → 04 serially. Adds ~5 min wall-time vs the parallel option, but eliminates the "Plan 02 partially broken if Plan 01 ships first and an operator runs the app" intermediate state. Phase 3 shipped serially despite no file overlap — recommend matching for consistency unless time-pressured.

### Q12: Anthropic strict-tools authoritative spec

**Answer (HIGH confidence — verified against `platform.claude.com/docs/en/api/messages` and `/docs/en/agents-and-tools/tool-use/strict-tool-use`, fetched 2026-05-21):**

- `tool_choice` shape: `{"type": "tool", "name": "tool_name_here", "disable_parallel_tool_use": true}` — field names verified verbatim. `disable_parallel_tool_use` is the correct documented spelling (snake_case in JSON body), and when true limits the response to ONE `tool_use` block.
- `tools[]` entry shape: `{"name": "...", "description": "...", "input_schema": {...}}` — `input_schema` is the JSON Schema dict.
- OPTIONAL `strict: true` on the tool definition activates grammar-constrained sampling for guaranteed schema conformance. **NOT REQUIRED for Phase 4** — CONTEXT.md doesn't lock this in, and it's a separate feature from `tool_choice.type="tool"`. The MGTI proxy may or may not support it; defence-in-depth `jsonschema.validate` catches schema drift either way. Recommend OMITTING `strict: true` from Phase 4 INTENT_TOOL (defer to Phase 5+ once Bedrock strict-mode support is verified).
- MGTI proxy pass-through: STATE.md decisions and `.planning/research/PITFALLS.md:22` (baseline pitfall #10) note "Tools support undocumented but works" — the MGTI proxy forwards `tools` and `tool_choice` to Bedrock unchanged. `ANTHROPIC_TOOLS_SUPPORTED=false` escape hatch exists exactly for the case where this regresses.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Prompt-based JSON parsing for intent classification | Native `tools[]` + `tool_choice` strict-mode | Phase 4 (this phase) | Eliminates fence-stripping, schema-drift risk, JSON parse-error retries |
| `dataclasses.fields(cls)[i].type` for type introspection | `typing.get_type_hints(cls)` | Python 3.10+ with `from __future__ import annotations` (PEP 563) | Forward references in field annotations no longer resolve through `.type` |
| Anthropic SDK `Authorization: Bearer` | MGTI proxy `X-Api-Key` | Phase 3 (project-specific) | Phase 4 inherits — no SDK introduction |
| Service-info-skipped smoke tests | Service-info `GET /` as first check | This phase | Catches `/messages` URL bug (baseline pitfall #1) before any model call |

**Deprecated/outdated:**
- `jsonschema 4.25.x` on dev box (requirements pin `>=4.26.0`) — Plan 04 must upgrade.
- Manual fence-stripping in `query_router.py:144-148` — removed by Plan 01 migration to `classify_with_tool`.
- `result.get("intent", "structured")` defaulting — schema validation now enforces `intent` presence at adapter boundary.

---

## Open Questions

### 1. Should `version: str` become `version: Literal["v1"]`?

**What we know:**
- `ClassificationResultV1.version` is currently typed `str` (`src/llm/types.py:54`).
- A `Literal["v1"]` would tighten the schema to `{"type": "string", "enum": ["v1"]}` instead of `{"type": "string"}`, making the LLM contract more restrictive.
- CONTEXT.md §Deferred Ideas explicitly says: "Schema versioning beyond `version: 'v1'` — `ClassificationResultV1` has `version` as a literal field. A future Phase could derive `v2` schema..."

**What's unclear:**
- "Literal field" in CONTEXT.md may mean "literal string in current code" (descriptive) OR "Python `Literal[]` annotation" (prescriptive).
- Tightening `version` field forces the LLM to actually output `"v1"`, but no downstream code reads/validates it today.

**Recommendation:** Leave as plain `str` for Phase 4. SC #1 only requires presence of `version` in `properties`, not enum constraint. If the planner adds `Literal["v1"]`, do so as a SEPARATE Plan-01 commit so the diff is auditable. The `_py_type_to_json_schema` helper above already handles the `Literal` case correctly.

### 2. Should `intent` get an `enum` constraint?

**What we know:**
- `ClassificationResultV1.intent: str` (no constraint at dataclass level).
- Currently `query_router.py:157-158` validates `result.get("intent") not in ["structured", "semantic", "hybrid"]` — a runtime check that Phase 4 plans to delete.
- Tightening to `Literal["structured", "semantic", "hybrid"]` would push that validation into `jsonschema.validate`.

**What's unclear:**
- Whether the LLM benefits from seeing `enum` (it usually does — fewer hallucinations of intent like "report" or "search").

**Recommendation:** STRONGLY consider adding `Literal["structured", "semantic", "hybrid"]` to `intent`. It's a free win: better LLM accuracy + schema-level enforcement of the values currently enforced by ad-hoc runtime check. Plan 01 can include this if the planner wants tighter schema. If left as plain `str`, ensure the deleted runtime validation doesn't reintroduce a regression — add a test that an out-of-vocabulary intent surfaces as `LLMSchemaError` (which it WON'T without the `enum` constraint — the LLM will silently return junk).

### 3. Should `_classify_via_text_mode` emit its own `llm_call` event?

**What we know:**
- CONTEXT.md §classify_with_tool log specifies `llm_tool_mode: "strict" | "text_fallback"` — both modes log.
- Text-mode delegates to `self.complete()` which ALREADY logs an `llm_call` event with `llm_outcome` etc.

**What's unclear:**
- Whether the dashboard wants ONE event per `classify_with_tool` call (regardless of mode) or whether double-events on text-mode are acceptable.

**Recommendation:** Pitfall 6 above flags this. Recommend the text-mode wrapper passes a kwarg `_suppress_log=True` (or similar) to `complete()` and emits its own event with `llm_tool_mode: "text_fallback"`. Alternative: accept that text-mode produces TWO `llm_call` events (one from `complete`, one from the wrapper) and document this as a known asymmetry. The planner should pick one and document the choice in Plan 02.

---

## Sources

### Primary (HIGH confidence)
- `src/llm/anthropic_mgti.py` (full file, 443 lines) — Phase 3 implementation; structure to mirror
- `src/llm/azure_openai.py` (full file, 295 lines) — text-mode `classify_with_tool` reference at lines 224-295
- `src/llm/base.py` (full file, 85 lines) — `LLMClient` ABC, method signatures
- `src/llm/types.py` (lines 1-76) — `ClassificationResultV1`, `ToolCall`, `ToolSchema` dataclass definitions
- `src/llm/config.py` (lines 41-50, 101-108) — `anthropic_tools_supported` field + `ANTHROPIC_TOOLS_SUPPORTED` env load
- `src/llm/errors.py` (lines 30-52) — `LLMSchemaError`/`LLMGuardrailError` already defined; no new errors needed
- `src/llm/_compat.py` (lines 111-117) — catch-all `LLMError` branch already dispatches by `e.provider`
- `src/query_router.py` (lines 101-175) — current `classify_intent` implementation; lines 121 (heuristic call), 144-148 (fence-stripping), 162-169 (heuristic merge), 171-175 (fallback try/except)
- `tests/test_phase3_adapter.py` (full file) — acceptance gate pattern to mirror
- `tests/manual/observe_correlation_echo.py` (full file) — script pattern to mirror
- `requirements.txt` (full file, 18 lines) — `jsonschema>=4.26.0,<5` already pinned
- `.env.example` (full file, 37 lines) — `ANTHROPIC_TOOLS_SUPPORTED=true` already present
- `platform.claude.com/docs/en/api/messages` — Messages API spec; verified `tool_choice` shape + content block types
- `platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls` — verified `stop_reason: "tool_use"` + mixed `text`+`tool_use` content example
- `platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use` — `strict: true` is OPTIONAL grammar-constrained sampling feature
- `python-jsonschema.readthedocs.io/en/stable/validate/` — `jsonschema.validate` canonical usage + `ValidationError.message`

### Secondary (HIGH confidence, derived empirically)
- `python -c` smoke test verifying `typing.get_type_hints(ClassificationResultV1)` returns real types under `from __future__ import annotations` (run 2026-05-21)
- `python -c` smoke test verifying `typing.get_origin(Literal["v1"]) is typing.Literal` (run 2026-05-21)
- `pip show jsonschema` → installed version is 4.25.1 (run 2026-05-21)
- `Glob scripts/**/*` → no matches; directory does not exist (run 2026-05-21)

### Tertiary (MEDIUM confidence)
- `.planning/research/PITFALLS.md:22` — "Tools support undocumented but works" (baseline pitfall #10 in mgti-anthropic-integration skill)
- CONTEXT.md §Specifics — `disable_parallel_tool_use=True` requirement and defensive iteration recommendation
- `tests/test_phase3_adapter.py:519-552` — COMPAT-DISPATCH test pattern to mirror in Plan 04

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — `jsonschema`/`requests`/`python-dotenv` already in `requirements.txt`; versions pinned
- Architecture patterns: HIGH — All patterns derived from existing Phase 2/3 code (lines cited)
- Anthropic API shape: HIGH — verified verbatim against current official docs (2026-05-21)
- Pitfalls: HIGH — 5 of 7 derived from empirical testing or CONTEXT.md error matrix; 2 derived from established Python gotchas (future-annotations, import-order)
- Code examples: HIGH — schema-derivation tested empirically; HTTP shape verified against docs

**Research date:** 2026-05-21
**Valid until:** 30 days (stable domain — Anthropic Messages API tool-use shape has been stable since 2024; MGTI proxy contract locked in Phase 3 STATE.md)
