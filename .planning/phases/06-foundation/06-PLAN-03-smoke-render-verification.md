---
phase: 06-foundation
plan: 03
type: execute
wave: 3
depends_on: ["01", "02"]
files_modified: []
autonomous: false

must_haves:
  truths:
    - "Launching `streamlit run app.py` shows a warm off-white (`#F5F0EB`) background across the entire viewport — no `#0a0a0a` brutalist black anywhere in the rendered DOM."
    - "The browser's computed body `font-family` resolves to a stack starting with `Inter` (NOT `JetBrains Mono`)."
    - "At least three distinct `st.button` instances in the running app render with cashmere brown (`#8B7355`) background, white text, 4px border-radius, uppercase tracked label (`letter-spacing: 0.1em`)."
    - "The browser tab favicon shows a `✦` glyph (U+2726 BLACK FOUR POINTED STAR), NOT the brutalist `▣`."
    - "The Streamlit app loads without console errors related to CSS injection or font loading (404s on Google Fonts URLs are allowed if offline, but no JS runtime errors)."
  artifacts:
    - path: ".planning/phases/06-foundation/06-03-SUMMARY.md"
      provides: "Smoke verification record — screenshot evidence + grep checks recording observed DOM state."
      contains: "FND-06"
  key_links:
    - from: "Running Streamlit app (Plan 02 output)"
      to: "Phase 6 success criteria #1, #4, #5"
      via: "Browser DOM inspection + visual check of buttons and favicon."
      pattern: "(visual verification — see SUMMARY)"
---

<objective>
Verify Phase 6 visually. Launch the app, confirm the Loro Piana foundation is live, and capture evidence for the SUMMARY. No new code — this plan is a checkpoint plus a few DOM grep checks that close FND-06 and Phase 6 success criteria #1, #4, #5.

Purpose: Phase 6's contract isn't "code compiles" — it's "the app actually looks warm and cashmere now." This plan confirms the rendered reality matches the CSS module. Lowest-friction approach per CONTEXT.md: use the seven existing `st.button` instances already in `app.py` (UNLOCK UPLOAD, REPLACE, APPEND, LOCK UPLOAD, REBUILD, UPDATE, CLEAR HISTORY) — no synthetic test buttons needed.

Output: A SUMMARY documenting observed background color, body font, three button visual checks, and favicon glyph. Optional screenshot path noted if user provides one.
</objective>

<execution_context>
@C:/Users/taylo/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/taylo/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/06-foundation/06-CONTEXT.md
@.planning/phases/06-foundation/06-01-SUMMARY.md
@.planning/phases/06-foundation/06-02-SUMMARY.md
@app.py
@src/ui/css.py
</context>

<tasks>

<task type="auto" id="1">
  <name>Task 1: Static pre-launch checks (no app running)</name>
  <files></files>
  <action>
Before launching Streamlit, run a battery of static checks against `app.py` and `src/ui/css.py` to confirm Plans 01 + 02 landed correctly. Record results inline; if any fail, STOP and report — do not proceed to the visual checkpoint with broken code.

Run each command and record output:

1. **CSS injection wired correctly:**
   ```
   grep -c "from src.ui.css import LORO_PIANA_CSS" app.py    # expect 1
   grep -c "LORO_PIANA_CSS" app.py                            # expect 2 (import + injection)
   grep -c '<style>' app.py                                   # expect 1
   ```

2. **Brutalist remnants gone:**
   ```
   grep -c "#0a0a0a" app.py                                   # expect 0
   grep -c "'JetBrains Mono', 'Courier New', monospace" app.py # expect 0
   grep -c 'page_icon="▣"' app.py                              # expect 0
   ```

3. **Page chrome refreshed:**
   ```
   grep -c 'page_icon="✦"' app.py                              # expect 1
   grep -c 'page_title="SNOWGREP"' app.py                      # expect 1
   ```

4. **Locked v2.1 strings preserved:**
   ```
   grep -cF '"LLM provider"' app.py                            # expect >=1
   grep -cF '"Azure OpenAI"' app.py                            # expect >=1
   grep -cF '"Anthropic Claude (MGTI)"' app.py                 # expect >=1
   grep -cF 'QUERY DISABLED' app.py                            # expect >=1
   ```

