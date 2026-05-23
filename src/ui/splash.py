"""SNOWGREP boot splash -- helix-motif loading interlude (v2.2 Phase 7).

This module exports a single function: `render_splash()`. It emits a fully
self-contained HTML/CSS block via `streamlit.components.v1.html` -- the
splash component lives in an iframe and CANNOT inherit the parent app's
CSS custom properties, so every brand color is string-interpolated from
`LORO_PIANA_TOKENS` at render time (NEVER a hex literal in this file).

Visual contract: .planning/design-mockups/00-splash-helix.png
Locked text:  wordmark "SNOWGREP", tagline "INCIDENT INTELLIGENCE",
              status label "LOADING YOUR DATA" -- all three verbatim.

The 16 synthetic INC IDs are generated once at module load with a fixed
seed so reruns inside a single Python process are reproducible.
"""

from __future__ import annotations

import random
import streamlit.components.v1 as components

from src.ui.css import LORO_PIANA_TOKENS

# ---------------------------------------------------------------------------
# Synthetic INC IDs -- built once at module load with a fixed seed so the
# splash is reproducible across reruns inside a session. INC + 7 zero-padded
# digits matches ServiceNow's recognizable format. Real data isn't loaded
# when the splash renders, and synthetic IDs protect privacy in screenshots.
# ---------------------------------------------------------------------------
_RNG = random.Random(20260522)  # fixed seed -> reproducible
_INC_IDS: tuple[str, ...] = tuple(
    f"INC{_RNG.randint(0, 9_999_999):07d}" for _ in range(16)
)


def _compute_stream_positions(
    rng: random.Random,
) -> tuple[list[dict], list[dict]]:
    """Compute per-ID viewport-percent positions for both streams.

    Returns (stream_a_positions, stream_b_positions) where each item is a
    dict with keys ``left``, ``top``, ``delay`` used to build inline styles.

    Stream A: top-left -> bottom-right (~-20 deg from horizontal).
    Stream B: top-right -> bottom-left (~+20 deg from horizontal).

    Center exclusion zone: ~300px x 140px rectangle around the wordmark
    (assumed iframe height=720, wordmark at 50% height, 50% width).
    Exclusion bounds in viewport-percent: left 27-73%, top 38-58%.
    Any position landing inside is pushed along the stream diagonal.
    """
    EXCL_LEFT_MIN = 27.0
    EXCL_LEFT_MAX = 73.0
    EXCL_TOP_MIN = 38.0
    EXCL_TOP_MAX = 58.0

    def _in_exclusion(left: float, top: float) -> bool:
        return (
            EXCL_LEFT_MIN <= left <= EXCL_LEFT_MAX
            and EXCL_TOP_MIN <= top <= EXCL_TOP_MAX
        )

    def _push_out_a(left: float, top: float) -> tuple[float, float]:
        """Push Stream A position along its diagonal until outside exclusion."""
        # Stream A goes top-left -> bottom-right; push in the negative direction
        # (towards top-left) by 15% increments until clear.
        step = 0
        while _in_exclusion(left, top) and step < 10:
            left -= 15.0
            top -= 5.4  # approx tan(20 deg) * 15
            step += 1
        return left, top

    def _push_out_b(left: float, top: float) -> tuple[float, float]:
        """Push Stream B position along its diagonal until outside exclusion."""
        # Stream B goes top-right -> bottom-left; push towards top-right.
        step = 0
        while _in_exclusion(left, top) and step < 10:
            left += 15.0
            top -= 5.4
            step += 1
        return left, top

    stream_a: list[dict] = []
    stream_b: list[dict] = []

    # Stream A: distribute 8 IDs along the -20 deg diagonal
    for i in range(8):
        # Base position along the diagonal: spread evenly 5-95% of viewport
        t = 5.0 + (90.0 / 7.0) * i  # parameter 0-100 along diagonal
        # -20 deg from horizontal: left increases ~cos(20) faster than top ~sin(20)
        left = t * 0.94  # cos(20 deg) ~ 0.94
        top = t * 0.34 + rng.uniform(-6, 6)  # sin(20 deg) ~ 0.34 + jitter
        # Perpendicular jitter (~+-60px, scaled to viewport percent for ~1200px wide)
        jitter = rng.uniform(-5.0, 5.0)
        left = max(1.0, min(95.0, left + jitter))
        top = max(2.0, min(92.0, top))
        if _in_exclusion(left, top):
            left, top = _push_out_a(left, top)
        delay = rng.uniform(0.0, 6.0)
        stream_a.append({
            "left": round(left, 1),
            "top": round(top, 1),
            "delay": round(delay, 2),
        })

    # Stream B: distribute 8 IDs along the +20 deg diagonal (top-right -> bottom-left)
    for i in range(8):
        t = 5.0 + (90.0 / 7.0) * i
        left = 95.0 - t * 0.94
        top = t * 0.34 + rng.uniform(-6, 6)
        jitter = rng.uniform(-5.0, 5.0)
        left = max(1.0, min(95.0, left + jitter))
        top = max(2.0, min(92.0, top))
        if _in_exclusion(left, top):
            left, top = _push_out_b(left, top)
        delay = rng.uniform(0.0, 6.0)
        stream_b.append({
            "left": round(left, 1),
            "top": round(top, 1),
            "delay": round(delay, 2),
        })

    return stream_a, stream_b


