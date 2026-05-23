---
phase: 07-splash-screen
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - "src/ui/splash.py"
autonomous: true
requirements:
  - SPL-01
  - SPL-03

must_haves:
  truths:
    - "`from src.ui.splash import render_splash` succeeds; `render_splash` is a callable with no required positional args."
    - "The HTML string produced by `render_splash` contains the verbatim wordmark `SNOWGREP`, tagline `INCIDENT INTELLIGENCE`, and status label `LOADING YOUR DATA` (all three exact strings)."
    - "The HTML string contains EB Garamond / Inter / JetBrains Mono via the same Google Fonts import URL used by `LORO_PIANA_CSS` (component runs in an iframe so it loads fonts itself)."
    - "The HTML string contains all four brand hex values consumed from `LORO_PIANA_TOKENS` — `#F5F0EB` (bg), `#2C2420` (text), `#8A7A6B` (text_subtle), `#B8A88A` (gold_decorative) — and `src/ui/splash.py` contains zero literal brand hex constants (every brand color is string-interpolated from `LORO_PIANA_TOKENS`)."
    - "The HTML string contains 16 synthetic INC IDs (8 per stream) generated once at module load with a fixed `random.Random(seed)` so the same IDs render across reruns inside a session."
    - "The HTML string contains a `@media (prefers-reduced-motion: reduce)` block that disables `translate` keyframes on the INC ID elements and keeps only opacity animation — wordmark/tagline/status label are NOT inside any reduced-motion override (they render identically in both modes)."
    - "The HTML string contains a CSS rule `.splash { transition: opacity 400ms ...; }` (matches CONTEXT.md line 48 — `--lp-transition-slow`) and a `.splash.is-dismissing { opacity: 0; }` rule, so adding the `is-dismissing` class triggers the locked 400ms fade-out."
    - "The HTML string contains a `<script>` block that owns ALL client-side splash timing: (1) `setTimeout(800ms)` sets an internal `readyToDismiss` flag (soft floor — CONTEXT.md line 46); (2) `setTimeout(4000ms)` adds `.is-dismissing` to `.splash` (hard cap — CONTEXT.md line 47 / SPL-02); (3) `window.addEventListener('message', ...)` listens for a parent-sent `{type:'snowgrep-splash-dismiss'}` postMessage and adds `.is-dismissing` — but defers if elapsed < 800ms until the floor is hit."
    - "Calling `render_splash()` invokes `streamlit.components.v1.html(html_str, height=N, scrolling=False)` once — verified by a unit-style smoke that monkey-patches `streamlit.components.v1.html` and captures the call."
  artifacts:
    - path: "src/ui/splash.py"
      provides: "`render_splash()` — emits the self-contained helix splash via `streamlit.components.v1.html`."
      contains: "def render_splash"
      min_lines: 150
  key_links:
    - from: "src/ui/splash.py"
      to: "src/ui/css.py::LORO_PIANA_TOKENS"
      via: "`from src.ui.css import LORO_PIANA_TOKENS` at module top; every brand hex is `LORO_PIANA_TOKENS['<key>']` string-interpolated into the HTML/CSS — never a hex literal."
      pattern: "from src\\.ui\\.css import LORO_PIANA_TOKENS"
    - from: "src/ui/splash.py::render_splash"
      to: "streamlit.components.v1.html"
      via: "Single call inside the function with the assembled HTML string."
      pattern: "components\\.v1\\.html\\("
---

<objective>
Create `src/ui/splash.py` exporting a `render_splash()` function that emits a self-contained `streamlit.components.v1.html(...)` block — the helix-motif boot splash: two slow diagonal streams of synthetic INC IDs over a warm off-white background, "SNOWGREP" wordmark center-anchored in EB Garamond, "INCIDENT INTELLIGENCE" tagline beneath, "LOADING YOUR DATA" near the bottom.

Purpose: Lock the visual contract from `.planning/design-mockups/00-splash-helix.png` into code. Phase 7 Plan 02 wires this function into `app.py::main()`; this plan ships the component in isolation so the wiring plan can stay small and focused.

