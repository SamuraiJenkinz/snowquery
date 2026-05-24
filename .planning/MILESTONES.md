# Project Milestones: snow_query

## v2.2 SNOWGREP Visual Revamp — Loro Piana Quiet Luxury (Shipped: 2026-05-24)

**Delivered:** The brutalist terminal CSS was replaced with an editorial Loro Piana quiet luxury aesthetic across every screen — helix-motif splash, branded SNOWGREP logo, small-caps tracked sidebar, warm-beige user-message cards, editorial HTML table hero + collapsible interactive view, `loro_piana` Altair theme with vibrant categorical palette, polished edge states — without touching v2.1 LLM behavior and without losing any v2.1 functionality.

**Phases completed:** 6-12 (17 plans total across 7 phases; Phase 12 inserted late to close audit doc-drift)

**Key accomplishments:**

- **Foundation CSS module + design tokens** — `src/ui/css.py` (1,407 LOC) exports `LORO_PIANA_TOKENS` dict and `LORO_PIANA_CSS` string as the single source of truth; EB Garamond + Inter + JetBrains Mono fonts (mono confined to code/data); warm earth palette `#F5F0EB` / `#8B7355` / `#2C2420`; single CSS injection from `app.py` — no inline `<style>` blocks remain; page chrome glyph refreshed `▣` → `✦`.
- **Helix-motif splash screen** — `src/ui/splash.py` (419 LOC) emits a self-contained `streamlit.components.v1.html` block with EB Garamond wordmark + two diagonal animated INC ID streams; iframe-managed 4s hard cap; `prefers-reduced-motion: reduce` swaps translation for fixed-position fades; single-shot per browser session via `_splash_shown` flag.
- **Editorial sidebar + main panel restyle (Phase 8, 12 reqs)** — branded SNOWGREP PNG logo at top of sidebar + main hero (`static/snowgrep-logo.png` served via `enableStaticServing = true`); small-caps tracked DATA/EMBEDDINGS/LLM PROVIDER/MODE labels; MODE `st.radio(horizontal=True)` with `:has(input:checked)` sage active-dot (approved deviation from button pills); EMBEDDINGS sage/terracotta status pill; bottom-border-only LLM PROVIDER select with locked `"LLM provider"` label; warm-beige `+` terracotta 3px left border WARNING card; warm-beige user-message cards (right-aligned, max 70%), white assistant cards with `1px solid #E8E0D8` border (left-aligned, max 85%); restyled provenance caption preserves the AST-locked v2.1 invariant (helper still reads only function args, never `st.session_state`); chat input bottom-border-only with cashmere ASK submit; all v2.1 locked UI strings preserved verbatim.
- **Editorial data visualization** — `_render_editorial_table` in `src/ui/results.py` (360 LOC, 5 functions) replaces native `st.dataframe` as hero view; italic priority cells, warm-beige row dividers, EB Garamond small-caps headers, 16/24px padding; 50-row truncation cap (approved deviation from 1000) with comma-formatted caption; full interactivity preserved behind single `st.expander("EXPAND · INTERACTIVE VIEW")` (U+00B7 middot). Custom `loro_piana` Altair theme registered via Altair 6 `@alt.theme.register("loro_piana", enable=True)` decorator API; `VIBRANT_PALETTE` = `[#C0392B, #2E5BBA, #2E7D32, #E67E22, #F39C12]` (crimson, royal blue, forest green, burnt orange, mustard yellow) is canonical chart data palette source; bar charts rewritten horizontal with layered value labels, no legend on single-series.
- **Polish + edge states** — `_render_empty_card` editorial empty-state for no-CSV; `.lp-loading` small-caps tracked indicators replace `st.spinner` at 4 callsites (LOADING DATA, BUILDING EMBEDDINGS ×2, ANALYZING) with `@keyframes lp-pulse`; XSS-escaped `_render_error_html` (terracotta 3px left border + "ERROR" label) at 6 process_query error paths + outer try/except for `QueryError`/`LLMError`; Streamlit alert palette overrides via CSS sweep — no browser-default toast colors leak through; zero call-site edits required for POL-04.
- **Documentation + acceptance gate (Phases 11-12)** — USER_GUIDE.md "VISUAL REFRESH (v2.2)" section + TOC renumber + v2.2 footer; README.md "Screenshots" subsection between Features and Tech Stack with three byte-identical PNG copies in `docs/screenshots/`; new `tests/test_phase6_visual.py` (12 tests, 314 LOC) — CSS presence/absence, renderer signatures, Altair theme registration, WCAG-AA contrast verification via inline sRGB linearization (`#2C2420`/`#F5F0EB` = 13.4363 body 4.5:1; `#6B5E52`/`#F5F0EB` = 5.5393 large text 3:1), negative usage scan over `var(--lp-text-muted)` rules with role-marker contract (uppercase | letter-spacing ≥ 0.1em | font-size ≥ 14px). Phase 12 closed three low-severity audit doc-drift items: expander caption (USER_GUIDE.md:35 + README.md:27 → `"EXPAND · INTERACTIVE VIEW"`), chart palette description (USER_GUIDE.md:36 → full VIBRANT_PALETTE), README placeholder GitHub link removed.

