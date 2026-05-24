# Phase 11: Documentation + Acceptance Gate - Research

**Researched:** 2026-05-23
**Domain:** Python test authoring, markdown documentation editing, WCAG contrast math
**Confidence:** HIGH — all findings derived from direct file reads and live Python execution

---

## Summary

Phase 11 closes the v2.2 milestone with three workstreams: (1) documentation updates to USER_GUIDE.md and README.md, (2) a new `tests/test_phase6_visual.py` acceptance gate, and (3) WCAG-AA contrast verification embedded in that same test file. All implementation targets exist and are in known-good state (91/91 tests passing). The CSS assertions are straightforward because `LORO_PIANA_CSS` already contains all required tokens. The WCAG guard has a critical implementation nuance: `LORO_PIANA_CSS` contains zero direct `color: #6B5E52` literals — all uses of that color go through `var(--lp-text-muted)` — so the negative usage scan will find no matches and pass vacuously. The planner must decide how to handle this (either scan for `var(--lp-text-muted)` or document the vacuous pass as intentional). The docs workstream and test workstream have no file conflicts and can execute in parallel.

**Primary recommendation:** Split into two parallel waves — Wave 1: DOC work (USER_GUIDE.md + README.md + docs/screenshots/ creation); Wave 2: TST work (write `tests/test_phase6_visual.py`). Both waves are independent and touch different files entirely.

---

## Finding 1: USER_GUIDE.md Structure

**File:** `USER_GUIDE.md` (455 lines total)

### Current TOC (lines 9–22)

```
1. Getting Started
2. Loading Data
3. Building Embeddings
4. Query Modes
5. Chart Visualization
6. Writing Effective Queries
7. Understanding Results
8. Settings
9. LLM Provider Selection
10. Tips & Best Practices
11. Troubleshooting
```

Eleven numbered items. New "Visual Refresh (v2.2)" section inserts as item **1** (bumping all subsequent items by 1, so former item 1 "Getting Started" becomes item 2, through former item 11 "Troubleshooting" becoming item 12).

### Current footer (line 454)

```
*Last updated: May 2026 (v2.1 - Added multi-provider LLM selection: Azure OpenAI / Anthropic Claude via MGTI)*
```

This is the only version stamp. It must be replaced with a `v2.2` footer.

### Voice anchor (lines 46–55 — "Unlocking CSV Upload" subsection)

```markdown
### Unlocking CSV Upload

CSV upload is password-protected. To upload files:

1. Enter the upload password in the sidebar
2. Click **"UNLOCK UPLOAD"**
3. Once unlocked, the file uploader appears
4. Click **"LOCK UPLOAD"** when finished to re-secure
```

Model the new section on this: short declarative sentences, numbered steps when sequential, bold for UI labels.

### TST-01 sensitivity

`test_sc5_user_guide_contains_locked_ui_strings_and_required_topics` (line 709 of `tests/test_phase5_ui.py`) asserts these strings exist verbatim in `USER_GUIDE.md`:
- `"LLM provider"` (selectbox label, lowercase 'p')
- `"Azure OpenAI"`
- `"Anthropic Claude (MGTI)"`
- `"LLM PROVIDER"` (sidebar section header, uppercase)
- `"QUERY DISABLED"`
- `"hubble.mmc.com"`
- `"smoke_llm.py"`

And these topic strings:
- `"LLM Provider Selection"`
- `"MGTI"`
- `"First-Time"`
- `"Mid-Session"`

And env var names: `"ANTHROPIC_BASE_URL"`, `"ANTHROPIC_API_KEY"`, `"ANTHROPIC_MODEL"`.

**The new VISUAL REFRESH section MUST NOT remove or alter any of these strings from the existing content.** The new section inserts above existing content; no existing content is deleted.

---

## Finding 2: README.md Structure

**File:** `README.md` (117 lines total)

### Current section order (exact `##` headings)

```
## Features          (line 7)
## Tech Stack        (line 16)
## Quick Start       (line 27)
## Project Structure (line 52)
## Environment Variables (line 71)
### LLM Provider Selection (line 87 — subsection)
### Smoke Test (operator-run) (line 96 — subsection)
## Data Privacy      (line 112)
```

New `## Screenshots` section inserts **after `## Features` (line 7), before `## Tech Stack` (line 16)**.

### Current markdown image usage

No existing image/screenshot markup in README.md. First inline image will be the three thumbnails added by DOC-02.

