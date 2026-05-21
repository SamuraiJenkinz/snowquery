"""Manual observation script — does MGTI echo our X-Correlation-Id?

Resolves the STATE.md blocker:
    "MGTI `usage` block pass-through and `X-Correlation-Id` echo unverified —
     capture a real stage response during Phase 3 to inform observability design"

Usage (requires a working stage .env):
    python tests/manual/observe_correlation_echo.py

This script:
  1. Constructs AnthropicMGTIClient from env vars.
  2. Sends ONE real text-mode request with a known X-Correlation-Id.
  3. Prints whether the response headers echo back the same correlation ID
     and what the usage block looked like.

The output is recorded in 03-03-SUMMARY.md and the commit message, so a
future Phase 5 work-item can decide whether to promote X-Correlation-Id echo
to a load-bearing log field.

NOT collected by pytest (this directory has no test_ prefix; pytest collection
is `tests/test_*.py` only). Safe to leave in the repo as a one-shot diagnostic.
"""
from __future__ import annotations

import os
import sys
import uuid

import requests


def main() -> int:
    base_url = os.getenv("ANTHROPIC_BASE_URL", "").rstrip("/")
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    model = os.getenv("ANTHROPIC_MODEL", "")
    version = os.getenv("ANTHROPIC_VERSION", "bedrock-2023-05-31")

    if not (base_url and api_key and model):
        print(
            "ERROR: set ANTHROPIC_BASE_URL, ANTHROPIC_API_KEY, and "
            "ANTHROPIC_MODEL in your environment first. Aborting.",
            file=sys.stderr,
        )
        return 2

    correlation_id = str(uuid.uuid4())
    url = f"{base_url}/model/{model}/messages"
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": api_key,
        "X-Correlation-Id": correlation_id,
    }
    body = {
        "anthropic_version": version,
        "messages": [{"role": "user", "content": "Reply with just the word 'ok'."}],
        "max_tokens": 16,
    }

    print(f"[observe_correlation_echo] sending POST {url}")
    print(f"[observe_correlation_echo] X-Correlation-Id sent: {correlation_id}")
    response = requests.post(url, headers=headers, json=body, timeout=30)
    print(f"[observe_correlation_echo] HTTP {response.status_code}")
    print(f"[observe_correlation_echo] response headers: {dict(response.headers)}")

    # Echo check — case-insensitive header lookup
    echoed = None
    for k, v in response.headers.items():
        if k.lower() == "x-correlation-id":
            echoed = v
            break

    if echoed is None:
        print("[observe_correlation_echo] RESULT: MGTI did NOT echo X-Correlation-Id.")
    elif echoed == correlation_id:
        print(f"[observe_correlation_echo] RESULT: MGTI echoed exactly. value={echoed}")
    else:
        print(
            f"[observe_correlation_echo] RESULT: MGTI returned a DIFFERENT correlation "
            f"id. sent={correlation_id} returned={echoed}"
        )

    # Usage block observation
    if response.ok:
        try:
            data = response.json()
            print(f"[observe_correlation_echo] usage block: {data.get('usage')}")
            print(f"[observe_correlation_echo] stop_reason: {data.get('stop_reason')}")
        except ValueError:
            print("[observe_correlation_echo] response body not JSON.")
    else:
        print(f"[observe_correlation_echo] error body: {response.text[:300]}")

    return 0 if response.ok else 1


if __name__ == "__main__":
    sys.exit(main())
