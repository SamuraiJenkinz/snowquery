# snow_query

## What This Is

A local-first Streamlit app for querying ServiceNow incident CSVs in natural language. The app classifies user intent, routes to SQL (DuckDB), semantic search (ChromaDB), or a hybrid of both, and produces tables, charts, and executive summaries. All data stays local; only the LLM call leaves the machine. As of v2.1, operators choose between Azure OpenAI and Anthropic Claude (via the MGTI Apigee/Bedrock proxy) per session.

## Core Value

Operators get accurate, fast natural-language answers about ServiceNow incidents using the LLM they choose — without their incident data ever leaving the box.

## Current State

**Shipped:** v2.2 (2026-05-24) — SNOWGREP Visual Revamp (Loro Piana). Brutalist terminal CSS replaced with editorial warm-toned design system across every screen — helix-motif splash, branded SNOWGREP logo, small-caps tracked sidebar, warm-beige user-message cards, editorial HTML table hero + collapsible interactive view, `loro_piana` Altair theme with vibrant categorical palette, horizontal bar charts with value labels, polished edge states. v2.1 LLM behavior untouched; all 22 v2.1 locked UI strings preserved verbatim; AST-locked `_render_provenance_caption` invariant preserved. 103/103 tests green (91 v2.1 + 12 new visual regression).

**Previously shipped:** v2.1 (2026-05-22) — Multi-provider LLM integration. Anthropic Claude (via MGTI Apigee/Bedrock proxy) alongside Azure OpenAI; provider toggle in sidebar; per-message provenance preserved across mid-session switches; missing-env warning disables chat input; `scripts/smoke_llm.py` gates production deploy.

**Open pre-prod gate (carried from v2.1):** Operator-run live smoke against staging MGTI gateway (`python scripts/smoke_llm.py --provider both --verbose`). Smoke script artifact is structurally verified; live execution requires staging credentials not present in CI/dev. See `.planning/milestones/v2.1-MILESTONE-AUDIT.md` §7.

## Next Milestone Goals

After v2.2 ships, candidate v2.3+ areas (v2 backlog from v2.1 + v2.2):

**From v2.1 backlog:**
- **Resilience**: Retry with exponential backoff on `LLMTransientError` (429 / 5xx)
- **Provider features**: Per-call-site model selection (Haiku for `classify_intent` / Sonnet for `generate_executive_summary`)
- **Opus 4.7 with adaptive thinking** — pending Hubble entitlement
- **Connection-test button**: Sidebar widget that runs a minimal Create Message call and reports latency

**From v2.2 backlog:**
- **THM-01**: Theme toggle in sidebar to switch between Loro Piana (default) and brutalist (preserved as alternate)
- **THM-02**: Dark-mode luxury variant — same warm earth tones at lower luminance for low-light operator environments
- **MIC-01**: Card hover states — subtle warm-beige shadow lift on assistant message cards
- **MIC-02**: Provider switch transition — fade between sidebar widget states when provider dropdown changes
- **CHT-01**: Sparkline column in editorial table for time-series fields
- **CHT-02**: Interactive crossfilter between editorial table and chart (click a bar → filter the table)

**Tech debt to optionally address:**
- Add `[tool.pytest.ini_options]\npythonpath = ["."]` to `pyproject.toml` (or create `conftest.py`) so bare `pytest tests/` works without `PYTHONPATH=.` prefix
- Migrate sidebar password-gate `st.error()` (app.py:209) + CSV-load/embeddings-build `st.error()` calls (app.py:161, 491) to `_render_error_html` if a richer treatment is desired
- Replace legacy `class="query-box"` div on the executive-summary block (app.py:588) with an editorial class name

## Requirements

### Validated

<!-- Existing capabilities inferred from .planning/codebase/ARCHITECTURE.md + STACK.md, plus everything shipped in v2.1. -->

Existing (pre-v2.1):

- ✓ CSV ingestion into DuckDB with multi-encoding fallback and schema inference
- ✓ Password-protected sidebar upload (`SNOWGREP_UPLOAD_PASSWORD`)
- ✓ Local semantic embeddings via `sentence-transformers` (`all-MiniLM-L6-v2`) + ChromaDB
- ✓ Intent classification via Azure OpenAI with heuristic fallback
- ✓ NL → SQL generation via Azure OpenAI with few-shot examples
- ✓ SQL execution against DuckDB with SELECT-only security gate
- ✓ Semantic search with metadata filters (priority, assignment_group)
- ✓ Hybrid query mode (SQL + semantic, deduplicated)
- ✓ Chart inference and Altair rendering (pie / bar / line, dark theme)
- ✓ Executive summary generation via Azure OpenAI
- ✓ Streamlit chat UI with persistent session state
- ✓ Persistent storage for DuckDB and ChromaDB on local disk
- ✓ Corporate proxy / Windows cert store support via `python-certifi-win32`