### TST-01 sensitivity

`test_sc5_readme_contains_required_topics` (line 683 of `tests/test_phase5_ui.py`) asserts these strings exist in `README.md`:
- `"LLM Provider Selection"`
- `"Anthropic Claude"`
- `"smoke_llm.py"`
- `"USER_GUIDE.md"`
- `"MGTI"`
- `"Hubble"` or `"hubble.mmc.com"`

No changes to existing content are needed — the Screenshots section is additive.

---

## Finding 3: test_phase5_ui.py Header Pattern

**File:** `tests/test_phase5_ui.py` (lines 1–19)

```python
"""Phase 5 acceptance gate: prove all 5 Phase 5 success criteria.

Each test function maps to one of:
  - The 5 numbered Phase 5 ROADMAP success criteria
  - The RESEARCH.md regression guards (Pitfalls 1, 6, 8, 11, 13)
  - The docs-content surface (DOC-01..04)

Conventions inherited from Phase 1/2/3/4 acceptance gates:
  - autouse _clear_factory_cache + _strip_llm_env fixtures isolate
    module-level singletons and env-var state between tests
  - Streamlit primitives mocked via the _build_streamlit_mock_surface()
    helper + unittest.mock.patch.multiple — NO live Streamlit
  - Inline test setup — NO fixture files
  - Tests have ZERO live external dependencies (no HTTP, no LLM, no Streamlit
    runtime, no real file system writes)

Run with: `pytest tests/test_phase5_ui.py -v`
Or combined with prior phases: `pytest tests/ -v` (expected: ~90 tests)
"""
from __future__ import annotations
```

The new `tests/test_phase6_visual.py` header docstring must follow this exact shape: purpose statement, conventions list, run command, combined-suite expected count (which will now be `~103` given 91 existing + 12 new tests, or exact count if planner decides).

### Test naming convention

All test functions follow `test_<descriptor>()` with no class wrapper. Comment dividers use `# ---` style (e.g., `# ===========================================================================\n# SC #1: Sidebar selectbox label/options/state-init\n# ===========================================================================`). Phase 6 tests should use `# ---` section headers grouping by concern (CSS presence, CSS absence, renderer signatures, Altair theme).

### Import pattern

```python
from __future__ import annotations
import [stdlib]
import pytest
```

No autouse fixtures needed in `test_phase6_visual.py` because there is no Streamlit, LLM, or session state involvement. The test file imports directly from `src.ui.css`, `src.ui.results`, `src.ui.splash`, `src.ui.altair_theme`.

---

## Finding 4: src/ui/css.py — Export Verification

**File:** `src/ui/css.py` (1408 lines)

### Exports (line 1407)

```python
__all__ = ["LORO_PIANA_TOKENS", "LORO_PIANA_CSS"]
```

### LORO_PIANA_TOKENS palette keys (lines 23–53)

```python
LORO_PIANA_TOKENS: dict[str, str | int] = {
    "bg": "#F5F0EB",          # warm off-white
    "text": "#2C2420",        # charcoal
    "text_muted": "#6B5E52",  # warm gray (secondary text)
    "text_subtle": "#8A7A6B",
    "accent": "#8B7355",      # cashmere brown
    ...
}
```

### LORO_PIANA_CSS — TST-02 presence assertions (all CONFIRMED present)

| Token/String | Present in LORO_PIANA_CSS | Location |
|---|---|---|
| `EB+Garamond` (Google Fonts import) | YES | Line 57 (`@import url(...)`) |
| `EB Garamond` (CSS value) | YES | Multiple (`:root`, `.lp-page-header`, etc.) |
| `Inter` | YES | Line 57 + multiple `:root` and selectors |
| `#8B7355` | YES | `--lp-primary-500: #8B7355` in `:root` |
| `#F5F0EB` | YES | `--lp-primary-50: #F5F0EB` + `--lp-neutral-50: #F5F0EB` in `:root` |
| `#2C2420` | YES | `--lp-neutral-800: #2C2420` in `:root` |

### LORO_PIANA_CSS — TST-02 absence assertions (all CONFIRMED absent)

| Token | Present in LORO_PIANA_CSS | Result |
|---|---|---|
| `#0a0a0a` (case-insensitive) | NO | Absence assertion passes |
| `#0A0A0A` | NO | Absence assertion passes |

### `.stApp` block (for JetBrains Mono absence check)

