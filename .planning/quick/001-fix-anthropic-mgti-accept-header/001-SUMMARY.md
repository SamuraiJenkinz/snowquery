# Quick Task 001 Summary: Add Accept: application/json header to Anthropic MGTI adapter

**Status:** ✅ Complete
**Date:** 2026-06-03
**Code commit:** `facfefa`
**Tests:** 103/103 green

## What changed

| File | Lines | Change |
| ---- | ----- | ------ |
| `src/llm/anthropic_mgti.py` | +2 | Added `"Accept": "application/json"` to the headers dict in `complete()` and `classify_with_tool()` |
| `tests/test_phase3_adapter.py` | +4 | Added regression assertion in `test_required_headers_present` so any future refactor that drops the Accept header fails in CI |

## Why

Operator reported `Anthropic MGTI HTTP error (HTTP 400): Invalid request: The Accept header must be set to application/json. AWS Bedrock requires this header.` against a previously-working integration. AWS Bedrock (behind the MGTI Apigee proxy at `apis.mmc.com/coreapi/llm/anthropic/v1`) has begun enforcing the `Accept` header at ingress. The v2.1 adapter shipped without it because Bedrock did not require it at that time (kbroles reference integration 2026-05-12 also predates this enforcement).

## Verification done

- ✅ `PYTHONPATH=. python -m pytest tests/test_phase3_adapter.py tests/test_phase4_strict_tools.py -q` — 51/51 pass
- ✅ `PYTHONPATH=. python -m pytest tests/ -q` — 103/103 pass (no regression across v2.1 + v2.2)

## Verification still open (operator)

- 🟡 Live smoke against staging gateway: `python scripts/smoke_llm.py --provider anthropic --verbose`. Carry-forward gate from v2.1; this hotfix is the precise change needed to restore the Anthropic path of that smoke.

## Follow-ups

- Update `mgti-anthropic-integration` skill (`~/.claude/skills/mgti-anthropic-integration/`) to add `Accept: application/json` to its reference adapter, minimal-request curl, and pitfalls list — so the next first-time integrator doesn't repeat this. Bedrock enforcement turned on between 2026-05-12 (skill provenance) and 2026-06-03 (this hotfix); both dates are worth recording.

## Decisions / non-changes

- Did NOT extract a shared `_build_headers` helper. Phase 3/4 locked the duplication on purpose (helper boundary is `_post_messages`, not header construction). Two-line addition × two dicts is the right shape for this fix.
- Did NOT add a Phase 4 header assertion. Both call paths build headers identically and share `_post_messages`; the Phase 3 assertion is sufficient as a contract guard.
- Did NOT pin a model bump or any other resilience work — strict scope hotfix.