Output: One file. `src/ui/splash.py` — module-level constant for the 16 synthetic INC IDs (built once via fixed seed), plus the `render_splash()` function that string-interpolates `LORO_PIANA_TOKENS` hex values into a self-contained HTML+CSS block and hands it to `streamlit.components.v1.html`. No changes to `app.py` in this plan.
</objective>

<execution_context>
@C:/Users/taylo/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/taylo/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/07-splash-screen/07-CONTEXT.md
@.planning/design-mockups/00-splash-helix.png
@src/ui/css.py
</context>

<tasks>

<task type="auto" id="1">
  <name>Task 1: Generate synthetic INC IDs at module load + draft helix HTML template</name>
  <files>src/ui/splash.py</files>
  <action>
Create `src/ui/splash.py`. Module structure (in order):

1. **Module docstring:**

```python
"""SNOWGREP boot splash — helix-motif loading interlude (v2.2 Phase 7).

This module exports a single function: `render_splash()`. It emits a fully
self-contained HTML/CSS block via `streamlit.components.v1.html` — the
splash component lives in an iframe and CANNOT inherit the parent app's
CSS custom properties, so every brand color is string-interpolated from
`LORO_PIANA_TOKENS` at render time (NEVER a hex literal in this file).

Visual contract: .planning/design-mockups/00-splash-helix.png
Locked text:  wordmark "SNOWGREP", tagline "INCIDENT INTELLIGENCE",
              status label "LOADING YOUR DATA" — all three verbatim.

The 16 synthetic INC IDs are generated once at module load with a fixed
seed so reruns inside a single Python process are reproducible.
"""
```

2. **Imports + future annotations:**

```python
from __future__ import annotations

import random
import streamlit.components.v1 as components

from src.ui.css import LORO_PIANA_TOKENS
```

`from src.ui.css import LORO_PIANA_TOKENS` is LOAD-BEARING. The brand color invariant is: every brand hex inside the component HTML/CSS is `LORO_PIANA_TOKENS['<key>']` string-interpolated — never a literal `#F5F0EB` / `#2C2420` / `#8A7A6B` / `#B8A88A` typed in `src/ui/splash.py`. The smoke test in Task 2 enforces this.

3. **Module-level constant — synthetic INC IDs (built once, fixed seed):**

```python
# Synthetic INC IDs are built once at module load with a fixed seed so the
# splash is reproducible across reruns inside a session. INC + 7 zero-padded
# digits matches ServiceNow's recognizable format. Real data isn't loaded
# when the splash renders, and synthetic IDs protect privacy in screenshots.
_RNG = random.Random(20260522)  # fixed seed → reproducible
_INC_IDS: tuple[str, ...] = tuple(
    f"INC{_RNG.randint(0, 9_999_999):07d}" for _ in range(16)
)
```

8 IDs feed Stream A (top-left → bottom-right, ~-20°); the next 8 feed Stream B (top-right → bottom-left, ~+20°). Slicing is done inside `render_splash()` (Task 2).

4. **The `render_splash()` function** — build the HTML string and call `components.v1.html`. Skeleton:

```python
def render_splash() -> None:
    """Emit the helix-motif splash via streamlit.components.v1.html.

    Self-contained: loads its own fonts, defines its own CSS keyframes, and
    interpolates brand hex values from LORO_PIANA_TOKENS. Called once per
    browser session from `app.py::main()` (Plan 02 wires the session-gating
    and the data-ready dismiss logic).
    """
    # Pull brand hex values from the single source of truth (LORO_PIANA_TOKENS).
    # NEVER hard-code these — the smoke test in tests / verification asserts
    # zero literal brand hex in this file.
    bg          = LORO_PIANA_TOKENS["bg"]              # "#F5F0EB"
    text        = LORO_PIANA_TOKENS["text"]            # "#2C2420"
    text_subtle = LORO_PIANA_TOKENS["text_subtle"]     # "#8A7A6B"
    gold        = LORO_PIANA_TOKENS["gold_decorative"] # "#B8A88A"

    stream_a = _INC_IDS[:8]
    stream_b = _INC_IDS[8:]

    # ... build HTML string ...

    components.v1.html(html, height=720, scrolling=False)
```