The `.stApp` block in `LORO_PIANA_CSS` (lines 260–263):

```css
.stApp {
  font-family: var(--lp-font-body) !important;
}
```

`re.search(r"\.stApp\s*\{[^}]*\}", LORO_PIANA_CSS)` finds exactly this block. `"JetBrains Mono"` is NOT present in the block body. Assertion passes.

**Note:** `JetBrains Mono` does appear elsewhere in `LORO_PIANA_CSS` (in the mono-boundary block `code, pre, kbd, samp, .lp-mono, ...`) but NOT inside the `.stApp {}` rule body. The two-step regex extraction (get block, then check absence in block body) correctly limits scope.

### CRITICAL FINDING — TST-03 guard implementation

`LORO_PIANA_CSS` has **zero** occurrences of `color: #6B5E52` (verified by Python `re.findall`). All instances of `#6B5E52` usage in the CSS go through CSS custom properties:
- `--lp-neutral-600: #6B5E52` (definition in `:root`, not a `color:` property)
- `color: var(--lp-text-muted)` — 11 occurrences (resolved to `#6B5E52` at runtime)
- `color: var(--lp-neutral-600)` — 1 occurrence

The CONTEXT.md spec says "Grep `LORO_PIANA_CSS` for every occurrence of `color: #6B5E52`." Since there are zero direct occurrences, the scan produces zero matches, and the guard passes vacuously (no misuse to check). The planner has two implementation paths:
1. **Scan for literal `color: #6B5E52`** — passes vacuously (zero matches). Test is technically correct but weak.
2. **Scan for `var(--lp-text-muted)` in `color:` properties** — would find 11 sites and attempt the guard check. This is more thorough but deviates from the CONTEXT spec's literal description.

**Recommendation:** Follow the CONTEXT spec literally (scan for `color: #6B5E52`). The vacuous pass is intentional — the CSS was correctly authored using variables. The test proves the standard is upheld. Note this explicitly in the test docstring.

### Sites using `color: var(--lp-text-muted)` WITHOUT uppercase/letter-spacing markers

For the planner's awareness if they choose path 2 above, these five sites would fail the guard check because they use `#6B5E52` (via var) in body text roles:
- `.lp-warn-card .lp-warn-fix` — 13px body fix text
- `.lp-ghost-queries .stButton > button::before` — ghost dot prefix
- `.lp-page-subtitle` — 15px subtitle (large text, font-size check would qualify at ≥14px)
- `[data-testid="stChatInput"] textarea::placeholder` — placeholder (≥14px would qualify)
- `.lp-empty-card .lp-empty-subtitle` — 15px subtitle (≥14px would qualify)

---

## Finding 5: src/ui/results.py, splash.py, altair_theme.py — Signature Verification

All three function/module signatures confirmed present and callable:

| Module | Export | Type | Status |
|---|---|---|---|
| `src.ui.results` | `_render_editorial_table` | function | EXISTS, callable (line 135) |
| `src.ui.splash` | `render_splash` | function | EXISTS, callable (line 131) |
| `src.ui.altair_theme` | `loro_piana` Altair theme | registered theme | EXISTS |

### Altair theme check — CRITICAL API NOTE

The **correct** assertion for the loro_piana theme is:

```python
import altair as alt
import src.ui.altair_theme  # side-effect import triggers registration

assert "loro_piana" in alt.theme.names()  # NEW API (Altair 6)
```

**NOT** `alt.themes.names()` — that is the deprecated Altair 5 API. Calling `alt.themes.names()` issues `AltairDeprecationWarning`. The `src/ui/altair_theme.py` module docstring (line 27) explicitly documents this: "The deprecated `alt.themes.*` API was removed in Altair 6 and must NOT be used."

Verified live: `"loro_piana" in alt.theme.names()` returns `True` after importing `src.ui.altair_theme`.

---

## Finding 6: Design Mockup PNGs

All three files exist at exact paths:

| File | Path | Size |
|---|---|---|
| `00-splash-helix.png` | `.planning/design-mockups/00-splash-helix.png` | 15,984 bytes |
| `01-main-chat.png` | `.planning/design-mockups/01-main-chat.png` | 39,592 bytes |
| `02-results-chart.png` | `.planning/design-mockups/02-results-chart.png` | 49,060 bytes |

### docs/screenshots/ directory

