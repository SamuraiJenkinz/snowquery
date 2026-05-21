# Phase 5: Sidebar UI Toggle + Documentation - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Expose provider selection in the Streamlit sidebar (Azure OpenAI default-selected), surface the provider + model on every assistant message, render a clear inline warning when the selected provider's credentials are missing, and document the feature end-to-end in README and USER_GUIDE. The selection persists in `st.session_state["llm_provider"]`, initialized from `LLM_PROVIDER_DEFAULT`. The `@st.cache_resource` adapter resolves with cache key `(provider, base_url, model, api_key_fingerprint)` so mid-session switches take effect on the next query without retroactive recompute.

Out of scope for this phase (new capabilities — belong in their own phase): multi-provider streaming, per-query provider override controls, server-side provider preference persistence, any change to provider behavior or smoke-test contract.

</domain>

<decisions>
## Implementation Decisions

### Sidebar layout & affordances
**Claude's Discretion — research-driven.** Researcher should investigate Streamlit sidebar patterns for `st.selectbox` placement, idiomatic ways to surface a read-only "active model" string beneath a selector, and conventions for help/tooltip text length. Planner picks: label wording for the selectbox ("LLM provider" per SC #1), position within the existing sidebar, exact widget used to display the read-only model name (caption vs code vs small markdown), and whether to include a help icon explaining the choice.

### Missing-credential warning UX
**Claude's Discretion — research-driven.** Researcher should investigate idiomatic Streamlit warning patterns (`st.warning` vs `st.error` vs `st.info`) for inline sidebar use, and how existing Streamlit apps disable a chat submit path when a precondition fails. Planner picks: warning severity and exact wording, what specifically gets blocked (chat input vs submit-only), how the user recovers (switch provider back vs populate `.env`), and whether the warning surfaces which specific env vars are missing (it should — `validate_config()` already returns the list).

### Per-message provider/model caption
**Claude's Discretion — research-driven.** Researcher should investigate Streamlit chat-message caption / metadata patterns and how existing chat apps surface provenance per assistant message without visual clutter. Planner picks: caption format (provider-only vs provider + model name), position (above message, below, inline), styling (`st.caption` vs small markdown), and whether the caption is recomputed for historical messages on provider switch (it should NOT — captions reflect the provider that produced that specific message).

### Documentation split & depth
**Claude's Discretion — research-driven.** Researcher should review existing README.md and USER_GUIDE.md (if present) to determine current structure and reading audience before deciding where each new content block lands. Planner picks: which document gets the conceptual "provider selection" overview, which gets the operational "switching providers / resolving warnings" walkthrough, whether to embed screenshots, and whether to include a first-time-Anthropic-setup checklist (env vars → smoke-test → toggle → first query).

### Locked by ROADMAP / Phase 4 contract (NOT discretionary)
- Selectbox label is exactly `"LLM provider"` (SC #1)
- Two options only: `"Azure OpenAI"` and `"Anthropic Claude (MGTI)"` (SC #1)
- Selection persists in `st.session_state["llm_provider"]`, initialized from `LLM_PROVIDER_DEFAULT` env var (SC #1)
- Active model name displayed read-only beneath the selectbox (SC #1)
- Provider switch takes effect on the **next query only** — no retroactive recompute (SC #2)
- Adapter cache key includes `(provider, base_url, model, api_key_fingerprint)` (SC #2)
- Missing-creds warning is rendered inline in the sidebar (not a modal, not a toast); submission is disabled until resolved or provider switched back (SC #3)
- Every assistant message displays a caption with provider and model (SC #4)
- Documentation MUST cover: provider selection, MGTI-only constraint for Anthropic, how to run `scripts/smoke_llm.py`, and what to do when a provider warning appears (SC #5)

</decisions>

<specifics>
## Specific Ideas

The user explicitly delegated all four discussed areas ("Based upon your in-depth research I will defer these decisions in these areas to your finding"). The researcher's mandate is therefore broader than usual for this phase:

- Treat each Claude's-Discretion area as a research target with a concrete deliverable (recommended pattern + rationale, not just options)
- Cross-reference against existing app conventions in `app.py` and any sidebar widgets already present (so the new toggle doesn't visually clash)
- Validate proposed patterns against current Streamlit version pinned in `requirements.txt`

Default-selected provider stays `azure_openai` (locked at Phase 3 — existing deployments remain byte-identical until an operator opts in).

</specifics>

<deferred>
## Deferred Ideas

- Per-query provider override (separate from session-level toggle) — future phase if operators request it
- Persisting provider choice server-side or per-user — out of scope (session state is sufficient for the operator-controlled tool this app is)
- Provider-specific UI affordances beyond the caption (e.g. distinct color, badge) — Claude may add lightly if research supports it, but not a requirement
- Telemetry / metric on toggle usage — separate observability work, not this phase

</deferred>

---

*Phase: 05-sidebar-ui-toggle-documentation*
*Context gathered: 2026-05-21*
