---
phase: 03-anthropic-mgti-adapter
verified: 2026-05-21T15:25:40Z
status: passed
score: 5/5 must-haves verified
re_verification: null
---

# Phase 3: Anthropic MGTI Adapter Verification Report

**Phase Goal:** Add AnthropicMGTIClient with text-mode complete() against the MGTI Apigee proxy, full typed-error mapping from MGTI HTTP responses, and observability hooks. The adapter is reachable via get_llm("anthropic_mgti") but no UI exposes it yet.

**Verified:** 2026-05-21T15:25:40Z
**Status:** passed
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| - | ----- | ------ | -------- |
| 1 | get_llm("anthropic_mgti").complete(...) POSTs to {base_url}/model/{model}/messages with X-Api-Key, Content-Type: application/json, and a fresh X-Correlation-Id UUID per call | PASS | End-to-end Python check produced URL https://example.com/v1/model/eu.anthropic.claude-opus-4-7-20251201-v1:0/messages. Tests test_url_construction, test_required_headers_present, test_fresh_correlation_id_per_call all green. |
| 2 | Bad model prefix raises LLMConfigError at __init__; opus-4-7 omits temperature/top_p/top_k from the body | PASS | Live check: ANTHROPIC_MODEL=gpt-4o raises LLMConfigError(provider="anthropic_mgti") with remediation text mentioning eu.anthropic.claude-. Opus-4-7 body keys observed: ["anthropic_version", "max_tokens", "messages"] - sampling params absent even when temperature kwarg passed. Tests test_init_raises_on_bad_model_prefix, test_init_no_raise_on_empty_model, test_opus_4_7_omits_sampling_params, test_non_opus_includes_temperature all green. |
| 3 | 401/403 -> LLMAuthError; 429/5xx -> LLMTransientError; requests.Timeout -> LLMTimeoutError; stop_reason=="guardrail_intervened" -> LLMGuardrailError; HTTP 200 + empty content + non-guardrail -> LLMSchemaError | PASS | All 7 mapping tests green. Order-sensitivity (guardrail-before-emptiness, RESEARCH.md Pitfall 4) confirmed by the pair of guardrail/empty-content tests. |
| 4 | .env.example lists all 9 new Anthropic variables with documented defaults | PASS | Read .env.example directly - all 9 keys present with non-empty defaults: LLM_PROVIDER_DEFAULT=azure_openai, ANTHROPIC_BASE_URL=https://stage.int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1, ANTHROPIC_API_KEY=your-anthropic-api-key-here, ANTHROPIC_MODEL=eu.anthropic.claude-sonnet-4-5-20250929-v1:0, ANTHROPIC_VERSION=bedrock-2023-05-31, ANTHROPIC_MAX_TOKENS=1024, ANTHROPIC_TEMPERATURE=0.0, ANTHROPIC_TIMEOUT_S=30, ANTHROPIC_TOOLS_SUPPORTED=true. |
| 5 | Startup logs llm_provider_loaded exactly once per loadable provider; generate_sql/generate_executive_summary call only complete() (no tool wrapping) | PASS | End-to-end Python check: two get_llm("anthropic_mgti") calls emit exactly one llm_provider_loaded event (factory cache idempotence). Grep of src/sql_generator.py and src/query_router.py for classify_with_tool returns no matches. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| src/llm/anthropic_mgti.py | Full AnthropicMGTIClient impl (>=350 lines) - model validation, MGTI HTTP, typed errors, correlation UUID, guardrail-before-emptiness, classify_with_tool stub | PASS | 442 lines. Class AnthropicMGTIClient(LLMClient). __init__ validates eu.anthropic.claude- prefix and emits llm_provider_loaded. complete() builds MGTI URL/headers/body, generates fresh UUID, dispatches typed errors in the correct order (guardrail before content-emptiness). classify_with_tool raises NotImplementedError (Phase 4 owns strict-tools). |
| src/llm/_compat.py | Per-provider e.provider dispatch for LLMAuthError / Timeout / Transient / catch-all | PASS | 117 lines. Each except branch checks getattr(e, "provider", None) == "anthropic_mgti" and surfaces an Anthropic-named QueryError; Azure path byte-identical to Phase 2. |
| src/llm/azure_openai.py | Adds llm_provider_loaded log emission in __init__ | PASS | Lines 91-94 emit logger.info("llm_provider_loaded", extra={"provider":"azure_openai","base_url":self._endpoint}). |
| src/llm/config.py | Anthropic settings fields + _REQUIRED_VARS["anthropic_mgti"] | PASS | LLMSettings declares all 8 anthropic_* fields with documented defaults. validate_config("anthropic_mgti") collects all missing vars at once (CFG-03). API key field uses repr=False (OBS-03). |
| src/llm/__init__.py | _REGISTRY["anthropic_mgti"] mapped; get_llm("anthropic_mgti") returns AnthropicMGTIClient | PASS | Line 56 registers anthropic_mgti -> src.llm.anthropic_mgti:AnthropicMGTIClient. Live import confirms isinstance check passes; second call returns the same cached instance. |
| .env.example | 9 vars present (LLM_PROVIDER_DEFAULT + 8 ANTHROPIC_*) with defaults | PASS | All 9 keys present with documented non-empty defaults; comments explain prod / non-prod URLs and the Phase 4 escape hatch. |
| tests/test_phase3_adapter.py | >=350 lines; 21 tests proving all 5 SCs + Plan 02 dispatch end-to-end | PASS | 552 lines; 21 test functions; each docstring cites the SC it proves; autouse fixtures isolate factory cache and env state. |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| src/llm/__init__.py:_REGISTRY | src/llm/anthropic_mgti.py:AnthropicMGTIClient | lazy importlib.import_module in _import_class | WIRED | Live get_llm("anthropic_mgti") returns an AnthropicMGTIClient instance and is cached. |
| AnthropicMGTIClient.complete() | requests.post | builds URL f"{base_url}/model/{model}/messages", sends X-Api-Key + fresh UUID correlation header | WIRED | URL / headers / body all verified end-to-end with mocked requests.post. |
| AnthropicMGTIClient.__init__ | src.utils.logger | logger.info("llm_provider_loaded", extra={...}) after settings load | WIRED | Confirmed live (LOG line emitted on construction); factory cache dedupes to exactly one event per process. |
| _compat.llm_to_query_error | per-provider QueryError wording | dispatch on e.provider == anthropic_mgti | WIRED | Tests test_anthropic_auth_error_translates_to_anthropic_query_error and test_anthropic_timeout_translates_to_anthropic_query_error lock the exact UI wording ("Anthropic API key not configured or not authorised" / "Anthropic API call failed"). |
| src/query_router.py:generate_executive_summary | client.complete(...) only | client = get_llm(); client.complete(messages, max_tokens=500) | WIRED | Source inspection: lines 501-503 use only complete(). No classify_with_tool reference anywhere in the file. |
| src/sql_generator.py:generate_sql | client.complete(...) only | client = get_llm(); client.complete(messages, max_tokens=1000) | WIRED | Source inspection: lines 142-144 use only complete(). No classify_with_tool reference anywhere in the file. |

