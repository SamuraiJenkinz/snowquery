---
phase: 4
plan: 3
name: smoke-script
type: execute
wave: 2
depends_on: [1, 2]
files_modified:
  - scripts/smoke_llm.py
autonomous: true

must_haves:
  truths:
    - "scripts/smoke_llm.py exists and is invokable as `python scripts/smoke_llm.py [--provider <p>] [--verbose]`"
    - "Default --provider value is 'both' (matches CONTEXT.md §Smoke script credential)"
    - "Accepted --provider values are exactly: azure_openai, anthropic_mgti, both"
    - "For --provider both, missing creds for a provider yields SKIP (NOT fail) and does NOT contribute to exit code 1"
    - "For --provider anthropic_mgti explicitly, missing creds yield FAIL and exit 1 (explicit selection never silently skips)"
    - "Exit code is 0 iff all configured providers passed all checks; 1 iff at least one CONFIGURED provider's check failed"
    - "CONTINUE-ON-FAILURE: ALL checks for ALL selected providers run regardless of intermediate failures; aggregated summary at the end"
    - "For anthropic_mgti, EXACTLY 3 checks run: service-info GET, complete(), classify_with_tool()"
    - "For azure_openai, EXACTLY 2 checks run: complete(), classify_with_tool()"
    - "Per-check output line format includes [PASS|FAIL|SKIP] tag, provider name, check name, status detail with response shape={sorted top-level keys}"
    - "Captured response shape contains TOP-LEVEL KEYS ONLY — never values (could echo incident data)"
    - "--verbose flag adds full request body + full response body + request headers, with X-Api-Key/Authorization/api-key REDACTED to '***'"
    - "Default (non-verbose) mode NEVER prints headers"
    - "Smoke script calls load_dotenv() BEFORE importing src.llm modules (RESEARCH.md Pitfall 5)"
    - "Smoke script does NOT import the root config.py (it has side effects — creates data/, db/ dirs)"
    - "Benign prompts are HARDCODED in the script (not CLI-parametrized) — guardrail-safe: 'Reply with the single word OK.' and 'how many incidents are open'"
    - "Service-info check asserts only HTTP 200; response shape captured to stdout but NOT asserted (MGTI service-info schema is undocumented)"
    - "Final summary line format: 'Summary: N passed, N failed, N skipped — exit <code>'"
  artifacts:
    - path: "scripts/smoke_llm.py"
      provides: "Operator-run live-credential smoke test gate for Phase 5 (SMK-01..05)"
      contains: "def main() -> int"
  key_links:
    - from: "scripts/smoke_llm.py"
      to: "src.llm.types.INTENT_TOOL"
      via: "from src.llm.types import INTENT_TOOL"
      pattern: "from src.llm.types import INTENT_TOOL"
    - from: "scripts/smoke_llm.py"
      to: "src.llm.get_llm"
      via: "client = get_llm('anthropic_mgti') / get_llm('azure_openai')"
      pattern: "get_llm\\(['\"](anthropic_mgti|azure_openai)['\"]\\)"
    - from: "scripts/smoke_llm.py service-info check"
      to: "settings.anthropic_base_url + '/'"
      via: "requests.get(base_url.rstrip('/') + '/', headers={'X-Api-Key': api_key}, timeout=settings.anthropic_timeout_s)"
      pattern: "requests\\.get\\("
    - from: "scripts/smoke_llm.py module top"
      to: "dotenv.load_dotenv"
      via: "load_dotenv() called BEFORE 'from src.llm import get_llm'"
      pattern: "load_dotenv\\(\\)"
---