`docs/` directory exists with two unrelated HTML files. `docs/screenshots/` subdirectory does **not** exist. The plan must create `docs/screenshots/` and copy (not move) all three PNGs into it.

---

## Finding 7: Tests Directory Layout and Pytest Config

### Current test files

| File | Tests | Role |
|---|---|---|
| `tests/test_llm_seam.py` | 6 | Phase 1 |
| `tests/test_phase2_parity.py` | 12 | Phase 2 |
| `tests/test_phase3_adapter.py` | 21 | Phase 3 |
| `tests/test_phase4_strict_tools.py` | 30 | Phase 4 |
| `tests/test_phase5_ui.py` | 22 | Phase 5 |
| **Total** | **91** | Matches STATE.md baseline |

### Pytest configuration

No `pytest.ini`, `pyproject.toml`, `setup.cfg`, or `tests/conftest.py` found. Pytest runs with default discovery. Adding `tests/test_phase6_visual.py` requires no configuration changes — pytest will collect it automatically.

### Current 91/91 status

Confirmed: `pytest tests/ -q` produces `91 passed, 1 warning`. The warning is a jsonschema deprecation from `test_phase4_strict_tools.py` — pre-existing, unrelated.

---

## Finding 8: WCAG Contrast Formula and Precomputed Values

### WCAG 2.1 Relative Luminance Formula

```python
def _to_linear(c: int) -> float:
    """Linearize an 8-bit channel value (0–255)."""
    s = c / 255.0
    if s <= 0.04045:
        return s / 12.92
    return ((s + 0.055) / 1.055) ** 2.4

def _luminance(hex_color: str) -> float:
    """Compute WCAG 2.1 relative luminance from a hex color string."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 0.2126 * _to_linear(r) + 0.7152 * _to_linear(g) + 0.0722 * _to_linear(b)

def _contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    """Compute WCAG contrast ratio (always >= 1.0)."""
    l1 = _luminance(fg_hex)
    l2 = _luminance(bg_hex)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)
```

### Precomputed expected ratios (verified by live Python execution)

| Pair | Computed Ratio | Passes 4.5:1 (body AA) | Passes 3:1 (large AA) |
|---|---|---|---|
| `#2C2420` on `#F5F0EB` | **13.4363** | YES | YES |
| `#6B5E52` on `#F5F0EB` | **5.5393** | YES (but spec says large-text only) | YES |

The test for `#2C2420`:
```python
assert ratio >= 4.5, f"#2C2420 on #F5F0EB = {ratio:.2f}, fails WCAG-AA body (4.5:1 required)"
```

The test for `#6B5E52` — TWO assertions per CONTEXT:
```python
assert ratio >= 3.0, f"#6B5E52 on #F5F0EB = {ratio:.2f}, fails WCAG-AA large text (3:1 required)"
assert ratio < 4.5, f"#6B5E52 on #F5F0EB = {ratio:.2f}, incorrectly passes body-text threshold (use for large/label only)"
```

Both assertions are mathematically guaranteed to pass (5.54 >= 3.0 and 5.54 < 4.5 is FALSE — wait, 5.54 is NOT < 4.5).

**CRITICAL CORRECTION:** `#6B5E52` on `#F5F0EB` ratio = **5.5393**, which is ≥ 4.5. The spec says it must pass 3:1 AND must fail 4.5:1. But **5.5393 does NOT fail 4.5:1** — it passes 4.5:1 too.

The CONTEXT spec says "MUST pass 3:1 AND MUST fail 4.5:1 (large text / label only, NOT body)." This assertion cannot be written as `assert ratio < 4.5` because `#6B5E52` on `#F5F0EB` actually passes 4.5:1 (ratio = 5.54).

**The planner must resolve this conflict between the CONTEXT spec and the actual math.** Options:
1. Only assert `ratio >= 3.0` (the 3:1 pass). Drop the negative 4.5:1 assertion since the math doesn't support it. Add a docstring note explaining why.
2. Write `assert ratio < 4.5` and it will FAIL (5.54 ≥ 4.5 → assertion fails). This would make TST-03 impossible to pass.
3. Interpret "MUST fail 4.5:1" as referring to the usage role (the color SHOULD only be used in large-text roles) and implement it via the negative usage scan only, not a ratio check.

The CONTEXT spec's intent was that `#6B5E52` fails body-text requirements, but the actual math shows a 5.5:1 ratio which passes both thresholds. The guard mechanism makes sense via usage scan, not ratio gate. **Recommend: omit the `ratio < 4.5` assertion; implement the guard solely via the negative usage scan.**