### Requirements Coverage

This phase has no explicit REQUIREMENTS.md ID mapping; the 5 Phase 3 ROADMAP success criteria serve as the requirement set and all map 1:1 to the truths above.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| src/llm/anthropic_mgti.py | 440 | raise NotImplementedError (Phase 4 message) | Info | Intentional - classify_with_tool deferred to Phase 4 per ROADMAP scope; matches base-class contract and the Plan 03 must_have. Not a stub of in-scope behavior. |
| src/llm/anthropic_mgti.py | 49 | Duplicated _log_llm_call helper (vs azure_openai.py:52) | Info | Intentional duplication - locked Phase 2 decision; both files note "no premature extraction" until a third adapter exists. Not a blocker. |

No TODO / FIXME / placeholder / empty-handler patterns found in the Phase 3 source files. No blocker or warning anti-patterns.

### Combined Acceptance Gate

```
$ pytest tests/test_llm_seam.py tests/test_phase2_parity.py tests/test_phase3_adapter.py -q
.......................................                                  [100%]
39 passed in 8.10s
```

- Phase 1 (tests/test_llm_seam.py): 8 tests
- Phase 2 (tests/test_phase2_parity.py): 10 tests
- Phase 3 (tests/test_phase3_adapter.py): 21 tests
- Total: 39 passed (matches anchor in verification prompt).

### Human Verification Required

None. All 5 success criteria are structurally verifiable and have been verified both via the acceptance-gate pytest run AND via independent end-to-end checks (live Python interpreter exercising the adapter against mocked requests.post, file-content scans of .env.example, and call-site source inspection of generate_sql / generate_executive_summary).

Phase 5 will introduce the UI dropdown; Phase 4 introduces strict-tools - neither is in Phase 3 scope, and no UI verification is requested by the goal ("no UI exposes it yet").

### Gaps Summary

No gaps. All 5 ROADMAP success criteria for Phase 3 are achieved end-to-end in the actual codebase:

- The adapter file (442 lines, fully substantive) implements MGTI URL construction, X-Api-Key auth, fresh-UUID correlation per call, the model-prefix guard at __init__, opus-4-7 sampling-param omission, and the full typed-error mapping including the order-sensitive guardrail-before-emptiness check.
- The factory registry wires get_llm("anthropic_mgti") to the adapter; cache idempotence ensures the llm_provider_loaded event fires exactly once per provider per process.
- The compat layer dispatches LLMError subclasses on e.provider so Anthropic errors get Anthropic-named QueryError wording in the UI - paying down the Phase 2 known debt locked in Plan 02.
- The Azure adapter also emits the symmetric llm_provider_loaded event so SC #5 for-each-loadable-provider clause is satisfied for both providers.
- The two call sites (generate_sql, generate_executive_summary) use only complete() - no tool-use wrapping - matching SC #5 second clause.
- .env.example documents all 9 vars with non-empty defaults; the commit timeline matches anchor commits 5ba5e0b -> 1bfdd0b.

Phase 3 is structurally complete and ready to proceed.

---

_Verified: 2026-05-21T15:25:40Z_
_Verifier: Claude (gsd-verifier)_