Shipped in v2.1 (2026-05-22):

- ✓ Provider-agnostic LLM seam (`src/llm/`) — `LLMClient` ABC, 6 typed errors, frozen+slots boundary types — v2.1
- ✓ Azure OpenAI extracted into adapter with byte-identical parity gate; all 3 LLM call sites route through `get_llm()` — v2.1
- ✓ Anthropic Claude (via MGTI Apigee/Bedrock proxy) wired with `X-Api-Key` auth, `X-Correlation-Id` per call, `eu.anthropic.claude-` prefix enforcement, opus-4-7 sampling-param omission — v2.1
- ✓ Per-provider typed-error mapping: 401/403 → auth, 429/5xx → transient, timeout → timeout, `stop_reason=guardrail_intervened` → guardrail, missing tool_use → schema — v2.1
- ✓ Strict-tools intent classification with `INTENT_TOOL` derived programmatically from `ClassificationResultV1`; `chart_requested`/`chart_type` excluded from LLM schema (heuristic-only) — v2.1
- ✓ Sidebar provider dropdown with session_state persistence + active-model caption; default `LLM_PROVIDER_DEFAULT=azure_openai` for byte-identical upgrade — v2.1
- ✓ Missing-env warning that disables `st.chat_input` with "QUERY DISABLED — see sidebar warning" placeholder — v2.1
- ✓ `@st.cache_resource` 4-arg tuple cache key (provider, base_url, model, api_key_fingerprint) — switching ANY of these re-resolves the adapter — v2.1
- ✓ Per-message provenance caption (`via **Provider** · \`model\``) that survives mid-session provider switches via stored-dict reads (AST-locked invariant: helper never reads session_state) — v2.1
- ✓ `_compat.py` per-provider QueryError dispatch on `e.provider` — Anthropic timeouts surface as "Anthropic API call failed", not "Azure OpenAI API call failed" — v2.1
- ✓ Env-flag escape hatch `ANTHROPIC_TOOLS_SUPPORTED=false` falls back to text-mode + JSON parse for classify_intent if MGTI proxy regresses on tool pass-through — v2.1
- ✓ `scripts/smoke_llm.py` operator-run live-credential gate (`--provider azure_openai|anthropic_mgti|both`) with service-info + complete + classify_with_tool checks — v2.1
- ✓ README + USER_GUIDE document provider selection, MGTI-only constraint, smoke script, warning resolution; 7 locked UI strings preserved verbatim in both docs — v2.1
- ✓ Comprehensive test coverage: 91 tests across Phases 1-5 in 8.13s, zero live HTTP / LLM / Streamlit / subprocess / network — v2.1

Shipped in v2.2 (2026-05-24):