# Compute positions once at module load (same RNG instance, extends seed sequence)
_STREAM_A_POS, _STREAM_B_POS = _compute_stream_positions(_RNG)


def render_splash() -> None:
    """Emit the helix-motif splash via streamlit.components.v1.html.

    Self-contained: loads its own fonts, defines its own CSS keyframes, and
    interpolates brand hex values from LORO_PIANA_TOKENS. Called once per
    browser session from `app.py::main()` (Plan 02 wires the session-gating
    and the data-ready dismiss logic).
    """
    # Pull brand hex values from the single source of truth (LORO_PIANA_TOKENS).
    # NEVER hard-code these -- the smoke test in tests / verification asserts
    # zero literal brand hex in this file.
    bg          = LORO_PIANA_TOKENS["bg"]              # warm off-white
    text        = LORO_PIANA_TOKENS["text"]            # charcoal
    text_subtle = LORO_PIANA_TOKENS["text_subtle"]     # warm gray
    gold        = LORO_PIANA_TOKENS["gold_decorative"] # muted gold

    stream_a = _INC_IDS[:8]
    stream_b = _INC_IDS[8:]

    # Build per-ID HTML fragments with inline stagger delays and positions.
    # These are pre-rendered into complete HTML strings so the main template
    # only needs two placeholders: {stream_a_html} and {stream_b_html}.
    stream_a_html = "\n".join(
        '<span class="inc-id" style="left:{left}%;top:{top}%;animation-delay:{delay}s;">'
        "{inc_id}</span>".format(
            left=pos["left"],
            top=pos["top"],
            delay=pos["delay"],
            inc_id=stream_a[i],
        )
        for i, pos in enumerate(_STREAM_A_POS)
    )

    stream_b_html = "\n".join(
        '<span class="inc-id" style="left:{left}%;top:{top}%;animation-delay:{delay}s;">'
        "{inc_id}</span>".format(
            left=pos["left"],
            top=pos["top"],
            delay=pos["delay"],
            inc_id=stream_b[i],
        )
        for i, pos in enumerate(_STREAM_B_POS)
    )

    # -----------------------------------------------------------------------
    # HTML/CSS template.
    # This is a plain triple-quoted string (NOT an f-string).
    #
    # BRACE ESCAPING RULES for str.format():
    #   - Actual Python placeholders: {bg}, {text}, {text_subtle}, {gold},
    #     {stream_a_html}, {stream_b_html} -- single braces, will be replaced.
    #   - ALL other braces (CSS rule blocks, JS function bodies, @keyframes
    #     percentages) MUST be doubled: {{ and }} to be treated as literals.
    #
    # JS object literals that would create {key: value} shapes are also avoided
    # by using a JS const for the dismiss-type string (plan option b), but even
    # so all JS {{ and }} must be doubled.
    # -----------------------------------------------------------------------
    template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    @import url('https://fonts.googleapis.com/css2?family=EB+Garamond:wght@300;400&family=Inter:wght@400;500&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Local custom properties -- hex values interpolated from LORO_PIANA_TOKENS */
    :root {{
      --lp-bg:          {bg};
      --lp-text:        {text};
      --lp-text-subtle: {text_subtle};
      --lp-gold:        {gold};
    }}

    *, *::before, *::after {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    html, body {{
      width: 100%;
      height: 100%;
      background: var(--lp-bg);
      overflow: hidden;
    }}

    /* -------- Splash container -------- */
    .splash {{
      position: relative;
      width: 100%;
      height: 100%;
      background: var(--lp-bg);
      overflow: hidden;
      opacity: 1;
      transition: opacity 400ms cubic-bezier(0.4, 0, 0.2, 1);
    }}

    .splash.is-dismissing {{
      opacity: 0;
    }}

    /* -------- Wordmark -------- */
    .wordmark {{
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      font-family: 'EB Garamond', Georgia, 'Times New Roman', serif;
      font-weight: 300;
      font-size: 64px;
      color: var(--lp-text);
      letter-spacing: 0.02em;
      line-height: 1;
      white-space: nowrap;
      z-index: 10;
      user-select: none;
    }}

    /* -------- Tagline (beneath wordmark, ~12px gap) -------- */
    .tagline {{
      position: absolute;
      top: calc(50% + 52px);
      left: 50%;
      transform: translateX(-50%);
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      font-weight: 500;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.15em;
      color: var(--lp-gold);
      white-space: nowrap;
      z-index: 10;
      user-select: none;
    }}

    /* -------- Status label (near bottom, ~80% viewport height) -------- */
    .status {{
      position: absolute;
      top: 80%;
      left: 50%;
      transform: translateX(-50%);
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      font-weight: 500;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.15em;
      color: var(--lp-gold);
      white-space: nowrap;
      z-index: 10;
      user-select: none;
    }}

    /* -------- Stream containers -------- */
    .stream {{
      position: absolute;
      inset: 0;
      pointer-events: none;
    }}

    /* -------- Individual INC ID elements (JetBrains Mono -- data identifiers) -------- */
    .inc-id {{
      position: absolute;
      font-family: 'JetBrains Mono', 'Consolas', 'Courier New', monospace;
      font-size: 11px;
      color: var(--lp-text-subtle);
      opacity: 0;
      pointer-events: none;
      white-space: nowrap;
    }}

    /* -------- Motion keyframes -- ~120px diagonal drift over 7s loop -------- */
    @keyframes helix-drift-a {{
      0%   {{ opacity: 0; transform: translate(0, 0); }}
      20%  {{ opacity: 0.6; }}
      80%  {{ opacity: 0.6; }}
      100% {{ opacity: 0; transform: translate(120px, -42px); }}
    }}

    @keyframes helix-drift-b {{
      0%   {{ opacity: 0; transform: translate(0, 0); }}
      20%  {{ opacity: 0.6; }}
      80%  {{ opacity: 0.6; }}
      100% {{ opacity: 0; transform: translate(-120px, -42px); }}
    }}

    .stream-a .inc-id {{
      animation: helix-drift-a 7s cubic-bezier(0.4, 0, 0.2, 1) infinite;
    }}

    .stream-b .inc-id {{
      animation: helix-drift-b 7s cubic-bezier(0.4, 0, 0.2, 1) infinite;
    }}

    /* -------- Reduced-motion variant (SPL-03) -------- */
    /* Wordmark, tagline, and status label are NOT inside this block --   */
    /* they render identically in both motion and reduced-motion modes.   */
    @media (prefers-reduced-motion: reduce) {{
      @keyframes helix-fade {{
        0%   {{ opacity: 0; }}
        30%  {{ opacity: 0.4; }}
        70%  {{ opacity: 0.4; }}
        100% {{ opacity: 0; }}
      }}
      .stream-a .inc-id,
      .stream-b .inc-id {{
        animation: helix-fade 11s ease-in-out infinite !important;
        transform: none !important;
      }}
    }}
  </style>
</head>
<body>
  <div class="splash" id="splash-root">

    <!-- INC ID helix streams -->
    <div class="stream stream-a">
{stream_a_html}
    </div>
    <div class="stream stream-b">
{stream_b_html}
    </div>

    <!-- Wordmark: EB Garamond weight 300, center-anchored -->
    <div class="wordmark">SNOWGREP</div>

    <!-- Tagline: Inter 500, uppercase, widest tracking, muted gold -->
    <div class="tagline">INCIDENT INTELLIGENCE</div>

    <!-- Status label: same type treatment as tagline, near bottom -->
    <div class="status">LOADING YOUR DATA</div>

  </div>

  <script>
    (function() {{
      var splash = document.querySelector('.splash');
      var mountedAt = Date.now();
      var readyToDismiss = false;
      var dismissPending = false;
      var FLOOR_MS = 800;
      var CAP_MS = 4000;
      // Declare dismiss type as a const to avoid JS object-literal syntax
      // such as {{type: 'snowgrep-splash-dismiss'}} which would collide with
      // Python str.format() parsing (plan option b).
      var DISMISS_TYPE = 'snowgrep-splash-dismiss';

      function doDismiss() {{
        if (splash && !splash.classList.contains('is-dismissing')) {{
          splash.classList.add('is-dismissing');
        }}
      }}

      // Soft floor (CONTEXT.md line 46): after 800ms, flag readyToDismiss.
      // If a dismiss signal arrived earlier it set dismissPending -- fire now.
      setTimeout(function() {{
        readyToDismiss = true;
        if (dismissPending) {{
          doDismiss();
        }}
      }}, FLOOR_MS);

      // Hard cap (CONTEXT.md line 47 / SPL-02): at 4000ms, fade regardless
      // of any external signal from the Python side.
      setTimeout(function() {{
        doDismiss();
      }}, CAP_MS);

      // External dismiss signal from parent frame (Plan 02 sends this when
      // data_loaded AND embeddings_ready are both true in session_state).
      window.addEventListener('message', function(ev) {{
        if (!ev.data || ev.data.type !== DISMISS_TYPE) return;
        var elapsed = Date.now() - mountedAt;
        if (elapsed >= FLOOR_MS) {{
          doDismiss();
        }} else {{
          dismissPending = true;
        }}
      }});
    }})();
  </script>
</body>
</html>"""

    html = template.format(**locals())
    components.html(html, height=720, scrolling=False)


__all__ = ["render_splash"]
