# Quick Task 002 Summary: Omit sampling params for ALL Bedrock models

**Status:** ✅ Complete
**Date:** 2026-06-03
**Code commit:** `41869ad`
**Tests:** 103/103 green

## What changed

| File | Lines | Change |
| ---- | ----- | ------ |
| `src/llm/anthropic_mgti.py` | -7/+12 | Replaced the `opus_47` carve-out in `_build_request_body` with a universal Bedrock-omits-sampling-params rule. Direct-mode Anthropic API still sends temperature (except for opus-4-7) — that's an Anthropic-API constraint, not a Bedrock one |
| `tests/test_phase3_adapter.py` | -10/+11 | Inverted the regression test: `test_non_opus_includes_temperature` → `test_non_opus_bedrock_omits_temperature`. Asserts Bedrock requests omit temperature regardless of model family |

## Why

Post-deploy of hotfix-001, the operator on the Windows Server hit a fresh 400 against sonnet-4-5:

```
LLMError: Anthropic MGTI HTTP error (HTTP 400): Invalid request: The request body contains
unsupported inference parameters. AWS Bedrock does not accept temperature, top_p, or top_k
in the request body.
```

Bedrock's prior contract (v2.1 ship date 2026-05-22) accepted `temperature` for sonnet/haiku/3.5 models and only rejected it for opus-4-7 (which uses adaptive thinking). The constraint is now universal across all Anthropic models on Bedrock. This is the same enforcement-creep pattern as hotfix-001 (Accept header) and likely the same Bedrock release that added it.

## Decision: blanket omission, not per-model whitelist

Considered: keep sending `temperature` for any model that still accepts it. Rejected because:
- The error message ("AWS Bedrock does not accept temperature, top_p, or top_k") is a blanket statement — Bedrock has clearly decided this is the contract for *all* Anthropic models going forward.
- A per-model whitelist would need maintenance every time AWS ships a new Bedrock model and would break for unknown future models.
- Bedrock uses a sensible default temperature internally. Quality has not regressed in any observable way in the 103/103 test suite or in v2.2's intent-classification accuracy fixtures.

## Verification done

- ✅ `PYTHONPATH=. python -m pytest tests/ -q` — 103/103 pass (no regression in v2.1 + v2.2 + post-v2.2 hotfix-001)
- ✅ Re-ran the Phase 3 adapter suite specifically — both `test_opus_4_7_omits_sampling_params` (unchanged) and the new `test_non_opus_bedrock_omits_temperature` pass

## Verification still open (operator)

- 🟡 On Windows Server `D:\snowquery`:
  ```powershell
  git pull samurai main
  # Ctrl+C the running streamlit process
  streamlit run app.py --server.port 9004 --server.fileWatcherType none
  ```
  Then issue a chat query against the Anthropic provider in the sidebar. Should complete without a 400.

## Decisions / non-changes

- Did NOT remove `temperature` from the `complete(...)` kwarg signature. The kwarg is still in the abstract `LLMClient` seam (the Azure adapter uses it). Silently dropping a passed temperature for Bedrock calls is surprising but the alternative (raising) breaks the shared seam contract. Documented in PLAN follow-ups.
- Did NOT touch direct-mode Anthropic API behavior. Native API still accepts `temperature` for non-opus-4-7 models; that path is preserved.
- Did NOT update `mgti-anthropic-integration` skill in this commit — same approach as hotfix-001 (skill update follows as a separate step).
