# Stack Research

**Domain:** Multi-provider LLM integration (Azure OpenAI + Anthropic Claude via MGTI Apigee/Bedrock proxy) in a Python 3.11 / Streamlit / requests app
**Researched:** 2026-05-19
**Confidence:** HIGH (all model IDs and library versions verified against AWS Bedrock model cards and PyPI as of May 2026)

---

## Scope of This Document

This research only covers the **new additions** required for the "add Anthropic Claude as a selectable provider" milestone. The existing stack (Python 3.11, Streamlit ≥1.40, DuckDB ≥1.1, ChromaDB ≥0.5, sentence-transformers ≥3.0, torch ≥2.6, transformers ≥4.51, pandas ≥2.2, altair ≥5, requests ≥2.31, python-dotenv ≥1.0, python-certifi-win32 ≥1.6.1) is documented in `.planning/codebase/STACK.md` and is acknowledged-but-not-re-researched per orchestrator instructions.

**Headline:** The milestone needs **at most ONE new pip dependency** (`jsonschema`), and even that is optional. Everything else is stdlib (`dataclasses`, `typing`, `enum`, `abc`). The "MGTI Apigee front of Bedrock" architecture deliberately avoids the official Anthropic SDK and the AWS `boto3` SDK — `requests` is the only HTTP client needed.

---

## Recommended Stack — New Additions

### Core Technologies (NEW)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **requests** (already pinned) | ≥2.31.0 | HTTP client for the MGTI `/coreapi/llm/anthropic/v1/model/{model}/messages` endpoint | Already in `requirements.txt` for Azure OpenAI. Same client, same TLS stack, same Windows cert-store integration (`python-certifi-win32`) — zero churn. The MGTI skill (`mgti-anthropic-integration`) explicitly targets `requests`-only adapters. Avoids pulling in `boto3` (~50 MB transitive) or the `anthropic` SDK (~30 MB) for a single POST endpoint. |
| **dataclasses** (stdlib) | n/a (Python 3.11 built-in) | Typed `AnthropicConfig` and `AzureOpenAIConfig` value objects, plus a shared `ProviderConfig` discriminated-union pattern | Already used in the MGTI skill's reference adapter (`@dataclass(frozen=True) class AnthropicConfig`). Zero dependencies, frozen instances are hashable + immutable (safe for module-level caching), and Python 3.11's `dataclasses` supports `kw_only=True` and `slots=True` for memory efficiency. Matches the existing codebase convention (no pydantic anywhere today). |
| **abc.ABC / typing.Protocol** (stdlib) | n/a (Python 3.11 built-in) | Provider-abstraction layer — define `LLMProvider` interface with `classify_intent()`, `generate_sql()`, `generate_summary()` | `typing.Protocol` (structural subtyping, no inheritance required) is the 2026-current best practice when callers can't be forced to inherit. `abc.ABC` (nominal subtyping, `@abstractmethod`) is preferred when you own both sides. For this milestone, `abc.ABC` is the right call because snow_query owns all providers — see "Provider Abstraction Decision" below. |

### Supporting Libraries (NEW — OPTIONAL)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **jsonschema** | ≥4.26.0,<5 | Defence-in-depth validation of strict-tools mode responses (validate the `tool_use.input` payload against the schema you sent) | **Only if** the milestone adopts strict-tools mode for `classify_intent()` / `sql_generator()` to get schema-enforced JSON. The MGTI skill includes a reference `validate_json(...)` helper using `jsonschema.validate`. Skip this if the milestone sticks with regex/`json.loads()`-with-retry parsing of free-form JSON (which already works for the Azure OpenAI path). Realistically: **add it.** Strict-tools mode eliminates a whole class of "the model returned malformed JSON" bugs that haunt the current Azure OpenAI flow. |

### Development Tools (NEW)

| Tool | Purpose | Notes |
|------|---------|-------|
| (none) | — | No new dev tooling required. The existing manual smoke-test pattern (run `python app.py`, exercise via Streamlit UI) covers both providers identically since both speak HTTP. The MGTI skill recommends a `curl` smoke-test against `/coreapi/llm/anthropic/v1/` (returns 200 OK without auth) before any Python code — document this in the runbook but no dev-dep needed. |

---

## Installation

Single line addition to `requirements.txt`:

```text
# === existing stack — unchanged ===
streamlit>=1.40.0
duckdb>=1.1.0
pandas>=2.2.0
python-dotenv>=1.0.0
chromadb>=0.5.0
sentence-transformers>=3.0.0
requests>=2.31.0
onnxruntime>=1.14.1
altair>=5.0.0
python-certifi-win32>=1.6.1; sys_platform == 'win32'
torch>=2.6.0
transformers>=4.51.0

# === NEW for multi-provider milestone ===
jsonschema>=4.26.0,<5  # Strict-tools response validation (optional but recommended)
```