**Stats:**

- 75 files changed (+16,646 / -677)
- ~2,290 LOC new Python in `src/ui/` (5 modules) + 314 LOC `tests/test_phase6_visual.py`
- 7 phases, 17 plans, 36/36 v1 requirements
- 103/103 tests green (91 v2.1 preserved + 12 new v2.2 visual regression)
- 89 commits
- 2 days from start to ship (2026-05-22 → 2026-05-24)

**Git range:** `docs: create milestone v2.2 roadmap` (b662524) → `docs(12): complete doc-accuracy-cleanup phase` (af2473c)

**Audit:** [milestones/v2.2-MILESTONE-AUDIT.md](milestones/v2.2-MILESTONE-AUDIT.md) — `passed` after Phase 12 closed initial-audit doc-drift

**What's next:** v2.3 — candidate areas: v2.1 resilience backlog (retry-with-backoff on `LLMTransientError`, per-call-site model selection, Opus 4.7 with adaptive thinking pending Hubble entitlement, sidebar connection-test button) + v2.2 visual backlog (THM-01 theme toggle, THM-02 dark-mode luxury, MIC-01/02 microinteractions, CHT-01 sparklines, CHT-02 crossfilter) + tech debt (`pyproject.toml` pytest `pythonpath` config so bare `pytest` works without `PYTHONPATH=.`).

---

## v2.1 Multi-Provider LLM Integration (Shipped: 2026-05-22)

**Delivered:** Anthropic Claude (via MGTI Apigee/Bedrock proxy) shipped as a session-selectable LLM provider alongside the existing Azure OpenAI integration, with provider-agnostic seam, byte-identical Azure parity, strict-tools intent classification, and per-message provenance that survives mid-session switches.

**Phases completed:** 1-5 (20 plans total)

**Key accomplishments:**

- Provider-agnostic LLM seam in `src/llm/` — `LLMClient` ABC, flat typed-error hierarchy (6 errors), frozen+slots adapter-boundary dataclasses, factory with single `@st.cache_resource` cache layer keyed on `(provider, base_url, model, api_key_fingerprint)`
- Azure OpenAI extracted into adapter with byte-identical parity gate (5 fixtures across structured/semantic/hybrid/exec-summary call sites); `_call_azure_openai` removed; all 3 LLM call sites route through `get_llm()` + `llm_to_query_error()`
- Anthropic MGTI adapter against `apis.mmc.com/coreapi/llm/anthropic/v1` with `X-Api-Key` auth, `X-Correlation-Id` per call, `eu.anthropic.claude-` prefix enforcement, opus-4-7 sampling-param omission, full typed-error mapping (401/403/429/5xx/timeout/guardrail/schema)
- Strict-tools intent classification — `INTENT_TOOL` derived programmatically from `ClassificationResultV1` (single source of truth, `chart_requested`/`chart_type` heuristic-only); env-flag `ANTHROPIC_TOOLS_SUPPORTED=false` escape hatch to text-mode + JSON parse
- Sidebar provider dropdown with session_state persistence, missing-env warning that disables `st.chat_input`, per-message provenance caption (`via **Provider** · \`model\``) that survives mid-session provider switches via stored-dict reads (never session_state)
- `scripts/smoke_llm.py` operator-run live-credential gate (Anthropic service-info + complete + classify_with_tool; Azure complete + classify_with_tool); README + USER_GUIDE document MGTI-only constraint, first-time Anthropic checklist, warning resolution
- Full test coverage: 91 tests in 8.13s, zero live HTTP / LLM / Streamlit / subprocess / network

**Stats:**

- 80 files changed (+26,275 / -250)
- ~1,964 LOC new Python in `src/llm/` + 470 LOC `scripts/smoke_llm.py` + ~3,050 LOC tests
- 5 phases, 20 plans, 91 tests
- 3 days from start to ship (2026-05-19 → 2026-05-22)

**Git range:** `feat(01-01)` → `docs(05)`

**What's next:** Operator-run smoke gate against staging MGTI gateway before production deploy. Next milestone TBD — candidate areas include resilience (retry-with-backoff on `LLMTransientError`), per-call-site model selection (Haiku for classify_intent / Sonnet for executive summary), Opus 4.7 with adaptive thinking (pending Hubble entitlement).

---
