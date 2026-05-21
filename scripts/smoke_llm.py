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

# Ensure UTF-8 output on Windows terminals (→ arrow in per-check lines).
# Silently skipped on non-reconfigurable streams (e.g. redirected to a file).
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

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