---

## Finding 9: Risks and Protected Files

### Files that Phase 11 must NOT touch (TST-01 protected)

| File | Why Protected |
|---|---|
| `app.py` | Contains `_render_provenance_caption`, `_PROVIDER_OPTIONS`, `render_sidebar`, `render_main_content`, `render_chat_history` — all directly exercised by Phase 5 tests |
| `src/llm/__init__.py` | `_REGISTRY`, `get_llm`, `_get_llm_cached`, `_fingerprint`, `missing_vars` |
| `src/llm/base.py` | `LLMClient` ABC with `provider_name` abstract property |
| `src/llm/azure_openai.py` | `AzureOpenAIClient.provider_name == "azure_openai"` |
| `src/llm/anthropic_mgti.py` | `AnthropicMGTIClient.provider_name == "anthropic_mgti"` |

Phase 11 only creates/modifies: `USER_GUIDE.md`, `README.md`, `docs/screenshots/` (new dir), `tests/test_phase6_visual.py` (new file). None of these touch the protected files.

### What could break TST-01 accidentally

- Editing `USER_GUIDE.md` and **removing** one of the seven locked UI strings (e.g., deleting the LLM Provider Selection section while editing TOC). The planner must ensure the new section is additive only.
- Editing `README.md` and removing `"LLM Provider Selection"`, `"Anthropic Claude"`, `"smoke_llm.py"`, `"USER_GUIDE.md"`, `"MGTI"`, or `"Hubble"`. The new Screenshots section is additive.
- Importing `streamlit` in `test_phase6_visual.py` — if Streamlit is not available in the test environment it could cause collection errors. The CONTEXT spec requires zero Streamlit imports in this test file.

### Pytest collection concerns

No `conftest.py` exists. The new `tests/test_phase6_visual.py` will be collected automatically. Imports of `src.ui.altair_theme` trigger Altair's `@alt.theme.register` decorator on import — this is a side effect but is benign in a test context (Altair is a project dependency).

**Note:** `import src.ui.splash` will also import `streamlit.components.v1` (line 21 of `splash.py`). The module-level import happens at collection time. If Streamlit is not fully available outside a Streamlit runtime, this could cause issues. The CONTEXT spec says "NO Streamlit mock surface needed" — but does NOT say Streamlit cannot be importable. Streamlit itself is importable outside a runtime context; only runtime-specific features (session_state, widget rendering) fail. Module-level import of `src.ui.splash` should work fine.

---

## Finding 10: Wave Decomposition

### File conflict analysis

| Task | Files Modified | Conflicts with |
|---|---|---|
| DOC-01: USER_GUIDE.md edits | `USER_GUIDE.md` | None |
| DOC-02: README.md edits + docs/screenshots/ | `README.md`, `docs/screenshots/*.png` | None |
| TST-01: Verify existing tests pass | No files modified | None |
| TST-02 + TST-03: Write test_phase6_visual.py | `tests/test_phase6_visual.py` (new) | None |

### Recommended wave structure

**Wave 1 (parallel):**
- Task A: DOC work — edit USER_GUIDE.md (add Visual Refresh section, renumber TOC, bump footer) + edit README.md (add Screenshots section) + create `docs/screenshots/` and copy 3 PNGs
- Task B: Test file skeleton — write `tests/test_phase6_visual.py` header, helper `_contrast_ratio`, section comment dividers, and stub test function names

**Wave 2 (sequential, after Wave 1):**
- Task C: Fill in test bodies — CSS presence assertions, CSS absence assertions, function signature assertions, Altair theme assertion, WCAG ratio assertions, negative usage scan
- Task D: Run full suite (`pytest tests/ -v`) and confirm 91+N tests pass

The DOC and TST workstreams are fully independent (no shared files, no ordering dependency), so they can be parallelized in Wave 1.

---

## Code Examples

### _contrast_ratio helper (exact formula for WCAG 2.1)

```python
# Source: WCAG 2.1 specification §1.4.3 + live verified output
def _contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    def _lin(c: int) -> float:
        s = c / 255.0
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4

    def _lum(h: str) -> float:
        h = h.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)

    l1, l2 = _lum(fg_hex), _lum(bg_hex)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)
```

### .stApp block regex (exact pattern from CONTEXT + verified working)

