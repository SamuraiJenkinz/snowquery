"""Loro Piana design tokens + CSS for SNOWGREP v2.2+.

Single source of truth for the v2.2 visual revamp. Exports:

- ``LORO_PIANA_TOKENS``: Python dict of design tokens (palette as hex strings,
  spacing/radii as integer pixels). Consume from Python code that needs
  raw values (e.g., Plotly chart styling, dynamic color decisions).

- ``LORO_PIANA_CSS``: A complete CSS string. Inject once via
  ``st.markdown(f"<style>{LORO_PIANA_CSS}</style>", unsafe_allow_html=True)``
  at the top of ``app.py``. Contains the canonical ``:root`` custom
  properties, base typographic styles, Streamlit-specific overrides, and
  the monospace boundary that confines code/data to JetBrains Mono while
  the rest of the app renders in EB Garamond (headlines) and Inter (body).

Design reference: ``C:\\Users\\taylo\\.claude\\skills\\loro-piana-aesthetic\\``.
No other module in the codebase should hardcode Loro Piana hex values or
Streamlit selector overrides — extend this file instead.
"""

from __future__ import annotations

LORO_PIANA_TOKENS: dict[str, str | int] = {
    # Palette — warm off-white background, cashmere brown accent
    "bg": "#F5F0EB",
    "surface": "#FFFFFF",
    "border": "#E8E0D8",
    "text": "#2C2420",
    "text_muted": "#6B5E52",
    "text_subtle": "#8A7A6B",
    "accent": "#8B7355",
    "accent_hover": "#A89680",
    "accent_pressed": "#6D5A42",
    "gold_decorative": "#B8A88A",
    # Semantic — muted earth equivalents
    "success": "#8A9A7D",
    "warning": "#C4A76B",
    "danger": "#A67866",
    "info": "#9B8F7D",
    # Spacing scale (px)
    "space_1": 4,
    "space_2": 8,
    "space_3": 12,
    "space_4": 16,
    "space_6": 24,
    "space_8": 32,
    "space_12": 48,
    "space_16": 64,
    # Radii (px)
    "radius_md": 4,
    "radius_lg": 8,
    "radius_full": 9999,
}


