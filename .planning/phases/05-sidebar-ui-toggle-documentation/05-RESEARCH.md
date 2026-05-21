# Phase 5 Research

**Researched:** 2026-05-21
**Streamlit version pinned:** `streamlit>=1.40.0` (live env: **1.52.1** — verified via `pip show streamlit`)
**Domain:** Streamlit sidebar UX + chat-message provenance + provider-cache invalidation + documentation split
**Overall confidence:** HIGH (all four discretionary areas verified against current Streamlit docs + live `inspect.signature` checks; codebase patterns read end-to-end)

---

## Summary

Phase 5 wires the existing `get_llm()` factory through a sidebar `st.selectbox`, replaces the Phase 1 module-level `_cache` dict with an `@st.cache_resource`-decorated resolver keyed on `(provider, base_url, model, api_key_fingerprint)`, blocks `st.chat_input` when the selected provider's credentials are missing, and stores per-message provider/model metadata in `st.session_state.messages` so historical captions remain accurate after a provider switch.

The pinned Streamlit version (1.40+, live 1.52.1) supports every API this plan needs: `st.chat_input(disabled=True)` (verified via `inspect.signature` — `disabled: 'bool' = False`), `st.cache_resource` with per-argument cache keys (verified via official docs — see Sources), `st.caption` with full Markdown support, and `st.warning(icon=...)`. No version-pinning bumps required.

**Primary recommendation:** Treat the four discretionary areas as a single visual contract — the toggle, the model line, the warning, and the per-message caption must all use the same compact "label / value" rhythm so the new UI surface feels like one feature rather than four widgets. Specific patterns prescribed below.

---

## Codebase Context

### Streamlit version (HIGH)
- `requirements.txt` line 1: `streamlit>=1.40.0`
- Live env: **1.52.1** (verified via `pip show streamlit`)
- Verified APIs work at the pinned floor:
  - `st.chat_input(... disabled: 'bool' = False, ...)` — present since 1.30
  - `st.cache_resource(... hash_funcs, max_entries, ttl, validate, show_spinner ...)` — stable since 1.18
  - `st.caption(body, *, help, unsafe_allow_html)` — supports GitHub-flavored Markdown
  - `st.warning(body, *, icon)` — `icon` param supports emojis and `:material/...` (since 1.23)

### Current `app.py` sidebar (HIGH — read `app.py` 402–571)

The `render_sidebar()` function (`app.py:402`) builds the sidebar in this **vertical order**, all inside `with st.sidebar:`:

1. **Logo block** — markdown HTML, `SNOWGREP` + "INCIDENT QUERY"
2. **DATA INGEST** (`app.py:416`) — password-protected file uploader
3. `st.divider()` (`app.py:485`)
4. **DATA STATUS** (`app.py:488`) — row count + column count metrics
5. `st.divider()` (`app.py:516`)
6. **EMBEDDINGS** (`app.py:519`) — embeddings count + REBUILD / UPDATE buttons
7. `st.divider()` (`app.py:547`)
8. **CONFIG** (`app.py:550`) — single expander "QUERY SETTINGS" containing a `top_k` slider, `show_sql` checkbox, `show_summary` checkbox

The brutalist CSS injection (lines 43–350) hard-codes the sidebar to **300px fixed width** (`min-width: 300px !important; max-width: 300px !important;`) — any new widget must work within that constraint. All sidebar h3 use `### UPPERCASE` markdown style, and dividers separate logical groups.

**The new `LLM PROVIDER` block fits naturally between EMBEDDINGS and CONFIG**, as a fourth top-level sidebar section. It is configuration but not "query settings" (which is per-query knobs); it is a session-level adapter choice. Putting it inside the CONFIG expander would bury it beneath an expander click on every fresh load — and per SC #3 the missing-creds warning must be **inline and visible**, which rules out the expander.

### Chat message storage and rendering (HIGH — read `app.py` 361–373, 628–643, 873–912)

**Init** (`app.py:365`):
```python
if "messages" not in st.session_state:
    st.session_state.messages = []
```

**Append on user input** (`app.py:879–882`):
```python
st.session_state.messages.append({
    "role": "user",
    "content": user_query
})
```

**Append on assistant response** (`app.py:903–912`):
```python
st.session_state.messages.append({
    "role": "assistant",
    "content": response["content"],
    "results": response["results"],
    "sql": response["sql"],
    "query_id": query_id,
    "executive_summary": response.get("executive_summary"),
    "chart": response.get("chart"),
    "chart_feedback": response.get("chart_feedback")
})
```

**Render loop** (`app.py:628–643`):
```python
def render_chat_history():
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "results" in message and message["results"] is not None:
                if not message["results"].empty:
                    display_results(...)
```

The message dict is **already a metadata bag**. Adding `"provider"` and `"model"` keys is one-line; rendering the caption is one line inside the existing `with st.chat_message("assistant"):` block. The render loop is **the ONLY place** that touches historical messages — captions are read from the stored dict, not re-resolved from current session state, so historical messages keep their original provenance after a switch.

### Current `get_llm()` factory and cache (HIGH — read `src/llm/__init__.py`)