5. **CSS module integrity:**
   ```
   python -c "from src.ui.css import LORO_PIANA_CSS, LORO_PIANA_TOKENS; \
              assert '#F5F0EB' in LORO_PIANA_CSS; \
              assert '#8B7355' in LORO_PIANA_CSS; \
              assert 'EB+Garamond' in LORO_PIANA_CSS; \
              assert 'Inter:wght@400;500' in LORO_PIANA_CSS; \
              assert 'rgba(0, 0, 0' not in LORO_PIANA_CSS; \
              assert 'rgba(0,0,0' not in LORO_PIANA_CSS; \
              assert '0a0a0a' not in LORO_PIANA_CSS; \
              assert LORO_PIANA_TOKENS['accent'] == '#8B7355'; \
              print('OK')"
   ```
   Expect: `OK`.

6. **Phase 5 regression still passes:**
   ```
   python -m pytest tests/test_phase5_ui.py -q
   ```
   Expect: exit 0.

7. **app.py compiles:**
   ```
   python -m py_compile app.py
   ```
   Expect: exit 0.

Record all observed counts and exit codes in scratch notes for the SUMMARY.
  </action>
  <verify>
All commands above return the expected counts/exit codes. If any deviate, halt and report the discrepancy — do NOT proceed to Task 2.
  </verify>
  <done>
All 7 static check groups return expected values. Ready to launch the app.
  </done>
</task>

<task type="checkpoint:human-verify" id="2" gate="blocking">
  <what-built>
Phase 6 has shipped: a Loro Piana CSS module (`src/ui/css.py`) wired into `app.py` via a single injection, plus a refreshed `page_icon="✦"`. The brutalist `#0a0a0a` background and `JetBrains Mono` body font are gone.
  </what-built>
  <how-to-verify>
Launch the app in a foreground terminal (do NOT use `run_in_background` — the user needs to see and interact):

```
streamlit run app.py
```

Wait for the local URL to print (typically `http://localhost:8501`). Open it in a browser.

**Visual checks (perform all five — record observed state for each in the SUMMARY):**