That is the entire diff. No new dev dependencies, no new build tools, no transitive surprises.

`jsonschema 4.26.0` (released January 2026) requires Python ≥3.10 — fully compatible with the project's Python 3.11 pin. It vendors `jsonschema-specifications` and `referencing` as required deps (both pure-Python, no native build).

---

## Anthropic Claude Model IDs — Verified Inventory (2026-05)

These are the exact strings the application code will accept as `model=...` values. **All verified against the AWS Bedrock model card pages on 2026-05-19.** The MGTI proxy is a thin pass-through to Bedrock's `bedrock-runtime` `InvokeModel` API, so any Bedrock-valid inference-profile ID with the `eu.` prefix should work (assuming the Hubble app entitlement covers the model).

### Currently Pinned in MGTI Skill (Default Recommendation)

| Model | Bedrock Inference Profile ID (EU) | Launch | Context | Max Out | Notes |
|-------|-----------------------------------|--------|---------|---------|-------|
| **Claude Sonnet 4.5** | `eu.anthropic.claude-sonnet-4-5-20250929-v1:0` | 2025-09-30 | 200K | 64K | EOL no sooner than 2026-09-29. **Default for this milestone.** Skill provenance confirms this is the operator-validated value as of 2026-05-12. |

### Newer Models Available via Bedrock (Promote Once Hubble Entitlement Confirmed)

| Model | Bedrock Inference Profile ID (EU) | Launch | Context | Max Out | Reasoning | Notes |
|-------|-----------------------------------|--------|---------|---------|-----------|-------|
| **Claude Haiku 4.5** | `eu.anthropic.claude-haiku-4-5-20251001-v1:0` | 2025-10-16 | 200K | 64K | Yes | Lightweight + fast. Strong candidate for `classify_intent()` (low-latency routing) while Sonnet handles `generate_sql()` / `generate_executive_summary()`. Knowledge cutoff Feb 2025. |
| **Claude Sonnet 4.6** | `eu.anthropic.claude-sonnet-4-6` | 2026-02-17 | **1M** | 64K | Yes | **Note the new naming convention** — no `-YYYYMMDD-v1:0` suffix. Bedrock dropped the date suffix starting with Sonnet 4.6. 1M context window is meaningful if anyone wants to dump an entire incident CSV into the prompt (probably not — DuckDB still wins on cost). Knowledge cutoff Aug 2025. |
| **Claude Opus 4.7** | `eu.anthropic.claude-opus-4-7` | 2026-04-16 | 1M | 128K | Yes (adaptive only) | Most capable. **Breaking changes vs prior Opus:** `temperature`, `top_p`, `top_k` are no longer supported — omit them entirely. Only `thinking.type: "adaptive"` is allowed (not `enabled` with `budget_tokens`). For snow_query's deterministic routing/SQL work this is fine (we don't need temperature tuning), but the request-builder code must conditionally drop those keys when the configured model starts with `eu.anthropic.claude-opus-4-7`. |

### Implication for Roadmap

The app should treat the model ID as a **runtime-configurable string** (env var or Streamlit selector), not a hardcoded constant. The MGTI skill already does this via `AnthropicConfig.model`. The provider-config schema should validate:

