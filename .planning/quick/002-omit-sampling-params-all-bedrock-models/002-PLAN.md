# Quick Task 002: Omit sampling params for ALL Bedrock models, not just opus-4-7

<objective>

Restore Anthropic LLM access (post-hotfix-001 follow-on). AWS Bedrock has tightened the inference-parameter contract — it now rejects `temperature`, `top_p`, and `top_k` in the request body for **all** Anthropic models, not just opus-4-7. The v2.1 adapter was correct at ship time (Bedrock only enforced this for opus-4-7); the constraint has since broadened. Generalize the omission rule so it applies to every Bedrock request regardless of model family.

</objective>

<context>

**Trigger:** After deploying hotfix-001 (Accept header) on the Windows Server (D:\snowquery, sonnet-4-5 configured), operator hit a new 400 on first chat call:

```
LLMError: Anthropic MGTI HTTP error (HTTP 400): Invalid request: The request body contains
unsupported inference parameters. AWS Bedrock does not accept temperature, top_p, or top_k
in the request body.
```

**Root cause:** `_build_request_body` in `src/llm/anthropic_mgti.py` had a model-specific carve-out:

```python
opus_47 = model.startswith("eu.anthropic.claude-opus-4-7") or ...
if not opus_47:
    body["temperature"] = temperature
```

Sonnet-4-5 isn't opus-4-7, so `temperature` was still sent. Bedrock now rejects this for sonnet too.

**Generalized rule (from the error text — "AWS Bedrock does not accept temperature, top_p, or top_k"):**

| Mode | Model | Send sampling params? |
|---|---|---|
| Bedrock (`direct_mode=False`) | any | **NO** (Bedrock constraint, all models) |
| Direct Anthropic API (`direct_mode=True`) | opus-4-7 | NO (adaptive thinking — model-specific constraint) |
| Direct Anthropic API (`direct_mode=True`) | other | YES |

Native Anthropic API still accepts `temperature` for non-opus-4-7 models, so direct-mode behavior is preserved.

</context>

<tasks>

1. **Rewrite the sampling-param block in `_build_request_body`** (`src/llm/anthropic_mgti.py:~127`). Replace the `opus_47` four-line conditional with a single conditional that only sends `temperature` when `direct_mode is True AND not opus-4-7`. Keep the explanatory comment so the next operator understands *why* (Bedrock-wide vs. opus-specific Anthropic-API constraint).

2. **Flip the regression test** (`tests/test_phase3_adapter.py:~280`). The pre-existing `test_non_opus_includes_temperature` was asserting the OLD contract. Rename to `test_non_opus_bedrock_omits_temperature` and invert assertions. Keep `test_opus_4_7_omits_sampling_params` unchanged (the rule is now universal but the opus-4-7 case is still a valid instance of it).

</tasks>

<verification>

- [x] `PYTHONPATH=. python -m pytest tests/ -q` — 103/103 pass
- [ ] **Open (operator):** Restart `streamlit run app.py` on the Windows Server after `git pull samurai main`; verify a sonnet-4-5 query completes against the live MGTI gateway

</verification>

<followups>

- Update `mgti-anthropic-integration` skill — the reference adapter currently sends `temperature` for all Bedrock models. Same pitfall pattern as hotfix-001 (Accept header); add to the pitfalls list.
- Consider whether the deprecated `temperature` kwarg in `complete(messages, *, max_tokens, temperature=0.1, ...)` should warn when invoked against a Bedrock-mode client. Today it's silently ignored for Bedrock requests — surprising, but the alternative (raising) breaks the LLMClient seam contract that's shared with the Azure adapter (which uses temperature). Leave as-is, document.

</followups>