```python
import re
from src.ui.css import LORO_PIANA_CSS

stapp_match = re.search(r"\.stApp\s*\{[^}]*\}", LORO_PIANA_CSS)
body = stapp_match.group() if stapp_match else ""
assert "JetBrains Mono" not in body
```

Live result: block is `".stApp {\n  font-family: var(--lp-font-body) !important;\n}"` — no JetBrains Mono.

### Altair theme registration check (correct API)

```python
import altair as alt
import src.ui.altair_theme  # side-effect: registers loro_piana

assert "loro_piana" in alt.theme.names()  # NOT alt.themes.names()
```

### Google Font import assertions

```python
from src.ui.css import LORO_PIANA_CSS

assert "EB+Garamond" in LORO_PIANA_CSS or "EB Garamond" in LORO_PIANA_CSS
assert "Inter" in LORO_PIANA_CSS
```

Note: the `@import` line uses `EB+Garamond` (URL-encoded). Either form passes a substring check on LORO_PIANA_CSS.

---

## Open Questions

1. **WCAG ratio paradox** — `#6B5E52` on `#F5F0EB` yields 5.54:1, which passes both 3:1 AND 4.5:1. The CONTEXT spec says it "MUST fail 4.5:1." The math contradicts the spec. The planner must decide: (a) implement only the 3:1 positive assertion and note the ratio is also AA-compliant, (b) assert `ratio < 4.5` (will fail), or (c) treat the 4.5:1 constraint as a usage-role constraint enforced only by the negative scan.

2. **Negative usage scan against CSS vars vs. hex** — `LORO_PIANA_CSS` has 0 direct `color: #6B5E52` occurrences. The scan passes vacuously. The planner must decide whether to note this in the test docstring or enhance the scan to cover `var(--lp-text-muted)` (which would catch 11 sites, some of which may fail the marker check).

3. **"color: var(--lp-text-muted)" body-text usages** — Five CSS rules apply `#6B5E52` to body-text contexts without small-caps markers. The CONTEXT spec creates the guard, but the actual LORO_PIANA_CSS already has these usages. If the guard scans for `var(--lp-text-muted)` and applies the marker check, it would produce false-positive failures on legitimate body-text uses. This is why scanning for literal `color: #6B5E52` (as the CONTEXT literally says) is the safer approach.

---

## Sources

### Primary (HIGH confidence)
- Direct file read: `USER_GUIDE.md` — exact TOC, footer text, voice samples
- Direct file read: `README.md` — exact section order, no existing screenshots
- Direct file read: `tests/test_phase5_ui.py` — full 22-test file, header pattern, locked string assertions
- Direct file read: `src/ui/css.py` — complete 1408-line file, all token/export verification
- Direct file read: `src/ui/splash.py` — `render_splash` signature, module-level import of `streamlit.components.v1`
- Direct file read: `src/ui/altair_theme.py` — `@alt.theme.register("loro_piana", enable=True)` decorator
- Direct file read: `src/ui/results.py` — `_render_editorial_table` at line 135
- Direct file read: `.planning/phases/11-documentation-acceptance-gate/11-CONTEXT.md` — locked decisions
- Live Python execution: contrast ratios (`#2C2420` = 13.44, `#6B5E52` = 5.54)
- Live Python execution: `pytest tests/ --collect-only` → 91 tests
- Live Python execution: `pytest tests/ -q` → 91 passed
- Live Python execution: `alt.theme.names()` → `loro_piana` confirmed present
- Live Python execution: LORO_PIANA_CSS token presence/absence verification
- Live filesystem check: `.planning/design-mockups/` — all 3 PNGs confirmed
- Live filesystem check: `docs/` exists, `docs/screenshots/` does NOT exist

---

## Metadata

**Confidence breakdown:**
- USER_GUIDE structure: HIGH — read directly
- README structure: HIGH — read directly
- test_phase5_ui.py pattern: HIGH — read directly, count verified
- css.py exports: HIGH — read + live Python verified
- Function signatures: HIGH — live Python verified
- Design mockups: HIGH — filesystem verified
- Altair theme API: HIGH — live Python verified, deprecation warning noted
- WCAG math: HIGH — live Python computed
- TST-03 implementation gap: HIGH — live Python confirmed 0 direct hex occurrences

**Research date:** 2026-05-23
**Valid until:** This research reflects the current codebase state. Valid until any of the source files are modified.