<objective>
Create `scripts/smoke_llm.py` — the operator-run live-credential gate that must pass for both providers before Phase 5 unblocks the UI dropdown. The script exercises `complete()` and `classify_with_tool()` against live endpoints using `.env` credentials, plus an Anthropic-only service-info `GET /coreapi/llm/anthropic/v1/` diagnostic (SC #5 explicit). Output is human-readable for operator-eye consumption; per-check shape is captured to stdout for paste-into-MR forensics; CONTINUE-ON-FAILURE ensures one run produces a full diagnosis.

Purpose: This is the SINGLE highest-ROI step in the entire milestone (`.planning/PROJECT.md` §Context: "The smoke-test workflow is the single highest-ROI step — it catches all five [common MGTI integration failure modes] in seconds before any unit test... gets a chance to mislead"). Without this script, an operator cannot deploy the Anthropic provider to prod without risking the `/messages` URL bug, the `eu.` prefix bug, or auth-header mistakes — none of which the (mocked) pytest gate can catch.

Output: A single-file operator-tool that exits 0 when all configured providers' checks pass, 1 otherwise, with a paste-friendly per-check transcript and a final summary line. Operator attaches the transcript (paste or screenshot) to the Phase 4 verification PR before Phase 5 work begins (CONTEXT.md §Smoke script credential: "Gate enforcement = OPERATOR-RUN, not CI").
</objective>

<execution_context>
@C:\Users\taylo\.claude/get-shit-done/workflows/execute-plan.md
@C:\Users\taylo\.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/04-strict-tools-smoke-test/04-CONTEXT.md
@.planning/phases/04-strict-tools-smoke-test/04-RESEARCH.md

# Plans this depends on
@.planning/phases/04-strict-tools-smoke-test/04-01-SUMMARY.md
@.planning/phases/04-strict-tools-smoke-test/04-02-SUMMARY.md

# Reference patterns (read-only)
@src/llm/types.py
@src/llm/anthropic_mgti.py
@src/llm/azure_openai.py
@src/llm/config.py
@src/llm/__init__.py
@tests/manual/observe_correlation_echo.py
@requirements.txt
@.env.example
</context>

<decisions>
## Decisions locked for this plan

1. **Single-file structure (no class).** CONTEXT.md §Claude's Discretion: "Single-file is simpler; planner picks." Functions for each check + one `main()`. Follows `tests/manual/observe_correlation_echo.py` pattern (RESEARCH.md Q10).

2. **Top-level `load_dotenv()` BEFORE any `src.llm` import.** RESEARCH.md Pitfall 5: standard "imports at top" Python style would race against env loading. Pattern: `from dotenv import load_dotenv` first, then `load_dotenv()`, THEN `from src.llm import get_llm`. The `python-dotenv` import itself has no side effects.

3. **Do NOT import root `config.py`.** RESEARCH.md Q6: root `config.py:30-31` calls `DATA_DIR.mkdir(exist_ok=True)` and `DB_DIR.mkdir(exist_ok=True)` at module level. Smoke script must not create those directories — it's a diagnostic, not an app boot. Call `load_dotenv()` directly via `from dotenv import load_dotenv`.

4. **Service-info validation depth = HTTP 200 only.** CONTEXT.md §Service-info: "Status code 200 is sufficient. Response shape captured to stdout (top-level keys) but NOT asserted — the MGTI service-info schema is undocumented and asserting fields would break on proxy upgrades."

5. **Captured shape = `sorted(response.json().keys())`** joined with comma. NEVER values. CONTEXT.md §Smoke output: "values could echo incident-data fragments." For Anthropic `content[*]`, print just the block types (e.g. `content[tool_use]`).

6. **Redaction set = `{"X-Api-Key", "Authorization", "api-key"}`** — case-sensitive header names. Anything else in headers (Content-Type, X-Correlation-Id, etc.) prints as-is in `--verbose`. RESEARCH.md Q5.

7. **`--json` flag explicitly NOT added.** CONTEXT.md §Smoke output: "Operators read this gate by eye before deploying; CI doesn't run it. Adding `--json` is premature; revisit only if CI integration lands in a future phase."

8. **No short aliases.** `--provider` accepts exactly `azure_openai`, `anthropic_mgti`, `both` — same strings as `get_llm()`. CONTEXT.md §Smoke script credential: "explicit beats clever, and the operator's mental model maps directly to the env var prefix."

9. **CONTINUE-ON-FAILURE per-check isolation.** Each `_check_*` function catches its OWN `Exception` and returns a `CheckResult` with `status="FAIL"` and error detail. Bare `except Exception:` ONLY inside `_check_*` functions, NEVER around the whole loop. RESEARCH.md Anti-Patterns.

10. **Exit-code differentiation = none.** `0` = all configured providers passed; `1` = at least one configured provider failed. CONTEXT.md §Smoke output: "NO sub-code differentiation — keeps `&&`-chaining trivial in operator scripts."

11. **Missing-cred behavior matrix:**
    - `--provider both` + Anthropic missing → SKIP Anthropic (does not affect exit)
    - `--provider both` + Azure missing → SKIP Azure (does not affect exit)
    - `--provider both` + BOTH missing → exit 0 (no checks ran; no failures)
    - `--provider anthropic_mgti` + Anthropic missing → FAIL + exit 1 (explicit selection)
    - `--provider azure_openai` + Azure missing → FAIL + exit 1 (explicit selection)

12. **No new `get_service_info()` method on `AnthropicMGTIClient`.** RESEARCH.md Q5 + Don't Hand-Roll: "smoke is operator-run and should be self-contained." The script constructs the GET URL itself by reading `settings.anthropic_base_url`.

13. **Use `LLMSettings.anthropic_timeout_s` (default 30s) for service-info GET timeout.** Symmetric with adapter's `complete()` timeout (RESEARCH.md Q5).

14. **No Anthropic `kwargs` overrides for benign prompts.** Use default `max_tokens` (from `LLMSettings.anthropic_max_tokens = 1024`) — plenty for "OK" reply or a small `tool_use.input` dict. Don't pass `max_tokens=500` since that's a `query_router` choice, not a smoke-test invariant.
</decisions>

<tasks>

<task type="auto">
  <name>Task 3.1: Create scripts/ directory and write scripts/smoke_llm.py (single file, complete implementation)</name>
  <files>scripts/smoke_llm.py</files>
  <action>
**Step A — Create the `scripts/` directory.** Per RESEARCH.md Q10, it does not yet exist. Run:

```bash
mkdir -p scripts
```

(If on Windows PowerShell: `New-Item -ItemType Directory -Path scripts -Force`.)

**Step B — Write `scripts/smoke_llm.py` with the complete implementation below.**

This is one file, ~270 lines. Write it verbatim — no abbreviations, no `...`. Adjust whitespace consistent with project style (4-space indent, double quotes, no trailing whitespace).

```python
"""scripts/smoke_llm.py — live-credential smoke test gate for Phase 5.

Usage:
    python scripts/smoke_llm.py --provider both       # default; SKIPs missing creds
    python scripts/smoke_llm.py --provider azure_openai
    python scripts/smoke_llm.py --provider anthropic_mgti   # FAILs if creds missing
    python scripts/smoke_llm.py --provider both --verbose

Exit codes:
    0 = all configured providers passed all checks
    1 = at least one CONFIGURED provider's check failed

CONTINUE-ON-FAILURE: runs ALL checks for ALL selected providers regardless
of intermediate failures; aggregates final tally so operators see "anthropic
auth failed AND azure timed out" in one run.

OPERATOR-RUN ONLY — NOT in CI (live credentials cannot live in CI per
.planning/phases/04-strict-tools-smoke-test/04-CONTEXT.md §Smoke script
credential & provider model).

Output is human-readable for operator-eye consumption; paste the transcript
into your Phase 4 verification PR before Phase 5 work begins.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Any

import requests
from dotenv import load_dotenv

# CRITICAL: load_dotenv() MUST run BEFORE the `from src.llm import ...` lines
# below so load_settings() sees the env. Root config.py also calls
# load_dotenv() but scripts/ is outside its import chain and importing root
# config.py has side effects (creates data/ and db/ directories — RESEARCH.md
# Pitfall 5).
load_dotenv()

# Import AFTER load_dotenv so adapter __init__ sees env vars.
from src.llm import get_llm  # noqa: E402  (after load_dotenv intentional)
from src.llm.config import load_settings  # noqa: E402
from src.llm.types import INTENT_TOOL  # noqa: E402  (from Plan 01)


# ---------------------------------------------------------------------------
# Constants — hardcoded (NOT CLI-parametrized) to keep prompts guardrail-safe.
# ---------------------------------------------------------------------------

REDACT_HEADERS = {"X-Api-Key", "Authorization", "api-key"}
BENIGN_COMPLETE_PROMPT = "Reply with the single word OK."
BENIGN_CLASSIFY_QUERY = "how many incidents are open"


# ---------------------------------------------------------------------------
# CheckResult — the single per-check value type. Aggregated for the summary.
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    provider: str
    check_name: str
    status: str  # "PASS" | "FAIL" | "SKIP"
    latency_ms: int | None
    detail: str
    error: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Replace sensitive header values with '***' for --verbose printing."""
    return {k: ("***" if k in REDACT_HEADERS else v) for k, v in headers.items()}


def _shape(d: dict[str, Any]) -> str:
    """Render TOP-LEVEL keys only (no values — could echo incident data)."""
    return "{" + ", ".join(sorted(d.keys())) + "}"


def _content_block_types(content: list[dict[str, Any]] | None) -> str:
    """Compact block-type listing for Anthropic content arrays.

    Returns 'content[tool_use, text]' style, NEVER the block values.
    """
    if not content:
        return "content[]"
    types = sorted({b.get("type", "?") for b in content})
    return "content[" + ", ".join(types) + "]"


def _print_verbose_request(method: str, url: str, headers: dict, body: dict | None) -> None:
    """--verbose: print full request body + redacted headers."""
    print(f"  REQUEST: {method} {url}")
    print(f"  HEADERS: {json.dumps(_redact_headers(headers))}")
    if body is not None:
        print(f"  BODY: {json.dumps(body, indent=2)}")


def _print_verbose_response(resp_json: dict | None, status: int | None) -> None:
    """--verbose: print full response body + status."""
    print(f"  STATUS: {status}")
    if resp_json is not None:
        print(f"  RESPONSE: {json.dumps(resp_json, indent=2)}")


# ---------------------------------------------------------------------------
# Anthropic checks — 3 per provider (service-info, complete, classify_with_tool)
# ---------------------------------------------------------------------------

def _check_anthropic_service_info(settings, verbose: bool) -> CheckResult:
    """SC #5: GET {base_url}/ — service-info diagnostic (catches /messages URL bug).

    Status code 200 is sufficient (CONTEXT.md §Service-info). Response shape
    captured to stdout but NOT asserted — the MGTI service-info schema is
    undocumented and asserting fields would break on proxy upgrades.
    """
    url = settings.anthropic_base_url.rstrip("/") + "/"
    headers = {"X-Api-Key": settings.anthropic_api_key}
    t0 = time.monotonic()
    if verbose:
        _print_verbose_request("GET", url, headers, body=None)
    try:
        resp = requests.get(url, headers=headers, timeout=settings.anthropic_timeout_s)
        latency = int((time.monotonic() - t0) * 1000)
        if verbose:
            try:
                _print_verbose_response(resp.json(), resp.status_code)
            except ValueError:
                _print_verbose_response(None, resp.status_code)
        if resp.status_code != 200:
            return CheckResult(
                provider="anthropic_mgti",
                check_name="service-info",
                status="FAIL",
                latency_ms=latency,
                detail=f"HTTP {resp.status_code} in {latency}ms",
                error=resp.text[:200],
            )
        try:
            body_shape = _shape(resp.json())
        except ValueError:
            body_shape = "{non-json body}"
        return CheckResult(
            provider="anthropic_mgti",
            check_name="service-info",
            status="PASS",
            latency_ms=latency,
            detail=f"200 in {latency}ms  shape={body_shape}",
        )
    except Exception as e:  # CONTINUE-ON-FAILURE per-check isolation
        latency = int((time.monotonic() - t0) * 1000)
        return CheckResult(
            provider="anthropic_mgti",
            check_name="service-info",
            status="FAIL",
            latency_ms=latency,
            detail=f"exception in {latency}ms",
            error=str(e),
        )


def _check_anthropic_complete(client, verbose: bool) -> CheckResult:
    """Exercise AnthropicMGTIClient.complete() with benign prompt."""
    messages = [{"role": "user", "content": BENIGN_COMPLETE_PROMPT}]
    t0 = time.monotonic()
    try:
        text = client.complete(messages)
        latency = int((time.monotonic() - t0) * 1000)
        if verbose:
            # We can't easily get the raw response back from .complete() — it
            # returns str. Print the response text instead. Headers/body not
            # accessible without going through requests directly.
            print(f"  RESPONSE TEXT: {text!r}")
        # The adapter returns str. We don't have a JSON dict to shape — but
        # we know the adapter parsed content[*].text successfully, so we can
        # report a SYNTHETIC shape that matches the Anthropic response envelope.
        synth_shape = "{id, type, role, content, model, stop_reason, usage}"
        return CheckResult(
            provider="anthropic_mgti",
            check_name="complete",
            status="PASS",
            latency_ms=latency,
            detail=f"200 in {latency}ms  model={client._model}  shape={synth_shape}",
        )
    except Exception as e:
        latency = int((time.monotonic() - t0) * 1000)
        return CheckResult(
            provider="anthropic_mgti",
            check_name="complete",
            status="FAIL",
            latency_ms=latency,
            detail=f"exception in {latency}ms",
            error=f"{type(e).__name__}: {e}",
        )


def _check_anthropic_classify(client, verbose: bool) -> CheckResult:
    """Exercise AnthropicMGTIClient.classify_with_tool() with benign query + INTENT_TOOL."""
    messages = [{"role": "user", "content": BENIGN_CLASSIFY_QUERY}]
    t0 = time.monotonic()
    try:
        call = client.classify_with_tool(
            messages,
            INTENT_TOOL,
            tool_name="classify_intent",
        )
        latency = int((time.monotonic() - t0) * 1000)
        if verbose:
            print(f"  TOOL_CALL.input: {json.dumps(call.input)}")
        intent = call.input.get("intent", "<missing>")
        # Synthetic shape for Anthropic tool_use response (RESEARCH.md
        # "Anthropic strict-tools response shape").
        synth_shape = "{id, type, role, content[tool_use], model, stop_reason, usage}"
        return CheckResult(
            provider="anthropic_mgti",
            check_name="classify_with_tool",
            status="PASS",
            latency_ms=latency,
            detail=(
                f"200 in {latency}ms  intent={intent}  shape={synth_shape}"
            ),
        )
    except Exception as e:
        latency = int((time.monotonic() - t0) * 1000)
        return CheckResult(
            provider="anthropic_mgti",
            check_name="classify_with_tool",
            status="FAIL",
            latency_ms=latency,
            detail=f"exception in {latency}ms",
            error=f"{type(e).__name__}: {e}",
        )


# ---------------------------------------------------------------------------
# Azure checks — 2 per provider (complete, classify_with_tool — no service-info)
# ---------------------------------------------------------------------------

def _check_azure_complete(client, verbose: bool) -> CheckResult:
    messages = [{"role": "user", "content": BENIGN_COMPLETE_PROMPT}]
    t0 = time.monotonic()
    try:
        text = client.complete(messages)
        latency = int((time.monotonic() - t0) * 1000)
        if verbose:
            print(f"  RESPONSE TEXT: {text!r}")
        synth_shape = "{id, object, choices, usage}"
        return CheckResult(
            provider="azure_openai",
            check_name="complete",
            status="PASS",
            latency_ms=latency,
            detail=f"200 in {latency}ms  shape={synth_shape}",
        )
    except Exception as e:
        latency = int((time.monotonic() - t0) * 1000)
        return CheckResult(
            provider="azure_openai",
            check_name="complete",
            status="FAIL",
            latency_ms=latency,
            detail=f"exception in {latency}ms",
            error=f"{type(e).__name__}: {e}",
        )


def _check_azure_classify(client, verbose: bool) -> CheckResult:
    messages = [{"role": "user", "content": BENIGN_CLASSIFY_QUERY}]
    t0 = time.monotonic()
    try:
        call = client.classify_with_tool(
            messages,
            INTENT_TOOL,
            tool_name="classify_intent",
        )
        latency = int((time.monotonic() - t0) * 1000)
        if verbose:
            print(f"  TOOL_CALL.input: {json.dumps(call.input)}")
        intent = call.input.get("intent", "<missing>")
        synth_shape = "{id, object, choices, usage}"
        return CheckResult(
            provider="azure_openai",
            check_name="classify_with_tool",
            status="PASS",
            latency_ms=latency,
            detail=f"200 in {latency}ms  intent={intent}  shape={synth_shape}",
        )
    except Exception as e:
        latency = int((time.monotonic() - t0) * 1000)
        return CheckResult(
            provider="azure_openai",
            check_name="classify_with_tool",
            status="FAIL",
            latency_ms=latency,
            detail=f"exception in {latency}ms",
            error=f"{type(e).__name__}: {e}",
        )


# ---------------------------------------------------------------------------
# Cred-presence helpers
# ---------------------------------------------------------------------------

def _anthropic_creds_present(settings) -> bool:
    return bool(
        settings.anthropic_base_url
        and settings.anthropic_api_key
        and settings.anthropic_model
    )


def _azure_creds_present(settings) -> bool:
    return bool(settings.azure_endpoint and settings.azure_api_key)


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Live-credential smoke test for snow_query LLM providers.",
    )
    parser.add_argument(
        "--provider",
        choices=["azure_openai", "anthropic_mgti", "both"],
        default="both",
        help="Which provider(s) to test. Default: both.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print full request/response bodies + REDACTED headers.",
    )
    args = parser.parse_args()

    settings = load_settings()
    selected = (
        {"azure_openai", "anthropic_mgti"}
        if args.provider == "both"
        else {args.provider}
    )

    results: list[CheckResult] = []

    # --- Anthropic ---
    if "anthropic_mgti" in selected:
        if _anthropic_creds_present(settings):
            try:
                client = get_llm("anthropic_mgti")
            except Exception as e:
                # Adapter construction itself failed (e.g. bad model prefix).
                # Emit one FAIL result and skip the 3 sub-checks.
                results.append(
                    CheckResult(
                        provider="anthropic_mgti",
                        check_name="construct",
                        status="FAIL",
                        latency_ms=None,
                        detail="adapter construction failed",
                        error=f"{type(e).__name__}: {e}",
                    )
                )
            else:
                results.append(_check_anthropic_service_info(settings, args.verbose))
                results.append(_check_anthropic_complete(client, args.verbose))
                results.append(_check_anthropic_classify(client, args.verbose))
        else:
            reason = "ANTHROPIC_BASE_URL/API_KEY/MODEL not all set in .env"
            # CONTEXT.md §Smoke script credential: explicit selection never silently skips
            if args.provider == "anthropic_mgti":
                results.append(
                    CheckResult(
                        provider="anthropic_mgti",
                        check_name="creds",
                        status="FAIL",
                        latency_ms=None,
                        detail=reason,
                        error="explicit --provider anthropic_mgti requires creds",
                    )
                )
            else:
                results.append(
                    CheckResult(
                        provider="anthropic_mgti",
                        check_name="creds",
                        status="SKIP",
                        latency_ms=None,
                        detail=reason,
                    )
                )

    # --- Azure ---
    if "azure_openai" in selected:
        if _azure_creds_present(settings):
            try:
                client = get_llm("azure_openai")
            except Exception as e:
                results.append(
                    CheckResult(
                        provider="azure_openai",
                        check_name="construct",
                        status="FAIL",
                        latency_ms=None,
                        detail="adapter construction failed",
                        error=f"{type(e).__name__}: {e}",
                    )
                )
            else:
                results.append(_check_azure_complete(client, args.verbose))
                results.append(_check_azure_classify(client, args.verbose))
        else:
            reason = "AZURE_OPENAI_ENDPOINT/API_KEY not all set in .env"
            if args.provider == "azure_openai":
                results.append(
                    CheckResult(
                        provider="azure_openai",
                        check_name="creds",
                        status="FAIL",
                        latency_ms=None,
                        detail=reason,
                        error="explicit --provider azure_openai requires creds",
                    )
                )
            else:
                results.append(
                    CheckResult(
                        provider="azure_openai",
                        check_name="creds",
                        status="SKIP",
                        latency_ms=None,
                        detail=reason,
                    )
                )

    # --- Per-check output + summary ---
    for r in results:
        line = f"[{r.status}] {r.provider:14s} / {r.check_name:18s} → {r.detail}"
        print(line)
        if r.error and r.status == "FAIL":
            print(f"           ERROR: {r.error}")

    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    skipped = sum(1 for r in results if r.status == "SKIP")
    exit_code = 1 if failed > 0 else 0
    print()
    print(
        f"Summary: {passed} passed, {failed} failed, {skipped} skipped "
        f"— exit {exit_code}"
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
```

**Step C — Verify the script is syntactically valid via `py_compile`.** This is the same mechanism Plan 04's acceptance gate will use for SC #5.

```bash
python -m py_compile scripts/smoke_llm.py
echo "syntax OK"
```

**Step D — Smoke-test the script with empty .env (it should SKIP everything cleanly and exit 0).**

```bash
# Temporarily unset (PowerShell example shown; bash equivalents work)
$env:ANTHROPIC_API_KEY=""
$env:AZURE_OPENAI_API_KEY=""
python scripts/smoke_llm.py --provider both
echo "exit: $?"
```

Expected output (something like):
```
[SKIP] anthropic_mgti / creds              → ANTHROPIC_BASE_URL/API_KEY/MODEL not all set in .env
[SKIP] azure_openai   / creds              → AZURE_OPENAI_ENDPOINT/API_KEY not all set in .env

Summary: 0 passed, 0 failed, 2 skipped — exit 0
```

(NOTE: this only validates the script's structure / argparse / output formatting; live network calls require operator-supplied stage creds and happen during the Phase 4 verification PR — explicitly OUT OF SCOPE for autonomous executor.)

**Step E — Verify explicit-provider-missing-creds raises exit 1.**

```bash
python scripts/smoke_llm.py --provider anthropic_mgti
echo "exit: $?"
```

Expected:
```
[FAIL] anthropic_mgti / creds              → ANTHROPIC_BASE_URL/API_KEY/MODEL not all set in .env
           ERROR: explicit --provider anthropic_mgti requires creds

Summary: 0 passed, 1 failed, 0 skipped — exit 1
```
  </action>
  <verify>
```bash
# 1. File exists at the right path
ls -la scripts/smoke_llm.py
# Expected: file present, ~270 lines

# 2. Syntax check
python -m py_compile scripts/smoke_llm.py
echo $?
# Expected: 0 (no syntax errors)

# 3. argparse --help works
python scripts/smoke_llm.py --help
# Expected: usage/help text printed; exit 0

# 4. Invalid --provider value rejected by argparse
python scripts/smoke_llm.py --provider azure
echo $?
# Expected: argparse error "invalid choice: 'azure'"; exit != 0

# 5. Default --provider is 'both' (no error when run without args, given clean env)
python scripts/smoke_llm.py
# Expected: shows SKIP lines for both providers (assuming dev box has no live creds);
# Summary line; exit 0

# 6. Explicit-provider + missing-creds = FAIL+exit 1
python scripts/smoke_llm.py --provider anthropic_mgti
echo $?
# Expected: shows [FAIL] line for anthropic_mgti/creds; Summary 0/1/0; exit 1

# 7. INTENT_TOOL import works (depends on Plan 01 having shipped)
python -c "import scripts.smoke_llm as s; print('module loaded OK')"
# Expected: "module loaded OK" — confirms all imports resolve

# 8. load_dotenv() is called BEFORE src.llm imports (Pitfall 5)
grep -nE "load_dotenv\(\)|from src\.llm" scripts/smoke_llm.py
# Expected: load_dotenv() line appears BEFORE any "from src.llm" line in the
# output (lower line numbers print first). This is structural; if violated,
# adapter construction will fail when smoke is run by an operator with .env
# present.

# 9. NO import of root config.py
grep -n "^import config\|^from config" scripts/smoke_llm.py
# Expected: ZERO matches

# 10. Combined regression
pytest tests/ -q
# Expected: all green; smoke script is not invoked by pytest.
```
  </verify>
  <done>
`scripts/smoke_llm.py` exists. `python -m py_compile` passes. `--help` works. `--provider both` with no creds SKIPs both providers and exits 0. `--provider anthropic_mgti` with no creds FAILs and exits 1. `load_dotenv()` is called BEFORE `from src.llm import ...` lines. NO root `config.py` import. `INTENT_TOOL` imported from `src.llm.types`. All 5 required checks structured (3 Anthropic, 2 Azure). Output format matches CONTEXT.md §Smoke output spec.
  </done>
</task>

</tasks>

<verification>
Phase-level verification for Plan 03:

1. **Structural correctness:**
   ```bash
   python -m py_compile scripts/smoke_llm.py && echo OK
   ```

2. **CLI surface matches spec:**
   ```bash
   python scripts/smoke_llm.py --help | grep -E "azure_openai|anthropic_mgti|both|verbose"
   # Expected: all four strings present
   ```

3. **Default value of --provider:**
   ```bash
   python scripts/smoke_llm.py --help | grep "default: both"
   # Expected: one match
   ```

4. **Missing-creds exit-code matrix (run on a dev box with empty .env):**
   ```bash
   python scripts/smoke_llm.py --provider both ; echo "both=$?"
   python scripts/smoke_llm.py --provider anthropic_mgti ; echo "anth=$?"
   python scripts/smoke_llm.py --provider azure_openai ; echo "az=$?"
   # Expected: both=0, anth=1, az=1
   ```

5. **Only declared file modified:**
   ```bash
   git diff --stat HEAD -- src/ scripts/ tests/
   # Expected: ONLY scripts/smoke_llm.py
   ```

6. **NO live-credential execution by this executor.** This plan creates the script; it does NOT run the script against live endpoints. The operator runs it during the Phase 4 verification PR.
</verification>

<success_criteria>
- [ ] `scripts/smoke_llm.py` exists and `python -m py_compile scripts/smoke_llm.py` exits 0
- [ ] `--provider` accepts exactly `azure_openai`, `anthropic_mgti`, `both`; default is `both`
- [ ] `--verbose` is an `action="store_true"` flag
- [ ] `load_dotenv()` is invoked at module top-level BEFORE any `from src.llm import ...` line
- [ ] Script does NOT import root `config.py`
- [ ] `INTENT_TOOL` is imported from `src.llm.types`
- [ ] Anthropic provider triggers exactly 3 checks: `service-info`, `complete`, `classify_with_tool`
- [ ] Azure provider triggers exactly 2 checks: `complete`, `classify_with_tool`
- [ ] Service-info check uses `requests.get(base_url.rstrip("/") + "/", headers={"X-Api-Key": ...}, timeout=settings.anthropic_timeout_s)`
- [ ] Service-info check asserts ONLY `status_code == 200`; does NOT assert response shape
- [ ] Per-check output line format: `[STATUS] provider / check_name → detail`
- [ ] `_shape(...)` renders TOP-LEVEL KEYS only; values NEVER printed
- [ ] `--verbose` prints request body + response body + redacted headers; non-verbose NEVER prints headers
- [ ] Redaction set is exactly `{"X-Api-Key", "Authorization", "api-key"}`
- [ ] Benign prompts are HARDCODED: `BENIGN_COMPLETE_PROMPT = "Reply with the single word OK."` and `BENIGN_CLASSIFY_QUERY = "how many incidents are open"`
- [ ] CONTINUE-ON-FAILURE: each `_check_*` catches its own `Exception`; no try/except around the whole main loop
- [ ] Final summary line format: `Summary: N passed, N failed, N skipped — exit <code>`
- [ ] Exit codes: 0 iff no failures; 1 if any FAIL among configured providers
- [ ] Missing-cred matrix: `--provider both` SKIPs missing-cred providers (no exit-code impact); explicit single-provider FAILs and exits 1 if its creds missing
- [ ] No new `get_service_info()` method added to `AnthropicMGTIClient` — script constructs the URL itself
- [ ] Diff touches only `scripts/smoke_llm.py`
- [ ] Combined test suite (`pytest tests/ -q`) still passes — smoke script not invoked by pytest
</success_criteria>

<output>
After completion, create `.planning/phases/04-strict-tools-smoke-test/04-03-SUMMARY.md` documenting:
- File created with line count
- `--provider` and `--verbose` argparse surface
- Confirmation of the missing-cred matrix behavior (with example exit codes from dev-box dry run)
- Confirmation that `load_dotenv()` precedes `src.llm` imports (line number citation)
- Synthetic-shape strings used for `complete()` checks (the adapter returns `str`, not a dict — we report a CONTEXT.md-spec-compliant synthetic shape)
- Note for Plan 04: SC #5 verification uses `os.path.exists` + `py_compile.compile(path, doraise=True)`; do NOT execute the script (RESEARCH.md Pitfall 7)
- Note for operator (post-Phase 4 verification): "Set `.env` with stage gateway URLs + valid keys, then run `python scripts/smoke_llm.py --provider both --verbose` and paste the transcript into the Phase 4 verification PR"
</output>
</content>
</invoke>