- ✓ Splash screen with helix-motif data animation on boot (`src/ui/splash.py`); EB Garamond wordmark + two diagonal INC ID streams; `prefers-reduced-motion`-compliant; 4s hard cap; single-shot per browser session via `_splash_shown` — v2.2
- ✓ Foundation CSS module (`src/ui/css.py`, 1,407 LOC) — EB Garamond + Inter + JetBrains Mono fonts, warm earth palette (`#F5F0EB` / `#8B7355` / `#2C2420` family), Streamlit color variable overrides; single `LORO_PIANA_CSS` injection from `app.py`; no inline `<style>` blocks remain — v2.2
- ✓ Sidebar restyle — branded SNOWGREP PNG logo (320px width), small-caps tracked section labels (DATA, EMBEDDINGS, LLM PROVIDER, MODE), MODE radio with sage active-dot via `:has(input:checked)`, EMBEDDINGS sage/terracotta pill, bottom-border-only LLM PROVIDER select with locked label "LLM provider" — v2.2
- ✓ Main panel restyle — branded SNOWGREP hero logo, ghost example queries (click-to-fill), warm-beige user message cards aligned right (max 70% width), white assistant cards with `1px solid #E8E0D8` border aligned left (max 85% width), restyled chat input with cashmere ASK submit — v2.2
- ✓ Provenance caption restyle — Inter 500 small-caps 11px muted gold `#B8A88A`; AST-locked v2.1 invariant preserved (helper still reads only function args, never `st.session_state`) — v2.2
- ✓ Editorial HTML table hero (`_render_editorial_table` in `src/ui/results.py`) — italic priority cells, warm-beige row dividers, EB Garamond small-caps headers, 16/24px padding; 50-row truncation with comma-formatted caption — v2.2
- ✓ Collapsible interactive dataframe — single `st.expander("EXPAND · INTERACTIVE VIEW")` (U+00B7 middot) beneath every editorial table containing native `st.dataframe(use_container_width=True, hide_index=True)` + CSV download; zero functionality loss vs. v2.1 — v2.2
- ✓ Altair `loro_piana` theme module (`src/ui/altair_theme.py`) — registered via Altair 6 `@alt.theme.register("loro_piana", enable=True)`; transparent bg, warm-beige gridlines, EB Garamond titles, no axis box; `VIBRANT_PALETTE` = `[#C0392B, #2E5BBA, #2E7D32, #E67E22, #F39C12]` (crimson, royal blue, forest green, burnt orange, mustard yellow) — v2.2
- ✓ Chart generator restyled (`src/chart_generator.py`) — `CHART_COLORS` + `configure_chart_theme` deleted; bar charts horizontal with layered value labels (Inter 12px charcoal, comma-formatted, dx=4, align=left); `legend=None` on single-series — v2.2
- ✓ Editorial empty state (`_render_empty_card`) — EB Garamond 24px "No data loaded" + Inter 15px warm-gray "Upload incidents.csv from the sidebar to begin." — v2.2
- ✓ Provider-warning state restyled — warm-beige `#F5F0EB` background + terracotta `#A67866` 3px left border + "WARNING — PROVIDER NOT CONFIGURED" small-caps; "QUERY DISABLED — see sidebar warning" placeholder preserved verbatim — v2.2
- ✓ Loading indicators — `.lp-loading` small-caps tracked replaces `st.spinner` at 4 callsites: LOADING DATA, BUILDING EMBEDDINGS ×2, ANALYZING; Inter 500 11px muted gold with `@keyframes lp-pulse` — v2.2
- ✓ Editorial error rendering (`_render_error_html`) — terracotta 3px left border + small-caps "ERROR" label + XSS-escaped message body at 6 process_query error paths + outer try/except for `QueryError`/`LLMError` — v2.2
- ✓ Streamlit alert palette overrides via CSS sweep — `stAlertContainer`, `stAlertContentSuccess|Error|Warning|Info`, `stAlertDynamicIcon` hidden; zero call-site edits — v2.2
- ✓ Page chrome refresh — `page_icon` `▣` → `✦` (U+2726); `page_title="SNOWGREP"` preserved verbatim — v2.2
- ✓ USER_GUIDE.md "VISUAL REFRESH (v2.2)" section + v2.2 footer; README.md "Screenshots" subsection with three byte-identical PNG copies in `docs/screenshots/`; loro-piana-aesthetic skill referenced — v2.2
- ✓ All 22 v2.1 Phase 5 UI tests stay green throughout — locked strings (LLM provider, Azure OpenAI, Anthropic Claude (MGTI), QUERY DISABLED — see sidebar warning, Ask anything about your incidents…, Ask in natural language. All data stays local., WARNING — PROVIDER NOT CONFIGURED) preserved verbatim — v2.2
- ✓ New `tests/test_phase6_visual.py` (12 tests, 314 LOC) — CSS presence/absence, renderer signatures, Altair theme registration, WCAG-AA contrast via inline sRGB linearization (`#2C2420`/`#F5F0EB` = 13.4363; `#6B5E52`/`#F5F0EB` = 5.5393), negative usage scan over `var(--lp-text-muted)` rules with role-marker contract — v2.2

### Active

<!-- v2.3 scope TBD — populated by /gsd:new-milestone after a fresh requirements pass. -->

(None — see Next Milestone Goals above for candidate areas)

### Out of Scope

<!-- Explicit exclusions with reasoning. -->

