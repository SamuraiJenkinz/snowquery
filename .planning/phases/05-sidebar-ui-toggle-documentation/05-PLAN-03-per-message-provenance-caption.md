---
phase: 5
plan: 3
name: per-message-provenance-caption
type: execute
wave: 3
depends_on: [1, 2]
files_modified:
  - app.py
autonomous: true

must_haves:
  truths:
    - "Every assistant message stored in st.session_state.messages has a 'provider' key and a 'model' key populated at write time"
    - "Every assistant message renders a caption ABOVE its content showing the provider human-name and the backticked model — via 'via **<Name>** · `<model>`' format"
    - "User messages do NOT render any provenance caption (guard: role == 'assistant' AND message.get('provider'))"
    - "After switching providers mid-session, historical messages STILL show the provider that originally produced them — caption is read from stored dict, not recomputed from current session_state"
    - "The render helper _render_provenance_caption takes explicit args (provider, model) — does NOT read st.session_state — regression vector locked"
    - "process_query captures (provider, model) from the get_llm() instance AT WRITE TIME via client.provider_name and client._model — falls back gracefully if provider_name absent"
  artifacts:
    - path: "app.py"
      provides: "Per-message provenance caption + write-time metadata capture in process_query and the on-submit append"
      contains: "_render_provenance_caption"
  key_links:
    - from: "app.py process_query"
      to: "src.llm.LLMClient.provider_name (added in Plan 05-01)"
      via: "client = get_llm(); provider = client.provider_name; model = client._model"
      pattern: "provider_name|_model"
    - from: "app.py on-submit append block"
      to: "st.session_state.messages assistant message dict"
      via: "writes 'provider' and 'model' keys at append time"
      pattern: '"provider":|"model":'
    - from: "app.py render_chat_history"
      to: "_render_provenance_caption(message['provider'], message.get('model'))"
      via: "guarded by role == 'assistant' AND message.get('provider')"
      pattern: '_render_provenance_caption\\('
    - from: "app.py on-submit assistant rendering block"
      to: "_render_provenance_caption(response['provider'], response.get('model'))"
      via: "render the caption ABOVE st.markdown(content) inside the new st.chat_message('assistant') block"
      pattern: 'with st\\.chat_message\\("assistant"\\)'
---

<objective>
Capture `(provider, model)` per assistant message at write time — both from `process_query()`'s return value and persisted into `st.session_state.messages` — and render a provenance caption (`via **<Provider>** · \`<model>\``) above every assistant message in both the historical render loop and the on-submit live render. Add a single shared helper `_render_provenance_caption(provider, model)` that takes explicit args (never reads session_state) to lock the regression vector where someone "simplifies" the helper into reading current provider state — which would silently break captions on historical messages after a switch.

Purpose: This is SC #4 — "Every assistant message displays a caption showing the provider and model that produced it." The load-bearing invariant is that historical messages keep their original provenance after a provider switch — solved by storing provider+model at write time and reading from the stored dict at render time. RESEARCH.md Pitfall 11 (caption-on-user-message regression guard) is addressed by the dual-guard `role == 'assistant' AND message.get('provider')`.

Output: One file modified (`app.py`); three contributions — (1) write-time capture in `process_query()` (~5 new lines), (2) the assistant-message dict append gets `"provider"` and `"model"` keys (~2 new dict keys), (3) `_render_provenance_caption` helper + caption-rendering inside the existing assistant `with st.chat_message(...)` blocks in both the historical loop (line ~628) and the on-submit live render (line ~887).
</objective>

<execution_context>
@C:\Users\taylo\.claude/get-shit-done/workflows/execute-plan.md
@C:\Users\taylo\.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/05-sidebar-ui-toggle-documentation/05-CONTEXT.md
@.planning/phases/05-sidebar-ui-toggle-documentation/05-RESEARCH.md

# This plan depends on Plan 05-01's outputs (provider_name property)
# AND Plan 05-02's outputs (_PROVIDER_LABELS dict + the from src.llm import line that 05-03 EXTENDS to add get_llm)
@.planning/phases/05-sidebar-ui-toggle-documentation/05-01-SUMMARY.md
@.planning/phases/05-sidebar-ui-toggle-documentation/05-02-SUMMARY.md

