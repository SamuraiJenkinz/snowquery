---
phase: 06-foundation
plan: 01
subsystem: ui
tags: [css, design-tokens, loro-piana, streamlit, typography]

# Dependency graph
requires: []
provides:
  - "src/ui/ Python package with __init__.py marker"
  - "LORO_PIANA_TOKENS dict (25 keys) — palette/spacing/radii values for Python consumers"
  - "LORO_PIANA_CSS string (380 lines) — :root custom properties, base styles, Streamlit overrides, mono boundary"
  - "Canonical Loro Piana design token surface for all of Phase 6+ (single source of truth)"
affects: [06-02, 07, 08, 09, 10, 11]

# Tech tracking
tech-stack:
  added: []  # Pure CSS + Python module; no new dependencies
  patterns:
    - "Two-constant module export: dict (Python access) + str (CSS injection)"
    - "Mono boundary: JetBrains Mono confined to code/pre/kbd/samp/stCodeBlock; Inter + EB Garamond everywhere else"
    - "Warm-brown focus rings via --lp-shadow-focus instead of browser-default blue"
    - "Streamlit chrome hidden (#MainMenu, footer, header, .stDeployButton) so the app owns the canvas"
    - "All Streamlit overrides use CSS custom properties (--lp-*) — no hardcoded hex in selector blocks"

key-files:
  created:
    - "src/ui/__init__.py"
    - "src/ui/css.py"
  modified: []

key-decisions:
  - "Verbatim port of :root + base styles from loro-piana-aesthetic skill template to keep skill as upstream"
  - "Google Fonts import trimmed to EB Garamond 300/400 + Inter 400/500 (per plan must_have) — skill template's wider weight palette not needed yet"
  - "JetBrains Mono kept at 400;500 only — confined to mono boundary selectors"
  - "Token dict uses 25 keys (plan stated '22 total' in prose but enumerated 25 distinct values; followed enumeration)"
  - "No legacy archive file created (per plan constraint)"
  - "No changes to app.py (Plan 02 wires the consumer)"

patterns-established:
  - "src/ui/ package: design-system home for v2.2+"
  - "CSS module export: triple-quoted str constant + companion dict — injectable via st.markdown(<style>...</style>)"
  - "Section header convention: /* ============ NAME ============ */ for visual scan inside the CSS string"

# Metrics
duration: 2min
completed: 2026-05-22
---

# Phase 6 Plan 01: Create CSS Module Summary

**Loro Piana design tokens shipped as a two-constant Python module (LORO_PIANA_TOKENS dict + LORO_PIANA_CSS string) — the single source of truth for warm off-white canvas, cashmere-brown accent, EB Garamond + Inter typography, and a mono boundary that confines JetBrains Mono to code/data only.**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-05-22T19:30:45Z
- **Completed:** 2026-05-22T19:32:57Z
- **Tasks:** 2 of 2
- **Files created:** 2

## Accomplishments

- `src/ui/__init__.py` created as the package marker for the v2.2+ UI helpers home.
- `src/ui/css.py` created with `LORO_PIANA_TOKENS` (25-key dict: palette + semantic + spacing + radii) and `LORO_PIANA_CSS` (380-line string).
- CSS string contains the four required sections — `COLORS` tokens, `BASE STYLES`, `STREAMLIT OVERRIDES`, and `MONO BOUNDARY` — visible via grep:
  - `============ COLORS ============`
  - `============ BASE STYLES ============`
  - `============ STREAMLIT OVERRIDES ============`
  - `============ MONO BOUNDARY ============`
- All must_have CSS strings present: `#F5F0EB`, `EB+Garamond`, `Inter:wght@400;500`, `JetBrains+Mono`, `--lp-shadow-warm: 0 4px 12px rgba(139, 115, 85, 0.08)`, focus ring `0 0 0 3px rgba(139, 115, 85, 0.2)`.
- Banned patterns absent: no `rgba(0, 0, 0, ...)`, no `rgba(0,0,0,...)`, no `#0a0a0a`, no `'JetBrains Mono', 'Courier New', monospace` on `.stApp`.
- Streamlit button selectors (`.stButton > button`, `[data-testid="stChatInputSubmitButton"]`, `[data-testid="baseButton-primary"]`, `[data-testid="baseButton-secondary"]`) all bound to `var(--lp-accent)` + white text + 4px radius + uppercase + 0.1em tracking.
- `.lp-label` utility class implements all six required properties (font-family, font-weight 500, uppercase, tracking-wider, 11px, text-muted).