- Direct Anthropic API (`api.anthropic.com`) — not authorized in MMC corporate app context; MGTI proxy only
- Claude models below 4.5 — MGTI proxy explicitly restricts to Claude 4.5+ with the `eu.` regional prefix
- Per-call automatic provider routing (e.g. "use Anthropic for classification, OpenAI for SQL") — user picks one provider per session; rejected as added complexity without proven payoff
- Removing the Azure OpenAI integration — both providers remain first-class
- Streaming responses — current call sites are request/response; staying request/response keeps the UI integration trivial
- Official Anthropic Python SDK — corporate proxy headers + custom URL shape means the existing `requests`-based pattern is correct
- Auto-failover between providers — would silently bypass content policy (guardrails); user must consciously switch
- OpenAI-shape translation layer — each adapter speaks its provider's native shape; no compatibility middleware
- Embedding-model swap to Bedrock embeddings — local `sentence-transformers` stays for data-privacy reasons
- Cost dashboards / usage analytics across providers — possible future milestone, not in v2.1
- Semantic cache of LLM responses — would compromise data-privacy invariants
- OpenTelemetry trace export — log-based correlation IDs sufficient for single-user local-first app
- Mid-session provider switch mid-query — confusing behavior; user-initiated swap-then-resend is the explicit pattern
- Free-form `chat(message)` method on the interface — invites shape drift
- Async LLM calls — Streamlit is synchronous; no benefit until we move off it
- Porting `app_brutalist.py` / `fixedapp.py` / `designui.py` variants — they may consume the new abstraction later; not in scope

## Context

**Infrastructure:**
- MMC corporate app context — runs against Apigee-fronted MGTI gateways
- Azure OpenAI ingress lives at `mgti.mmc.com`
- Anthropic proxy lives at `apis.mmc.com` (different host, different auth header, different request shape — they are NOT interchangeable)
- Stage Anthropic gateway: `https://stage.int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1`
- Prod Anthropic gateway: `https://int.nasa.apis.mmc.com/coreapi/llm/anthropic/v1`

**Current LLM call sites:**
1. `src/query_router.py::classify_intent()` — strict-tools mode on Anthropic; prompt-based JSON parse on Azure
2. `src/sql_generator.py::generate_sql()` — text mode on both providers, max_tokens=1000
3. `src/query_router.py::generate_executive_summary()` — text mode on both providers, max_tokens=500; broad `except Exception: return None` invariant preserved

All routed through `LLMClient` via `get_llm()` + `llm_to_query_error()`.

**Test suite:** 103 tests (91 v2.1 + 12 new v2.2 visual regression) across `tests/test_llm_seam.py`, `tests/test_phase2_parity.py`, `tests/test_phase3_adapter.py`, `tests/test_phase4_strict_tools.py`, `tests/test_phase5_ui.py`, `tests/test_phase6_visual.py`. Zero live HTTP / LLM / Streamlit / subprocess / network. Combined run: ~10s with `PYTHONPATH=. python -m pytest tests/ -q`.

**Codebase state after v2.2:**
- ~1,964 LOC in `src/llm/` (8 modules — unchanged from v2.1)
- ~2,290 LOC in `src/ui/` (5 modules: `__init__.py`, `css.py`, `altair_theme.py`, `results.py`, `splash.py` — new in v2.2)
- 470 LOC `scripts/smoke_llm.py` (unchanged from v2.1)
- ~3,050 LOC in v2.1 test files + 314 LOC `tests/test_phase6_visual.py` (new in v2.2)
- v2.1 range: 80 files changed (+26,275 / -250)
- v2.2 range: 75 files changed (+16,646 / -677) across 89 commits over 2 days (2026-05-22 → 2026-05-24)
- `static/snowgrep-logo.png` + `.streamlit/config.toml` (`enableStaticServing = true`) — new in v2.2
- `docs/screenshots/` byte-identical PNG copies of `.planning/design-mockups/` — new in v2.2

## Constraints