# Files modified
@app.py

# Reference: existing process_query at app.py:701, render_chat_history at app.py:628,
# on-submit block at app.py:873-912 — read in full before editing
</context>

<decisions>
## Decisions locked for this plan

1. **Capture location: inside `process_query()`, after the `route_query` call.** Place the capture AFTER the result is built (so we know route_query succeeded) and BEFORE the final return. This guarantees the provider that produced the response is captured exactly — even if a future refactor wraps `process_query` in retry logic, the captured value reflects the actual adapter used (RESEARCH.md §3 rationale).

2. **Use the SAME adapter instance.** Re-call `get_llm()` inside `process_query()` — `@st.cache_resource` returns the SAME instance route_query used (cache key tuple is identical because session_state and env haven't changed during the synchronous Streamlit run — Pitfall 4 confirms this). The redundant `get_llm()` call costs nothing (cache hit) and gives us a clean handle to `provider_name` and `_model`.

3. **Defensive `getattr` for `provider_name` and `_model`:**
   ```python
   _client = get_llm()
   _provider = getattr(_client, "provider_name", st.session_state.get("llm_provider", "unknown"))
   _model = getattr(_client, "_model", "unknown")
   ```
   - `provider_name` is now an abstract property post-Plan-01, so present on all adapters — but `getattr` with session_state fallback is correct at write time AND defensive against future adapters that forget to override.
   - `_model` is a private attribute. Plan 05-01 confirmed `AzureOpenAIClient._model` exists (line ~84 — set via `_extract_model_from_endpoint`) and `AnthropicMGTIClient._model` exists (line ~157 — set from settings). Defensive `getattr` with `"unknown"` fallback handles the case where a future adapter forgets to set it (degrades to provider-only caption, doesn't crash).
   - Underscore prefix on locals (`_client`, `_provider`, `_model`) matches the convention used elsewhere in app.py and avoids polluting locals dict.

4. **Capture for the error-return paths too** (the early returns inside `process_query` at lines ~703-708 and ~712-716 — "NO DATA LOADED" and "NO EMBEDDINGS"). These error returns currently don't include provider/model. **Decision: leave them as-is.** The caption guard `if message.get("provider")` will silently skip rendering for these "no data" errors — which is correct, because no LLM actually produced them. Pure additive: messages with provider get a caption; messages without provider don't. Backwards compatible with any future error path.

5. **Provider human-name mapping reuses Plan 05-02's `_PROVIDER_LABELS` dict.** No duplicate dict — single source of truth at module scope. The helper looks up `_PROVIDER_LABELS.get(provider, provider)` so an unknown provider key degrades to the raw string (e.g. a future hypothetical `"openai_direct"` would render as `"via **openai_direct** · `gpt-4o`"` until someone updates the dict). Acceptable degradation.

6. **Caption format (RESEARCH Recommendation 3 verbatim):** `f"via **{human_name}** · `{model}`"` — preposition "via", bold provider name, interpunct `·` (U+00B7) separator, backticked model. When `model` is missing/empty/None, drop the model half: `f"via **{human_name}**"`. The helper handles both branches.

7. **Helper API (single source of truth, regression vector locked):**
   ```python
   def _render_provenance_caption(provider: str, model: str | None) -> None:
       """Render a single-line provenance caption above an assistant message.

       Args are EXPLICIT — this helper MUST NOT read st.session_state for
       provider/model. Reading session_state would silently break historical
       captions after a provider switch (Phase 5 RESEARCH.md Pitfall 11).
       Tests in Plan 05-05 lock this invariant.
       """
       human_name = _PROVIDER_LABELS.get(provider, provider)
       if model:
           st.caption(f"via **{human_name}** · `{model}`")
       else:
           st.caption(f"via **{human_name}**")
   ```
   Place this helper at module scope (NOT inside another function), AFTER the `_PROVIDER_LABELS` definition added by Plan 05-02. Treat as a private helper (underscore prefix).

8. **Render position: ABOVE `st.markdown(message["content"])`** (RESEARCH Recommendation 3). Two render sites must be updated identically:
   - `render_chat_history()` at `app.py:628-643` — historical message loop.
   - The on-submit block at `app.py:887-891` — the live `with st.chat_message("assistant"):` block where the fresh response is rendered.
   In both, the caption is the FIRST thing inside the `with st.chat_message("assistant"):` context manager.

9. **Guards on the caption render:**
   - In `render_chat_history()`: `if message["role"] == "assistant" and message.get("provider"):` (both conditions required — Pitfall 11).
   - In the on-submit live render: the message dict isn't constructed yet at the moment the caption is needed; instead, render directly from `response.get("provider")` / `response.get("model")` — same guard (`if response.get("provider")`).

10. **Append-block update** at `app.py:903-912` — add two keys to the dict:
    ```python
    st.session_state.messages.append({
        "role": "assistant",
        "content": response["content"],
        "results": response["results"],
        "sql": response["sql"],
        "query_id": query_id,
        "executive_summary": response.get("executive_summary"),
        "chart": response.get("chart"),
        "chart_feedback": response.get("chart_feedback"),
        "provider": response.get("provider"),       # NEW Phase 5
        "model": response.get("model"),             # NEW Phase 5
    })
    ```
    The `.get(...)` calls (vs `[...]` access) preserve the SC #3 contract: if `process_query` returned an early error path that didn't set provider/model, the append still succeeds (with `None` values), and the caption guard skips the render.

11. **`process_query` return value addition:** the returned dict gets two new keys, both inside the happy path:
    ```python
    return {
        "content": ...,
        "results": ...,
        "sql": ...,
        "executive_summary": ...,
        "chart": chart,
        "chart_feedback": chart_feedback,
        "provider": _provider,    # NEW Phase 5
        "model": _model,          # NEW Phase 5
    }
    ```
    Plus the existing early-return dicts (NO DATA LOADED, NO EMBEDDINGS, error paths) DO NOT get provider/model — by design (locked decision §4). Caption guard handles their absence.

12. **No changes to `route_query`, `classify_intent`, `generate_sql`, or any LLM-side code.** Phase 5 is purely UI metadata capture and render — the LLM call sites are untouched. The `client.provider_name` / `client._model` reads in `process_query()` are non-LLM-calling getters.

13. **Test plan integration:** Plan 05-05 will patch `get_llm` to return a mock client with controlled `provider_name` and `_model`, write messages with one provider, switch session_state to the other, render history, and assert the historical caption still names the ORIGINAL provider. This is the SC #4 load-bearing test.

14. **`get_llm` import strategy — EXTEND the Plan 05-02 module-level import line (Option B).**

    **Premise check (run before editing):**
    ```bash
    grep -nE "^from src\.llm import" app.py
    grep -nE "get_llm" app.py
    ```
    Pre-Phase-5 / pre-Plan-05-02 state: `app.py` does NOT import `from src.llm` at all (only `route_query` from `src.query_router` exists, line 20). It also does NOT reference `get_llm` directly. The earlier draft of this plan claimed `from src.llm import get_llm` "already exists in app.py (Phase 2 work)" — that was WRONG. The actual Phase 2 wiring lives behind `route_query` / `src.query_router`, which is a different seam.

    **Approach (Option B — chosen):** Plan 05-02 introduces the module-level line `from src.llm import missing_vars, load_settings`. Plan 05-03 EXTENDS that line to `from src.llm import get_llm, missing_vars, load_settings`. This keeps all `src.llm` imports on a single module-level line (matches the prevailing import style in `app.py`) and avoids redundant inline imports inside `process_query`.

    **Alternatives considered:**
    - Option A (inline `from src.llm import get_llm` inside `process_query`): clean local scope but inconsistent with the file's prevailing module-level import style.
    - Option C (Plan 05-03 adds its own separate top-of-file `from src.llm import get_llm` independent of Plan 05-02): two separate `from src.llm import ...` lines in the same file = stylistic clutter.

    **Trade-off:** Option B requires Plan 05-03 to depend on Plan 05-02 (the `from src.llm import ...` line must exist before 05-03 can extend it). This pushes 05-03 from Wave 2 → Wave 3 — see locked decision §16. The benefit: one canonical import line, zero redundant inline imports, matches `app.py`'s prevailing style.

    **Concrete edit in Plan 05-03 Task 3.1:** Locate the line added by Plan 05-02:
    ```python
    from src.llm import missing_vars, load_settings
    ```
    Replace with:
    ```python
    from src.llm import get_llm, missing_vars, load_settings
    ```
    (Names alphabetized: `get_llm`, `load_settings`, `missing_vars`. Adjust order to your prevailing style if `app.py` uses a different convention — match what Plan 05-02 wrote.)

15. **NO interaction with the `_llm_provider_blocked` flag** — that's Plan 05-02's domain. This plan is purely the provenance caption.

16. **Wave 3 placement — dependency on Plan 05-02.**

    **Why Wave 3, not Wave 2:** Prior phases (1–4) never had two plans in the same wave touching the same file. Plan 05-02 and Plan 05-03 both modify `app.py`, AND Plan 05-03 depends on two artifacts introduced by Plan 05-02:
    1. The module-level `_PROVIDER_LABELS` dict (decision §5 — used by `_render_provenance_caption`).
    2. The module-level `from src.llm import ...` line (decision §14 — extended to include `get_llm`).

    Either dependency is genuine; together they make Wave-2 parallelism with Plan 05-02 unsafe even under a "serializes-within-wave" executor convention. Plan 05-03 therefore declares `depends_on: [1, 2]` and `wave: 3`, matching prior-phase convention.

    **Downstream impact:** Plan 05-05 (acceptance gate, formerly Wave 3) becomes Wave 4. Plan 05-04 (docs) stays in Wave 2 in parallel with Plan 05-02 — it has no code dependencies.
</decisions>

<tasks>

<task type="auto">
  <name>Task 3.1: Extend src.llm import to include get_llm + Add _render_provenance_caption helper + capture provider/model in process_query</name>
  <files>app.py</files>
  <action>
**Goal:** Extend the Plan-05-02 `from src.llm import ...` line to include `get_llm`, add the shared rendering helper at module scope, and capture `(provider, model)` at the bottom of `process_query()` so the return dict carries the metadata into the append block.

**Step 0 — VERIFY THE PRE-CONDITION (premise check, run BEFORE editing):**

```bash
# Confirm Plan 05-02 already landed its import line
grep -nE "^from src\.llm import" app.py
# Expected: 1 match, exactly: `from src.llm import missing_vars, load_settings`
# (or whatever order Plan 05-02 used)

# Confirm get_llm is NOT yet imported (Plan 05-03's job)
grep -nE "\\bget_llm\\b" app.py
# Expected: 0 matches
```

If the Plan 05-02 line is missing, STOP and report — Plan 05-03 depends on it (wave 2 → wave 3 ordering). If `get_llm` is already imported, the line was extended by a prior partial run — verify and skip Step 1.

**Step 1 — Extend the Plan 05-02 import line.** Locate the module-level line added by Plan 05-02 (near the other `from src...` imports at the top of `app.py`):

```python
from src.llm import missing_vars, load_settings
```

Replace it with (names alphabetized — match Plan 05-02's prevailing style):

```python
from src.llm import get_llm, load_settings, missing_vars
```

(If Plan 05-02 used a different name order, preserve that order and INSERT `get_llm` in the alphabetical-ish slot — e.g. `from src.llm import get_llm, missing_vars, load_settings`. The exact order is a style preference; the load-bearing requirement is that `get_llm` is on the line.)

**Step 2 — Add the helper at module scope.** Place it AFTER Plan 05-02's `_PROVIDER_LABELS` definition. Concretely, find this line (added by Plan 05-02):

```python
_PROVIDER_KEYS: tuple[str, ...] = tuple(_PROVIDER_OPTIONS.values())
```

Insert IMMEDIATELY after it:

```python


def _render_provenance_caption(provider: str, model: str | None) -> None:
    """Render the assistant-message provenance caption.

    Format: "via **<Human Name>** · `<model>`" — or, if model is falsy, just
    "via **<Human Name>**". Uses the _PROVIDER_LABELS map for the human-name;
    unknown provider keys fall through to the raw string (degraded but
    non-crashing). Caller MUST guard with `role == 'assistant' AND
    message.get('provider')` before calling — this helper does NOT validate
    its args (Phase 5 RESEARCH.md Pitfall 11).

    CRITICAL INVARIANT: This helper MUST NOT read st.session_state for the
    provider or model — args are explicit. Reading session_state would
    silently break historical captions after a provider switch (a
    historical message produced by Azure would caption as Anthropic
    immediately after the user switched the sidebar). The test in
    tests/test_phase5_ui.py locks this invariant — do not refactor
    to read session_state without removing that test first.
    """
    human_name = _PROVIDER_LABELS.get(provider, provider)
    if model:
        st.caption(f"via **{human_name}** · `{model}`")
    else:
        st.caption(f"via **{human_name}**")
```

**Step 3 — Capture provider/model in `process_query()`.** Locate the function at `app.py:701`. Find the FINAL `return {...}` (the happy-path return — search for the line with `chart_feedback` in it; that's the final return's dict). It looks approximately like:

```python
        return {
            "content": ...,
            "results": ...,
            "sql": ...,
            "executive_summary": ...,
            "chart": chart,
            "chart_feedback": chart_feedback,
        }
```

(Exact field names match the existing code — DO NOT rename.)

IMMEDIATELY BEFORE this `return {...}` statement, add the capture block:

```python
        # Phase 5: capture which adapter produced this response for the
        # per-message provenance caption (SC #4). Reuses the same cached
        # adapter instance route_query() resolved — @st.cache_resource cache
        # hit, no extra HTTP, no extra startup log. Defensive getattr keeps
        # the path crash-free even if a future adapter forgets to set _model
        # or override provider_name.
        _client = get_llm()
        _provider = getattr(
            _client, "provider_name", st.session_state.get("llm_provider", "unknown")
        )
        _model = getattr(_client, "_model", "unknown")

```

Note: NO inline `from src.llm import get_llm` here — it was added at module scope in Step 1. If you find an inline import was added by mistake, delete it (single module-level import is the locked decision §14 choice).

Then ADD the two new keys to the return dict:

```python
        return {
            "content": ...,
            "results": ...,
            "sql": ...,
            "executive_summary": ...,
            "chart": chart,
            "chart_feedback": chart_feedback,
            "provider": _provider,   # NEW Phase 5 (SC #4)
            "model": _model,         # NEW Phase 5 (SC #4)
        }
```

(Use whatever keys are currently in the dict — `provider` and `model` go at the END so diffs are minimal.)

**Step 4 — Do NOT modify the early-return dicts.** The "NO DATA LOADED" and "NO EMBEDDINGS" early returns stay exactly as they are. Locked decision §4: error returns don't carry provider/model; caption guard skips them.

**Step 5 — Do NOT modify any error-return inside the `try` block.** The `if result.get("error"):` branch at `app.py:726-731` also stays as-is — no LLM produced that content for the failure case.

**Step 6 — Final verification: the import line is the SINGLE source of `get_llm` in app.py.** Grep:

```bash
grep -nE "from src\.llm import" app.py
# Expected: 1 match — the extended Plan-05-02 line
grep -nE "import get_llm|from src\.llm import.*get_llm" app.py
# Expected: 1 match (the same line)
```

If there are multiple `from src.llm import` lines, consolidate them.
  </action>
  <verify>
```bash
# Premise check satisfied: get_llm imported at module scope
grep -nE "from src\.llm import.*get_llm" app.py
# Expected: 1 match (the extended Plan-05-02 line)

# Single from-src-llm import line
grep -cE "^from src\.llm import" app.py
# Expected: 1

# NO inline import of get_llm inside any function body
grep -nE "    from src\.llm import get_llm" app.py
# Expected: 0 matches (must be module-level only)

# Helper defined at module scope
grep -nE "^def _render_provenance_caption" app.py
# Expected: 1 match

# Helper docstring includes the invariant warning
grep -nE "MUST NOT read st.session_state" app.py
# Expected: 1 match (in the helper docstring)

# Capture block present in process_query
grep -nE "_provider = getattr\(" app.py
grep -nE "_model = getattr\(" app.py
# Both: 1 match each

# Return dict carries new keys
grep -nE '"provider": _provider' app.py
grep -nE '"model": _model' app.py
# Both: 1 match each

# Helper is callable (smoke)
python -c "
import ast
with open('app.py') as f:
    tree = ast.parse(f.read())
fn_names = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
assert '_render_provenance_caption' in fn_names
print('OK')
"
# Expected: OK

# Suite still green
pytest tests/ -v --tb=short
# Expected: 69 passed
```
  </verify>
  <done>
`from src.llm import get_llm, ...` exists at module scope in `app.py` (the Plan-05-02 import line was extended to include `get_llm`). NO inline `from src.llm import get_llm` inside any function body. `_render_provenance_caption(provider, model)` exists at `app.py` module scope, takes explicit args, NEVER reads session_state (locked by docstring invariant). `process_query()` captures `_provider` and `_model` via `get_llm() + getattr` BEFORE the happy-path `return`; the return dict has new `"provider"` and `"model"` keys. Early-return dicts (error paths) UNTOUCHED. `app.py` parses cleanly. All 69 prior tests still pass.
  </done>
</task>

<task type="auto">
  <name>Task 3.2: Wire the caption into render_chat_history + on-submit assistant render + persist provider/model in messages dict</name>
  <files>app.py</files>
  <action>
**Goal:** Render the caption above every assistant message in BOTH the historical loop and the live on-submit render. Persist `provider` and `model` keys into the `st.session_state.messages` dict on append.

**Step 1 — `render_chat_history()` modification.** Locate at `app.py:628-643`. Current body:

```python
def render_chat_history():
    """Render chat message history."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            if "results" in message and message["results"] is not None:
                if not message["results"].empty:
                    display_results(...)
```

Modify the inner `with` block to render the caption FIRST when role == assistant AND provider key present:

```python
def render_chat_history():
    """Render chat message history."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            # Phase 5: provenance caption ABOVE content for assistant messages
            # that carry provider metadata. Read from the stored dict — never
            # from session_state — so historical messages keep their original
            # provenance after a provider switch (SC #4 + RESEARCH.md Pitfall 11).
            if message["role"] == "assistant" and message.get("provider"):
                _render_provenance_caption(
                    message["provider"], message.get("model")
                )

            st.markdown(message["content"])

            if "results" in message and message["results"] is not None:
                if not message["results"].empty:
                    display_results(...)
```

(Keep the existing `display_results(...)` call unchanged — full arg list verbatim from the existing code.)

**Step 2 — On-submit assistant render** at `app.py:887-891`. Current body:

```python
        with st.chat_message("assistant"):
            with st.spinner("PROCESSING..."):
                response = process_query(user_query, selected_mode)

            st.markdown(response["content"], unsafe_allow_html=True)
```

Modify to render the caption AFTER the spinner finishes (so the caption only appears when we actually have a response) and BEFORE `st.markdown(response["content"])`:

```python
        with st.chat_message("assistant"):
            with st.spinner("PROCESSING..."):
                response = process_query(user_query, selected_mode)

            # Phase 5: provenance caption for the fresh response (SC #4).
            # Same render contract as history: explicit args, only render when
            # provider was captured (some early-return error paths in
            # process_query don't carry provider/model — caption is skipped
            # gracefully).
            if response.get("provider"):
                _render_provenance_caption(
                    response["provider"], response.get("model")
                )

            st.markdown(response["content"], unsafe_allow_html=True)
```

Keep the rest of the on-submit block (the `if response["results"] is not None and not response["results"].empty: display_results(...)` block) UNCHANGED.

**Step 3 — Persist provider+model into the appended message dict** at `app.py:903-912`. Current body:

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

Add two new keys at the END of the dict (preserving existing key order so diffs are minimal):

```python
        st.session_state.messages.append({
            "role": "assistant",
            "content": response["content"],
            "results": response["results"],
            "sql": response["sql"],
            "query_id": query_id,
            "executive_summary": response.get("executive_summary"),
            "chart": response.get("chart"),
            "chart_feedback": response.get("chart_feedback"),
            "provider": response.get("provider"),       # NEW Phase 5 (SC #4)
            "model": response.get("model"),             # NEW Phase 5 (SC #4)
        })
```

The trailing comma on `chart_feedback` is intentional (Black-style); add it when inserting the two new keys.

**Step 4 — User-message append at `app.py:879-882` is UNTOUCHED.** It does NOT get provider/model — guard in step 1 above ensures user messages don't render a caption even if a future code path accidentally writes `role == 'assistant'` on a user-content message (defense in depth).

**Step 5 — verify no other render path in app.py renders assistant messages.** Grep:

```bash
grep -nE 'st\.chat_message\("assistant"\)' app.py
```

Expected: TWO matches — one in `render_chat_history` (post-edit) and one in the on-submit block (post-edit). Both must have the caption render block. If there are more (e.g. an alternate code path), they must also be updated.

**Step 6 — verify the `process_query` early-return paths don't crash this render.** If `process_query` returns the "NO DATA LOADED" dict (no `"provider"` key), `response.get("provider")` returns `None`, the `if response.get("provider"):` guard skips the caption render. No crash; no caption. Correct.
  </action>
  <verify>
```bash
# render_chat_history has the assistant-only caption block
grep -nE 'message\["role"\] == "assistant" and message\.get\("provider"\)' app.py
# Expected: 1 match (in render_chat_history)

# On-submit block has response-based caption guard
grep -nE 'if response\.get\("provider"\):' app.py
# Expected: 1 match (in on-submit)

# Both render sites call the helper
grep -cE '_render_provenance_caption\(' app.py
# Expected: 2 matches (history + on-submit) — plus the def line = 3 total
grep -cE 'def _render_provenance_caption|_render_provenance_caption\(' app.py
# Expected: 3

# Two new keys in the assistant message dict
grep -nE '"provider": response\.get\("provider"\)' app.py
grep -nE '"model": response\.get\("model"\)' app.py
# Each: 1 match (in the append block)

# Exactly TWO assistant chat_message render sites
grep -cE 'st\.chat_message\("assistant"\)' app.py
# Expected: 2

# Suite still green
pytest tests/ -v --tb=short
# Expected: 69 passed
```
  </verify>
  <done>
`render_chat_history()` and the on-submit assistant block both render `_render_provenance_caption(...)` ABOVE `st.markdown(message_or_response["content"])`, guarded by `role == "assistant" AND message.get("provider")` (history) and `response.get("provider")` (live). The append at `app.py:903-912` writes `"provider"` and `"model"` keys into the message dict. User-message append unchanged. Only TWO `st.chat_message("assistant")` sites exist in `app.py`; both have the caption block. Full 69-test suite still green.
  </done>
</task>

</tasks>

<verification>
Plan-level verification:

1. **Only `app.py` modified:**
   ```bash
   git diff --stat HEAD -- .
   # Expected: ONLY app.py
   ```

2. **`get_llm` imported at module scope (single from-src-llm line):**
   ```bash
   grep -cE "^from src\.llm import" app.py
   # Expected: 1
   grep -nE "from src\.llm import.*get_llm" app.py
   # Expected: 1 match
   grep -nE "    from src\.llm import get_llm" app.py
   # Expected: 0 (no inline imports inside functions)
   ```

3. **Helper defined once, called twice:**
   ```bash
   grep -nE "def _render_provenance_caption" app.py
   # Expected: 1
   grep -cE "_render_provenance_caption\(" app.py
   # Expected: 3 (1 def + 2 calls)
   ```

4. **No accidental session_state read inside the helper:**
   ```bash
   # Extract helper body and check it doesn't reference session_state
   python -c "
   import ast, sys
   with open('app.py') as f:
       tree = ast.parse(f.read())
   for n in ast.walk(tree):
       if isinstance(n, ast.FunctionDef) and n.name == '_render_provenance_caption':
           src = ast.unparse(n)
           assert 'session_state' not in src, f'helper reads session_state — Pitfall 11 violated:\n{src}'
           print('Helper invariant OK')
           break
   "
   # Expected: Helper invariant OK
   ```

5. **process_query happy-path return carries provider+model:**
   ```bash
   grep -nE '"provider": _provider' app.py
   grep -nE '"model": _model' app.py
   # Each: 1 match
   ```

6. **Append dict has both new keys:**
   ```bash
   grep -nE '"provider": response\.get\("provider"\)' app.py
   grep -nE '"model": response\.get\("model"\)' app.py
   # Each: 1 match (in the append block)
   ```

7. **Caption render position (above markdown):**
   The caption call must appear BEFORE `st.markdown(...)` inside each `with st.chat_message("assistant"):` block. Visual inspection of the diff for app.py confirms this — the regex check below does a coarse ordering test:
   ```bash
   python -c "
   import re
   with open('app.py') as f:
       src = f.read()
   # Find each chat_message('assistant') block start
   for m in re.finditer(r'with st\.chat_message\(\"assistant\"\):', src):
       start = m.end()
       # Look at next 600 chars
       window = src[start:start+600]
       cap_idx = window.find('_render_provenance_caption(')
       md_idx = window.find('st.markdown(')
       assert cap_idx != -1 and md_idx != -1 and cap_idx < md_idx, (
           f'caption must precede st.markdown in window: {window[:200]!r}'
       )
   print('order OK')
   "
   # Expected: order OK
   ```

8. **User messages do NOT render a caption** (verified by the guard regex above and Plan 05-05's mock-based test).

9. **No new src/ or doc edits:**
   ```bash
   git diff --stat HEAD -- src/ scripts/ tests/ README.md USER_GUIDE.md .env.example
   # Expected: ZERO output
   ```

10. **Full test suite green:**
    ```bash
    pytest tests/ -v --tb=short
    # Expected: 69 passed
    ```
</verification>

<success_criteria>
- [ ] Plan-05-02 import line extended to include `get_llm` — single module-level `from src.llm import ...` line in `app.py` covers `get_llm`, `load_settings`, `missing_vars`
- [ ] NO inline `from src.llm import get_llm` inside any function body
- [ ] `_render_provenance_caption(provider, model)` defined at module scope; docstring locks the "MUST NOT read session_state" invariant
- [ ] Helper handles `model=None`/empty (caption degrades to "via **<Name>**" without the model half)
- [ ] `process_query` happy-path return dict carries `"provider"` and `"model"` keys captured via `getattr(client, "provider_name", ...)` / `getattr(client, "_model", "unknown")`
- [ ] `st.session_state.messages.append({...})` in the on-submit block writes `"provider"` and `"model"` keys
- [ ] `render_chat_history()` renders the caption ABOVE `st.markdown(message["content"])` for assistant messages with a `provider` key
- [ ] On-submit `with st.chat_message("assistant"):` block renders the caption ABOVE `st.markdown(response["content"])` when `response.get("provider")` is truthy
- [ ] User messages NEVER render the caption (guarded by `role == "assistant"` + dict-key presence)
- [ ] Early-return error paths in `process_query` (NO DATA, NO EMBEDDINGS, route_query error) DO NOT carry provider/model and DO NOT render a caption
- [ ] Only `app.py` modified
- [ ] Full 69-test suite still green
</success_criteria>

<output>
After completion, create `.planning/phases/05-sidebar-ui-toggle-documentation/05-03-SUMMARY.md` documenting:
- Lines modified in `app.py` (extended import line, helper def, process_query capture, append block, both render sites)
- Confirmation: `get_llm` imported at module scope (Option B from decision §14); helper takes explicit args (no session_state read); two render sites both above-markdown
- 69-test suite still green
- Unblocks: Plan 05-05 (acceptance gate's SC #4 test can now assert history-survives-switch)
- Note for Plan 05-04 (docs): the per-message caption format is `via **<Human Name>** · \`<model>\`` — quote this exact format in the USER_GUIDE explanation
</output>
</output>