1. Model ID starts with `eu.anthropic.claude-` (the `eu.` prefix is mandatory through MGTI's EMEA Bedrock entitlement).
2. Model ID is a known-good value from the table above (fail-fast on typos like `eu.anthropic.claude-sonnet-4.5` instead of `4-5`).

Recommend defaulting to `eu.anthropic.claude-sonnet-4-5-20250929-v1:0` and exposing the others as opt-in choices in the sidebar — Sonnet 4.5 is the only one with full operator validation in the MGTI skill's provenance. Sonnet 4.6 / Haiku 4.5 / Opus 4.7 IDs are confirmed valid on Bedrock itself but the **Hubble app entitlement** may not yet permit them; treat as "ship as a config option but document the 'Model not supported' 404 as the expected response if entitlement is missing."

---

## Provider Abstraction Decision: `abc.ABC` vs `typing.Protocol`

Both work. Strong recommendation: **`abc.ABC` with `@abstractmethod`**.

| Criterion | `abc.ABC` (recommended) | `typing.Protocol` |
|-----------|-------------------------|-------------------|
| Nominal vs structural typing | Nominal — provider classes must `class X(LLMProvider):` | Structural — any class with matching methods satisfies it |
| Runtime check | `isinstance(x, LLMProvider)` works out of the box; instantiating an incomplete subclass raises `TypeError` at construction | `isinstance` only works with `@runtime_checkable` and is shallow (doesn't check signatures) |
| IDE / static analysis | Excellent (pyright, mypy, PyCharm all happy) | Excellent, but mypy reports "missing implementation" differently |
| Right fit when | You own both sides of the contract and want construction-time enforcement | You can't modify the implementer (e.g. wrapping a third-party SDK) |

snow_query owns both providers (`AzureOpenAIProvider`, `MGTIAnthropicProvider`) and the registry that picks between them. `abc.ABC` gives "you forgot to implement `generate_sql()`" as a `TypeError` at app boot, not a confusing AttributeError at first user query. This is what the codebase implicitly wants given its current "fail fast at startup" config-validation pattern in `config.py`.

**Skeleton (informational — not part of the requirements.txt change):**

```python
# providers/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

ProviderName = Literal["azure_openai", "mgti_anthropic"]

@dataclass(frozen=True, slots=True)
class IntentResult:
    intent: str
    confidence: float
    reasoning: str
    detected_filters: dict
    chart_requested: bool
    chart_type: str | None

class LLMProvider(ABC):
    name: ProviderName

    @abstractmethod
    def classify_intent(self, question: str, schema_hint: str) -> IntentResult: ...

    @abstractmethod
    def generate_sql(self, question: str, schema: str, intent: IntentResult) -> str: ...

    @abstractmethod
    def generate_executive_summary(self, question: str, rows: list[dict]) -> str: ...
```

Why **`@dataclass(frozen=True, slots=True)`** for return types: frozen prevents downstream mutation bugs; `slots=True` (Python 3.10+) cuts per-instance memory ~40% and prevents attribute-typo bugs (`result.intnet = "x"` raises). Both are zero-cost and project-convention-aligned.

---

## Provider-Config Typing: dataclass vs TypedDict vs pydantic

Recommendation: **`@dataclass(frozen=True)`** (already in use via the MGTI skill).

| Approach | Verdict | Why |
|----------|---------|-----|
| **dataclass** (recommended) | YES | Zero new deps. Frozen instances are hashable + immutable (safe for module-level caching, `lru_cache`). Validation happens in `__post_init__` (already the pattern in the MGTI skill — see `_validate(cfg)`). Plays nicely with `typing.Protocol` and `abc.ABC`. **Already used by the MGTI skill's reference code** — adopting it for AzureOpenAI config too gives the codebase one consistent pattern. |
| TypedDict | NO | No runtime validation. Users pass raw dicts → typos in keys aren't caught until KeyError at first use. Only good when you're consuming external dicts (e.g. JSON config files) — and even then, parse into a dataclass after loading. |
| pydantic v2 | NO (for this milestone) | Pulls in a Rust-compiled wheel (~5 MB), `pydantic-core`, and an annotated-types dep. Powerful runtime validation and JSON-schema generation, but **massive overkill** for ~5 string/int fields per provider that get loaded once at app boot from `.env`. The codebase has zero pydantic today; introducing it for this one use case is unwarranted complexity. Revisit if/when the app gains a REST API surface that accepts user-submitted config. |

**Decision matrix:** dataclass when config is internal + trusted (env vars under operator control) → that's snow_query. Pydantic when config crosses a trust boundary (browser POST, untrusted YAML). TypedDict for static-type-only dict shapes (e.g. annotating the JSON response from Anthropic for the IDE's benefit — could be useful internally, but not as the primary config type).

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `requests` (continue using) | `httpx` ≥0.27 | If/when the app gains async streaming (Streamlit ≥1.40 does support `st.write_stream` for streaming LLM tokens). `httpx` is the modern async-capable successor to `requests`. Not needed today — snow_query's three call sites are all blocking and short (<10s). Migration would touch the Azure path too, which is out of scope. |
| `requests` (continue using) | `anthropic` SDK (`pip install -U "anthropic[bedrock]"`) | If the app moved off MGTI to direct Anthropic API or direct Bedrock. The SDK adds ~30 MB and assumes `Authorization: Bearer` / AWS SigV4 auth — neither matches MGTI's `X-Api-Key` model. **Hard incompatible** with the MGTI proxy. |
| `requests` (continue using) | `boto3` + `bedrock-runtime` client | If the app got direct AWS Bedrock access (IAM credentials, not MGTI). ~50 MB transitive (`botocore`, `s3transfer`, etc.). The MGTI proxy exists precisely so MMC apps don't need AWS IAM — using `boto3` defeats the proxy's purpose. |
| `jsonschema` (for strict-tools) | `pydantic` (use a BaseModel as the schema source) | If you ALREADY had pydantic in the stack. Pydantic v2 can both define a schema and validate against it. Since snow_query doesn't have pydantic, adding pydantic (~5 MB) just for response validation is worse than adding `jsonschema` (pure Python, ~150 KB). |
| `jsonschema` (for strict-tools) | Custom regex/`json.loads()` + retry | Acceptable for `generate_executive_summary()` (free-form prose). Inadequate for `classify_intent()` (structured return with required keys) and `generate_sql()` (single SQL string) — strict-tools mode gives much higher first-try success and is worth the dependency. |
| `abc.ABC` | `typing.Protocol` | If the provider abstraction needed to accept third-party classes the app doesn't own (e.g. user-supplied plugin LLM providers). Not the snow_query case. |
| `@dataclass(frozen=True)` | `attrs` (`pip install attrs`) | If the codebase already used `attrs`. It doesn't. Modern dataclasses (3.10+) cover every meaningful `attrs` feature (`slots`, `kw_only`, `frozen`) without the dep. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `anthropic` SDK / `anthropic[bedrock]` | Speaks `Authorization: Bearer` (direct API) or AWS SigV4 (Bedrock direct). The MGTI proxy mandates `X-Api-Key`. Adding the SDK would either bypass MGTI (security/audit violation) or require monkey-patching the SDK's auth — both bad. | `requests` directly against `/coreapi/llm/anthropic/v1/model/{model}/messages` with `X-Api-Key`. |
| `boto3` + `bedrock-runtime` | Requires AWS IAM credentials. MGTI was deployed precisely so apps don't need IAM. Using boto3 introduces a parallel auth path that won't pass MMC security review. ~50 MB transitive. | `requests` against MGTI. |
| `langchain` / `langchain-anthropic` | Massive dep tree (15+ packages), unstable API across minor versions, and adds an abstraction layer on top of an abstraction layer (MGTI is already the provider abstraction). The three LLM call sites in snow_query don't justify a framework. | Direct `requests`-based provider classes implementing `LLMProvider` ABC. |
| pydantic (just for provider config) | Heavy dep (~5 MB compiled, transitive `pydantic-core`, `annotated-types`) for ~5 config fields per provider. Project has zero pydantic today; introducing it sets a precedent of "use pydantic for everything." | `@dataclass(frozen=True)` with `__post_init__` validation, as the MGTI skill already demonstrates. |
| `openai` SDK | The codebase calls Azure OpenAI via raw `requests` today — **don't add the SDK now** as part of the multi-provider refactor. Stay consistent (both providers via `requests`) and you avoid mixed-paradigm cognitive load. | Keep the current `requests`-based Azure OpenAI call path; add the `requests`-based MGTI Anthropic call path alongside it. |
| `temperature: 0.0` in Opus 4.7 requests | Claude Opus 4.7 dropped support for `temperature`, `top_p`, `top_k` — sending them returns a 400 error. | Omit these keys conditionally for any model ID matching `eu.anthropic.claude-opus-4-7*`. For Sonnet 4.5/4.6 and Haiku 4.5, keep sending them. |
| `thinking.type: "enabled"` + `budget_tokens` on Opus 4.7 | Opus 4.7 only supports `thinking.type: "adaptive"` — `enabled` with budget returns 400. | If extended thinking is ever wanted on Opus 4.7, use `"adaptive"`. For now, snow_query has no thinking-mode use case — just don't include the `thinking` key. |

---

## Stack Patterns by Variant

**If snow_query stays single-tenant local-only (current case):**
- Use `@dataclass(frozen=True)` for both `AzureOpenAIConfig` and `AnthropicConfig`.
- Load from `.env` via `python-dotenv` at module import time (existing pattern in `config.py`).
- Validate in `__post_init__` — fail at startup, not at first query.
- Skip `jsonschema` if the milestone explicitly defers strict-tools mode.

**If a future milestone adds multi-tenant / web-config UI for LLM settings:**
- Promote configs to pydantic v2 `BaseModel` at that point (validation across trust boundary).
- Add `httpx` for async streaming if Streamlit `st.write_stream` becomes a UX requirement.
- Not part of this milestone.

**If MGTI proxy fails entitlement check for a model (e.g. Sonnet 4.6 returns `Model not supported` 404):**
- App should fall back to `eu.anthropic.claude-sonnet-4-5-20250929-v1:0` automatically with a logged warning, NOT crash. This means model selection logic needs a `verified_models: list[str]` env var or constants block. Implementation detail for roadmap, but call it out here so it's not forgotten.

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| `jsonschema>=4.26.0` | Python ≥3.10 | Perfect overlap with project's Python 3.11 pin. Drops support for 3.8/3.9 (irrelevant). |
| `jsonschema>=4.26.0` | `requests>=2.31.0` | Independent — no interaction. Both pure-Python at the import surface (`jsonschema` has no compiled deps). |
| `jsonschema>=4.26.0` | `streamlit>=1.40` | Independent. Streamlit doesn't use jsonschema internally. |
| `requests>=2.31.0` | `python-certifi-win32>=1.6.1` | Existing combo, unchanged. Windows cert-store integration applies identically to the new MGTI endpoint (`int.nasa.apis.mmc.com` — same TLS issuer family as the existing Azure OpenAI endpoint via the MMC corporate CA). |
| `dataclasses` (stdlib) | Python 3.11 | `kw_only=True` requires 3.10+; `slots=True` requires 3.10+. Both safe. |
| MGTI Anthropic endpoint (`/coreapi/llm/anthropic/v1`) | All Claude 4.5+ models with `eu.` prefix | Below-4.5 models return 404 `Model not supported`. The MGTI skill's provenance (kbroles Quicks 008–012, 2026-05-12) confirms 4.5 works in production; 4.6 / Haiku 4.5 / Opus 4.7 work on Bedrock itself but Hubble entitlement must be verified per-app. |

---

## Sources

- **AWS Bedrock model card — Claude Sonnet 4.5** — https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-4-5.html — verified Bedrock model ID `anthropic.claude-sonnet-4-5-20250929-v1:0` and EU inference profile `eu.anthropic.claude-sonnet-4-5-20250929-v1:0`. Confidence: HIGH.
- **AWS Bedrock model card — Claude Sonnet 4.6** — https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-sonnet-4-6.html — verified `eu.anthropic.claude-sonnet-4-6` (no date suffix), 1M context window, launch date 2026-02-17. Confidence: HIGH.
- **AWS Bedrock model card — Claude Haiku 4.5** — https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-4-5.html — verified `eu.anthropic.claude-haiku-4-5-20251001-v1:0`, launch 2025-10-16, 200K context. Confidence: HIGH.
- **AWS Bedrock model card — Claude Opus 4.7** — https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-opus-4-7.html — verified `eu.anthropic.claude-opus-4-7`, launch 2026-04-16, AND the breaking changes (no `temperature`/`top_p`/`top_k`, `thinking.type: "adaptive"` only). Confidence: HIGH.
- **AWS Bedrock Messages API** — https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-anthropic-claude-messages.html — confirms `anthropic_version: "bedrock-2023-05-31"` remains the required body field as of May 2026. Confidence: HIGH.
- **AWS Bedrock inference profile support** — https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html — confirms the `eu.` prefix is the EU geo cross-region inference profile, routing within Frankfurt/Stockholm/Milan/Spain/Ireland/Paris (matches data-residency requirements for MMC EMEA). Confidence: HIGH.
- **jsonschema on PyPI** — https://pypi.org/project/jsonschema/ — verified version 4.26.0 (released Jan 2026), Python ≥3.10 requirement, pure-Python distribution. Confidence: HIGH.
- **MGTI Anthropic integration skill** — `C:\Users\taylo\.claude\skills\mgti-anthropic-integration\SKILL.md` (validated against kbroles Quicks 008–012, commit `4477a7e` of `mmctech/coreapi-apigee`) — provenance for `X-Api-Key`, `/messages` URL suffix, `eu.` prefix mandatory, `@dataclass(frozen=True) AnthropicConfig` pattern. Confidence: HIGH (operator-validated in production).
- **Existing codebase analysis** — `.planning/codebase/STACK.md`, `requirements.txt` — confirms current pins and absence of pydantic/boto3/anthropic-sdk. Confidence: HIGH (direct file inspection).
- **Python typing best practices (2026)** — Multiple sources via WebSearch agreeing: dataclass for trusted internal data, TypedDict for static-only annotation, pydantic for trust-boundary validation. Confidence: MEDIUM (community consensus, not a single authoritative spec) — recommendation still holds since pydantic's overkill verdict comes from dependency-cost analysis, not the community guidance.

---

*Stack research for: multi-provider LLM integration (Azure OpenAI + Anthropic Claude via MGTI)*
*Researched: 2026-05-19*
