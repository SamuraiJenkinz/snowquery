# Phase 1: Abstraction Seam - Context

**Gathered:** 2026-05-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the provider-agnostic seam in `src/llm/` — the `LLMClient` ABC, error taxonomy, config validation, and factory — so all subsequent provider work (Azure extraction in Phase 2, Anthropic adapter in Phase 3, strict-tools in Phase 4, UI in Phase 5) plugs into a stable interface.

**Hard constraints carried from ROADMAP.md success criteria:**
- `src/llm/` is a real Python package importable from a REPL inside the project venv (must include `__init__.py`, `base.py`, `errors.py` at minimum)
- `LLMClient` is an `abc.ABC` whose two-method contract (`complete`, `classify_with_tool`) is enforced at construction time
- `get_llm(provider)` is cached and resolves provider in the order: explicit kwarg > `st.session_state` > env default; env default falls back to `azure_openai`
- `validate_config(provider)` raises `LLMConfigError` listing **every** missing variable for that provider
- No log line and no `repr()` output across the package exposes an API key (full, prefix, or pre-image of a fingerprint)
- **No behavior change ships in Phase 1** — call sites are not modified, no adapter is wired into `query_router` / `sql_generator` yet

This phase is foundation only. Call-site rewrite is Phase 2.

</domain>

<decisions>
## Implementation Decisions

### Secret handling (user-locked)
- **MVP-level:** API keys live in `.env` and are read via the existing project pattern (no vault, no secret manager, no rotation tooling)
- Repr/log safety must still hold (success-criterion #5 is non-negotiable) — but the *mechanism* can be the simplest thing that works (e.g. `__repr__` override or `field(repr=False)` on dataclasses, plain string in code, never logged)
- A "fingerprint" of the API key (for the Phase 5 cache key `(provider, base_url, model, api_key_fingerprint)`) is **not required in Phase 1** — caching by `provider` alone is sufficient for the seam; fingerprinting can be added in Phase 5 if needed for live key-swap, or skipped entirely if MVP doesn't need mid-session key reload

### Claude's Discretion (all four discussed areas)

The user explicitly delegated these to research + planner. Researcher should investigate and propose; planner should bake the chosen shape into tasks. No further user input required unless a decision creates ambiguity downstream.

**1. Module layout under `src/llm/`**
- Required (by success criteria): `__init__.py`, `base.py`, `errors.py`
- Open: whether to also add `config.py` (housing `validate_config` + per-provider required-var lists), `types.py` (housing `Message`, `CompletionResult`, `ToolCall` dataclasses), `factory.py` (housing `get_llm` + provider registry), or fold these into `base.py` / `__init__.py`
- Researcher should weigh: keep small in Phase 1 (YAGNI) vs prepare clean slots for Phases 2–4 to drop into

**2. Error taxonomy**
- Required classes (by ROADMAP.md across phases): `LLMError` (base), `LLMConfigError` (Phase 1), `LLMAuthError`, `LLMTransientError`, `LLMTimeoutError`, `LLMGuardrailError` (Phase 3), `LLMSchemaError` (Phase 4)
- Phase 1 must define **all** of these even though only `LLMConfigError` is raised yet — otherwise Phase 3/4 has to revisit the seam
- Open: inheritance shape (flat under `LLMError` vs grouped — e.g. retryable subtree), what `__init__` carries (message; optionally provider name, status code, correlation id), whether a `retryable: bool` class attribute is exposed
- Constraint from Phase 2 success criterion #3: call sites still re-raise `QueryError` on Azure timeout/5xx, so `LLMError` subclasses must be **catchable** by name at the call-site boundary

**3. Method contracts on `LLMClient`**
- Two methods enforced at construction: `complete(...)` and `classify_with_tool(...)`
- Open: exact signatures, what dataclasses they consume/produce
  - `complete` input: messages list (likely `list[dict]` matching the existing Azure shape to keep Phase 2 parity trivial — but a `Message` dataclass is acceptable if conversion is cheap), plus kwargs (`model`, `temperature`, `max_tokens`, etc.) or a `CompletionRequest` dataclass
  - `complete` output: a `CompletionResult` dataclass with at minimum `text: str` and optional `usage`, `model`, `provider`, `latency_ms` — Phase 2 success criterion #4 requires one structured log event per call with provider/model/latency/outcome/tokens, so the result needs to carry enough to log
  - `classify_with_tool` input: messages + tool definition + tool name
  - `classify_with_tool` output: a `ToolCall` dataclass with the validated tool input (Phase 4 success criterion #2)
- Researcher should propose signatures that minimize Phase 2 diff against the current `_call_azure_openai` callers

**4. Factory + caching**
- `get_llm(provider)` is cached (success criterion #3) — caching key in Phase 1 can be just `provider` (no key fingerprint yet, per MVP decision above)
- Resolution order: explicit kwarg → `st.session_state["llm_provider"]` → `LLM_PROVIDER_DEFAULT` env → `"azure_openai"`
- Open: registry pattern (dict mapping provider string → adapter class) vs `if/elif` — researcher's call; both satisfy the criterion. Note Phase 1 only registers one provider (Azure) and a stub/raise for `anthropic_mgti` if needed; the real Azure adapter doesn't land until Phase 2

</decisions>

<specifics>
## Specific Ideas

- **MGTI Anthropic skill exists** (`mgti-anthropic-integration` — see `~/.claude` skills) and documents the exact request/response shape, headers (`X-Api-Key`, `X-Correlation-Id`, `anthropic-version: bedrock-2023-05-31`), model-name validation (`eu.anthropic.claude-*`), and guardrail handling. Researcher should consult this when shaping `complete()` and the error taxonomy so Phase 3 plugs in with zero seam friction.
- **Parity gate in Phase 2 is the constraint:** every Phase 1 shape decision should be evaluated against "will this make the Azure extraction byte-identical?" If a fancier interface would require translating Azure's existing message format, prefer the simpler one.
- Default provider stays `azure_openai` — this is locked in PROJECT.md key decisions.

</specifics>

<deferred>
## Deferred Ideas

- **API key fingerprinting / live key reload** — deferred to Phase 5 if the UI toggle requires re-resolving adapters when env vars change mid-session; may not be needed at all for MVP
- **Secret vault / rotation tooling** — explicitly out of scope (MVP uses `.env`)
- **Telemetry/observability backend** (beyond structured logs) — Phase 2/3 emit log events; shipping them to a sink is a future concern

</deferred>

---

*Phase: 01-abstraction-seam*
*Context gathered: 2026-05-19*