- Module-level cache: `_cache: dict[str, LLMClient] = {}` (line 61) — keyed by **provider string only** (Phase 1 decision)
- `_resolve_provider(explicit)` (line 71–87) reads `st.session_state["llm_provider"]` via `try/except Exception` — already Phase-5-ready
- `_REGISTRY` (line 54–57) maps to `"src.llm.azure_openai:AzureOpenAIClient"` and `"src.llm.anthropic_mgti:AnthropicMGTIClient"`
- Comment at line 59–60: "Phase 5 may wrap this with `@st.cache_resource` and clear() this dict before the decorator takes over."

**What Phase 5 changes:**
- Replace the `_cache: dict` + `_cache[resolved]` lookups with an `@st.cache_resource`-decorated helper that takes `(provider, base_url, model, api_key_fingerprint)` as positional args (Streamlit caches per arg-tuple)
- The outer `get_llm(provider=None)` keeps its current signature; it now computes the cache key inputs from `load_settings()` and the resolved provider, then calls the decorated helper
- Adapters expose `_model` and (Anthropic) `_base_url` on `self` — these are already populated in both `AzureOpenAIClient.__init__` (`azure_openai.py:81–84`) and `AnthropicMGTIClient.__init__` (`anthropic_mgti.py:155–157`). The cache key inputs come from `load_settings()` directly, NOT from the constructed instance (we need them BEFORE construction to compute the key).

**Pre-construction key derivation** (the only viable order):
```python
settings = load_settings()
if provider == "azure_openai":
    base_url, model, raw_key = settings.azure_endpoint, _extract_model_from_endpoint(settings.azure_endpoint), settings.azure_api_key
elif provider == "anthropic_mgti":
    base_url, model, raw_key = settings.anthropic_base_url, settings.anthropic_model, settings.anthropic_api_key
fingerprint = _fingerprint(raw_key)
client = _get_llm_cached(provider, base_url, model, fingerprint)
```

