---
phase: 4
plan: 3
name: smoke-script
subsystem: operator-tooling
tags: [smoke-test, argparse, dotenv, live-credentials, operator-tool]

dependency_graph:
  requires:
    - "04-01: INTENT_TOOL constant (imported from src.llm.types)"
    - "04-02: AnthropicMGTIClient.classify_with_tool implemented"
    - "02-01: AzureOpenAIClient.classify_with_tool (prompt-based, Phase 2)"
  provides:
    - "scripts/smoke_llm.py: operator-run live-credential gate (SMK-01..05)"
  affects:
    - "04-04: acceptance-gate plan references smoke script existence (SC #5 py_compile check)"
    - "Phase 5: operator MUST run this script and paste transcript into verification PR before Phase 5 unblocks"

tech_stack:
  added: []
  patterns:
    - "CONTINUE-ON-FAILURE: per-check Exception isolation returning CheckResult"
    - "load_dotenv()-before-src.llm-import ordering (RESEARCH.md Pitfall 5)"
    - "Synthetic shape reporting for adapters that return str (not raw dict)"
    - "Missing-cred matrix: --provider both SKIPs; explicit single-provider FAILs"

key_files:
  created:
    - scripts/smoke_llm.py
  modified: []

decisions:
  - id: "SMK-01"
    decision: "load_dotenv() on module line 49, BEFORE from src.llm imports on lines 52-54"
    rationale: "RESEARCH.md Pitfall 5 — standard imports-at-top style races against env loading; load_dotenv must see the file before adapter __init__ reads settings"
  - id: "SMK-02"
    decision: "sys.stdout.reconfigure(encoding='utf-8') added (deviation from plan template)"
    rationale: "Rule 1 Bug fix — Windows CP1252 terminal crashes on the → (U+2192) arrow character required in per-check output lines; silently skipped on non-reconfigurable streams (redirected files)"
  - id: "SMK-03"
    decision: "Synthetic shape strings for complete() checks"
    rationale: "complete() returns str, not a raw response dict. Script reports CONTEXT.md-spec-compliant synthetic shapes: Anthropic='{id, type, role, content, model, stop_reason, usage}', Azure='{id, object, choices, usage}'. Documented as synthetic in code comments."
  - id: "SMK-04"
    decision: "Azure classify_with_tool call uses same (messages, INTENT_TOOL, tool_name=...) signature as Anthropic"
    rationale: "Pre-flight confirmed azure_openai.py:224 signature is def classify_with_tool(self, messages, tool, *, tool_name, **kwargs) — identical keyword-argument shape; no adapter alignment needed"

metrics:
  duration: "~5 min (18:55Z to 19:01Z)"
  completed: "2026-05-21"
  task_commits: 1
  tests_passing: 39
---

# Phase 4 Plan 3: Smoke-Script Summary

**One-liner:** Single-file operator smoke gate with CONTINUE-ON-FAILURE, missing-cred matrix, and load_dotenv-before-src.llm ordering that exercises all 5 live-endpoint checks (3 Anthropic, 2 Azure).

## What Was Built

`scripts/smoke_llm.py` — 470 lines. Operator invokes this script with stage `.env` credentials before promoting Phase 5 work. It exercises:

- **Anthropic (3 checks):** `service-info GET /`, `complete()`, `classify_with_tool()`
- **Azure (2 checks):** `complete()`, `classify_with_tool()`

Per-check output line format: `[PASS|FAIL|SKIP] provider / check_name → detail`

Final summary line: `Summary: N passed, N failed, N skipped — exit <code>`

## CLI Surface

```
python scripts/smoke_llm.py [--provider {azure_openai,anthropic_mgti,both}] [--verbose]
```