- **Tech stack**: Python 3.11, Streamlit ≥1.40, `requests` for HTTP — no SDK migration in scope
- **LLM transport**: HTTPS only through MGTI Apigee proxy — corporate compliance; direct API not permitted
- **Model**: Claude 4.5+ with `eu.` regional prefix — hard requirement from the MGTI proxy
- **Auth**: `X-Api-Key` for Anthropic, `api-key` for Azure OpenAI — different gateways, different conventions
- **Anthropic request body**: `anthropic_version: bedrock-2023-05-31`, top-level `system`, required `max_tokens`
- **Data privacy**: Incident data must not leak beyond the LLM call payload itself — embeddings stay local, persistence stays local
- **Performance**: New provider path matches Azure OpenAI baseline latency within ~20%
- **Backwards compatibility**: Azure OpenAI flow remains functional and default-selected — `LLM_PROVIDER_DEFAULT=azure_openai`
- **Secrets**: API keys live in `.env`, never committed; never logged

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| User-selectable provider in UI (sidebar dropdown) | Operators need to A/B providers per session as conditions shift; per-deploy env-var locking is too coarse | ✓ Good — UI-01..07 shipped in v2.1 Phase 5; no operator escalation requesting deploy-time-only |
| Both providers stay configured; no replacement | Removes the migration risk and preserves Azure OpenAI as a fallback if the Anthropic proxy degrades | ✓ Good — default stays `azure_openai`; existing deployments byte-identical after upgrade |
| Strict-tools mode for intent classification only | Classification returns structured JSON — schema enforcement here eliminates parse-failure cascades; SQL/summaries are text by nature and don't benefit | ✓ Good — 30-test Phase 4 gate covers all branches; env-flag fallback ready if MGTI proxy regresses |
| MGTI Apigee proxy only, no direct Anthropic API | Corporate compliance; this is an MMC app context | ✓ Good — locked into adapter __init__ via `eu.anthropic.claude-` prefix validation |
| Provider abstraction layer (interface + two adapters) over per-call `if` branches | Three call sites today, more later; keeping site-level code provider-agnostic is the only way to keep it readable | ✓ Good — `LLMClient` ABC + `get_llm()` factory; future third adapter triggers `_log_llm_call` extraction (currently duplicated by design) |
| Anthropic adapter speaks native MGTI shape, not an OpenAI translation layer | The skill provides a validated minimal adapter; translating Anthropic-into-OpenAI-shape adds bugs with no upside | ✓ Good — `_compat.py` translates errors only, never request shapes |
| Live smoke test required before any prod deploy | Validated practice from kbroles Quicks 008–012; catches the `/messages` and `eu.`-prefix bugs that unit tests can't | ⚠️ Pending operator — script artifact exists + structurally verified; live run against staging is the open pre-prod gate (SMK-05 in v2.1 audit §7) |
| Default provider stays Azure OpenAI initially | Don't change observable behavior of existing users in the same release that adds the new option | ✓ Good — zero regression reports; upgrade is byte-identical |
| Flat error hierarchy (no retryable grouping) | Retry logic isn't in v2.1 scope; defer grouping until v2 RES-01 lands with production signal | — Pending — retry logic in v2 backlog |
| Single cache layer: `@st.cache_resource` only | Phase 1 module-level `_cache: dict` + Streamlit cache would be double-caching; the dict was anticipated for deletion at Phase 1 close | ✓ Good — Phase 5 deleted the dict; single-cache lock holds |
| `_log_llm_call` duplicated between azure_openai.py and anthropic_mgti.py | No premature extraction until a third adapter exists; both files annotate the duplication | — Pending — extract when third adapter lands |
| `_compat.py` dispatches on `e.provider` for per-provider QueryError wording | Phase 2 hardcoded Azure remediation text; Phase 3 added dispatch to prevent "Azure OpenAI API call failed" appearing for Anthropic errors | ✓ Good — locked by Phase 4 COMPAT-DISPATCH test pair |
| `_render_provenance_caption` must never read `st.session_state` | History messages must keep their original provenance after a mid-session provider switch — caption helper must read from the stored message dict, not current session_state | ✓ Good — AST-based regression test locks the invariant at executable level (test_sc4_render_provenance_caption_does_not_read_session_state) |
| `INTENT_TOOL` derived via `typing.get_type_hints()` not `fields().type` | Under `from __future__ import annotations`, `fields().type` returns strings — `get_type_hints` resolves to types | ✓ Good — Phase 4 Pitfall 1 guard; locked by acceptance gate |
| `chart_requested`/`chart_type` heuristic-populated, excluded from LLM schema | Heuristic outperforms the LLM on these two fields; LLM cannot overwrite the heuristic for them | ✓ Good — TOOL-04 test injects `chart_requested=True` into ToolCall.input and asserts classify_intent reads from heuristic locals (False) |
| Guardrail check BEFORE content-emptiness check in Anthropic HTTP 200 handler | Anthropic returns HTTP 200 + empty content when guardrail intervenes; checking emptiness first would silently succeed on guardrail blocks | ✓ Good — Phase 3 Pitfall 4 guard; locked by paired tests `test_guardrail_intervened_raises_guardrail_error` + `test_empty_content_non_guardrail_raises_schema_error` |
| v2.2: Phase 8 merged from two phases to one (two waves) | Sidebar + main panel target disjoint DOM regions and consume Phase 6 tokens read-only; mergeable into one phase with two parallel waves (Wave A: SBR-*, Wave B: MAIN-*) | ✓ Good — reduced v2.2 phase count from 8 to 7 without losing coverage; both waves shipped 2026-05-23 |
| v2.2: Editorial HTML hero + `st.expander` for native dataframe (DVZ-02) | Chosen over fighting glide-data-grid CSS; removes 4-6h estimate risk; zero functionality loss vs. v2.1 | ✓ Good — operators get scannable editorial view + full interactivity one click away; no widget feature loss |
| v2.2: `st.radio(horizontal=True)` for MODE with `:has(input:checked)` sage active-dot (SBR-03 approved deviation) | Three `st.button` pills failed because sibling DOM structure prevented active-state CSS matching; native primitive with `:has()` selector is cleaner and Streamlit-idiomatic | ✓ Good — same write contract (`query_mode` ∈ `auto/structured/semantic`); no Python-side class juggling |
| v2.2: Branded SNOWGREP PNG logo for both sidebar and main panel hero (SBR-01/MAIN-01 approved deviation) | Single asset at `static/snowgrep-logo.png` served via Streamlit static serving (`enableStaticServing = true`); dark backdrop intentional — high-contrast brand mark against warm-beige page | ✓ Good — alt text carries "Incident Intelligence" for accessibility; visually approved by user |
| v2.2: DVZ-03 truncation cap at 50 rows, not REQUIREMENTS.md's `>1000` (approved deviation) | Editorial table is the hero view and must be scannable at a glance; full df still available behind the expander | ✓ Good — encoded as `_TRUNCATION_CAP = 50` constant; comma-formatted N in caption |
| v2.2: Altair 6 `@alt.theme.register("loro_piana", enable=True)` decorator API (DVZ-04) | NOT the deprecated `alt.themes.*` namespace; `enable=True` registers and activates in one call | ✓ Good — SNOWGREP canonical pattern; activates process-wide at import time via side-effect import `import src.ui.altair_theme  # noqa: F401` in `app.py` |
| v2.2: `src/ui/css.py` is the single source of truth for hex values | No module is permitted to hardcode Loro Piana hex values or Streamlit selector overrides | ✓ Good — documented exception: `src/chart_generator.py:350` `mark_text(color="#2C2420")` and line mark `color="#C0392B"` are Altair mark properties (not color encodings) where theme `range.category` does not apply |
| v2.2: `VIBRANT_PALETTE` in `src/ui/altair_theme.py:42-48` is the canonical chart data palette source | Five hex values: `#C0392B` (crimson), `#2E5BBA` (royal blue), `#2E7D32` (forest green), `#E67E22` (burnt orange), `#F39C12` (mustard yellow); imported by `src/chart_generator.py` | ✓ Good — Phase 12 doc-accuracy cleanup re-aligned USER_GUIDE.md:36 to match this exactly |
| v2.2: Pure-string-builder pattern for renderers (`src/ui/results.py`) | Functions return HTML strings; `st.markdown(html, unsafe_allow_html=True)` wrapping happens at call sites in `app.py`. All dynamic inputs `html.escape()`-wrapped | ✓ Good — no Streamlit import in renderer module; XSS contract documented in module docstring |
| v2.2: `PYTHONPATH=. python -m pytest tests/` invocation pattern | Repo has no `pyproject.toml` / `pytest.ini` / `conftest.py`; bare `pytest tests/` fails with `ModuleNotFoundError: No module named 'src'` | — Pending — adding `[tool.pytest.ini_options]\npythonpath = ["."]` deferred to v2.3 backlog as orthogonal change |
| v2.2: Phase 12 inserted late to close audit doc-drift | Initial milestone audit returned `tech_debt` status with 4 low-severity doc-drift items in USER_GUIDE.md / README.md; Phase 12 (`doc-accuracy-cleanup`) closed all four | ✓ Good — re-audit promoted milestone to `passed`; established pattern of audit → close-gaps → re-audit before archival |
| v2.2: `AST-locked _render_provenance_caption` invariant preserved across 7 phases | Helper body reads only function args, never `st.session_state`; regression test in `tests/test_phase5_ui.py` runs after every phase | ✓ Good — load-bearing invariant from v2.1 Phase 5 stayed green throughout v2.2 |

---
*Last updated: 2026-05-24 after v2.2 milestone complete (Phases 6-12 shipped). 36/36 v2.2 v1 requirements validated; 103/103 tests green.*