`_extract_model_from_endpoint` already exists at `azure_openai.py:35` and is the right function to call from outside (it's module-level, not a method).

### `validate_config()` shape (HIGH — read `src/llm/config.py:112–133`)

- Signature: `validate_config(provider: str) -> None`
- Raises `LLMConfigError` with **all** missing vars in one message: `f"Missing required env vars for {provider}: " + ", ".join(missing)`
- Required vars per provider:
  - `azure_openai`: `("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY")` — `API_VERSION` has default, NOT required
  - `anthropic_mgti`: `("ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL")`
- Raises on **unknown provider** too (with the known-providers list)

**Critical for the UI warning:** `validate_config()` raises an exception. To render the warning **without throwing**, Phase 5 needs a sibling helper `missing_vars(provider) -> list[str]` (or wrap `validate_config` in `try/except LLMConfigError` and parse the message — but a separate helper is cleaner). The cleanest API addition is `missing_vars(provider: str) -> list[str]` that returns the list of missing env-var names (empty list = ok), built from the same `_REQUIRED_VARS` table. The planner picks the exact API surface; the existing `_REQUIRED_VARS` dict at `config.py:53` is the single source of truth either way.

### `scripts/smoke_llm.py` invocation surface (HIGH — read full file)

- Entry point: `python scripts/smoke_llm.py --provider {azure_openai|anthropic_mgti|both} [--verbose]`
- Exit `0` = all configured providers passed; `1` = at least one CONFIGURED provider failed
- `--provider both` SKIPs missing creds; `--provider anthropic_mgti` (explicit) **FAILs** if creds missing — important docs nuance
- Operator-run only — never in CI (live creds policy per Phase 4 CONTEXT)

### README & USER_GUIDE current state (HIGH — read both)

- **README.md** (86 lines) — short, **install/quick-start oriented**. Sections: Features, Tech Stack, Quick Start, Project Structure, Environment Variables (table), Data Privacy. Reading audience: someone cloning the repo to deploy it. No screenshots. Markdown tables for env vars.
- **USER_GUIDE.md** (378 lines) — long, **task-oriented walkthrough**. TOC with 10 sections, lots of tables for queries / chart types / keyboard shortcuts / status indicators. Reading audience: an analyst who has the app running and wants to use it. No screenshots. Uses emojis sparingly in tables. Versioned footer: "Last updated: December 2024 (v2.0 - Added password protection & chart visualization)."

The split is clear: **README is "set up the app", USER_GUIDE is "use the app".** Provider selection is partly setup (env vars, smoke test) and partly use (the toggle, what the captions mean, what to do when a warning appears). Each doc gets its half.

---

## Recommendations

### 1. Sidebar layout & affordances

**Recommendation:**

Insert a new `### LLM PROVIDER` block in the sidebar **between EMBEDDINGS and CONFIG** (after the line-547 `st.divider()` and before the existing `st.markdown("### CONFIG")`). The block contains, in order:

```python
st.markdown("### LLM PROVIDER")

# Initialize session state from env default on first render
if "llm_provider" not in st.session_state:
    default = os.getenv("LLM_PROVIDER_DEFAULT", "azure_openai")
    # Defensive: clamp unknown values to azure_openai so the selectbox
    # has a valid index even with a typo in .env
    st.session_state["llm_provider"] = default if default in PROVIDER_OPTIONS else "azure_openai"

PROVIDER_OPTIONS = {
    "Azure OpenAI": "azure_openai",
    "Anthropic Claude (MGTI)": "anthropic_mgti",
}
# Reverse map for selectbox index lookup
PROVIDER_LABELS = {v: k for k, v in PROVIDER_OPTIONS.items()}

selected_label = st.selectbox(
    "LLM provider",                              # SC #1 exact label
    options=list(PROVIDER_OPTIONS.keys()),       # ["Azure OpenAI", "Anthropic Claude (MGTI)"]
    index=list(PROVIDER_OPTIONS.values()).index(st.session_state["llm_provider"]),
    help="Which LLM serves classification, SQL generation, and executive summaries. Default is Azure OpenAI.",
    key="llm_provider_selectbox",
)
st.session_state["llm_provider"] = PROVIDER_OPTIONS[selected_label]

# Read-only active model line beneath the selector
active_model = _active_model_for(st.session_state["llm_provider"])  # see Recommendation 2
st.caption(f"MODEL: `{active_model or 'NOT CONFIGURED'}`")
```

Widget choice for the model line: **`st.caption` with a fenced backtick** for the model string. Reasons:
1. `st.caption` is the documented Streamlit primitive for "captions, asides, footnotes" (verified — Streamlit docs); fits semantically.
2. Backtick formatting (which `st.caption` supports — GitHub-flavored Markdown) gives the monospace presentation that matches the brutalist terminal aesthetic in the rest of `app.py`.
3. `st.code(model)` would be a full code block — too visually heavy under a selectbox.
4. Plain markdown would not get the smaller "caption" font that signals secondary information.

Help-text length: **one sentence** ("Which LLM serves classification, SQL generation, and executive summaries. Default is Azure OpenAI.") — matches the help-text length used elsewhere in the codebase (`app.py:559` "Number of results for semantic search"; `app.py:564` "Display generated SQL").

No help icon beyond `help=` on the selectbox itself — Streamlit auto-renders the `?` tooltip. A separate "help" block in the sidebar is unnecessary visual noise.

**Rationale:**

- Position between EMBEDDINGS and CONFIG groups it with other "session-affecting" config (not under the QUERY SETTINGS expander, which is per-query knobs — provider choice persists across queries until switched).
- Top-level (not in an expander) is required by SC #3: the missing-creds warning must be inline and visible, so the whole block must be unconditionally visible.
- The "MODEL:" prefix matches the brutalist UPPERCASE label convention used in adjacent sidebar widgets ("MODE", "INCIDENTS", "COLUMNS", "RESULTS LIMIT").
- Storing the boolean-to-internal-name mapping in a module-level `PROVIDER_OPTIONS` dict avoids string-literal duplication between selectbox display and state storage.
- The `index=…` calculation makes the selectbox **resilient to refreshes**: after a `st.rerun()` triggered elsewhere, the selectbox shows the current `st.session_state["llm_provider"]` value rather than resetting to the first option.

---

### 2. Missing-credential warning UX

**Recommendation:**

Render the warning **inline immediately below the model caption** (still inside the LLM PROVIDER sidebar block) using `st.warning(...)` (not `st.error`, not `st.info`). When missing, **disable `st.chat_input` via the `disabled=True` parameter** (verified present in Streamlit 1.52.1 via `inspect.signature`).

Exact pattern:

```python
# After the selectbox + caption block (in render_sidebar)
missing = missing_vars(st.session_state["llm_provider"])     # new helper in src/llm/config.py
if missing:
    st.warning(
        f"**{PROVIDER_LABELS[st.session_state['llm_provider']]}** "
        f"is not configured. Missing env vars: " + ", ".join(f"`{v}`" for v in missing) +
        ".\n\nAdd them to your `.env` and restart the app, or switch back to Azure OpenAI above.",
        icon=":material/warning:",
    )
    st.session_state["_llm_provider_blocked"] = True
else:
    st.session_state["_llm_provider_blocked"] = False
```

Then in `render_main_content()` (`app.py:876`) where `st.chat_input` is called:

```python
blocked = st.session_state.get("_llm_provider_blocked", False)
if user_query := st.chat_input(
    "ENTER QUERY..." if not blocked else "QUERY DISABLED — see sidebar warning",
    disabled=blocked,
):
    ...
```

What gets blocked: **only `st.chat_input` is disabled**. The chat history, sidebar controls, schema viewer, data status, and embeddings management all stay interactive — the user must be able to switch back to Azure OpenAI in the sidebar without the page being half-broken. This matches the "switch provider back vs populate .env" recovery path in CONTEXT.md.

Severity choice: **`st.warning` (not `st.error`)**. Rationale:
- `st.error` is reserved in the existing codebase for **failures** (e.g. `app.py:398` "Failed to load CSV", `app.py:440` "INVALID PASSWORD"). Missing creds is a **configuration gap**, not a failure — switching back to Azure OpenAI immediately resolves it.
- `st.info` is too quiet — the chat input is disabled and the user needs to know **why** with high signal.
- `st.warning` matches existing codebase usage at `app.py:664` (chart feedback warning) and is styled with the brutalist orange (`#ffbd2e`) at `app.py:290` — already visually integrated.

The warning **explicitly names the missing env vars** (per CONTEXT.md "it should — `validate_config()` already returns the list") and tells the user the two recovery paths.

Add helper to `src/llm/config.py`:

```python
def missing_vars(provider: str) -> list[str]:
    """Return list of missing required env-var names for provider; empty if ok.

    Unlike validate_config(), this is non-raising — for UI use.
    Unknown providers return [] (caller already validated via UI selectbox enum).
    """
    if provider not in _REQUIRED_VARS:
        return []
    return [name for name in _REQUIRED_VARS[provider] if not os.getenv(name)]
```

**Rationale:**

- `st.chat_input(disabled=True)` is the **canonical** Streamlit way to block submission (verified — official docs confirm "Whether the chat input should be disabled. This defaults to False."). No CSS hack needed.
- Naming the specific missing vars eliminates the "is it the URL or the key?" guessing game. The list comes from `_REQUIRED_VARS` which is already the single source of truth.
- Switching the placeholder text gives users a self-explanatory hint without requiring them to read the sidebar — important because the chat input is the most prominent focal point.
- Putting the boolean blocked flag in `st.session_state["_llm_provider_blocked"]` (underscore prefix = internal) decouples the sidebar render (where the check happens) from the main-content render (where the block applies), so the order of `render_sidebar()` and `render_main_content()` in `main()` (`app.py:921–925`) doesn't need to change.

---

### 3. Per-message provider/model caption

**Recommendation:**

Add `"provider"` and `"model"` keys to the assistant message dict **at write time**, and render them with `st.caption(...)` **inside the `with st.chat_message("assistant"):` block, immediately above `st.markdown(message["content"])`** (i.e. captioned BEFORE the content, not after — see Rationale).

**Storage** — in `process_query()` (`app.py:701`) capture provider + model **before returning**:

```python
def process_query(user_query: str, mode: str):
    ...
    # NEW: capture which adapter produced this response (after route_query runs,
    # because route_query is what calls get_llm() internally — we need the SAME
    # adapter instance, not a fresh resolve that could race with a mid-flight switch)
    from src.llm import get_llm
    client = get_llm()  # session-state resolution; cached
    provider = getattr(client, "provider_name", st.session_state.get("llm_provider", "unknown"))
    model = getattr(client, "_model", "unknown")
    ...
    return {
        ...,
        "provider": provider,
        "model": model,
    }
```

Then in the on-submit block (`app.py:887–912`) write them to the message dict:

```python
st.session_state.messages.append({
    "role": "assistant",
    "content": response["content"],
    ...,
    "provider": response.get("provider"),       # NEW
    "model": response.get("model"),             # NEW
})
```

**Rendering** — modify `render_chat_history()` (`app.py:628–643`) and the inline assistant render (`app.py:887–891`):

```python
def render_chat_history():
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and message.get("provider"):
                _render_provenance_caption(message["provider"], message.get("model"))
            st.markdown(message["content"])
            ...

def _render_provenance_caption(provider: str, model: str | None) -> None:
    """Render a single-line provenance caption above an assistant message."""
    label = {"azure_openai": "Azure OpenAI", "anthropic_mgti": "Anthropic Claude (MGTI)"}.get(provider, provider)
    if model:
        st.caption(f"via **{label}** · `{model}`")
    else:
        st.caption(f"via **{label}**")
```

Caption format: `via **Azure OpenAI** · ` + backticked model name. Reasons:
- "via" is the conventional English preposition for "produced by" — short and natural.
- The bold provider name lets the user scan multi-message threads for one provider.
- Backticked model gives monospace presentation matching the brutalist aesthetic and clearly delimits the technical identifier.
- The interpunct `·` (U+00B7) is a standard typographic separator that doesn't clash with chat content or markdown.

**Provider name source** — `provider_name` is an abstract property on the `LLMClient` base class (referenced in `query_router.py` analysis above as `llm.provider_name`). If for any reason it isn't exposed on the adapter, the fallback to `st.session_state.get("llm_provider")` at write time is correct because the **session-state value at the moment of write IS the provider that just produced the response** (the SC #4 contract says captions reflect "the provider that produced THAT specific message" — which is exactly what was active at write time).

**Historical messages must NOT recompute the caption** — they read `message["provider"]` and `message["model"]` from the stored dict. The render loop already does this naturally because it iterates the stored messages, but the helper `_render_provenance_caption` MUST take both args as explicit parameters (not pull from `st.session_state["llm_provider"]` inside) — that's the regression vector.

**Rationale:**

- Caption position **above content** matches how most chat UIs (Claude.ai, ChatGPT, Slack thread replies) show provenance — eye lands on the source first, then the body. Below the content competes for attention with the results table / chart / SQL block already rendered there.
- `st.caption` is the documented Streamlit primitive (smaller font, secondary text style) and matches the existing usage pattern at `app.py:451`, `app.py:468`, `app.py:871`.
- Storing provider+model at write time (not at render time) is **required by SC #4** — historical messages must reflect the provider that produced them, not the currently selected one. Stored metadata survives provider switches by construction.
- `_render_provenance_caption` taking explicit args (not session_state) prevents the future regression where someone "simplifies" by reading session_state — that would silently break history captions after a switch.
- Using `getattr(client, "_model", "unknown")` is defensive — if a future provider adapter forgets to set `_model`, the caption degrades to provider-only rather than crashing.

---

### 4. Documentation split & depth

**Recommendation:**

Split the new content across README.md and USER_GUIDE.md so each doc keeps its existing reading audience:

**README.md additions (deploy/setup audience):**

1. **Tech Stack table update** — replace the single "Azure OpenAI - Query routing and SQL generation" line with: "Azure OpenAI **or** Anthropic Claude via MGTI (MMC Apigee gateway) — Query routing, SQL generation, executive summaries; selectable in sidebar."
2. **Environment Variables table update** — append Anthropic rows after the existing Azure rows:
   - `LLM_PROVIDER_DEFAULT` — `azure_openai` or `anthropic_mgti` — Default: `azure_openai`
   - `ANTHROPIC_BASE_URL` — MGTI proxy v1 base URL (prod / non-prod URLs given) — required for Anthropic
   - `ANTHROPIC_API_KEY` — Issued via Hubble after MGTI onboarding — required for Anthropic
   - `ANTHROPIC_MODEL` — Must start with `eu.anthropic.claude-` (Claude 4.5+, EU Bedrock) — required for Anthropic
   - Optional Anthropic vars (max_tokens, temperature, timeout, version, tools_supported) — point to `.env.example` for full list
3. **New short subsection "LLM Provider Selection"** (≤ 8 lines) — one paragraph: where to switch in the UI, default behavior, and a one-line pointer: "For day-to-day switching and warning resolution, see `USER_GUIDE.md` § LLM Provider Selection."
4. **New short subsection "Smoke Test"** (≤ 10 lines) — when and how to run `scripts/smoke_llm.py`:
   - When: after `.env` Anthropic vars change; before every prod deploy
   - How: `python scripts/smoke_llm.py --provider both` (default), `--provider anthropic_mgti --verbose` for diagnosis
   - Exit codes: 0 = ok, 1 = at least one configured provider failed
   - Operator-run only — never in CI (live creds policy)
5. **MGTI onboarding pointer** — one-line note under the Anthropic env-var block: "Anthropic access is restricted to MGTI users; request credentials via Hubble (https://hubble.mmc.com/apps) after coreapi-infrastructure merge."

**USER_GUIDE.md additions (in-app use audience):**

1. **New TOC entry** between "Settings" (current §8) and "Tips & Best Practices" (current §9): **§9 LLM Provider Selection** (renumber subsequent sections).
2. **Section §9 LLM Provider Selection** — ≈ 60–80 lines, structured as:
   - **Overview** (3–5 lines) — what the toggle does, where to find it, why you'd switch (Azure OpenAI is the default; Anthropic gives Claude 4.5+ for comparison/eval)
   - **MGTI-Only Constraint for Anthropic** (one paragraph) — explains the policy that Anthropic credentials are issued only to MGTI-enrolled users via Hubble; link to https://hubble.mmc.com/apps; explicit "if you don't have credentials, stay on Azure OpenAI"
   - **How to Switch** (numbered list, 5–6 steps) — locate sidebar block, choose from dropdown, confirm the "MODEL:" line updates, send a query and look at the per-message caption
   - **What the Per-Message Caption Means** (one paragraph) — explains the `via Azure OpenAI · gpt-4o` style caption; emphasizes historical messages keep their original provenance after a switch
   - **What to Do When a Warning Appears** (table — matches the existing USER_GUIDE.md style):
     | Warning text contains | Cause | Fix |
     | `ANTHROPIC_BASE_URL` | Anthropic proxy URL not set | Add `ANTHROPIC_BASE_URL` to `.env`, restart Streamlit |
     | `ANTHROPIC_API_KEY` | Anthropic key not set or empty | Issue via Hubble, add to `.env`, restart Streamlit |
     | `ANTHROPIC_MODEL` | Claude model identifier not set | Set `ANTHROPIC_MODEL=eu.anthropic.claude-sonnet-4-5-20250929-v1:0` (or 4.5+ equivalent) |
     | `AZURE_OPENAI_*` | Azure creds not set | Add Azure values to `.env`; or switch back to Anthropic |
   - **First-Time-Anthropic Setup Checklist** (numbered list, 4 items — per CONTEXT.md prompt):
     1. Obtain MGTI access via Hubble (link)
     2. Populate `.env` with `ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`
     3. Run `python scripts/smoke_llm.py --provider anthropic_mgti --verbose` and confirm exit 0
     4. Restart Streamlit, switch the sidebar selector to "Anthropic Claude (MGTI)", send a test query, confirm the per-message caption shows Claude
   - **Mid-Session Switching Behavior** (short paragraph) — switches take effect on the **next query only**; in-flight queries finish on the previously selected provider; historical messages retain their original provider in their captions
3. **Update the Tech Stack mention in §1 Getting Started** — change "Azure OpenAI" to "Azure OpenAI or Anthropic Claude (MGTI), selectable per session" if such a mention exists. (Verified — no tech-stack mention in current USER_GUIDE.md, so no change needed there. Skip.)
4. **Update the bottom-of-file version stamp** — bump from "v2.0 - Added password protection & chart visualization" to "v2.1 - Added multi-provider LLM selection (Azure OpenAI / Anthropic Claude via MGTI)" with current date.

**Screenshots: do NOT embed.** Justifications:
- Existing README + USER_GUIDE have **zero** screenshots — keeping the same convention.
- The brutalist UI changes color/CSS in ways that screenshots quickly become misleading after the next CSS tweak.
- Text-only docs survive `git diff` review cleanly; image diffs do not.
- This is a research/internal tool, not a marketed product.

**First-time setup checklist: YES, include it** (in USER_GUIDE as the 4-step list above) — CONTEXT.md explicitly raises this and the chain "env vars → smoke test → toggle → first query" is the exact ordered ritual that prevents the silent-misconfiguration cliff.

**Rationale:**

- The README/USER_GUIDE split mirrors the existing convention (deploy concerns vs use concerns). Cross-linking once from README to USER_GUIDE avoids duplication.
- Naming env-var-specific warnings in the troubleshooting table lets the user copy-paste the missing variable name directly from the sidebar warning into the docs and find the fix.
- The checklist's four steps **enforce the operator order** (env → smoke → toggle → query). Skipping the smoke step is the highest-cost failure mode (silent misconfig discovered mid-presentation), so it's third — between env-var setup and first UI use.
- No screenshots keeps the docs PR-reviewable and CSS-tweak-resilient, matching the existing convention.
- Version stamp bump preserves the existing "what changed when" trail at the bottom of USER_GUIDE.

---

## Pitfalls and Edge Cases

### 1. `api_key_fingerprint` derivation must never leak the key

**What goes wrong:** Putting the raw API key in the `@st.cache_resource` argument list — Streamlit may render arg values in error messages, log lines, and `streamlit run --logger.level=debug` output. Even a "fingerprint" can leak if computed naively (e.g. first 8 chars of a 32-char key gives an attacker 25% of the key).

**Mitigation:** Compute a one-way hash:
```python
import hashlib
def _fingerprint(api_key: str) -> str:
    """8-hex-char SHA-256 of the API key; '' for empty key (unconfigured).
    Sufficient to detect rotation; cryptographically infeasible to reverse."""
    if not api_key:
        return ""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:8]
```
- SHA-256 is one-way; truncating to 8 hex chars (32 bits) still gives 4-billion-way uniqueness which is far more than needed for cache invalidation between two providers.
- The empty-key case returns `""` instead of hashing the empty string, so the cache key for "unconfigured provider" is distinct from any real key — preventing collisions and avoiding "ghost" cache entries with the SHA of empty bytes.
- NEVER use "first N chars of the key" — that's leaking key material.

### 2. `LLM_PROVIDER_DEFAULT` env parsing — empty / unknown / case

**What goes wrong:** User sets `LLM_PROVIDER_DEFAULT=` (empty), `LLM_PROVIDER_DEFAULT=Anthropic_MGTI` (wrong case), or `LLM_PROVIDER_DEFAULT=anthropic` (close but wrong). The selectbox `index=...` calculation calls `.index()` on a list and raises `ValueError`.

**Mitigation:** Clamp to a known value before initializing session state:
```python
PROVIDER_KEYS = ("azure_openai", "anthropic_mgti")
default = os.getenv("LLM_PROVIDER_DEFAULT", "azure_openai").strip()
if default not in PROVIDER_KEYS:
    logger.warning(f"LLM_PROVIDER_DEFAULT={default!r} not in {PROVIDER_KEYS}; "
                   f"falling back to azure_openai")
    default = "azure_openai"
st.session_state["llm_provider"] = default
```
- The `.strip()` handles trailing whitespace.
- The fallback to `"azure_openai"` is consistent with `src/llm/config.py:20` `DEFAULT_PROVIDER`.
- A logger.warning surfaces the typo at startup without crashing the UI.

### 3. `st.chat_input(disabled=True)` placeholder gotcha

**What goes wrong:** When `disabled=True`, the textarea is greyed out but the placeholder text still shows. If the placeholder is the same as the active-state placeholder ("ENTER QUERY..."), users may not realize they're blocked.

**Mitigation:** Use a different placeholder when blocked: `placeholder="QUERY DISABLED — see sidebar warning"`. Verified to work in Streamlit 1.52.1 — `st.chat_input` accepts both `placeholder` (first positional) and `disabled` simultaneously.

### 4. Provider switch races with in-flight query

**What goes wrong:** User submits "show me P1 incidents", clicks Anthropic in the sidebar while the Azure call is still going, gets a response. Which provider caption do we display?

**Mitigation:** **The provider/model captured at write time is correct** because the synchronous Streamlit script execution model means `process_query()` runs to completion before the sidebar selectbox can update `st.session_state["llm_provider"]`. The race window doesn't exist in Streamlit's execution model — each user action triggers a fresh top-to-bottom rerun. Sidebar interaction during an in-flight query is queued; it cannot interleave. SC #2 ("no retroactive recompute") is naturally satisfied.

### 5. Sidebar order — render BEFORE main content matters

**What goes wrong:** `render_sidebar()` writes `st.session_state["_llm_provider_blocked"]`; `render_main_content()` reads it. If a future refactor reverses the order (`main()` at `app.py:921`), `chat_input` reads stale state from the previous run.

**Mitigation:** The current order in `main()` is correct (`render_sidebar()` then `render_main_content()` — `app.py:923–925`). Add a code comment to `main()` flagging that the order is **load-bearing** for the chat_input disable flag.

### 6. Phase 1 module-level `_cache` and Phase 5 `@st.cache_resource` co-existence

**What goes wrong:** Phase 1's `_cache: dict[str, LLMClient]` in `src/llm/__init__.py:61` returns cached instances keyed by provider string. Phase 5 wraps `get_llm` with `@st.cache_resource` keyed on `(provider, base_url, model, fingerprint)`. If both layers stay active, the inner dict caches forever even when the outer cache invalidates due to a fingerprint change.

**Mitigation:** **Delete the module-level `_cache` dict in Phase 5.** Replace `get_llm()` so the cached helper IS the only cache layer. The Phase 1 comment at line 59–60 explicitly anticipates this: "Phase 5 may wrap this with `@st.cache_resource` and clear() this dict before the decorator takes over." The planner should ensure the new factory has exactly one cache, not two.

### 7. `validate_config()` raises — the UI must not raise

**What goes wrong:** The current `validate_config(provider)` (`src/llm/config.py:112`) raises `LLMConfigError` on missing vars. If the sidebar calls it directly to check, an unhandled exception kills the whole Streamlit script.

**Mitigation:** Add the non-raising `missing_vars(provider) -> list[str]` helper (Recommendation 2 above). Reserve `validate_config()` for the explicit startup check in `app.py` (which CAN catch the exception and display a startup error). Two functions, two purposes.

### 8. `provider_name` attribute on adapters — verify exposed

**What goes wrong:** The recommendation in §3 reads `client.provider_name`. If the `LLMClient` ABC doesn't expose this, the `getattr(client, "provider_name", ...)` falls back to session_state, which is **correct at write time but** brittle — a refactor that runs the write after a sidebar switch would caption wrong. Better to fix at the abstract base class.

**Mitigation:** Verify `LLMClient.provider_name` (or equivalent) is exposed and returns a stable string. Read `src/llm/base.py` during planning — if not present, the planner adds it as part of Phase 5 (one-line abstract property on the ABC, one-line override on each adapter). Both `AzureOpenAIClient` and `AnthropicMGTIClient` already know their identity (they log `"provider": "azure_openai"` and `"provider": "anthropic_mgti"` at __init__).

### 9. Anthropic optional vars NOT in the missing-list

**What goes wrong:** A user sees the warning "Missing: `ANTHROPIC_TIMEOUT_S`" and thinks they need to set every Anthropic variable. They don't — only the three required ones (`ANTHROPIC_BASE_URL`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`) gate startup.

**Mitigation:** The `_REQUIRED_VARS` dict (`src/llm/config.py:53`) already lists ONLY required vars per provider — the optional vars (max_tokens, temperature, etc.) have defaults baked into `load_settings`. So `missing_vars(provider)` naturally returns only the truly-required missing names. No additional filtering needed; this is correct by construction. Documented here so the planner doesn't introduce a "list all unset Anthropic vars" antipattern.

### 10. Sidebar warning re-renders on every interaction

**What goes wrong:** Streamlit re-runs the script top-to-bottom on every widget interaction. The `missing_vars()` call (which reads `os.environ`) runs on every interaction. Cheap, but not free if `os.environ` access ever becomes slow (e.g. a future env loader).

**Mitigation:** Acceptable as-is — `os.getenv` is O(1) dict access on a normal Python interpreter. Do NOT cache `missing_vars()` with `@st.cache_data` because that would defeat the purpose of detecting a credential addition between runs. (User adds `.env` var, hits Ctrl-R to refresh, expects the warning to vanish — caching would prevent that.)

### 11. Per-message caption rendered for user messages

**What goes wrong:** If the `_render_provenance_caption` block isn't guarded by `if message["role"] == "assistant"`, a "via Azure OpenAI" caption appears above user messages too — visually wrong and confusing.

**Mitigation:** The recommended pattern (§3) already guards with `if message["role"] == "assistant" and message.get("provider"):` — both checks needed. Older user messages without `provider` key never render the caption, even if a future code path accidentally writes the role wrong.

### 12. `.cache_resource` for the adapter and `.cache_data` for downstream functions

**What goes wrong:** `app.py` (or other modules) might cache the **result** of `client.complete()` or `client.classify_with_tool()` via `@st.cache_data` somewhere downstream. If those caches' keys don't include the provider, switching providers reuses stale Azure results when displaying with an "Anthropic" caption.

**Mitigation:** Audit during planning — grep for `@st.cache_data` and `@st.cache_resource` in `src/` and confirm none of them wrap LLM-output-producing functions without including `provider` in the args. The existing codebase (per grep `cache_resource|cache_data` not yielding hits inside `src/`) suggests this is currently clean. Verify before merging Phase 5.

### 13. Documentation drift (PF-16)

**What goes wrong:** The README and USER_GUIDE updates land in Phase 5 but the labels in the actual app shift in a Phase 5.5 hotfix (e.g. someone renames the selectbox label from "LLM provider" to "AI provider"). Docs now lie.

**Mitigation:** Lock the exact UI strings in the plan tasks (label `"LLM provider"`, options `"Azure OpenAI"` / `"Anthropic Claude (MGTI)"`) — these come from SC #1 and CONTEXT.md and are non-discretionary. Reference these strings verbatim in both docs so a future diff catches drift between docs and app.

---

## Open Questions for Planner

1. **`LLMClient.provider_name` abstract property exposure** — Recommendation 3 assumes adapters expose a `provider_name` attribute. Confirm during planning by reading `src/llm/base.py`. If absent, add as part of Phase 5 (lightweight one-line addition to the ABC and both adapter classes). Fallback to `st.session_state["llm_provider"]` at write time works correctly for SC #4 but is more brittle to future refactors.

2. **Position of the new sidebar block — between EMBEDDINGS and CONFIG, or above EMBEDDINGS?** Recommendation 1 chose between-and-before because LLM provider feels closer to a session-config choice than to data management. Alternative: place it as the very first block under the SNOWGREP logo (top of sidebar) since it affects every query. Defer to the planner; the implementation cost is identical (one block move).

3. **Whether to fold `missing_vars()` into existing `validate_config()` via a `raise_on_missing: bool = True` flag, or expose as a separate function.** Recommendation 2 chose a separate function for API clarity. The planner may prefer overloading the existing function with a flag — either works; pick one to keep the public API surface minimal.

4. **Whether to add a "Reload config" button** alongside the LLM provider block (mentioned in PITFALLS.md research as a nice-to-have for invalidating the cache after an `.env` edit). Not in Phase 5 SC. Recommendation: SKIP for Phase 5 — the `(provider, base_url, model, fingerprint)` cache key already invalidates on env change after an app restart, and Streamlit's existing "Rerun" feature handles in-session reloads if needed. The button is gold-plating; add only if a Phase 5.5 user reports needing it.

---

## Sources

### Primary (HIGH confidence)

- **Streamlit official docs — st.chat_input** — https://docs.streamlit.io/develop/api-reference/chat/st.chat_input — confirmed `disabled: bool` param officially documented; precondition-blocking is a supported pattern.
- **Streamlit official docs — st.cache_resource** — https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_resource — confirmed per-argument cache-key computation, `.clear(args)` per-key invalidation, hashability requirements.
- **Streamlit official docs — st.caption** — https://docs.streamlit.io/develop/api-reference/text/st.caption — confirmed GitHub-flavored Markdown support including backtick formatting and color/emoji syntax.
- **Streamlit official docs — st.chat_message** — https://docs.streamlit.io/develop/api-reference/chat/st.chat_message — confirmed no built-in metadata feature; manual composition with `st.caption` or `st.text` inside the container is the recommended pattern; storing metadata in `st.session_state` alongside content is the recommended persistence pattern.
- **Streamlit official docs — st.warning** — https://docs.streamlit.io/develop/api-reference/status/st.warning — confirmed `icon` param supports emoji and `:material/...` syntax; semantic guidance for warning vs info vs error.
- **Live `inspect.signature` verification** in the project venv (`streamlit==1.52.1`):
  - `st.chat_input(... disabled: 'bool' = False, ...)` — verified present in the pinned version.
  - `st.cache_resource(... hash_funcs, max_entries, ttl, validate ...)` — verified, decorator returns `CachedFunc` with `.clear()` method.
- **Codebase files read end-to-end:** `app.py`, `src/llm/__init__.py`, `src/llm/config.py`, `src/llm/errors.py`, `src/llm/azure_openai.py` (excerpt), `src/llm/anthropic_mgti.py` (excerpt), `src/query_router.py` (call sites), `scripts/smoke_llm.py`, `README.md`, `USER_GUIDE.md`, `requirements.txt`, `.env.example`.
- **Prior planning files read:** `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/STATE.md`, `.planning/phases/01-abstraction-seam/01-RESEARCH.md` (relevant sections), `.planning/research/SUMMARY.md`, `.planning/research/PITFALLS.md` (relevant pitfalls), `.planning/phases/05-sidebar-ui-toggle-documentation/05-CONTEXT.md`.

### Secondary (MEDIUM confidence)

- **Streamlit caching overview** — https://docs.streamlit.io/develop/concepts/architecture/caching — corroborates official docs on `cache_resource` semantics; same vendor.

### Tertiary (LOW confidence — not used for prescriptive recommendations)

- General community discussions of Streamlit chat caption patterns — used only to confirm that `st.caption` inside `st.chat_message` is a common community pattern; not load-bearing for any recommendation.

---

## Metadata

**Confidence breakdown:**
- Sidebar layout (Rec 1): **HIGH** — direct codebase read; Streamlit primitives confirmed.
- Missing-creds warning (Rec 2): **HIGH** — `st.chat_input(disabled=True)` verified by both signature inspection and official docs; `_REQUIRED_VARS` already exists in codebase.
- Per-message caption (Rec 3): **HIGH** — message-dict storage pattern already in use at `app.py:903–912`; `st.caption` documented for this purpose; adapter `_model` attribute confirmed present on both adapters.
- Documentation split (Rec 4): **HIGH** — both files read in full; split aligns with established convention.
- Cache-key derivation: **HIGH** — Streamlit per-argument caching verified in official docs; SHA-256 + truncation is standard one-way fingerprint technique.

**Research date:** 2026-05-21
**Valid until:** 2026-06-21 (30 days — Streamlit pinned floor is 1.40, no breaking API changes expected within window)