For Task 1, draft the HTML/CSS string scaffolding inside `render_splash()` with the THREE locked verbatim strings + the four token interpolations wired up, but the keyframe animations and per-ID staggers can be approximate / placeholder. The HTML must include:

- A full document fragment starting with `<!DOCTYPE html><html><head>` so it works inside `components.v1.html`'s iframe.
- A `<style>` block that begins with:
  ```css
  @import url('https://fonts.googleapis.com/css2?family=EB+Garamond:wght@300;400&family=Inter:wght@400;500&family=JetBrains+Mono:wght@400;500&display=swap');
  ```
  (Same `@import` URL used in `src/ui/css.py` — the iframe loads its own fonts since CSS variables can't cross the boundary.)
- A `:root` block inside the `<style>` that mirrors the four needed token values via local CSS custom props (e.g., `--lp-bg: {bg};`) so the rest of the CSS references `var(--lp-bg)` for readability — Python f-string interpolates the four hex values into the four `:root` declarations and nowhere else.
- A `.splash` container: full-viewport, `background: var(--lp-bg)`, `position: relative`, `overflow: hidden`.
- A `.wordmark` element with the literal text `SNOWGREP`, EB Garamond, weight 300, ~64px, `color: var(--lp-text)`, `letter-spacing: 0.02em`, center-anchored (absolute positioning with `top: 50%; left: 50%; transform: translate(-50%, -50%);`).
- A `.tagline` element with the literal text `INCIDENT INTELLIGENCE`, Inter weight 500, 11px, `text-transform: uppercase`, `letter-spacing: 0.15em`, `color: var(--lp-gold)`, positioned ~12px beneath the wordmark.
- A `.status` element with the literal text `LOADING YOUR DATA`, same type treatment as tagline (Inter 500, 11px, uppercase, 0.15em tracking, `color: var(--lp-gold)`), positioned near `top: 80%`.
- Two `<div class="stream stream-a">` and `<div class="stream stream-b">` containers, each holding 8 `<span class="inc-id">` elements rendered from `stream_a` / `stream_b` (use a Python list comprehension building HTML fragments with f-strings).

Inline styles per INC ID may carry the diagonal position and stagger delay — keyframe motion is finalized in Task 2.

**Interpolation strategy — LOCKED to `.format(**locals())`. Do NOT use f-strings for the HTML/CSS template.**

The HTML template is 150+ lines of CSS containing dozens of `{...}` selector blocks. Under f-strings, every CSS brace must be escaped as `{{` / `}}` — a single missed escape produces silently broken CSS that still parses Python-side. To eliminate this footgun:

1. Build the HTML/CSS as one large triple-quoted plain string (NOT an f-string — no `f""" ... """` prefix).
2. Use `{bg}`, `{text}`, `{text_subtle}`, `{gold}`, `{stream_a_html}`, `{stream_b_html}` (and any other Python-side computed values) as the ONLY `{...}` placeholders.
3. CSS braces remain single (`.splash { ... }`) — they pass through `.format()` untouched because the CSS doesn't contain any `{name}` patterns that collide with our placeholders.
4. At the bottom of `render_splash()`, do exactly one substitution: `html = template.format(**locals())`.
5. If any computed value's name collides with a CSS token (e.g., never name a local `keyframes`), rename the local. The `str.format()` placeholder set is the union of `{bg, text, text_subtle, gold, stream_a_html, stream_b_html}` — keep it tight.

The smoke test in Task 2 step #5 catches broken interpolation by asserting the four brand hexes + three locked strings are present in the rendered HTML, so any escape bug fails the verify step loudly.
  </action>
  <verify>
1. `python -c "from src.ui.splash import render_splash, _INC_IDS; assert callable(render_splash); assert len(_INC_IDS) == 16; assert all(s.startswith('INC') and len(s) == 10 and s[3:].isdigit() for s in _INC_IDS); print('OK', _INC_IDS[:3])"` prints `OK` plus three INC IDs.

2. `python -c "import random; r = random.Random(20260522); ids = tuple(f'INC{r.randint(0, 9_999_999):07d}' for _ in range(16)); from src.ui.splash import _INC_IDS; assert _INC_IDS == ids; print('seed reproducible')"` prints `seed reproducible` — confirming the seed/length contract from CONTEXT.md.

3. `grep -c "SNOWGREP\|INCIDENT INTELLIGENCE\|LOADING YOUR DATA" src/ui/splash.py` returns at least 3 (one match per locked string).

4. `grep -E "'#F5F0EB'|'#2C2420'|'#8A7A6B'|'#B8A88A'|\"#F5F0EB\"|\"#2C2420\"|\"#8A7A6B\"|\"#B8A88A\"" src/ui/splash.py` returns NO matches — brand hex literals must not appear in the file (every brand color is `LORO_PIANA_TOKENS['<key>']` string-interpolated at runtime).

5. `python -c "from src.ui.css import LORO_PIANA_TOKENS; print(LORO_PIANA_TOKENS['bg'], LORO_PIANA_TOKENS['text'], LORO_PIANA_TOKENS['text_subtle'], LORO_PIANA_TOKENS['gold_decorative'])"` prints `#F5F0EB #2C2420 #8A7A6B #B8A88A` — confirms the token keys this plan consumes exist and resolve as expected.
  </verify>
  <done>
`src/ui/splash.py` exists. The three locked verbatim strings appear in the file. `_INC_IDS` is a 16-element tuple of `INC` + 7-digit IDs generated from `random.Random(20260522)`. `render_splash` is callable. No literal brand hex appears in the file — every brand color is sourced from `LORO_PIANA_TOKENS`.
  </done>
</task>

<task type="auto" id="2">
  <name>Task 2: Add helix CSS keyframes (motion + reduced-motion variant) and finalize the `components.v1.html` call</name>
  <files>src/ui/splash.py</files>
  <action>
Extend the HTML/CSS string built in Task 1 with the helix animation system, then finalize the `components.v1.html(html, height=N, scrolling=False)` call.

**A. Stream geometry + per-ID positions.**

Stream A (top-left → bottom-right, ~-20° from horizontal). Stream B (top-right → bottom-left, ~+20°). For each of the 8 IDs per stream, compute a starting position along its diagonal axis at module-load time using the same `_RNG` instance from Task 1 (or extend the seed sequence). Each ID needs:

- A starting `left` and `top` in viewport-percent units (so the splash scales with the iframe height).
- A perpendicular jitter (~±60px) so IDs don't form a perfectly straight line.
- A stagger delay (0-6s) so the canvas always has some IDs visible and some fading.

Build a Python list (or dict) of position records at module level and emit them as inline `style="left: X%; top: Y%; animation-delay: Zs;"` on each `<span class="inc-id">`. Keep these helpers private (`_compute_stream_positions()` or similar) — only `render_splash` and `_INC_IDS` should be considered the public surface.

**Center exclusion zone:** clamp positions so no INC ID lands inside a ~300px × ~140px rectangle around the wordmark (viewport-percent equivalent assuming `height=720`). The simplest implementation: for each candidate position, if it falls inside the exclusion rectangle, push it outward along the stream's diagonal until it exits.

**B. CSS keyframes (motion variant):**

```css
@keyframes helix-drift-a {
  0%   { opacity: 0; transform: translate(0, 0); }
  20%  { opacity: 0.6; }
  80%  { opacity: 0.6; }
  100% { opacity: 0; transform: translate(120px, -42px); }
  /* 120px along the -20° diagonal ≈ (cos -20° × 128, sin -20° × 128) */
}
@keyframes helix-drift-b {
  0%   { opacity: 0; transform: translate(0, 0); }
  20%  { opacity: 0.6; }
  80%  { opacity: 0.6; }
  100% { opacity: 0; transform: translate(-120px, -42px); }
  /* mirrored for +20° diagonal */
}

.stream-a .inc-id {
  animation: helix-drift-a 7s var(--lp-easing-smooth, cubic-bezier(0.4, 0, 0.2, 1)) infinite;
}
.stream-b .inc-id {
  animation: helix-drift-b 7s var(--lp-easing-smooth, cubic-bezier(0.4, 0, 0.2, 1)) infinite;
}

.inc-id {
  position: absolute;
  font-family: 'JetBrains Mono', 'Consolas', 'Courier New', monospace;
  font-size: 11px;
  color: var(--lp-text-subtle);
  opacity: 0;
  pointer-events: none;
  white-space: nowrap;
  /* per-element animation-delay set inline (staggered 0..6s) */
}
```

Loop duration 6-8s, easing `cubic-bezier(0.4, 0, 0.2, 1)` (matches `--lp-easing-smooth` in `LORO_PIANA_CSS`). The translation is ~120px along the diagonal (subtle drift, ~15-20px/sec). Color is `var(--lp-text-subtle)` (which is `#8A7A6B` — interpolated into the `:root` block, NOT typed as a literal).

**C. Reduced-motion variant — CRITICAL for SPL-03:**

```css
@media (prefers-reduced-motion: reduce) {
  @keyframes helix-fade {
    0%   { opacity: 0; }
    30%  { opacity: 0.4; }
    70%  { opacity: 0.4; }
    100% { opacity: 0; }
  }
  .stream-a .inc-id,
  .stream-b .inc-id {
    animation: helix-fade 11s ease-in-out infinite !important;
    transform: none !important;  /* override any translate */
  }
}
```

Key contract: under `prefers-reduced-motion: reduce`, INC IDs fade in/out at FIXED positions (no `translate` keyframes), the opacity loop is slowed to 10-12s, and max opacity is capped at 0.4. The `!important` flags are necessary because the motion-variant animation rules win specificity-wise otherwise.

Wordmark, tagline, and status label MUST render identically in both modes — they have no animation, so they need no reduced-motion override. Verify the `@media` block only touches `.stream-a .inc-id` and `.stream-b .inc-id`.

**D. Client-side dismiss timing — owns ALL timing (CONTEXT.md lines 44-48).**

The splash is mounted in an iframe (`streamlit.components.v1.html`). Streamlit's Python side cannot reliably re-render on a wall-clock timer — reruns only happen on user interaction or session_state mutation. So ALL timing-critical splash behavior (soft floor, hard cap, fade-out) lives client-side inside this iframe. The Python side (Plan 02) is a one-shot mount + a dismiss-signal sender.

**D.1. CSS fade-out rule** — add to the `<style>` block alongside the `.splash` container rule:

```css
.splash {
  /* ... existing rules ... */
  opacity: 1;
  transition: opacity 400ms cubic-bezier(0.4, 0, 0.2, 1);
}
.splash.is-dismissing {
  opacity: 0;
}
```

400ms matches CONTEXT.md line 48 (`--lp-transition-slow`). The cubic-bezier matches `--lp-easing-smooth`. The reduced-motion variant does NOT override this — per CONTEXT.md line 56, "400ms fade-out on dismiss retained (low motion budget, doesn't trigger vestibular concerns)."

**D.2. Inline `<script>` block** — add IMMEDIATELY BEFORE `</body>` in the HTML template:

```html
<script>
  (function() {
    var splash = document.querySelector('.splash');
    var mountedAt = Date.now();
    var readyToDismiss = false;
    var dismissPending = false;
    var FLOOR_MS = 800;   // CONTEXT.md line 46 — soft floor
    var CAP_MS = 4000;    // CONTEXT.md line 47 / SPL-02 — hard cap

    function doDismiss() {
      if (splash && !splash.classList.contains('is-dismissing')) {
        splash.classList.add('is-dismissing');
      }
    }

    // Soft floor: after 800ms, flag readyToDismiss. If a dismiss signal
    // arrived earlier, it set dismissPending — fire it now.
    setTimeout(function() {
      readyToDismiss = true;
      if (dismissPending) doDismiss();
    }, FLOOR_MS);

    // Hard cap: at 4000ms, fade regardless of any external signal.
    setTimeout(function() {
      doDismiss();
    }, CAP_MS);

    // External dismiss signal from parent (Plan 02 sends this when
    // data_loaded AND embeddings_ready are both true).
    window.addEventListener('message', function(ev) {
      if (!ev.data || ev.data.type !== 'snowgrep-splash-dismiss') return;
      var elapsed = Date.now() - mountedAt;
      if (elapsed >= FLOOR_MS) {
        doDismiss();
      } else {
        dismissPending = true;  // floor-timer will fire it at 800ms
      }
    });
  })();
</script>
```

**Notes:**
- The script is plain JS, no dependencies, runs synchronously after `.splash` is in the DOM (placement before `</body>` guarantees this).
- `Date.now()` is used (not `performance.now()`) for max compatibility inside Streamlit's iframe sandbox.
- The `(function(){ ... })()` IIFE keeps `mountedAt` / `readyToDismiss` / `dismissPending` out of any global namespace.
- The postMessage payload shape (`{type: 'snowgrep-splash-dismiss'}`) is the contract Plan 02 will produce. Keep this string stable.
- Adding `is-dismissing` triggers the CSS `transition: opacity 400ms`. The iframe still occupies its placeholder for those 400ms; Plan 02's Python side sleeps 400ms before clearing the placeholder so the fade visibly completes.
- Under reduced-motion, the 400ms fade IS retained per CONTEXT.md line 56. No special handling needed.

This script must be INSIDE the same template as the HTML — interpolated via `.format(**locals())` along with everything else. The script contains no Python placeholders, but the curly braces in JS function bodies (`function() { ... }`) are fine under `.format()` because none of them collide with the placeholder names (`{bg}`, `{text}`, etc.).

**Footgun — JS object literals DO collide with `.format()`:** the postMessage payload comparison `ev.data.type !== 'snowgrep-splash-dismiss'` is safe because it has no `{...}` around it, but if you write a literal object such as `{type: 'snowgrep-splash-dismiss'}` anywhere in the script, Python's `.format()` will read `{type}` as a placeholder named `type` and raise `KeyError: 'type'` at module import. Fix by either (a) escaping the literal as `{{type: 'snowgrep-splash-dismiss'}}`, or (b) assigning the dispatch type to a JS `const` at the top of the IIFE so the `{key:` shape never appears inside the formatted template body. Recommended: option (b) — declare `const DISMISS_TYPE = 'snowgrep-splash-dismiss';` once, then compare via `ev.data.type !== DISMISS_TYPE`. Verify step #7's smoke test would catch a missed escape at import time, but pre-empting is cheaper.

**E. Finalize `components.v1.html(...)` call:**

```python
components.v1.html(html, height=720, scrolling=False)
```

`height=720` is the canonical splash viewport height — adjust within 600-820 if visual mockup match requires it. `scrolling=False` is required so the splash never grows scrollbars inside its iframe even if the user resizes weirdly.

**E. Public surface stays minimal.** Module exports:

```python
__all__ = ["render_splash"]
```

`_INC_IDS` and any position-helper functions stay underscore-prefixed (private).

**Non-goals (do NOT add in this plan):**

- Do NOT add session-state checks, `_splash_shown` gating, `data_loaded` / `embeddings_ready` polling, or `placeholder.empty()` calls — that's Plan 02's contract.
- Do NOT import `streamlit as st` — only `streamlit.components.v1` is needed.
- Do NOT add unit tests in this plan (tests are TST-02 work in Phase 11).
- Do NOT add a Python-side `time.sleep` or wall-clock check for the 4s cap — the cap lives entirely in the iframe's `<script>` block (section D.2).
  </action>
  <verify>
1. `python -c "from src.ui.splash import render_splash; import inspect; src = inspect.getsource(render_splash); assert 'components.v1.html' in src or 'components.html' in src; assert 'prefers-reduced-motion' in src or 'reduced-motion' in src; print('OK')"` prints `OK` — proves the iframe call site and the reduced-motion media query are wired.

2. `grep -c "@keyframes" src/ui/splash.py` returns at least 2 (one motion keyframe per stream, plus the reduced-motion fade keyframe inside the media query — count may be 3).

3. `grep -c "prefers-reduced-motion: reduce" src/ui/splash.py` returns exactly 1.

4. `grep -E "'#F5F0EB'|'#2C2420'|'#8A7A6B'|'#B8A88A'|\"#F5F0EB\"|\"#2C2420\"|\"#8A7A6B\"|\"#B8A88A\"" src/ui/splash.py` returns NO matches — re-verifying the brand-hex-literal invariant after adding keyframes.

5. Smoke that `render_splash` actually calls `components.v1.html` exactly once:
```
python -c "
import sys, types
calls = []
class FakeComponents:
    @staticmethod
    def html(html, **kwargs): calls.append((html, kwargs))
# Monkey-patch BEFORE importing splash so the module-level import binds to the fake.
fake_pkg = types.ModuleType('streamlit.components.v1')
fake_pkg.html = FakeComponents.html
sys.modules['streamlit.components.v1'] = fake_pkg
fake_root = types.ModuleType('streamlit.components')
fake_root.v1 = fake_pkg
sys.modules['streamlit.components'] = fake_root
# Also stub streamlit so the import doesn't pull the full package.
sys.modules.setdefault('streamlit', types.ModuleType('streamlit'))
from src.ui.splash import render_splash
render_splash()
assert len(calls) == 1, f'expected 1 components.v1.html call, got {len(calls)}'
html, kwargs = calls[0]
for needle in ('SNOWGREP', 'INCIDENT INTELLIGENCE', 'LOADING YOUR DATA', '#F5F0EB', '#2C2420', '#B8A88A', '#8A7A6B', 'prefers-reduced-motion'):
    assert needle in html, f'missing: {needle!r}'
print('OK: 1 call, all 3 verbatim strings + 4 brand hexes + reduced-motion present')
"
```
Prints `OK: 1 call, all 3 verbatim strings + 4 brand hexes + reduced-motion present`.

6. `grep -c "JetBrains Mono" src/ui/splash.py` returns at least 1 (the INC IDs use mono — Phase 6 mono-boundary exception for data identifiers).

7. Client-side timing + fade-out invariants (CONTEXT.md lines 44-48). The smoke from step 5 produced `html`; extend it (or re-run with these extra asserts after the existing ones):

```
python -c "
import sys, types
calls = []
class FakeComponents:
    @staticmethod
    def html(html, **kwargs): calls.append((html, kwargs))
fake_pkg = types.ModuleType('streamlit.components.v1')
fake_pkg.html = FakeComponents.html
sys.modules['streamlit.components.v1'] = fake_pkg
fake_root = types.ModuleType('streamlit.components')
fake_root.v1 = fake_pkg
sys.modules['streamlit.components'] = fake_root
sys.modules.setdefault('streamlit', types.ModuleType('streamlit'))
from src.ui.splash import render_splash
render_splash()
html, _ = calls[0]
# CSS fade-out rule
assert 'transition: opacity 400ms' in html, 'missing 400ms opacity transition (CONTEXT.md line 48)'
assert 'is-dismissing' in html, 'missing .is-dismissing class for fade-out trigger'
# Client-side timing script
assert '<script>' in html, 'missing inline <script> for client-side timing'
assert '800' in html, 'missing 800ms soft-floor literal (CONTEXT.md line 46)'
assert '4000' in html, 'missing 4000ms hard-cap literal (CONTEXT.md line 47 / SPL-02)'
assert 'snowgrep-splash-dismiss' in html, 'missing postMessage contract string'
assert 'addEventListener' in html and 'message' in html, 'missing postMessage listener'
print('OK: client-side timing + 400ms fade-out present')
"
```
Prints `OK: client-side timing + 400ms fade-out present`.
  </verify>
  <done>
`render_splash()` emits a self-contained HTML document containing: the three locked verbatim strings, all four `LORO_PIANA_TOKENS` brand hex values (interpolated, not literal), 16 INC IDs split into two diagonal streams, motion-variant keyframes with ~120px translation + 6-8s loop, a `prefers-reduced-motion: reduce` media query that disables translation and slows opacity loop to 10-12s with max 0.4 opacity, a `.splash { transition: opacity 400ms }` + `.splash.is-dismissing { opacity: 0 }` CSS pair, and an inline `<script>` block that owns the 800ms soft floor, the 4000ms hard cap, and a `message` listener for the `snowgrep-splash-dismiss` postMessage contract. The function makes exactly one `streamlit.components.v1.html(...)` call with `scrolling=False`. No brand hex literals in the source.
  </done>
</task>

</tasks>

<verification>
From project root:

```
python -c "from src.ui.splash import render_splash, _INC_IDS; print(len(_INC_IDS), callable(render_splash))"
```

Expected: `16 True`.

```
grep -c "SNOWGREP\|INCIDENT INTELLIGENCE\|LOADING YOUR DATA" src/ui/splash.py
```

Expected: at least 3.

```
grep -c "prefers-reduced-motion" src/ui/splash.py
```

Expected: exactly 1.

Brand-hex-literal absence check (must return zero matches):

```
grep -E "'#F5F0EB'|'#2C2420'|'#8A7A6B'|'#B8A88A'|\"#F5F0EB\"|\"#2C2420\"|\"#8A7A6B\"|\"#B8A88A\"" src/ui/splash.py
```

Expected: no output (exit code 1 = no matches found, which is the pass condition).
</verification>

<success_criteria>
- `src/ui/splash.py` exists and is importable.
- Exports `render_splash` (callable, no required args).
- Exports `_INC_IDS` (private, 16 elements, INC + 7-digit format, fixed-seed reproducible).
- Calling `render_splash()` invokes `streamlit.components.v1.html(html_str, height=N, scrolling=False)` exactly once.
- The HTML contains the three locked verbatim strings: `SNOWGREP`, `INCIDENT INTELLIGENCE`, `LOADING YOUR DATA`.
- The HTML contains the four required brand hex values from `LORO_PIANA_TOKENS` — `#F5F0EB`, `#2C2420`, `#8A7A6B`, `#B8A88A` — and `src/ui/splash.py` contains zero brand hex literals (every brand color is interpolated from `LORO_PIANA_TOKENS`).
- The CSS contains motion keyframes (~120px translation per stream, 6-8s loop, easing `cubic-bezier(0.4, 0, 0.2, 1)`).
- The CSS contains a `@media (prefers-reduced-motion: reduce)` block that overrides only the INC ID animations (not the wordmark/tagline/status) — disables `translate`, slows opacity loop to 10-12s, caps max opacity at 0.4.
- The CSS contains `.splash { transition: opacity 400ms ...; }` + `.splash.is-dismissing { opacity: 0; }` — the locked 400ms fade-out from CONTEXT.md line 48.
- The HTML contains an inline `<script>` block that owns ALL client-side splash timing: 800ms soft floor (CONTEXT.md line 46), 4000ms hard cap (CONTEXT.md line 47 / SPL-02), and a `postMessage` listener for `{type: 'snowgrep-splash-dismiss'}` that adds `.is-dismissing` (deferring until the 800ms floor if signaled earlier).
- Satisfies SPL-01 (component emits the helix via `streamlit.components.v1.html`), SPL-02 (4s hard cap enforced client-side regardless of Python rerun cadence), and SPL-03 (reduced-motion variant).
- Does NOT satisfy SPL-04 (`_splash_shown` session gating) — that's Plan 02's contract.
</success_criteria>

<output>
After completion, create `.planning/phases/07-splash-screen/07-01-SUMMARY.md` documenting:
- Final file path and line count for `src/ui/splash.py`.
- The 16 INC IDs generated by the fixed seed (so future debugging can spot drift).
- Confirmation that the verification checks all pass.
- Confirmation that zero brand hex literals appear in the source.
- Any deviations from 07-CONTEXT.md (expected: none).
</output>
