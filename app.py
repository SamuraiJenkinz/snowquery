"""
SNOWGREP - ServiceNow Incident Query Tool
Brutalist Terminal-Style Interface
"""
from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
import streamlit as st

from src.chart_generator import generate_chart, infer_chart_type
from src.embeddings import (
    build_embeddings,
    embeddings_exist,
    get_embedding_stats,
)
from src.ingest import get_schema_summary, load_csv, table_exists
from src.llm import get_llm, load_settings, missing_vars
from src.query_router import generate_executive_summary, get_mode_description, route_query
from src.utils import (
    dataframe_to_csv_bytes,
    format_dataframe_for_display,
    format_error_message,
    generate_export_filename,
    logger,
)
from src.ui.css import LORO_PIANA_CSS
from src.ui.splash import render_splash

# Page configuration
st.set_page_config(
    page_title="SNOWGREP",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# LORO PIANA CSS — single-injection from src/ui/css.py (v2.2 Phase 6)
# ============================================================
st.markdown(f"<style>{LORO_PIANA_CSS}</style>", unsafe_allow_html=True)

# Mode mapping for UI
MODE_OPTIONS = {
    "AUTO": "auto",
    "REPORT [SQL]": "structured",
    "SIMILAR [SEMANTIC]": "semantic",
    "ANALYZE [HYBRID]": "hybrid"
}

# Phase 5: LLM provider selectbox option mapping.
# Display labels (left) → internal _REGISTRY keys (right). MUST match the keys
# in src/llm/__init__.py::_REGISTRY exactly. Insertion order = selectbox order:
# Azure first so the default-selected option is the existing behavior.
_PROVIDER_OPTIONS: dict[str, str] = {
    "Azure OpenAI": "azure_openai",
    "Anthropic Claude (MGTI)": "anthropic_mgti",
}
_PROVIDER_LABELS: dict[str, str] = {v: k for k, v in _PROVIDER_OPTIONS.items()}
_PROVIDER_KEYS: tuple[str, ...] = tuple(_PROVIDER_OPTIONS.values())  # ("azure_openai", "anthropic_mgti")


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


def init_session_state():
    """Initialize session state variables."""
    if "schema" not in st.session_state:
        st.session_state.schema = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "data_loaded" not in st.session_state:
        st.session_state.data_loaded = False
    if "embeddings_ready" not in st.session_state:
        st.session_state.embeddings_ready = False
    if "upload_authenticated" not in st.session_state:
        st.session_state.upload_authenticated = False
    # Phase 7 splash lifecycle. `_splash_shown` is the once-per-session gate
    # (SPL-04). `_splash_placeholder` holds the `st.empty()` handle returned
    # at first mount so subsequent reruns can clear it after data is ready.
    # `_splash_dismiss_sent` ensures the dismiss postMessage + 400ms-sleep
    # path runs exactly once per session.
    #
    # NOTE: There is no start-timestamp and no Python-side 4s cap. The
    # 4s hard cap (SPL-02) lives entirely in the iframe's <script> block
    # (Plan 01 section D.2) — adding a Python wall-clock check is pointless
    # because Streamlit does not rerun on a wall-clock timer, so any Python
    # cap would only fire on the next user interaction (too late).
    if "_splash_shown" not in st.session_state:
        st.session_state._splash_shown = False
    if "_splash_placeholder" not in st.session_state:
        st.session_state._splash_placeholder = None
    if "_splash_dismiss_sent" not in st.session_state:
        st.session_state._splash_dismiss_sent = False


def _load_csv_data(uploaded_file, append: bool = False):
    """Load CSV data with replace or append mode."""
    mode_text = "APPENDING" if append else "LOADING"
    with st.spinner(f"{mode_text} CSV DATA..."):
        try:
            schema = load_csv(uploaded_file, append=append)
            st.session_state.schema = schema
            st.session_state.data_loaded = True

            if append:
                st.success(
                    f"[OK] APPENDED — {schema['row_count']:,} TOTAL INCIDENTS"
                )
                logger.info(f"Appended data, total: {schema['row_count']} rows")
            else:
                st.success(
                    f"[OK] LOADED {schema['row_count']:,} INCIDENTS / "
                    f"{len(schema['columns'])} COLUMNS"
                )
                logger.info(f"Successfully loaded {schema['row_count']} rows")

            st.rerun()
        except Exception as e:
            st.error(format_error_message(e))
            logger.exception("Failed to load CSV")


def render_sidebar():
    """Render the sidebar with data management controls."""
    with st.sidebar:
        # ----------------------------------------------------------------
        # SBR-01 — Wordmark hero (Phase 8: replaces brutalist terminal logo)
        # ----------------------------------------------------------------
        st.markdown(
            '<h1 class="lp-sidebar-wordmark">SNOWGREP</h1>',
            unsafe_allow_html=True,
        )
        st.markdown('<hr class="lp-section-rule" />', unsafe_allow_html=True)

        # ----------------------------------------------------------------
        # DATA section (merged from legacy DATA INGEST + DATA STATUS)
        # ----------------------------------------------------------------
        st.markdown('<p class="lp-section-header">DATA</p>', unsafe_allow_html=True)

        # Password protection for upload
        # Password can be set via SNOWGREP_UPLOAD_PASSWORD environment variable
        # Default is "admin123" for development (NOT for production use)
        upload_password = os.getenv("SNOWGREP_UPLOAD_PASSWORD", "admin123")

        if not st.session_state.upload_authenticated:
            # Show password input when locked
            password_input = st.text_input(
                "UPLOAD PASSWORD",
                type="password",
                help="Enter password to unlock CSV upload functionality",
                label_visibility="collapsed",
                placeholder="ENTER PASSWORD..."
            )

            col1, col2 = st.columns([2, 1])
            with col1:
                if st.button("UNLOCK UPLOAD", type="primary", use_container_width=True, key="unlock_upload"):
                    if password_input == upload_password:
                        st.session_state.upload_authenticated = True
                        st.rerun()
                    else:
                        st.error("[ERR] INVALID PASSWORD")

            # Show warning if using default password
            if upload_password == "admin123":
                st.markdown(
                    '<span class="lp-pill-warn">USING DEFAULT PASSWORD</span>',
                    unsafe_allow_html=True,
                )
        else:
            # Show unlocked status
            st.markdown(
                '<p class="lp-label">UPLOAD UNLOCKED</p>',
                unsafe_allow_html=True,
            )

            # CSV Upload (only visible when authenticated)
            uploaded_file = st.file_uploader(
                "UPLOAD SERVICENOW CSV",
                type=["csv"],
                help="Upload a CSV export from ServiceNow containing incident data",
                label_visibility="collapsed"
            )

            st.caption("DROP CSV FILE HERE")

            if uploaded_file is not None:
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("REPLACE", type="primary", use_container_width=True):
                        _load_csv_data(uploaded_file, append=False)
                with col2:
                    if st.button("APPEND", type="secondary", use_container_width=True):
                        _load_csv_data(uploaded_file, append=True)

            # Lock upload button
            st.write("")
            if st.button("LOCK UPLOAD", use_container_width=True):
                st.session_state.upload_authenticated = False
                st.rerun()

        # Data status (consolidated into DATA section)
        if st.session_state.schema:
            schema = st.session_state.schema
            col1, col2 = st.columns(2)
            with col1:
                st.metric("INCIDENTS", f"{schema['row_count']:,}")
            with col2:
                st.metric("COLUMNS", len(schema['columns']))
        elif table_exists():
            schema = get_schema_summary()
            if schema:
                st.session_state.schema = schema
                st.session_state.data_loaded = True
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("INCIDENTS", f"{schema['row_count']:,}")
                with col2:
                    st.metric("COLUMNS", len(schema['columns']))
            else:
                st.markdown(
                    '<p class="lp-label" style="color: var(--lp-danger);">NO DATA LOADED</p>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<p class="lp-label" style="color: var(--lp-danger);">NO DATA LOADED</p>',
                unsafe_allow_html=True,
            )

        st.markdown('<hr class="lp-section-rule" />', unsafe_allow_html=True)

        # ----------------------------------------------------------------
        # SBR-04 — EMBEDDINGS section with sage/terracotta status pill
        # ----------------------------------------------------------------
        st.markdown('<p class="lp-section-header">EMBEDDINGS</p>', unsafe_allow_html=True)

        if embeddings_exist():
            stats = get_embedding_stats()
            st.session_state.embeddings_ready = True
            st.markdown(
                f'<span class="lp-status-pill lp-status-pill--ready">READY · {stats["document_count"]:,} DOCS</span>',
                unsafe_allow_html=True,
            )
        else:
            st.session_state.embeddings_ready = False
            st.markdown(
                '<span class="lp-status-pill lp-status-pill--missing">MISSING</span>',
                unsafe_allow_html=True,
            )

        if st.session_state.data_loaded:
            st.write("")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("REBUILD", use_container_width=True):
                    _build_embeddings_with_progress(force=True)
            with col2:
                if st.button("UPDATE", use_container_width=True):
                    _build_embeddings_with_progress(force=False)

        st.markdown('<hr class="lp-section-rule" />', unsafe_allow_html=True)

        # ----------------------------------------------------------------
        # SBR-05 — LLM PROVIDER section with bottom-border-only selectbox
        # ----------------------------------------------------------------
        st.markdown('<p class="lp-section-header">LLM PROVIDER</p>', unsafe_allow_html=True)

        # Initialize session_state on first render. Clamp unknown values to
        # azure_openai (defense against typos in LLM_PROVIDER_DEFAULT — RESEARCH.md
        # Pitfall 2). The .strip() handles trailing whitespace.
        if "llm_provider" not in st.session_state:
            default = os.getenv("LLM_PROVIDER_DEFAULT", "azure_openai").strip()
            if default not in _PROVIDER_KEYS:
                logger.warning(
                    f"LLM_PROVIDER_DEFAULT={default!r} not in {_PROVIDER_KEYS}; "
                    f"falling back to 'azure_openai'"
                )
                default = "azure_openai"
            st.session_state["llm_provider"] = default

        # Selectbox wrapped in lp-bb-select for bottom-border-only styling.
        # Locked label "LLM provider"; options exactly ["Azure OpenAI",
        # "Anthropic Claude (MGTI)"]; index resolved from current session_state so
        # reruns preserve the selection.
        st.markdown('<div class="lp-bb-select">', unsafe_allow_html=True)
        selected_label = st.selectbox(
            "LLM provider",  # LOCKED v2.1 string — VERBATIM
            options=list(_PROVIDER_OPTIONS.keys()),
            index=_PROVIDER_KEYS.index(st.session_state["llm_provider"]),
            help="Which LLM serves classification, SQL generation, and executive summaries. Default is Azure OpenAI.",
        )
        st.session_state["llm_provider"] = _PROVIDER_OPTIONS[selected_label]
        st.markdown('</div>', unsafe_allow_html=True)

        # Read-only active-model caption beneath the selector. Use load_settings()
        # NOT get_llm() — sidebar render must not side-effect adapter construction
        # or startup logs (Plan 05-02 decision §11).
        _settings = load_settings()
        if st.session_state["llm_provider"] == "azure_openai":
            # Azure: extract deployment from endpoint URL the same way the adapter does.
            from src.llm.azure_openai import _extract_model_from_endpoint
            _active_model = _extract_model_from_endpoint(_settings.azure_endpoint) if _settings.azure_endpoint else ""
        else:
            _active_model = _settings.anthropic_model
        st.markdown(
            f'<p class="lp-active-model">MODEL · {(_active_model or "NOT CONFIGURED")}</p>',
            unsafe_allow_html=True,
        )

        # Missing-creds warning + blocked-flag set. Called every rerun — cheap
        # (os.getenv is O(1)). Do NOT @st.cache_data this — adding env vars
        # between runs must invalidate immediately (RESEARCH.md Pitfall 10).
        # SBR-06: replaced st.warning() with editorial warm-beige warning card.
        _missing = missing_vars(st.session_state["llm_provider"])
        if _missing:
            _human_name = _PROVIDER_LABELS[st.session_state["llm_provider"]]
            _missing_code = ", ".join(f"<code>{v}</code>" for v in _missing)
            st.markdown(
                f'''<div class="lp-warn-card">
  <p class="lp-warn-label">WARNING — PROVIDER NOT CONFIGURED</p>
  <p class="lp-warn-body"><strong>{_human_name}</strong> is not configured. Missing: {_missing_code}.</p>
  <p class="lp-warn-fix">Add them to <code>.env</code> and restart, or switch provider above.</p>
</div>''',
                unsafe_allow_html=True,
            )
            st.session_state["_llm_provider_blocked"] = True
        else:
            st.session_state["_llm_provider_blocked"] = False

        st.markdown('<hr class="lp-section-rule" />', unsafe_allow_html=True)

        # ----------------------------------------------------------------
        # SBR-03 — MODE selector (Phase 8 Wave A)
        # Renders as a horizontal st.radio with a sage filled dot on the
        # active label (custom CSS in src/ui/css.py .lp-mode-radio block).
        # Writes st.session_state["query_mode"] to "auto" / "structured" /
        # "semantic" — same internal values MODE_OPTIONS produces. The legacy
        # main-panel selectbox at app.py:684-699 is deleted by Plan 02 (Wave B).
        # ----------------------------------------------------------------
        st.markdown('<p class="lp-section-header">MODE</p>', unsafe_allow_html=True)

        # Initialize query_mode session state. MODE_OPTIONS at app.py:46-51 stays the
        # source of truth; radio exposes 3 modes (AUTO/SQL/SEMANTIC). HYBRID is dropped
        # from the visible selector in v2.2 but internal "hybrid" value still works if
        # anything else writes it.
        if "query_mode" not in st.session_state:
            st.session_state["query_mode"] = "auto"  # MODE_OPTIONS["AUTO"] internal value

        _blocked = st.session_state.get("_llm_provider_blocked", False)

        _MODE_LABEL_TO_INTERNAL = {
            "AUTO":     "auto",       # MODE_OPTIONS["AUTO"]
            "SQL":      "structured", # MODE_OPTIONS["REPORT [SQL]"]
            "SEMANTIC": "semantic",   # MODE_OPTIONS["SIMILAR [SEMANTIC]"]
        }
        _INTERNAL_TO_MODE_LABEL = {v: k for k, v in _MODE_LABEL_TO_INTERNAL.items()}
        _mode_labels = list(_MODE_LABEL_TO_INTERNAL.keys())
        _current_label = _INTERNAL_TO_MODE_LABEL.get(
            st.session_state["query_mode"], "AUTO"
        )

        st.markdown('<div class="lp-mode-radio">', unsafe_allow_html=True)
        _selected_label = st.radio(
            "MODE",
            options=_mode_labels,
            index=_mode_labels.index(_current_label),
            horizontal=True,
            label_visibility="collapsed",
            disabled=_blocked,
            key="_mode_radio",
        )
        st.markdown('</div>', unsafe_allow_html=True)

        _new_internal = _MODE_LABEL_TO_INTERNAL[_selected_label]
        if _new_internal != st.session_state["query_mode"]:
            st.session_state["query_mode"] = _new_internal

        st.markdown('<hr class="lp-section-rule" />', unsafe_allow_html=True)

        # ----------------------------------------------------------------
        # CONFIG section (preserved from v2.1)
        # ----------------------------------------------------------------
        st.markdown('<p class="lp-section-header">CONFIG</p>', unsafe_allow_html=True)

        with st.expander("QUERY SETTINGS"):
            st.session_state.top_k = st.slider(
                "RESULTS LIMIT",
                min_value=5,
                max_value=50,
                value=10,
                help="Number of results for semantic search"
            )

            st.session_state.show_sql = st.checkbox(
                "SHOW SQL",
                value=True,
                help="Display generated SQL"
            )

            st.session_state.show_summary = st.checkbox(
                "EXEC SUMMARY",
                value=True,
                help="Generate AI summary"
            )


def _build_embeddings_with_progress(force: bool = False):
    """Build embeddings with progress display."""
    progress_bar = st.progress(0)
    status_text = st.empty()

    def progress_callback(progress: float, message: str):
        progress_bar.progress(progress)
        status_text.text(message.upper())

    try:
        stats = build_embeddings(
            force_rebuild=force,
            progress_callback=progress_callback
        )
        st.session_state.embeddings_ready = True
        st.success(
            f"[OK] EMBEDDED {stats['total_embedded']:,} INCIDENTS / "
            f"{stats['time_taken']:.1f}s"
        )
        st.rerun()
    except Exception as e:
        st.error(format_error_message(e))
    finally:
        progress_bar.empty()
        status_text.empty()


def render_schema_details():
    """Render schema details in an expander."""
    if not st.session_state.schema:
        return

    schema = st.session_state.schema

    with st.expander("SCHEMA DETAILS"):
        st.markdown(f"**TABLE:** `{schema['table_name']}`")
        st.markdown(f"**ROWS:** `{schema['row_count']:,}`")

        cols_data = [
            {
                "COLUMN": col["name"],
                "TYPE": col["type"],
                "SAMPLE": col["sample"][:50] + "..." if len(col["sample"]) > 50 else col["sample"]
            }
            for col in schema["columns"]
        ]

        st.dataframe(
            cols_data,
            use_container_width=True,
            hide_index=True
        )


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
                    display_results(
                        message["results"],
                        message.get("sql"),
                        message.get("query_id", ""),
                        message.get("executive_summary"),
                        message.get("chart"),
                        message.get("chart_feedback")
                    )


def display_results(df: pd.DataFrame, sql: str | None, query_id: str, executive_summary: str | None = None, chart=None, chart_feedback: str | None = None):
    """Display query results with formatting and export."""
    # Executive summary
    if executive_summary:
        st.markdown("### EXECUTIVE SUMMARY")
        st.markdown(f'<div class="query-box">{executive_summary}</div>', unsafe_allow_html=True)
        st.divider()

    # Chart display
    if chart is not None:
        st.markdown("### VISUALIZATION")
        # Show feedback about chart adjustments (e.g., "Switched to bar chart")
        if chart_feedback:
            st.info(f"📊 {chart_feedback}")
        st.altair_chart(chart, use_container_width=True)
        st.divider()
    elif chart_feedback:
        # Show feedback when chart couldn't be generated
        st.warning(f"📊 {chart_feedback}")

    # Results table
    display_df = format_dataframe_for_display(df)

    priority_cols = ["number", "short_description", "priority", "opened_at", "similarity_score"]
    available_priority = [c for c in priority_cols if c in display_df.columns]
    other_cols = [c for c in display_df.columns if c not in priority_cols]
    column_order = available_priority + other_cols

    display_df = display_df[column_order]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    # Export and SQL section
    col1, col2 = st.columns([1, 3])

    with col1:
        csv_data = dataframe_to_csv_bytes(df)
        st.download_button(
            label="EXPORT CSV",
            data=csv_data,
            file_name=generate_export_filename("incidents"),
            mime="text/csv",
            key=f"export_{query_id}"
        )

    with col2:
        if sql and st.session_state.get("show_sql", True):
            with st.expander("GENERATED SQL"):
                st.code(sql, language="sql")


def process_query(user_query: str, mode: str):
    """Process a user query and return formatted response."""
    if not st.session_state.schema:
        return {
            "content": "[ERR] NO DATA LOADED — UPLOAD CSV FIRST",
            "results": None,
            "sql": None
        }

    if mode in ["semantic", "hybrid", "auto"] and not st.session_state.embeddings_ready:
        if mode == "semantic":
            return {
                "content": "[ERR] NO EMBEDDINGS — BUILD VIA SIDEBAR",
                "results": None,
                "sql": None
            }

    try:
        result = route_query(
            user_query,
            st.session_state.schema,
            mode=mode,
            top_k=st.session_state.get("top_k", 10)
        )

        if result.get("error"):
            return {
                "content": f"[ERR] {result['error']}",
                "results": None,
                "sql": result.get("sql")
            }

        route_used = result.get("route_used", "unknown")
        classification = result.get("classification", {})
        confidence = classification.get("confidence", 0)
        reasoning = classification.get("reasoning", "")
        row_count = result.get("row_count", 0)
        explanation = result.get("explanation", "")
        chart_requested = classification.get("chart_requested", False)
        chart_type = classification.get("chart_type")

        # Generate chart if requested and we have results
        chart = None
        chart_feedback = None
        if chart_requested and result.get("results") is not None:
            df = result["results"]
            if not df.empty:
                chart_config = infer_chart_type(user_query, df)
                if chart_config:
                    # Capture any feedback about chart generation
                    chart_feedback = chart_config.get("feedback")

                    # Only generate if we have a valid chart type
                    if chart_config.get("type"):
                        # Override with explicit type if provided
                        if chart_type:
                            chart_config["type"] = chart_type
                        chart = generate_chart(df, chart_config)

        # Route badge colors
        route_colors = {
            "structured": "#00ff00",
            "semantic": "#ff00ff",
            "hybrid": "#00ffff"
        }
        route_color = route_colors.get(route_used, "#888")

        content_parts = [
            f'<span class="route-badge {route_used}">{route_used.upper()}</span> '
            f'<span style="color: #666;">CONFIDENCE: {confidence:.0%}</span>'
        ]

        if reasoning:
            content_parts.append(f"\n\n**REASONING:** {reasoning}")

        if explanation:
            content_parts.append(f"\n\n**QUERY:** {explanation}")

        content_parts.append(f'\n\n<span class="results-count">{row_count:,}</span> <span style="color: #666; font-size: 0.8rem; text-transform: uppercase;">INCIDENTS FOUND</span>')

        if row_count == 0:
            content_parts.append("\n\n_No results. Try different query or mode._")

        executive_summary = None
        if row_count > 0 and st.session_state.get("show_summary", True):
            executive_summary = generate_executive_summary(
                user_query,
                result.get("results"),
                route_used
            )

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

        return {
            "content": "".join(content_parts),
            "results": result.get("results"),
            "sql": result.get("sql"),
            "executive_summary": executive_summary,
            "chart": chart,
            "chart_feedback": chart_feedback,
            "provider": _provider,   # NEW Phase 5 (SC #4)
            "model": _model,         # NEW Phase 5 (SC #4)
        }

    except Exception as e:
        logger.exception("Error processing query")
        return {
            "content": f"[ERR] {str(e)}",
            "results": None,
            "sql": None
        }


def render_main_content():
    """Render the main content area."""
    # Custom header
    st.markdown("""
    <div class="terminal-header">
        <div class="terminal-header-icon">S</div>
        <div class="terminal-header-text">
            <h1>SNOWGREP</h1>
            <p>ServiceNow Incident Query Tool</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.data_loaded:
        st.markdown("""
        <div style="border: 1px solid #333; padding: 2rem; margin: 2rem 0;">
            <p style="color: #00ff00; font-size: 0.9rem; margin-bottom: 1rem;">> READY FOR INPUT</p>
            <p style="color: #666; font-size: 0.8rem;">Upload ServiceNow incident CSV via sidebar to begin.</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### EXAMPLE QUERIES")
        st.markdown("""
        <div class="example-query">Show all P1 incidents from last month</div>
        <div class="example-query">Find incidents similar to Outlook crashes</div>
        <div class="example-query">Top 5 assignment groups by volume</div>
        <div class="example-query">How many incidents opened this week?</div>
        """, unsafe_allow_html=True)
        return

    # Status bar
    schema = st.session_state.schema
    embeddings_status = "READY" if st.session_state.embeddings_ready else "NOT BUILT"
    embeddings_color = "green" if st.session_state.embeddings_ready else "yellow"
    
    st.markdown(f"""
    <div class="status-bar">
        <div class="status-item"><div class="status-dot green"></div>DATA: {schema['row_count']:,} ROWS</div>
        <div class="status-item"><div class="status-dot {embeddings_color}"></div>EMBEDDINGS: {embeddings_status}</div>
        <div class="status-item"><div class="status-dot green"></div>MODE: ACTIVE</div>
    </div>
    """, unsafe_allow_html=True)

    render_schema_details()

    # Mode selection
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("### QUERY INTERFACE")

    with col2:
        selected_mode_label = st.selectbox(
            "MODE",
            options=list(MODE_OPTIONS.keys()),
            index=0,
            help=get_mode_description(MODE_OPTIONS[list(MODE_OPTIONS.keys())[0]]),
            label_visibility="collapsed"
        )
        selected_mode = MODE_OPTIONS[selected_mode_label]

    st.caption(f"MODE: {get_mode_description(selected_mode).upper()}")

    render_chat_history()

    # Query input
    # Phase 5: honor sidebar's missing-creds blocked flag — disable chat input
    # and swap placeholder so users see WHY they can't submit. The blocked flag
    # is set by render_sidebar() on every rerun (Phase 5 RESEARCH.md Pitfall 5
    # — order is load-bearing; see main()).
    _blocked = st.session_state.get("_llm_provider_blocked", False)
    _placeholder = "ENTER QUERY..." if not _blocked else "QUERY DISABLED — see sidebar warning"
    if user_query := st.chat_input(_placeholder, disabled=_blocked):
        query_id = datetime.now().strftime("%Y%m%d%H%M%S%f")

        st.session_state.messages.append({
            "role": "user",
            "content": user_query
        })

        with st.chat_message("user"):
            st.markdown(user_query)

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

            if response["results"] is not None and not response["results"].empty:
                display_results(
                    response["results"],
                    response["sql"],
                    query_id,
                    response.get("executive_summary"),
                    response.get("chart"),
                    response.get("chart_feedback")
                )

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

    # Clear chat button
    if st.session_state.messages:
        if st.button("CLEAR HISTORY"):
            st.session_state.messages = []
            st.rerun()


def _run_splash_lifecycle() -> None:
    """Mount + dismiss-signal the boot splash. Phase 7 SPL-01, SPL-02, SPL-04.

    Two-state machine (Python side only — all timing-critical behavior lives
    in the iframe; see Plan 01 section D.2):

    State 1 — FIRST rerun of a browser session (`_splash_shown` is False):
        Mount the splash into a fresh `st.empty()` placeholder, stash the
        placeholder handle in session_state, and flip `_splash_shown` to True.
        Return.

    State 2 — subsequent reruns (`_splash_shown` is True):
        If the placeholder has already been cleared and the dismiss signal
        already sent, return immediately (steady-state, post-dismiss).

        Otherwise, check `data_loaded AND embeddings_ready`. If both True
        AND we haven't yet sent the dismiss signal:
            (a) Render a tiny inline <script> via st.markdown that sends
                the dismiss postMessage into every iframe (the splash
                iframe's listener consumes it and adds `.is-dismissing`,
                triggering the 400ms CSS fade).
            (b) Set `_splash_dismiss_sent = True`.
            (c) Sleep 400ms so the iframe's fade visibly completes
                before we tear down its container.
            (d) `placeholder.empty()` clears the iframe from the DOM.

        If data is NOT yet ready, do nothing — the iframe is still on
        screen, its own 4s hard-cap timer (Plan 01 section D.2) will fade
        it out client-side if data never arrives. Next rerun re-checks.

    Why no Python 4s cap: Streamlit only reruns on user interaction or
    session_state mutation. A wall-clock cap in Python would only fire on
    the next rerun, which may be never. The cap MUST live in the iframe.
    """
    import time

    # Fast path: dismiss already sent + placeholder cleared — nothing to do.
    if st.session_state.get("_splash_shown") and st.session_state.get("_splash_dismiss_sent"):
        return

    # State 1: first mount of the session.
    if not st.session_state.get("_splash_shown"):
        placeholder = st.empty()
        with placeholder.container():
            render_splash()
        st.session_state._splash_shown = True
        st.session_state._splash_placeholder = placeholder
        return

    # State 2: splash is mounted, dismiss not yet sent. Check data readiness.
    if (
        st.session_state.get("data_loaded")
        and st.session_state.get("embeddings_ready")
    ):
        # (a) Send dismiss signal into every iframe. The splash iframe's
        #     postMessage listener (Plan 01 section D.2) consumes the
        #     dismiss type and adds .is-dismissing to the splash element.
        #     Loop over window.frames so this targets the splash iframe
        #     regardless of how many iframes Streamlit has spawned.
        st.markdown(
            """
            <script>
              (function() {
                var payload = {type: 'snowgrep-splash-dismiss'};
                for (var i = 0; i < window.frames.length; i++) {
                  try { window.frames[i].postMessage(payload, '*'); } catch (e) {}
                }
              })();
            </script>
            """,
            unsafe_allow_html=True,
        )
        # (b) Mark sent so we don't double-fire.
        st.session_state._splash_dismiss_sent = True
        # (c) Wait for the 400ms iframe fade to complete (CONTEXT.md line 48).
        time.sleep(0.4)
        # (d) Tear down the placeholder. The iframe is already fully faded.
        placeholder = st.session_state.get("_splash_placeholder")
        if placeholder is not None:
            placeholder.empty()
        st.session_state._splash_placeholder = None
        return

    # Data not ready yet. Iframe is still showing; its own 4s hard-cap
    # timer will fade it out if data never arrives. Next rerun re-checks.
    return


def main():
    """Main application entry point.

    ORDER IS LOAD-BEARING: render_sidebar() must run BEFORE render_main_content()
    because the sidebar writes st.session_state["_llm_provider_blocked"] which
    render_main_content() reads at the st.chat_input call site. Reversing the
    order would leak stale blocked state across reruns (Phase 5 SC #3 + RESEARCH
    Pitfall 5).

    Phase 7 (SPL-02, SPL-04): `_run_splash_lifecycle()` runs AFTER
    `init_session_state()` (which creates `_splash_shown` /
    `_splash_placeholder` / `_splash_dismiss_sent`) and BEFORE the
    sidebar/main render so the splash mounts at the very top of the DOM
    during the boot window. First rerun mounts the splash; subsequent
    reruns either (a) do nothing if dismiss already sent, or (b) send the
    dismiss postMessage into the iframe and tear down the placeholder once
    data is ready. The 4s hard cap (SPL-02) is enforced entirely
    client-side inside the iframe.
    """
    init_session_state()
    _run_splash_lifecycle()  # Phase 7: mount + gate + dismiss boot splash
    render_sidebar()
    render_main_content()


if __name__ == "__main__":
    main()