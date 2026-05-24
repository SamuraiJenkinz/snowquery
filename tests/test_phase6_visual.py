"""Phase 6/11 acceptance gate: prove the v2.2 visual surface holds.

Filename names FOUNDATION (Phase 6) — that's where the typography +
palette tokens live. Plan-of-record is Phase 11 (TST-02 + TST-03).

Each test function maps to one of:
  - TST-02: CSS presence (4 tests), CSS absence (2 tests), renderer
    signatures (2 tests), Altair theme registration (1 test)
  - TST-03: WCAG-AA contrast (2 tests) + negative usage scan (1 test)

Conventions inherited from tests/test_phase5_ui.py:
  - from __future__ import annotations at top
  - Module-level imports of src.ui.css / src.ui.results / src.ui.splash /
    src.ui.altair_theme — ZERO live Streamlit / HTTP / LLM
  - No class wrappers, no parametrization (one def test_* per spec assertion)
  - # --- comment dividers group tests by concern

Per Phase 11 planning, the role constraint on #6B5E52 is enforced via
usage scan, not a `< 4.5` ratio gate (the computed 5.54 ratio passes
4.5:1; the constraint is on intended usage role, not measured contrast).

Run with: `pytest tests/test_phase6_visual.py -v`
Or combined with prior phases: `pytest tests/ -v` (expected: 103 tests
total — 91 pre-Phase-11 + 12 new).
"""
from __future__ import annotations

import inspect
import re

import altair as alt

import src.ui.altair_theme  # noqa: F401 — side-effect: registers loro_piana theme
from src.ui.css import LORO_PIANA_CSS
from src.ui.results import _render_editorial_table
from src.ui.splash import render_splash


# ---------------------------------------------------------------------------
# WCAG 2.1 contrast helper (TST-03)
# ---------------------------------------------------------------------------


def _contrast_ratio(fg_hex: str, bg_hex: str) -> float:
    """Compute WCAG 2.1 contrast ratio for two #RRGGBB sRGB colors.

    Formula: (L_lighter + 0.05) / (L_darker + 0.05), where L is
    relative luminance computed from sRGB-linearized RGB channels.
    No external dependency; ~10 lines of math.
    """
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


# ---------------------------------------------------------------------------
# (a) CSS presence — TST-02 typography + palette tokens
# ---------------------------------------------------------------------------


def test_css_imports_eb_garamond():
    """EB Garamond display font must be imported in LORO_PIANA_CSS."""
    assert "EB Garamond" in LORO_PIANA_CSS, \
        "TST-02: EB Garamond import missing from LORO_PIANA_CSS"


def test_css_imports_inter():
    """Inter body font must be imported in LORO_PIANA_CSS."""
    assert "Inter" in LORO_PIANA_CSS, \
        "TST-02: Inter import missing from LORO_PIANA_CSS"


def test_css_contains_palette_muted_gold():
    """Muted gold accent token #8B7355 must appear in LORO_PIANA_CSS."""
    assert "#8B7355" in LORO_PIANA_CSS, \
        "TST-02: palette token #8B7355 (muted gold) missing"


def test_css_contains_palette_warm_beige_and_charcoal():
    """Warm-beige page background #F5F0EB and charcoal body #2C2420 must appear."""
    assert "#F5F0EB" in LORO_PIANA_CSS, \
        "TST-02: palette token #F5F0EB (warm beige) missing"
    assert "#2C2420" in LORO_PIANA_CSS, \
        "TST-02: palette token #2C2420 (charcoal) missing"


# ---------------------------------------------------------------------------
# (b) CSS absence — TST-02 brutalist palette + monospace must NOT leak
# ---------------------------------------------------------------------------


def test_css_does_not_contain_brutalist_black():
    """Brutalist near-black #0a0a0a must NOT appear in LORO_PIANA_CSS."""
    # Case-insensitive guard — #0A0A0A and #0a0a0a both forbidden.
    lowered = LORO_PIANA_CSS.lower()
    assert "#0a0a0a" not in lowered, \
        "TST-02: brutalist black #0a0a0a leaked into LORO_PIANA_CSS"


def test_stapp_block_does_not_use_jetbrains_mono():
    """The .stApp rule must NOT declare JetBrains Mono font-family."""
    # Extract the .stApp block via regex; assert JetBrains Mono is absent.
    m = re.search(r"\.stApp\s*\{[^}]*\}", LORO_PIANA_CSS)
    assert m, "TST-02: .stApp rule missing from LORO_PIANA_CSS"
    body = m.group(0)
    assert "JetBrains Mono" not in body, \
        f"TST-02: JetBrains Mono leaked into .stApp block:\n{body}"


