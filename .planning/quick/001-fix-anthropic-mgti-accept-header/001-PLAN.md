# Quick Task 001: Add Accept: application/json header to Anthropic MGTI adapter

<objective>

Restore Anthropic LLM access via the MMC MGTI Apigee/Bedrock proxy by adding the `Accept: application/json` request header that AWS Bedrock now requires. The provider previously worked and started returning HTTP 400 with `Invalid request: The Accept header must be set to application/json. AWS Bedrock requires this header.` — a server-side enforcement change at the Bedrock layer behind the proxy.

</objective>

<context>

**Trigger:** Operator reported `Anthropic API call failed Anthropic MGTI HTTP error (HTTP 400): Invalid request: The Accept header must be set to application/json. AWS Bedrock requires this header.` against a previously-working integration.

**Root cause:** `src/llm/anthropic_mgti.py` builds its `headers` dict in two places (one per call path: `complete()` and `classify_with_tool()`). Neither dict included `Accept: application/json`. Bedrock has begun enforcing this header at the proxy ingress.

**Why two places need editing:** The adapter intentionally duplicates the headers dict per call path rather than sharing a helper (per the Phase 3/4 lock that the helper boundary is `_post_messages`, not header construction). The fix has to touch both dicts.

**Reference:** `mgti-anthropic-integration` skill at `C:\Users\taylo\.claude\skills\mgti-anthropic-integration\` documents the MGTI request shape — its reference adapter also pre-dates this Bedrock change and lacks the Accept header; the skill should be updated separately as a follow-up.

</context>

<tasks>

1. **Add `Accept: application/json` to `complete()` headers dict** — `src/llm/anthropic_mgti.py:~373`. Insert immediately after `Content-Type: application/json` so related headers stay adjacent.

2. **Add `Accept: application/json` to `classify_with_tool()` headers dict** — `src/llm/anthropic_mgti.py:~564`. Same position and rationale.

3. **Add regression assertion to `test_required_headers_present`** — `tests/test_phase3_adapter.py:~198`. Assert `headers["Accept"] == "application/json"` so a future refactor that drops the Accept header fails fast in CI rather than at a live request. Phase 4 has no header-assertion test today; not adding one — both call paths build headers identically and share `_post_messages`, so the Phase 3 assertion is sufficient as a contract guard.

</tasks>

<verification>

- [x] `PYTHONPATH=. python -m pytest tests/test_phase3_adapter.py tests/test_phase4_strict_tools.py -q` — 51/51 pass
- [x] `PYTHONPATH=. python -m pytest tests/ -q` — 103/103 pass (no regression in v2.1 + v2.2 suites)
- [ ] **Open (operator):** Live smoke against staging — `python scripts/smoke_llm.py --provider anthropic --verbose` should now succeed end-to-end against `apis.mmc.com/coreapi/llm/anthropic/v1`

</verification>

<followups>

- Update `mgti-anthropic-integration` skill (`<python_adapter>` block + `<minimal_request>` curl + `<pitfalls>` list) to require `Accept: application/json` so future integrations don't hit this on day one.
- The skill should also note that this header became Bedrock-mandatory between the original integration (kbroles, 2026-05-12) and 2026-06-03 — useful provenance for the next operator who wonders why the original adapter worked without it.

</followups>
