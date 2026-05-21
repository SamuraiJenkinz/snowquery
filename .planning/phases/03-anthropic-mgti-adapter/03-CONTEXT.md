# Phase 3: Anthropic MGTI Adapter - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement `AnthropicMGTIClient` in `src/llm/anthropic_mgti.py` against the MGTI Apigee proxy at `{ANTHROPIC_BASE_URL}/model/{model}/messages`. Adapter provides `complete()` only (text-mode); typed-error mapping from MGTI HTTP responses; structured log emission; `.env.example` updated with Anthropic vars. Reachable via `get_llm("anthropic_mgti")` but NO UI surface — `LLM_PROVIDER_DEFAULT=azure_openai` stays unchanged.

Strict-tools mode (`classify_with_tool` Anthropic path) is Phase 4. Live-credential smoke test is Phase 4. UI toggle is Phase 5.

</domain>

<decisions>
## Implementation Decisions

### System prompt + message shaping

- **System extraction**: Filter ALL `role="system"` messages out of the input `messages: list[dict]`; concatenate their `content` strings with `"\n\n"` separator; set the result as the top-level `system` body field. Defensive over first-wins because the cost of getting it wrong (silent drop of a second system message) outweighs the cost of joining.
- **No system messages present**: Omit `system` key from the body entirely. Do NOT send `system: ""` — the Anthropic Messages API treats absent and empty differently and empty is the surprise path.
- **Remaining messages**: Pass through as the `messages` array with `role`/`content` preserved verbatim. No reordering, no role normalization beyond removing system.
- **`anthropic_version` body field**: Sourced from `ANTHROPIC_VERSION` env var. Default `"bedrock-2023-05-31"` (Bedrock-required constant per MGTI quickstart). Set on every request body.
- **`max_tokens` body field**: Always sent (Anthropic API requires it — unlike OpenAI where it's optional). Per-call value from caller; falls back to `ANTHROPIC_MAX_TOKENS` env default if call omits.
- **Sampling params (`temperature`, `top_p`, `top_k`)**: Omitted entirely from the request body for any model name matching `eu.anthropic.claude-opus-4-7*` (per SC #2). For other `eu.anthropic.claude-*` models, `temperature` is sent (from env or call kwarg); `top_p`/`top_k` are not sent unless explicitly passed.
- **No response text stripping in adapter**: Adapter returns raw `content[*].text` concatenation. Call sites strip if needed. Mirrors Phase 2 Pitfall 1 guard for symmetric provider behavior.

### Response edge-case handling

`stop_reason` mapping:
- `end_turn` → success
- `stop_sequence` → success
- `max_tokens` → success with `outcome="truncated"` in log event; do NOT raise (caller chose `max_tokens`, truncation is a known outcome of that choice)
- `guardrail_intervened` → `LLMGuardrailError` (per SC #3)
- `tool_use` reaching `complete()` text-mode → `LLMSchemaError("unexpected tool_use stop_reason in complete() path")` (Phase 4 owns the tool-use path; surfacing here means the wrong call site)
- Missing or unknown `stop_reason` → `LLMSchemaError("unknown stop_reason: {value}")`

Content edge cases:
- HTTP 200 with empty `content` array AND `stop_reason != "guardrail_intervened"` → `LLMSchemaError("empty content with stop_reason={value}")` (per SC #3: "HTTP 200 + empty content does NOT count as success")
- `content` non-empty but no text blocks present → `LLMSchemaError("no text blocks in content")`
- Multiple text blocks → concatenate `b["text"]` in order into single string (idiomatic per Anthropic Messages API conventions)

Error envelope:
- 4xx/5xx with parseable body matching `{"error": {"title", "detail", ...}}` → use `"{title}: {detail}"` as the typed-error message (MGTI proxy envelope, NOT native Anthropic SDK envelope — they differ)
- 4xx/5xx without parseable JSON body → use `response.text[:200]` as the message
- HTTP code → typed error class per SC #3: 401/403 → `LLMAuthError`; 429/5xx → `LLMTransientError`; `requests.Timeout` → `LLMTimeoutError`

### Observability shape (usage + correlation)

`_log_llm_call()` is duplicated verbatim from `azure_openai.py` per Phase 2 decision (intentional duplication, no premature extraction). The log event shape is shared across providers; Anthropic-specific normalization happens before the helper call.

Log event fields:
- `provider`: `"anthropic_mgti"`
- `model`: full `eu.anthropic.claude-*` string
- `latency_ms`: int (wall-clock around `requests.post`)
- `outcome`: one of `"success" | "truncated" | "guardrail" | "auth_error" | "transient_error" | "timeout" | "schema_error" | "error"`
- `prompt_tokens`: from response `usage.input_tokens` — **normalized to Azure field name** for cross-provider log grep / dashboard clarity
- `completion_tokens`: from response `usage.output_tokens` — same rationale
- `correlation_id`: the sent UUID (always; fresh per call per SC #1)
- `stop_reason`: included on both success and error paths for debug context

Token field absence: If `usage` missing or sub-fields missing, log fields default to `None`. Adapter does not synthesize counts; downstream consumers handle `None` gracefully.

Correlation echo: Phase 3 observes whether MGTI echoes `X-Correlation-Id` in response headers and documents the finding in the commit message. NOT promoted to a separate log field in Phase 3 — defer to Phase 5 only if echo-matching proves load-bearing for debugging. (Resolves the "MGTI X-Correlation-Id echo unverified" blocker in STATE.md from observation rather than implementation.)

### Verification strategy

- **Test module**: `tests/test_phase3_adapter.py` — acceptance gate covering all 5 Phase 3 success criteria. Self-contained (no `conftest.py`, matches Phase 1/Phase 2 gate pattern).
- **Patching level**: `requests.post` patching (matches Phase 2 Level A) for adapter-direct tests. Hand-crafted response bodies as inline Python dicts in test code — no separate fixture files. (Anthropic has no parity baseline; Phase 2's fixture-file pattern was specifically for byte-identical Azure comparison and doesn't apply here.)
- **Verification surface**:
  - SC #1: URL construction (`{base_url}/model/{model}/messages`), header presence (`X-Api-Key`, `Content-Type: application/json`, `X-Correlation-Id`), correlation ID is a fresh UUID per call (assert two calls produce different IDs)
  - SC #2: Constructor with non-`eu.anthropic.claude-` model → `LLMConfigError`; constructor with `eu.anthropic.claude-opus-4-7*` model → request body omits `temperature`/`top_p`/`top_k` (assert via `requests.post` call args)
  - SC #3: 401 → `LLMAuthError`; 403 → `LLMAuthError`; 429 → `LLMTransientError`; 503 → `LLMTransientError`; `requests.Timeout` → `LLMTimeoutError`; `stop_reason="guardrail_intervened"` → `LLMGuardrailError`; HTTP 200 + empty content (non-guardrail) → `LLMSchemaError`
  - SC #4: Read `.env.example`, assert all 9 listed vars present with non-empty default-value comments
  - SC #5: Startup log emission (mock logger at app boot path; assert one `base_url` log per loadable provider; assert `generate_sql` / `generate_executive_summary` call paths invoke only `complete()` — no tool wrapping)
- **Zero live HTTP**. Phase 4 owns the live-credential smoke test per ROADMAP.
- **Combined target**: 18 (Phase 1+2) + Phase 3 tests, all passing on `pytest -q`.

### Claude's Discretion

User delegated decision-making for all four discussed areas; decisions above are made and locked. Remaining flexibility for the planner / executor:
- Exact module layout within `src/llm/anthropic_mgti.py` (helper function boundaries, private vs. public)
- Whether to extract a `_build_request_body()` helper or inline the body construction
- Exact phrasing of `LLMConfigError` remediation text (must mention `eu.anthropic.claude-` prefix and Claude 4.5+ requirement)
- Test naming conventions and grouping within the acceptance gate module
- Whether to include a debug-mode response capture for the correlation-echo observation (e.g., a `tests/manual/observe_correlation_echo.py` script)

</decisions>

<specifics>
## Specific Ideas

- Log fields **normalized to Azure naming** (`prompt_tokens`/`completion_tokens`) — explicit so the Phase 3 implementer does NOT introduce Anthropic-native field names that would break cross-provider grep.
- Adapter NEVER strips response text — call sites strip. Mirrors Phase 2 Pitfall 1 guard; preserves symmetric provider behavior even though parity is not the Phase 3 concern.
- `system` body field is **top-level**, NOT a `{"role": "system", ...}` message. Common porting mistake from OpenAI/Azure shape; called out here so the implementer doesn't trip on it.
- MGTI proxy error envelope is `{"error": {"title", "detail", "status"}}` — NOT the native Anthropic SDK shape `{"type": "error", "error": {"type", "message"}}`. Copy-pasting from the official `anthropic` SDK error handling will silently swallow the detail field.
- `X-Correlation-Id` is always sent (fresh UUID per call per SC #1). Echo behavior to be observed during Phase 3 testing and noted in the implementation commit; not promoted to a separate log field unless Phase 5 needs it.
- Phase 2's `_log_llm_call()` is duplicated verbatim into `anthropic_mgti.py` — intentional, no extraction. Established pattern.

</specifics>

<deferred>
## Deferred Ideas

- **Pre-filtering blank/near-blank user input** to dodge Bedrock guardrail false-positives (MGTI skill Pitfall 7) — Phase 3 surfaces these as `LLMGuardrailError` and lets them propagate through the seam to the user. Defensive pre-filter is a UX concern → Phase 5 input validation.
- **Retry policy on 429/5xx** — Phase 3 passes through to `LLMTransientError` (matches Phase 2 Azure symmetric behavior). Adapter-level backoff/retry deferred; revisit in Phase 5 if user-visible "try again" UX is insufficient.
- **Correlation ID echo as a load-bearing log field** — Phase 3 observes only; promote to log field in Phase 5 if echo-matching informs debugging value.
- **Cost / token-usage dashboard** — Phase 5 documentation + observability concern; out of scope for adapter implementation.
- **Anthropic-native error envelope compatibility** — adapter only handles the MGTI proxy envelope. If MMC ever swaps to native Anthropic SDK or a direct Anthropic endpoint, error parsing needs revisiting. Not a Phase 3 concern (proxy is the only target).
- **Caching `usage.cache_creation_input_tokens` / `cache_read_input_tokens`** (Anthropic prompt caching fields) — out of scope; revisit if Phase 5 prompt-caching work lands.

</deferred>

---

*Phase: 03-anthropic-mgti-adapter*
*Context gathered: 2026-05-21*