## Task Commits

Each task committed atomically:

1. **Task 1: create src/ui package marker** — `1df15db` (feat)
2. **Task 2: add Loro Piana CSS tokens module** — `7205cb0` (feat)

Plan metadata commit follows this SUMMARY.

## Files Created/Modified

- `src/ui/__init__.py` (1 line) — package marker with v2.2 module docstring; no re-exports.
- `src/ui/css.py` (380 lines) — `LORO_PIANA_TOKENS` dict + `LORO_PIANA_CSS` string; `__all__` whitelist.

## Verification Asserts (Plan Task 2)

All three verification gates pass:

1. **Import + asserts** (`python -c "..."`):
   - `LORO_PIANA_TOKENS['accent'] == '#8B7355'` ✓
   - `LORO_PIANA_TOKENS['bg'] == '#F5F0EB'` ✓
   - `'#F5F0EB' in LORO_PIANA_CSS` ✓
   - `'EB+Garamond' in LORO_PIANA_CSS` ✓
   - `'Inter:wght@400;500' in LORO_PIANA_CSS` ✓
   - `'JetBrains+Mono' in LORO_PIANA_CSS` ✓
   - `'0 0 0 3px rgba(139, 115, 85, 0.2)' in LORO_PIANA_CSS` ✓
   - `'rgba(0, 0, 0' not in LORO_PIANA_CSS` ✓
   - `'rgba(0,0,0' not in LORO_PIANA_CSS` ✓
   - `'#0a0a0a' not in LORO_PIANA_CSS` ✓
   - Prints `OK` ✓
2. **`.lp-label` count:** 1 occurrence in `src/ui/css.py` (required ≥1) ✓
3. **`letter-spacing.*var(--lp-tracking-wider)` count:** 2 occurrences (required ≥2) ✓

Additional sanity checks (beyond the plan's stated asserts):

- `len(LORO_PIANA_TOKENS) == 25` (matches the enumerated key list in the plan; see Decisions below).
- All four section header banners present in `LORO_PIANA_CSS`.
- `min_lines: 200` (must_have) — actual line count 380 ✓.

## Decisions Made

- **Token dict count:** Plan prose says "22 keys total" but enumerates 25 distinct keys (10 palette + 4 semantic + 8 spacing + 3 radii). I followed the enumeration — all named keys present, none omitted. The "22" appears to be a transcription error in the plan must_haves header line; not a deviation from the actual specification.
- **Font weight subset:** Loaded EB Garamond 300;400 + Inter 400;500 + JetBrains Mono 400;500 per plan must_have, even though the skill template includes wider weight ranges (Garamond 300;400;500, Inter 400;500;600). The skill's `:root` tokens reference only `font-weight: 300` (h1-h3) and `font-weight: 500` (h4-h6 and `.lp-label`), so the trimmed subset covers all token uses.
- **CSS custom property comment line:** Replaced the skill template's leading `/** ... */` HTML link-method comment with a single `/* Loro Piana tokens — see src/ui/css.py module docstring */` pointer comment per plan instruction.
- **No `app.py` touched:** Per plan constraint — Plan 02 will wire the consumer.

## Deviations from Plan

None — plan executed exactly as written.

The "22 vs 25 token dict keys" difference is a count discrepancy inside the plan text itself (header line vs enumerated list), not a deviation from the specified key set. Every named key in the plan's enumeration is present.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required for this plan.

## Next Phase Readiness

- **Plan 02 (wire consumer in app.py)** can proceed: imports will resolve at `from src.ui.css import LORO_PIANA_CSS`, and the CSS string is injection-ready via `st.markdown(f"<style>{LORO_PIANA_CSS}</style>", unsafe_allow_html=True)`.
- **Phase 7 (splash) and Phase 8 (sidebar + main restyle)** can read tokens/CSS from `src.ui.css` as a shared, read-only design surface.
- **v2.1 invariants preserved:** `_render_provenance_caption` untouched, locked UI strings untouched, `app.py` untouched.

No blockers; no concerns.

---
*Phase: 06-foundation*
*Completed: 2026-05-22*