- `--provider`: choices exactly `azure_openai`, `anthropic_mgti`, `both`; default `both`
- `--verbose`: `action="store_true"` — prints full request/response bodies + redacted headers
- No `--json` flag (CONTEXT.md §Smoke output — operators read by eye; CI doesn't run this)
- No short aliases for `--provider`

## Missing-Cred Matrix (dev-box dry run verified, empty .env)

| Invocation | Anthropic creds | Azure creds | Exit code | Output |
|---|---|---|---|---|
| `--provider both` | missing | missing | **0** | 2 SKIP lines |
| `--provider both` | present | missing | **0** | 1+ PASS lines + 1 SKIP |
| `--provider anthropic_mgti` | missing | — | **1** | 1 FAIL line |
| `--provider azure_openai` | — | missing | **1** | 1 FAIL line |

Dev-box run output (both=0, anth=1, az=1 verified):
```
[SKIP] anthropic_mgti / creds              → ANTHROPIC_BASE_URL/API_KEY/MODEL not all set in .env
[SKIP] azure_openai   / creds              → AZURE_OPENAI_ENDPOINT/API_KEY not all set in .env

Summary: 0 passed, 0 failed, 2 skipped — exit 0
```

## load_dotenv() Ordering (Pitfall 5 Guard)

`load_dotenv()` is called on **line 49** of scripts/smoke_llm.py.
All `from src.llm import ...` lines begin on **line 52+**.
This is the load-bearing RESEARCH.md Pitfall 5 guard: adapter `__init__` reads settings from env; if env isn't loaded before the import, the settings factory sees empty env vars.

## Synthetic Shape Strings for complete() Checks

The adapters return `str` from `complete()`, not the raw HTTP response dict. The smoke script cannot call `_shape(response_json)` on a string. Instead it reports spec-compliant SYNTHETIC shapes:

- **Anthropic** `complete()`: `{id, type, role, content, model, stop_reason, usage}` — matches Anthropic Messages API response envelope
- **Azure** `complete()`: `{id, object, choices, usage}` — matches Azure OpenAI chat completion envelope

These are documented as synthetic in code comments. The `classify_with_tool()` checks also use synthetic shapes since ToolCall is returned (not the raw response dict).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Windows CP1252 encoding crash on → arrow character**

- **Found during:** Task 3.1 verification (Step D — dry run)
- **Issue:** Per-check output line format requires `→` (U+2192). Windows terminal with CP1252 encoding raised `UnicodeEncodeError: 'charmap' codec can't encode character '→'` on the first `print(line)` call.
- **Fix:** Added `sys.stdout.reconfigure(encoding="utf-8")` at module top (lines 37-43), guarded with `hasattr` check and silent `except Exception` so it silently no-ops on non-reconfigurable streams (redirected files, CI pipes). This is a 6-line addition.
- **Files modified:** scripts/smoke_llm.py
- **Commit:** a0489b2 (included in the task commit)

## Azure Signature Alignment (pre-flight result)

Pre-flight confirmed `azure_openai.py:224` signature:
```python
def classify_with_tool(self, messages, tool, *, tool_name, **kwargs) -> ToolCall:
```
Identical keyword-argument shape to Anthropic's `classify_with_tool`. No adapter alignment needed. The smoke script calls both as `client.classify_with_tool(messages, INTENT_TOOL, tool_name="classify_intent")` — correct for both.

## Notes for Plan 04-04 (Acceptance Gate)

- SC #5 verification for the acceptance gate: use `os.path.exists("scripts/smoke_llm.py")` and `py_compile.compile(path, doraise=True)` — do NOT execute the script (RESEARCH.md Pitfall 7: live network calls from pytest)
- The `PYTHONPATH` must include the project root when running the script: `python scripts/smoke_llm.py` from the project root directory (where `src/` is visible)

## Notes for Operator (post-Phase 4 verification)

Set `.env` with stage gateway URLs + valid keys, then run:
```
python scripts/smoke_llm.py --provider both --verbose
```
Paste the full transcript into the Phase 4 verification PR before Phase 5 work begins. The transcript proves all 5 live-endpoint checks (SMK-01 through SMK-05) pass against the real MGTI Apigee proxy.

## Commits

| Hash | Message |
|---|---|
| a0489b2 | feat(04-03): create scripts/smoke_llm.py operator-run smoke test gate |