# ---------------------------------------------------------------------------
# (c) Renderer signatures — TST-02 callable + correct module location
# ---------------------------------------------------------------------------


def test_render_editorial_table_is_callable():
    """src.ui.results._render_editorial_table must be a callable function."""
    assert callable(_render_editorial_table), \
        "TST-02: _render_editorial_table is not callable"
    # Sanity: the symbol lives in src.ui.results (not some other module)
    assert _render_editorial_table.__module__ == "src.ui.results", \
        f"TST-02: _render_editorial_table.__module__ is {_render_editorial_table.__module__!r}"


def test_render_splash_is_callable():
    """src.ui.splash.render_splash must be a callable function."""
    assert callable(render_splash), "TST-02: render_splash is not callable"
    assert render_splash.__module__ == "src.ui.splash", \
        f"TST-02: render_splash.__module__ is {render_splash.__module__!r}"


# ---------------------------------------------------------------------------
# (d) Altair theme registration — TST-02 loro_piana theme registered
# ---------------------------------------------------------------------------


def test_altair_loro_piana_theme_registered():
    """The loro_piana Altair theme must be registered via alt.theme.names().

    CRITICAL: use alt.theme.names() (Altair 6, current) — NOT the
    deprecated themes-plural namespace (removed in Altair 5+).
    The side-effect import of src.ui.altair_theme at module top
    triggers the @alt.theme.register('loro_piana', enable=True) decorator.
    """
    assert "loro_piana" in alt.theme.names(), \
        f"TST-02: 'loro_piana' theme not registered; available: {alt.theme.names()}"


# ---------------------------------------------------------------------------
# (e) WCAG-AA contrast checks — TST-03 (per Resolution 1: positive 3:1
# only for the warm-gray pair; NO upper-bound contrast assertion).
# ---------------------------------------------------------------------------


def test_wcag_body_text_passes_aa_4_5():
    """#2C2420 charcoal body on #F5F0EB warm beige must pass WCAG AA 4.5:1.

    Computed ratio is ~13.4363 — well above the 4.5:1 minimum for normal text.
    """
    ratio = _contrast_ratio("#2C2420", "#F5F0EB")
    assert ratio >= 4.5, \
        f"TST-03: body text contrast {ratio:.4f} < 4.5 (charcoal on warm beige)"


def test_wcag_warm_gray_on_beige_passes_aa_large_3():
    """#6B5E52 warm gray on #F5F0EB warm beige must pass WCAG AA 3.0:1.

    Computed ratio is ~5.5393 — passes the 3.0:1 floor for large text.
    Per Phase 11 planning (Resolution 1), the role constraint on this
    color is enforced by the negative usage scan
    (test_negative_usage_scan_var_text_muted_role_markers), NOT by a
    `< 4.5` ratio gate (the computed 5.54 ratio passes 4.5:1; the
    constraint is on intended usage role, not measured contrast).
    """
    ratio = _contrast_ratio("#6B5E52", "#F5F0EB")
    assert ratio >= 3.0, \
        f"TST-03: warm gray contrast {ratio:.4f} < 3.0 (warm gray on warm beige)"


# ---------------------------------------------------------------------------
# (f) Negative usage scan — TST-03 (per Resolution 2: scan
# `var(--lp-text-muted)` usages, not literal hex strings. For each
# rule painting in --lp-text-muted, require it ALSO declares one of:
# text-transform: uppercase | letter-spacing >= 0.1em | font-size >= 14px.
# ---------------------------------------------------------------------------

# Pseudo-element selectors whose font-size is inherited from a sibling
# parent rule. The CSS rule itself doesn't declare font-size, but the
# parent does. Allowlisted explicitly so the scan stays declarative
# and doesn't need a CSS-parent-rule lookup engine.
#
# Documented inherited font-sizes (verified against src/ui/css.py at
# planning time):
#   .lp-ghost-queries .stButton > button::before — inherits 14px from
#     .lp-ghost-queries .stButton > button (rule at ~line 879-894 sets
#     font-size: 14px on the parent).
_ROLE_MARKER_ALLOWLIST = {
    ".lp-ghost-queries .stButton > button::before",
}