LORO_PIANA_CSS: str = """\
@import url('https://fonts.googleapis.com/css2?family=EB+Garamond:wght@300;400&family=Inter:wght@400;500&family=JetBrains+Mono:wght@400;500&display=swap');

/* Loro Piana tokens — see src/ui/css.py module docstring */

:root {
  /* ============ COLORS ============ */

  /* Primary scale — cashmere brown */
  --lp-primary-50:  #F5F0EB;
  --lp-primary-100: #E8DDD0;
  --lp-primary-200: #D4C5B0;
  --lp-primary-300: #C4B5A0;
  --lp-primary-400: #A89680;
  --lp-primary-500: #8B7355;  /* PRIMARY */
  --lp-primary-600: #6D5A42;
  --lp-primary-700: #4F4130;

  /* Neutral scale — warm grays */
  --lp-neutral-0:   #FFFFFF;
  --lp-neutral-50:  #F5F0EB;  /* BACKGROUND */
  --lp-neutral-100: #EDE6DD;
  --lp-neutral-200: #E8E0D8;  /* borders */
  --lp-neutral-300: #D4CBC0;
  --lp-neutral-400: #B8A88A;  /* decorative only */
  --lp-neutral-500: #8A7A6B;
  --lp-neutral-600: #6B5E52;  /* secondary text */
  --lp-neutral-700: #4A3F36;
  --lp-neutral-800: #2C2420;  /* primary text */
  --lp-neutral-900: #1A1410;

  /* Semantic — muted earth equivalents */
  --lp-success: #8A9A7D;  /* sage */
  --lp-warning: #C4A76B;  /* amber */
  --lp-danger:  #A67866;  /* terracotta */
  --lp-info:    #9B8F7D;  /* taupe */

  /* Aliases for common use */
  --lp-bg:          var(--lp-neutral-50);
  --lp-surface:     var(--lp-neutral-0);
  --lp-border:      var(--lp-neutral-200);
  --lp-text:        var(--lp-neutral-800);
  --lp-text-muted:  var(--lp-neutral-600);
  --lp-text-subtle: var(--lp-neutral-500);
  --lp-accent:      var(--lp-primary-500);

  /* ============ TYPOGRAPHY ============ */

  --lp-font-headline: 'EB Garamond', Georgia, 'Times New Roman', serif;
  --lp-font-body: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --lp-font-mono: 'JetBrains Mono', 'Consolas', 'Courier New', monospace;

  /* Type scale */
  --lp-text-display: 48px;
  --lp-text-h1: 36px;
  --lp-text-h2: 28px;
  --lp-text-h3: 22px;
  --lp-text-h4: 18px;
  --lp-text-body-size: 16px;
  --lp-text-small: 14px;
  --lp-text-xs: 12px;
  --lp-text-label: 11px;

  /* Letter spacing */
  --lp-tracking-tight: -0.02em;
  --lp-tracking-normal: 0;
  --lp-tracking-wide: 0.05em;
  --lp-tracking-wider: 0.1em;
  --lp-tracking-widest: 0.15em;

  /* ============ SPACING ============ */

  --lp-space-0:  0;
  --lp-space-1:  4px;
  --lp-space-2:  8px;
  --lp-space-3:  12px;
  --lp-space-4:  16px;
  --lp-space-5:  20px;
  --lp-space-6:  24px;
  --lp-space-8:  32px;
  --lp-space-10: 40px;
  --lp-space-12: 48px;
  --lp-space-16: 64px;
  --lp-space-20: 80px;
  --lp-space-24: 96px;

  /* ============ RADIUS ============ */

  --lp-radius-none: 0;
  --lp-radius-sm:   2px;
  --lp-radius-md:   4px;
  --lp-radius-lg:   8px;
  --lp-radius-full: 9999px;

  /* ============ SHADOWS ============ */

  --lp-shadow-none: none;
  --lp-shadow-soft: 0 1px 2px rgba(139, 115, 85, 0.06);
  --lp-shadow-warm: 0 4px 12px rgba(139, 115, 85, 0.08);
  --lp-shadow-lifted: 0 8px 24px rgba(139, 115, 85, 0.10);
  --lp-shadow-focus: 0 0 0 3px rgba(139, 115, 85, 0.2);

  /* ============ TRANSITIONS ============ */

  --lp-transition-fast: 150ms ease;
  --lp-transition-base: 250ms ease;
  --lp-transition-slow: 400ms ease;
  --lp-easing-smooth: cubic-bezier(0.4, 0, 0.2, 1);

  /* ============ Z-INDEX ============ */

  --lp-z-base: 0;
  --lp-z-raised: 10;
  --lp-z-sticky: 100;
  --lp-z-overlay: 1000;
  --lp-z-modal: 1100;
  --lp-z-tooltip: 1200;
}

/* ============ BASE STYLES ============ */

html, body {
  background: var(--lp-bg);
  color: var(--lp-text);
  font-family: var(--lp-font-body);
  font-size: var(--lp-text-body-size);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

h1, h2, h3 {
  font-family: var(--lp-font-headline);
  font-weight: 300;
  letter-spacing: var(--lp-tracking-tight);
  color: var(--lp-text);
  line-height: 1.2;
}

h1 { font-size: var(--lp-text-h1); }
h2 { font-size: var(--lp-text-h2); }
h3 { font-size: var(--lp-text-h3); }

h4, h5, h6 {
  font-family: var(--lp-font-body);
  font-weight: 500;
  color: var(--lp-text);
}

p {
  color: var(--lp-text);
  line-height: 1.6;
}

a {
  color: var(--lp-accent);
  text-decoration: none;
  border-bottom: 1px solid transparent;
  transition: border-color var(--lp-transition-base);
}

a:hover {
  border-bottom-color: var(--lp-accent);
}

/* Focus ring — warm brown, not blue */
*:focus-visible {
  outline: none;
  box-shadow: var(--lp-shadow-focus);
  border-radius: var(--lp-radius-md);
}

/* Utility: small-caps label */
.lp-label {
  font-family: var(--lp-font-body);
  font-size: var(--lp-text-label);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: var(--lp-tracking-wider);
  color: var(--lp-text-muted);
}

/* Utility: decorative divider */
.lp-divider {
  width: 80px;
  height: 1px;
  background: var(--lp-primary-200);
  margin: var(--lp-space-12) auto;
  border: none;
}

/* ============ STREAMLIT OVERRIDES ============ */

/* App canvas — warm off-white, Inter body, no dark mode bleed */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
.main,
.block-container {
  background: var(--lp-bg);
  color: var(--lp-text);
  font-family: var(--lp-font-body);
}

/* Clobber Streamlit's monospace default on the app root */
.stApp {
  font-family: var(--lp-font-body) !important;
}

/* Sidebar — slightly warmer surface, hairline border */
[data-testid="stSidebar"] {
  background: var(--lp-neutral-100);
  border-right: 1px solid var(--lp-border);
}

[data-testid="stSidebar"] * {
  font-family: var(--lp-font-body);
  color: var(--lp-text);
}

/* Restore Material Symbols font for icon spans. The universal *
   rule above clobbers Streamlit's icon font (used by st.expander
   chevron, help tooltips, etc.) and causes raw icon names like
   "keyboard_arrow_down" to render as text. */
[data-testid="stSidebar"] [class*="material-symbols"],
[data-testid="stSidebar"] [class*="material-icons"],
[data-testid="stSidebar"] [data-testid*="Icon"],
[data-testid="stSidebar"] .material-symbols-outlined,
[data-testid="stSidebar"] .material-symbols-rounded,
[data-testid="stSidebar"] .material-icons,
[data-testid="stSidebar"] .stIcon,
[data-testid="stSidebar"] [data-testid="stIconMaterial"] {
  font-family: 'Material Symbols Outlined', 'Material Symbols Rounded', 'Material Icons' !important;
}

/* Hide Streamlit chrome — own the canvas */
#MainMenu,
footer,
header {
  visibility: hidden;
}

.stDeployButton {
  display: none;
}

/* Buttons — cashmere accent, uppercase tracking, sharp 4px corners */
.stButton > button,
[data-testid="stChatInputSubmitButton"],
[data-testid="baseButton-primary"],
[data-testid="baseButton-secondary"] {
  background: var(--lp-accent);
  color: var(--lp-neutral-0);
  border: 1px solid var(--lp-accent);
  border-radius: var(--lp-radius-md);
  font-family: var(--lp-font-body);
  font-weight: 500;
  font-size: var(--lp-text-small);
  text-transform: uppercase;
  letter-spacing: var(--lp-tracking-wider);
  padding: var(--lp-space-3) var(--lp-space-6);
  transition: var(--lp-transition-base);
  box-shadow: none;
}

.stButton > button:hover,
[data-testid="stChatInputSubmitButton"]:hover,
[data-testid="baseButton-primary"]:hover,
[data-testid="baseButton-secondary"]:hover {
  background: var(--lp-primary-400);
  border-color: var(--lp-primary-400);
  color: var(--lp-neutral-0);
  box-shadow: var(--lp-shadow-warm);
}

.stButton > button:active,
[data-testid="stChatInputSubmitButton"]:active,
[data-testid="baseButton-primary"]:active,
[data-testid="baseButton-secondary"]:active {
  background: var(--lp-primary-600);
  border-color: var(--lp-primary-600);
  color: var(--lp-neutral-0);
  box-shadow: none;
}

.stButton > button:focus-visible,
[data-testid="stChatInputSubmitButton"]:focus-visible,
[data-testid="baseButton-primary"]:focus-visible,
[data-testid="baseButton-secondary"]:focus-visible {
  outline: none;
  box-shadow: var(--lp-shadow-focus);
}

.stButton > button:disabled,
[data-testid="stChatInputSubmitButton"]:disabled,
[data-testid="baseButton-primary"]:disabled,
[data-testid="baseButton-secondary"]:disabled {
  background: var(--lp-neutral-300);
  border-color: var(--lp-neutral-300);
  color: var(--lp-text-subtle);
  cursor: not-allowed;
  box-shadow: none;
}

/* ============ MONO BOUNDARY ============ */
/* Code/data only — keep JetBrains Mono confined; everything else is Inter/Garamond. */

code,
pre,
kbd,
samp,
.lp-mono,
[data-testid="stCodeBlock"],
[data-testid="stCode"] {
  font-family: var(--lp-font-mono);
}

/* Inputs — surface bg, hairline border, body font */
.stTextInput input,
.stTextArea textarea,
.stSelectbox [data-baseweb="select"],
[data-testid="stChatInput"] textarea {
  background: var(--lp-surface);
  color: var(--lp-text);
  border: 1px solid var(--lp-border);
  border-radius: var(--lp-radius-md);
  font-family: var(--lp-font-body);
}

.stTextInput input:focus-visible,
.stTextArea textarea:focus-visible,
[data-testid="stChatInput"] textarea:focus-visible {
  outline: none;
  border-color: var(--lp-accent);
  box-shadow: var(--lp-shadow-focus);
}

/* === Sidebar (Phase 8 SBR-*) === */

/* SBR-01 — Wordmark hero */
[data-testid="stSidebar"] .lp-sidebar-wordmark {
  font-family: var(--lp-font-headline);
  font-weight: 300;
  font-size: 28px;
  color: var(--lp-text);
  letter-spacing: 0.02em;
  padding: var(--lp-space-6) 0 var(--lp-space-4) 0;
  margin: 0;
  line-height: 1;
}

[data-testid="stSidebar"] {
  width: 320px !important;
  min-width: 320px !important;
  max-width: 320px !important;
  /* Phase 6 hides <header> globally — including the expand toggle — so a
     collapsed sidebar has no in-UI recovery affordance. Force the section
     visible regardless of Streamlit's aria-expanded state. */
  transform: none !important;
  margin-left: 0 !important;
  visibility: visible !important;
}
[data-testid="stSidebar"][aria-expanded="false"] {
  transform: none !important;
  margin-left: 0 !important;
  visibility: visible !important;
}
/* Hide the in-sidebar collapse button so users can't strand themselves. */
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebar"] button[kind="header"] {
  display: none !important;
}
[data-testid="stSidebar"] [data-testid="stSidebarContent"],
[data-testid="stSidebar"] > div:first-child {
  background: var(--lp-bg);  /* override Phase 6 --lp-neutral-100 to match mockup */
  padding-left: var(--lp-space-6);
  padding-right: var(--lp-space-6);
}

/* SBR-02 — Section headers (small-caps tracked) */
[data-testid="stSidebar"] .lp-section-header {
  font-family: var(--lp-font-body);
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--lp-text-muted);
  margin: 0 0 var(--lp-space-3) 0;
  padding: 0;
}
[data-testid="stSidebar"] .lp-section-rule {
  height: 1px;
  background: var(--lp-border);
  border: 0;
  margin: var(--lp-space-6) 0;
}

/* SBR-03 — MODE selector (horizontal st.radio with sage dot indicator)
   Renders three labels AUTO / SQL / SEMANTIC in a row. The native radio
   circle is replaced with a sage dot that only shows when the option is
   active — inactive labels have a hollow hairline ring instead. */
[data-testid="stSidebar"] .lp-mode-radio + div [data-testid="stRadio"] > div[role="radiogroup"] {
  display: flex;
  flex-direction: row;
  gap: var(--lp-space-4);
  margin-top: var(--lp-space-2);
}
[data-testid="stSidebar"] .lp-mode-radio + div [data-testid="stRadio"] label {
  display: flex;
  align-items: center;
  gap: var(--lp-space-2);
  cursor: pointer;
  padding: 0;
  margin: 0;
}
[data-testid="stSidebar"] .lp-mode-radio + div [data-testid="stRadio"] label > div:first-child {
  /* The native circle wrapper — neutralize its default size/look */
  width: 10px;
  height: 10px;
  min-width: 10px;
  min-height: 10px;
  border-radius: 50%;
  border: 1px solid var(--lp-border);
  background: transparent;
  box-shadow: none;
  flex-shrink: 0;
  position: relative;
  overflow: hidden;
}
[data-testid="stSidebar"] .lp-mode-radio + div [data-testid="stRadio"] label > div:first-child > div {
  /* Hide the inner native indicator (Streamlit emits an inner div for checked state) */
  display: none;
}
[data-testid="stSidebar"] .lp-mode-radio + div [data-testid="stRadio"] label:has(input:checked) > div:first-child {
  background: var(--lp-success);  /* sage filled dot when active */
  border-color: var(--lp-success);
}
[data-testid="stSidebar"] .lp-mode-radio + div [data-testid="stRadio"] label > div:last-child,
[data-testid="stSidebar"] .lp-mode-radio + div [data-testid="stRadio"] label p {
  font-family: var(--lp-font-body);
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--lp-text-muted);
  margin: 0;
  white-space: nowrap;
}
[data-testid="stSidebar"] .lp-mode-radio + div [data-testid="stRadio"] label:has(input:checked) p,
[data-testid="stSidebar"] .lp-mode-radio + div [data-testid="stRadio"] label:has(input:checked) > div:last-child {
  color: var(--lp-text);  /* active label darkens to charcoal */
}
[data-testid="stSidebar"] .lp-mode-radio + div [data-testid="stRadio"][aria-disabled="true"],
[data-testid="stSidebar"] .lp-mode-radio + div [data-testid="stRadio"]:has(input:disabled) {
  opacity: 0.5;
  cursor: not-allowed;
}

/* SBR-04 — EMBEDDINGS status pill */
[data-testid="stSidebar"] .lp-status-pill {
  display: inline-block;
  font-family: var(--lp-font-body);
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  padding: var(--lp-space-1) var(--lp-space-3);
  border-radius: var(--lp-radius-full);
}
[data-testid="stSidebar"] .lp-status-pill--ready {
  background: rgba(138, 154, 125, 0.12);  /* warm-base-color at ~12% */
  color: var(--lp-success);
}
[data-testid="stSidebar"] .lp-status-pill--missing {
  background: rgba(166, 120, 102, 0.12);  /* warm-base-color at ~12% */
  color: var(--lp-danger);
}

/* SBR-05 — Bottom-border-only LLM PROVIDER selectbox */
[data-testid="stSidebar"] .lp-bb-select .stSelectbox [data-baseweb="select"] {
  background: var(--lp-surface);
  border: 0;
  border-bottom: 1px solid var(--lp-border);
  border-radius: 0;
  box-shadow: none;
}
[data-testid="stSidebar"] .lp-bb-select .stSelectbox [data-baseweb="select"]:focus-within {
  border-bottom-color: var(--lp-accent);
  box-shadow: none;
}
[data-testid="stSidebar"] .lp-bb-select .stSelectbox label {
  font-family: var(--lp-font-body);
  font-size: 11px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--lp-text-muted);
}
[data-testid="stSidebar"] .lp-active-model {
  font-family: var(--lp-font-body);
  font-size: 11px;
  font-weight: 500;
  color: var(--lp-neutral-400);  /* muted gold */
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-top: var(--lp-space-2);
}

/* SBR-06 — Provider warning container */
[data-testid="stSidebar"] .lp-warn-card {
  background: var(--lp-bg);
  border-left: 3px solid var(--lp-danger);
  border-top: 0;
  border-right: 0;
  border-bottom: 0;
  border-radius: 0 var(--lp-radius-md) var(--lp-radius-md) 0;
  padding: var(--lp-space-4);
  margin: var(--lp-space-3) 0;
}
[data-testid="stSidebar"] .lp-warn-card .lp-warn-label {
  font-family: var(--lp-font-body);
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--lp-danger);
  margin: 0 0 var(--lp-space-2) 0;
}
[data-testid="stSidebar"] .lp-warn-card .lp-warn-body {
  font-family: var(--lp-font-body);
  font-size: 14px;
  color: var(--lp-text);
  margin: 0 0 var(--lp-space-2) 0;
  line-height: 1.4;
}
[data-testid="stSidebar"] .lp-warn-card .lp-warn-fix {
  font-family: var(--lp-font-body);
  font-size: 13px;
  color: var(--lp-text-muted);
  margin: 0;
  line-height: 1.4;
}
[data-testid="stSidebar"] .lp-warn-card code {
  background: rgba(166, 120, 102, 0.08);
  padding: 1px 4px;
  border-radius: 2px;
  /* font-family inherits JetBrains Mono via Phase 6 mono boundary */
}

/* ============================================================
   Phase 8 fixes — Streamlit defaults that bleed bright red /
   raw icon names through the editorial palette. Restyles
   checkboxes, slider, expander, and the warning pill / unlock
   button to match the EMBEDDINGS MISSING pill aesthetic.
   ============================================================ */

/* Expander — editorial header instead of Streamlit's bold default */
[data-testid="stSidebar"] [data-testid="stExpander"] summary,
[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderToggleIcon"] + div,
[data-testid="stSidebar"] details > summary {
  font-family: var(--lp-font-body) !important;
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--lp-text-muted);
}
[data-testid="stSidebar"] [data-testid="stExpander"] {
  background: transparent;
  border: 1px solid var(--lp-border);
  border-radius: var(--lp-radius-md);
  box-shadow: none;
}

/* Checkboxes — cashmere accent in place of Streamlit's red */
[data-testid="stSidebar"] [data-baseweb="checkbox"] [data-baseweb="checkmark"],
[data-testid="stSidebar"] [data-testid="stCheckbox"] label > span:first-child {
  background-color: transparent !important;
  border: 1px solid var(--lp-border) !important;
  border-radius: var(--lp-radius-sm) !important;
  box-shadow: none !important;
}
[data-testid="stSidebar"] [data-baseweb="checkbox"] input:checked + div,
[data-testid="stSidebar"] [data-baseweb="checkbox"] [aria-checked="true"] [data-baseweb="checkmark"],
[data-testid="stSidebar"] [data-testid="stCheckbox"] label:has(input:checked) > span:first-child {
  background-color: var(--lp-accent) !important;
  border-color: var(--lp-accent) !important;
  color: var(--lp-neutral-0) !important;
}
[data-testid="stSidebar"] [data-testid="stCheckbox"] label p,
[data-testid="stSidebar"] [data-baseweb="checkbox"] label {
  font-family: var(--lp-font-body);
  font-size: 12px;
  font-weight: 400;
  color: var(--lp-text);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

/* Slider — cashmere thumb, warm-beige track */
[data-testid="stSidebar"] [data-testid="stSlider"] [data-baseweb="slider"] [role="slider"] {
  background: var(--lp-accent) !important;
  border-color: var(--lp-accent) !important;
  box-shadow: none !important;
}
[data-testid="stSidebar"] [data-testid="stSlider"] [data-baseweb="slider"] > div > div:first-child {
  background: var(--lp-border) !important;  /* unfilled track */
}
[data-testid="stSidebar"] [data-testid="stSlider"] [data-baseweb="slider"] > div > div:first-child > div {
  background: var(--lp-accent) !important;  /* filled portion */
}
[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stTickBar"] *,
[data-testid="stSidebar"] [data-testid="stSlider"] [aria-valuetext] {
  color: var(--lp-text) !important;
  font-family: var(--lp-font-body);
}
[data-testid="stSidebar"] [data-testid="stSlider"] label p {
  font-family: var(--lp-font-body);
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--lp-text-muted);
}

/* Soft warning pill — used inline for status indicators that mirror
   the EMBEDDINGS MISSING pill shape (warm-beige tint, terracotta text,
   rounded). */
[data-testid="stSidebar"] .lp-pill-warn {
  display: inline-block;
  font-family: var(--lp-font-body);
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--lp-danger);
  background: rgba(166, 120, 102, 0.12);
  padding: var(--lp-space-1) var(--lp-space-3);
  border-radius: var(--lp-radius-full);
  margin: var(--lp-space-2) 0;
}

/* UNLOCK UPLOAD button — pill-shape variant that matches the soft
   warning pill aesthetic. Streamlit 1.36+ emits .st-key-{key} on
   the button wrapper when key= is set on st.button. Override the
   global cashmere fill from Phase 6 for this specific button. */
[data-testid="stSidebar"] .st-key-unlock_upload .stButton > button,
[data-testid="stSidebar"] .st-key-unlock_upload button {
  background: rgba(166, 120, 102, 0.12) !important;
  color: var(--lp-danger) !important;
  border: 0 !important;
  border-radius: var(--lp-radius-full) !important;
  font-family: var(--lp-font-body) !important;
  font-weight: 500 !important;
  font-size: 11px !important;
  text-transform: uppercase !important;
  letter-spacing: 0.1em !important;
  padding: var(--lp-space-2) var(--lp-space-4) !important;
  box-shadow: none !important;
}
[data-testid="stSidebar"] .st-key-unlock_upload .stButton > button:hover,
[data-testid="stSidebar"] .st-key-unlock_upload button:hover {
  background: rgba(166, 120, 102, 0.2) !important;
  color: var(--lp-danger) !important;
  border: 0 !important;
  box-shadow: none !important;
}
/* Streamlit wraps button text in <p>/<div>/<span> — propagate the
   pill typography down so it matches .lp-pill-warn exactly. */
[data-testid="stSidebar"] .st-key-unlock_upload button p,
[data-testid="stSidebar"] .st-key-unlock_upload button div,
[data-testid="stSidebar"] .st-key-unlock_upload button span {
  font-family: var(--lp-font-body) !important;
  font-weight: 500 !important;
  font-size: 11px !important;
  text-transform: uppercase !important;
  letter-spacing: 0.1em !important;
  color: var(--lp-danger) !important;
  line-height: 1 !important;
  margin: 0 !important;
}
"""


__all__ = ["LORO_PIANA_TOKENS", "LORO_PIANA_CSS"]