1. **Background color (FND-02, Success #1):** The page background is warm off-white. Open browser DevTools → Elements → click `<body>` → Computed → confirm `background-color` resolves to `rgb(245, 240, 235)` (= `#F5F0EB`). Confirm there is NO `#0a0a0a` (`rgb(10, 10, 10)`) anywhere in the rendered tree.

2. **Body font (FND-01, Success #1):** In DevTools → Elements → click `<body>` → Computed → confirm `font-family` starts with `Inter` (not `JetBrains Mono`). The actual rendered text on the page reads in a sans-serif Inter, not in monospace.

3. **Buttons (FND-06, Success #4):** With a CSV uploaded (or use the sidebar without one — `UNLOCK UPLOAD` is always present), inspect at least three distinct visible `st.button` instances. Candidates that are likely visible on first load: `UNLOCK UPLOAD` (sidebar), `CLEAR HISTORY` (chat area, may be conditional on history), and either `REBUILD` or `UPDATE` (embeddings section). For each of the three buttons, in DevTools confirm computed styles:
   - `background-color: rgb(139, 115, 85)` (= `#8B7355`)
   - `color: rgb(255, 255, 255)` (= white)
   - `border-radius: 4px`
   - `text-transform: uppercase`
   - `letter-spacing: 1.6px` (= `0.1em` × 16px base; may show as `0.1em` directly depending on browser)

4. **Page icon (FND-05, Success #5):** Look at the browser tab. The favicon shows `✦` (a four-pointed star), NOT `▣` (a boxed square). The tab title still reads `SNOWGREP`.

5. **Google Fonts loaded (FND-01, Success #2):** DevTools → Network → filter "fonts" or "googleapis". Confirm at least two requests to `fonts.googleapis.com` or `fonts.gstatic.com` succeed (EB Garamond + Inter). JetBrains Mono may also load — that's fine; it's retained for code/data blocks.

**Capture evidence:**
- Take a single screenshot of the running app showing the warm background, a visible cashmere button, and the browser tab favicon. Save it to `.planning/phases/06-foundation/06-03-smoke.png` (or whatever path the user prefers).
- Note any deviations (e.g., a button somewhere still showing the old brutalist styling — that would indicate Phase 6 CSS specificity is too low and needs a `!important` on a button rule).

**Stop the app:** Press Ctrl+C in the terminal.
  </how-to-verify>
  <resume-signal>
Type `approved` if all five visual checks pass. If something looks wrong, describe the symptom (e.g., "background is still black", "buttons are still gray", "favicon still shows the square") — that becomes a gap that may need a `--gaps` follow-up plan.
  </resume-signal>
</task>

<task type="auto" id="3">
  <name>Task 3: Write SUMMARY with observed evidence</name>
  <files>.planning/phases/06-foundation/06-03-SUMMARY.md</files>
  <action>
Create `.planning/phases/06-foundation/06-03-SUMMARY.md` recording:

1. All 7 static check results from Task 1 (exact grep counts and exit codes).

2. The five visual check observations from Task 2:
   - Computed body `background-color` value as read from DevTools.
   - Computed body `font-family` value (first family in the stack).
   - Three button names + their computed `background-color`, `color`, `border-radius`, `text-transform`, `letter-spacing`.
   - Favicon glyph observed in the browser tab.
   - Google Fonts network requests confirmed (or "skipped — offline" if applicable).

3. Path to the screenshot if one was saved.

4. Phase 6 success criteria coverage table:
   | # | Criterion | Status | Evidence |
   |---|-----------|--------|----------|
   | 1 | Warm off-white background, body font Inter | PASS/FAIL | DevTools observation |
   | 2 | Google Fonts EB Garamond + Inter loaded | PASS/FAIL | Network panel observation |
   | 3 | CSS sourced from single module, single injection | PASS/FAIL | grep counts from Task 1 |
   | 4 | Three buttons cashmere + 4px + 0.1em uppercase | PASS/FAIL | DevTools observation |
   | 5 | page_icon ✦, page_title SNOWGREP | PASS/FAIL | grep + visual |

5. FND requirement coverage:
   - FND-01: covered by Plan 01 (font imports in `LORO_PIANA_CSS`) + Plan 03 visual confirmation.
   - FND-02: covered by Plan 01 (`:root` overrides) + Plan 03 DevTools background check.
   - FND-03: covered by Plan 02 (single-injection wiring) + Plan 03 grep counts.
   - FND-04: covered by Plan 01 (`.lp-label` class definition). Phase 8 verifies it's applied to real DOM labels; Phase 6 only ships the class.
   - FND-05: covered by Plan 02 (`page_icon="✦"`) + Plan 03 favicon visual.
   - FND-06: covered by Plan 01 (button CSS rules) + Plan 03 DevTools button computed styles.

6. Any deviations from CONTEXT.md (expected: none).

7. Note that v2.1 invariants are preserved: `_render_provenance_caption` untouched, locked UI strings still present, `tests/test_phase5_ui.py` still passes.
  </action>
  <verify>
`ls .planning/phases/06-foundation/06-03-SUMMARY.md` succeeds. File is non-empty and contains the coverage table.
  </verify>
  <done>
Summary written. Phase 6 visual evidence captured.
  </done>
</task>

</tasks>

<verification>
After all three tasks:

- `.planning/phases/06-foundation/06-03-SUMMARY.md` exists.
- The SUMMARY's success criteria table shows PASS for all 5 criteria.
- The user has typed `approved` at the checkpoint (or any deviations are documented).
</verification>

<success_criteria>
- Static pre-launch checks all pass.
- Visual checkpoint approved by user.
- SUMMARY documents all 5 Phase 6 success criteria as PASS.
- Satisfies: FND-06 (visual button verification on ≥3 instances), Success Criteria #1, #4, #5 (closed by visual inspection).
</success_criteria>

<output>
After completion, the SUMMARY at `.planning/phases/06-foundation/06-03-SUMMARY.md` is the canonical Phase 6 closeout record. Phase 6 is shipped; Phase 7 (Splash) and Phase 8 (Screen restyle) are now unblocked.
</output>