def _parse_letter_spacing_em(value: str) -> float:
    """Return the em-component of a letter-spacing value, or 0.0 if not em.

    Examples:
      "0.1em"  -> 0.1
      "0.15em" -> 0.15
      "var(--lp-tracking-wider)" -> 0.0 (cannot resolve var without context)
      "1px" -> 0.0 (not em)
    """
    m = re.match(r"\s*(-?\d+(?:\.\d+)?)\s*em\s*$", value)
    return float(m.group(1)) if m else 0.0


def _parse_font_size_px(value: str) -> float:
    """Return the px-component of a font-size value, or 0.0 if not px.

    Examples:
      "14px" -> 14.0
      "var(--lp-text-label)" -> 0.0 (cannot resolve var without context)
      "1rem" -> 0.0 (not px)
    """
    m = re.match(r"\s*(\d+(?:\.\d+)?)\s*px\s*$", value)
    return float(m.group(1)) if m else 0.0


def test_negative_usage_scan_var_text_muted_role_markers():
    """Every rule painting in var(--lp-text-muted) (i.e., the warm gray
    #6B5E52) must satisfy the 'large-text-only' role contract via one of:
      - text-transform: uppercase
      - letter-spacing >= 0.1em (em-tracking large enough for label use)
      - font-size >= 14px (WCAG large-text floor)

    Note on var(--lp-tracking-wider): the token resolves to a value
    >=0.1em (verified at planning time as 0.12em); the scan treats any
    `letter-spacing: var(--lp-tracking-wider)` as satisfying the
    >=0.1em marker via TOKEN_LETTER_SPACING_OK below.

    Rules that paint in --lp-text-muted via inheritance (pseudo-elements)
    are explicitly allowlisted in _ROLE_MARKER_ALLOWLIST above.
    """
    # var(--lp-tracking-wider) is the small-caps label tracking token.
    # Treat its presence as letter-spacing >= 0.1em.
    TOKEN_LETTER_SPACING_OK = {"var(--lp-tracking-wider)"}

    # Match every CSS rule containing `color: var(--lp-text-muted)`
    # (and the no-space form `color:var(--lp-text-muted)`).
    # A rule = selector text + opening brace + body + closing brace.
    # We use a regex that captures the selector (everything up to `{`)
    # and the body (everything between `{` and `}`).
    rule_re = re.compile(
        r"([^{}\s][^{}]*?)\{([^{}]*?color\s*:\s*var\(--lp-text-muted\)[^{}]*?)\}",
        re.DOTALL,
    )

    matches = rule_re.findall(LORO_PIANA_CSS)
    assert matches, \
        "TST-03 negative usage scan: no `color: var(--lp-text-muted)` rule " \
        "found — the warm-gray paint surface is gone. Either the token was " \
        "renamed (update this test) or the entire muted-text role was removed " \
        "(rare — investigate)."

    failures: list[str] = []
    for selector_raw, body in matches:
        selector = selector_raw.strip()

        # Allowlist exact-match selectors (pseudo-elements with inherited
        # font-size from a sibling parent rule).
        if selector in _ROLE_MARKER_ALLOWLIST:
            continue

        # Marker 1: text-transform: uppercase
        if re.search(r"text-transform\s*:\s*uppercase", body):
            continue

        # Marker 2: letter-spacing >= 0.1em (literal em OR known token)
        ls_match = re.search(r"letter-spacing\s*:\s*([^;]+);", body)
        if ls_match:
            ls_value = ls_match.group(1).strip()
            if ls_value in TOKEN_LETTER_SPACING_OK:
                continue
            if _parse_letter_spacing_em(ls_value) >= 0.1:
                continue

        # Marker 3: font-size >= 14px (literal px)
        fs_match = re.search(r"font-size\s*:\s*([^;]+);", body)
        if fs_match:
            fs_value = fs_match.group(1).strip()
            if _parse_font_size_px(fs_value) >= 14.0:
                continue

        # No marker matched — record failure with context.
        failures.append(
            f"selector={selector!r}\n"
            f"  body (truncated 200ch): {body.strip()[:200]}"
        )

    assert not failures, (
        "TST-03 negative usage scan: the following CSS rules paint in "
        "var(--lp-text-muted) (i.e., #6B5E52 warm gray) but do NOT declare "
        "any of the required role markers "
        "(text-transform: uppercase | letter-spacing >= 0.1em | "
        "font-size >= 14px). Either tighten the rule, add it to "
        "_ROLE_MARKER_ALLOWLIST with rationale, or remove the muted-gray paint:\n\n"
        + "\n\n".join(failures)
    )
