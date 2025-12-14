"""
SNOWGREP - ServiceNow Incident Query Tool
Brutalist Terminal-Style Interface
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from src.embeddings import (
    build_embeddings,
    embeddings_exist,
    get_embedding_stats,
)
from src.ingest import get_schema_summary, load_csv, table_exists
from src.query_router import generate_executive_summary, get_mode_description, route_query
from src.utils import (
    dataframe_to_csv_bytes,
    format_dataframe_for_display,
    format_error_message,
    generate_export_filename,
    logger,
)

# Page configuration
st.set_page_config(
    page_title="SNOWGREP",
    page_icon="▣",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# CLEANED CSS INJECTION (replaces the previous BRUTALIST block)
# - Hides textual icon fallbacks (e.g., "keyboard_arrow_down") using
#   a visual-hide technique (text-indent/clip) that preserves layout.
# - Avoids non-standard selectors like :contains and avoids hiding SVGs.
# ============================================================
st.markdown("""
<style>
    /* Import monospace font AND Material Icons */
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700;800&display=swap');
    @import url('https://fonts.googleapis.com/icon?family=Material+Icons');

    /* ===== GLOBAL RESET ===== */
    .stApp {
        background-color: #0a0a0a;
        font-family: 'JetBrains Mono', 'Courier New', monospace;
    }

    /* Hide Streamlit branding */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    .stDeployButton { display: none; }

    /* ===== ALWAYS VISIBLE SIDEBAR ===== */
    [data-testid="collapsedControl"] { display: none !important; }
    [data-testid="stSidebar"] { min-width: 300px !important; max-width: 300px !important; transform: none !important; position: relative !important; }
    [data-testid="stSidebar"] > div:first-child { width: 300px !important; }
    button[kind="header"] { display: none !important; }
    [data-testid="stSidebar"][aria-expanded] { transform: none !important; transition: none !important; }

    /* ===== ICONS: Robust fix for Material Icons fallback text ===== */
    /*
      Goal: visually hide textual fallbacks such as "keyboard_arrow_down"
      while keeping actual icons visible (SVG or properly-rendered ligatures).
      We do this by visually hiding raw text nodes in icon-font containers but
      allowing SVG children or correctly-rendered ligatures to show.
    */
    .material-icons,
    [class*="material-icons"],
    [data-testid="stIconMaterial"] {
        font-family: 'Material Icons' !important;
        speak: none;
        display: inline-block;
        width: 1rem;
        height: 1rem;
        line-height: 1rem;
        vertical-align: middle;

        /* visually hide raw text content (safe technique) */
        text-indent: 100%;
        white-space: nowrap;
        overflow: hidden;
        clip: rect(0 0 0 0);
        clip-path: inset(50%);
    }

    /* Ensure any SVG children inside icon containers are visible and sized */
    .material-icons svg,
    [class*="material-icons"] svg,
    [data-testid="stIconMaterial"] svg,
    svg[data-testid] {
        display: inline-block !important;
        width: 1rem !important;
        height: 1rem !important;
        fill: currentColor !important;
        color: inherit !important;
        clip-path: none !important;
        text-indent: 0 !important;
        overflow: visible !important;
    }

    /* Additional safe targets: if streamlit outputs a generic icon container class */
    [class*="icon-"],
    [data-testid*="Icon"] {
        text-indent: 100%;
        white-space: nowrap;
        overflow: hidden;
        clip: rect(0 0 0 0);
        clip-path: inset(50%);
        display: inline-block;
        width: 1rem;
        height: 1rem;
        line-height: 1rem;
        vertical-align: middle;
    }
    [data-testid*="Icon"] svg { display: inline-block !important; width:1rem !important; height:1rem !important; }

    /* ===== FIX EXPANDER ICON TEXT FALLBACK ===== */
    /*
      Hide the textual node that may appear to the right of the expander summary.
      Visual-hide preserves layout and leaves SVG arrow intact.
    */
    [data-testid="stExpander"] summary > div:last-child,
    [data-testid="stExpander"] summary > div:last-child * {
        text-indent: 100%;
        white-space: nowrap;
        overflow: hidden;
        clip: rect(0 0 0 0);
        clip-path: inset(50%);
        display: inline-block;
        width: 1rem;
        height: 1rem;
        line-height: 1rem;
        vertical-align: middle;
    }

    /* Ensure SVG arrow inside expanders remains visible and styled */
    [data-testid="stExpander"] summary svg {
        display: inline-block !important;
        width: 1rem !important;
        height: 1rem !important;
        color: #00ff00 !important;
        fill: currentColor !important;
        vertical-align: middle;
        margin-left: 0.25rem;
    }

    /* Provide a clear, custom text indicator for expanders so UX is preserved */
    [data-testid="stExpander"] summary {
        position: relative;
    }
    [data-testid="stExpander"] summary::before {
        content: "[+] ";
        color: #00ff00;
        font-family: 'JetBrains Mono', monospace;
        margin-right: 0.5rem;
        font-size: 0.85rem;
    }
    [data-testid="stExpander"][open] summary::before,
    details[open] summary::before {
        content: "[-] ";
    }

    /* ===== TYPOGRAPHY ===== */
    h1, h2, h3, h4, h5, h6, p, span, div, label {
        font-family: 'JetBrains Mono', 'Courier New', monospace !important;
        color: #e0e0e0;
    }
    h1 {
        font-size: 2rem !important;
        font-weight: 800 !important;
        text-transform: uppercase !important;
        letter-spacing: -1px !important;
        color: #fff !important;
        border-bottom: 3px solid #00ff00 !important;
        padding-bottom: 0.5rem !important;
    }
    h2, .stSubheader {
        font-size: 1rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
        color: #00ff00 !important;
    }
    h3 { font-size: 0.9rem !important; font-weight: 700 !important; text-transform: uppercase !important; letter-spacing: 1px !important; color: #888 !important; }

    /* ===== SIDEBAR ===== */
    [data-testid="stSidebar"] {
        background-color: #111 !important;
        border-right: 2px solid #00ff00 !important;
        min-width: 300px !important;
        max-width: 300px !important;
        width: 300px !important;
    }
    [data-testid="stSidebar"] > div { background-color: #111 !important; padding-top: 1rem !important; }
    [data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3 { color: #00ff00 !important; }
    [data-testid="stSidebar"] .stMarkdown p { color: #888 !important; font-size: 0.8rem !important; }
    [data-testid="stSidebar"] [data-testid="stHeadingWithActionElements"] { border-bottom: 1px solid #333; padding-bottom: 0.5rem; margin-bottom: 1rem; }

    /* ===== BUTTONS ===== */
    .stButton > button {
        font-family: 'JetBrains Mono', monospace !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        font-size: 0.75rem !important;
        font-weight: 700 !important;
        border-radius: 0 !important;
        border: 2px solid #00ff00 !important;
        background-color: #0a0a0a !important;
        color: #00ff00 !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.1s ease !important;
    }
    .stButton > button:hover { background-color: #00ff00 !important; color: #0a0a0a !important; }
    .stButton > button[kind="primary"] { background-color: #00ff00 !important; color: #0a0a0a !important; }
    .stButton > button[kind="primary"]:hover { background-color: #00cc00 !important; }

    /* Download button */
    .stDownloadButton > button { font-family: 'JetBrains Mono', monospace !important; text-transform: uppercase !important; letter-spacing: 1px !important; font-size: 0.75rem !important; border-radius: 0 !important; border: 2px solid #00ff00 !important; background-color: #0a0a0a !important; color: #00ff00 !important; }
    .stDownloadButton > button:hover { background-color: #00ff00 !important; color: #0a0a0a !important; }

    /* ===== INPUTS ===== */
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        font-family: 'JetBrains Mono', monospace !important;
        background-color: #111 !important;
        border: 2px solid #333 !important;
        border-radius: 0 !important;
        color: #00ff00 !important;
        font-size: 0.85rem !important;
    }
    .stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus { border-color: #00ff00 !important; box-shadow: none !important; }

    /* Chat input */
    .stChatInput > div { background-color: #111 !important; border: 2px solid #00ff00 !important; border-radius: 0 !important; }
    .stChatInput textarea { font-family: 'JetBrains Mono', monospace !important; color: #00ff00 !important; background-color: transparent !important; }

    /* Selectbox styling */
    .stSelectbox > div > div { background-color: #111 !important; border: 2px solid #333 !important; border-radius: 0 !important; }
    .stSelectbox > div > div:hover { border-color: #00ff00 !important; }
    .stSelectbox [data-baseweb="select"] { background-color: #111 !important; }
    .stSelectbox [data-baseweb="select"] > div { background-color: #111 !important; border: none !important; }
    .stSelectbox [data-baseweb="select"] svg { color: #00ff00 !important; fill: #00ff00 !important; width:1rem !important; height:1rem !important; }

    /* Hide any icon font text in selectbox containers via visual-hide (keeps SVG) */
    .stSelectbox [data-baseweb="select"] [data-testid="stIconMaterial"],
    .stSelectbox [data-baseweb="select"] [class*="material-icons"] {
        text-indent: 100%;
        white-space: nowrap;
        overflow: hidden;
        clip: rect(0 0 0 0);
        clip-path: inset(50%);
        display: inline-block;
        width: 1rem;
        height: 1rem;
        line-height: 1rem;
    }

    /* Dropdown menu styling */
    [data-baseweb="popover"] { background-color: #111 !important; border: 2px solid #00ff00 !important; border-radius: 0 !important; }
    [data-baseweb="menu"] { background-color: #111 !important; }
    [data-baseweb="menu"] li { font-family: 'JetBrains Mono', monospace !important; background-color: #111 !important; color: #888 !important; }
    [data-baseweb="menu"] li:hover { background-color: #1a1a1a !important; color: #00ff00 !important; }

    /* Slider, checkbox, uploader, metrics, dataframes, alerts etc. (kept as before) */
    .stSlider > div > div > div > div { background-color: #00ff00 !important; }
    .stSlider [data-baseweb="slider"] [role="slider"] { background-color: #00ff00 !important; }
    .stCheckbox label span { color: #888 !important; font-size: 0.8rem !important; }
    .stFileUploader > div { background-color: #111 !important; border: 2px dashed #333 !important; border-radius: 0 !important; }
    .stFileUploader > div:hover { border-color: #00ff00 !important; }
    .stFileUploader label { color: #888 !important; }

    /* Metric styles */
    [data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace !important; font-size: 2rem !important; font-weight: 800 !important; color: #00ff00 !important; }
    [data-testid="stMetricLabel"] { font-family: 'JetBrains Mono', monospace !important; text-transform: uppercase !important; letter-spacing: 2px !important; font-size: 0.7rem !important; color: #666 !important; }
    [data-testid="stMetricDelta"] { font-family: 'JetBrains Mono', monospace !important; }

    /* Dataframe */
    .stDataFrame { border: 2px solid #333 !important; }
    .stDataFrame [data-testid="stDataFrameResizable"] { background-color: #111 !important; }

    /* Alerts */
    .stSuccess { background-color: rgba(0, 255, 0, 0.1) !important; border: 1px solid #00ff00 !important; border-radius: 0 !important; color: #00ff00 !important; }
    .stWarning { background-color: rgba(255, 189, 46, 0.1) !important; border: 1px solid #ffbd2e !important; border-radius: 0 !important; color: #ffbd2e !important; }
    .stError { background-color: rgba(255, 95, 86, 0.1) !important; border: 1px solid #ff5f56 !important; border-radius: 0 !important; color: #ff5f56 !important; }
    .stInfo { background-color: rgba(0, 255, 0, 0.05) !important; border: 1px solid #333 !important; border-radius: 0 !important; color: #888 !important; }

    /* ===== EXPANDER VISUALS ===== */
    [data-testid="stExpander"] { border: 1px solid #333 !important; border-radius: 0 !important; background-color: #111 !important; }
    [data-testid="stExpander"] summary {
        font-family: 'JetBrains Mono', monospace !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        font-size: 0.8rem !important;
        background-color: #111 !important;
        border-radius: 0 !important;
        color: #888 !important;
        padding: 0.75rem 1rem !important;
    }
    [data-testid="stExpander"] summary:hover { color: #00ff00 !important; }
    [data-testid="stExpander"] > details > div { background-color: #0d0d0d !important; border: 1px solid #333 !important; border-top: none !important; border-radius: 0 !important; padding: 1rem !important; }

    .streamlit-expanderHeader { font-family: 'JetBrains Mono', monospace !important; text-transform: uppercase !important; letter-spacing: 1px !important; font-size: 0.8rem !important; background-color: #111 !important; border: 1px solid #333 !important; border-radius: 0 !important; color: #888 !important; }
    .streamlit-expanderHeader:hover { border-color: #00ff00 !important; color: #00ff00 !important; }
    .streamlit-expanderContent { background-color: #0d0d0d !important; border: 1px solid #333 !important; border-top: none !important; border-radius: 0 !important; }

    /* ===== MISC LAYOUT / UI CLASSES (kept) ===== */
    hr { border-color: #333 !important; }
    .terminal-header { background: #111; border: 2px solid #00ff00; padding: 1rem 1.5rem; margin-bottom: 2rem; display: flex; align-items: center; gap: 1rem; }
    .terminal-header-icon { width: 50px; height: 50px; border: 2px solid #00ff00; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; color: #00ff00; font-weight: 800; }
    .terminal-header-text h1 { margin: 0 !important; padding: 0 !important; border: none !important; font-size: 1.5rem !important; }
    .terminal-header-text p { margin: 0; font-size: 0.7rem; color: #666; text-transform: uppercase; letter-spacing: 2px; }

    .status-bar { display: flex; gap: 2rem; padding: 0.75rem 0; border-top: 1px solid #333; border-bottom: 1px solid #333; margin: 1rem 0; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; color: #666; }
    .status-item { display: flex; align-items: center; gap: 0.5rem; }
    .status-dot { width: 8px; height: 8px; border-radius: 50%; }
    .status-dot.green { background-color: #00ff00; }
    .status-dot.yellow { background-color: #ffbd2e; }
    .status-dot.red { background-color: #ff5f56; }

    .route-badge { display: inline-block; padding: 0.25rem 0.75rem; border: 1px solid; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; margin-right: 0.5rem; }
    .route-badge.structured { border-color: #00ff00; color: #00ff00; }
    .route-badge.semantic { border-color: #ff00ff; color: #ff00ff; }
    .route-badge.hybrid { border-color: #00ffff; color: #00ffff; }

    .results-count { font-size: 2rem; font-weight: 800; color: #00ff00; }
    .query-box { background: #0d0d0d; border: 1px solid #333; padding: 1rem; margin: 0.5rem 0; font-size: 0.8rem; }
    .example-query { background: #111; border-left: 3px solid #333; padding: 0.75rem 1rem; margin: 0.5rem 0; font-size: 0.8rem; color: #888; cursor: pointer; transition: all 0.1s ease; }
    .example-query:hover { border-color: #00ff00; color: #00ff00; }
    .example-query::before { content: "> "; color: #00ff00; }

    /* Final safety: ensure SVG icons generally visible */
    svg { fill: currentColor; display: inline-block; }

</style>
""", unsafe_allow_html=True)

# Mode mapping for UI
MODE_OPTIONS = {
    "AUTO": "auto",
    "REPORT [SQL]": "structured",
    "SIMILAR [SEMANTIC]": "semantic",
    "ANALYZE [HYBRID]": "hybrid"
}


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
        # Logo header
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 2px solid #00ff00;">
            <div style="width: 40px; height: 40px; border: 2px solid #00ff00; display: flex; align-items: center; justify-content: center; font-size: 1.2rem; color: #00ff00; font-weight: 800;">S</div>
            <div>
                <div style="font-size: 1.1rem; font-weight: 800; color: #fff; letter-spacing: -0.5px;">SNOWGREP</div>
                <div style="font-size: 0.6rem; color: #666; text-transform: uppercase; letter-spacing: 1px;">INCIDENT QUERY</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### DATA INGEST")

        # CSV Upload
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

        st.divider()

        # Display current data status
        st.markdown("### DATA STATUS")

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
                st.markdown('<div class="status-item"><div class="status-dot red"></div>NO DATA</div>', unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="color: #666; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px;">
                <span style="color: #ff5f56;">●</span> NO DATA LOADED
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # Embeddings management
        st.markdown("### EMBEDDINGS")

        if embeddings_exist():
            stats = get_embedding_stats()
            st.session_state.embeddings_ready = True
            st.markdown(f"""
            <div style="color: #00ff00; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px;">
                <span>●</span> {stats['document_count']:,} DOCS INDEXED
            </div>
            """, unsafe_allow_html=True)
        else:
            st.session_state.embeddings_ready = False
            st.markdown("""
            <div style="color: #ffbd2e; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px;">
                <span>●</span> NO EMBEDDINGS
            </div>
            """, unsafe_allow_html=True)

        if st.session_state.data_loaded:
            st.write("")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("REBUILD", use_container_width=True):
                    _build_embeddings_with_progress(force=True)
            with col2:
                if st.button("UPDATE", use_container_width=True):
                    _build_embeddings_with_progress(force=False)

        st.divider()

        # Settings
        st.markdown("### CONFIG")

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
            st.markdown(message["content"])

            if "results" in message and message["results"] is not None:
                if not message["results"].empty:
                    display_results(
                        message["results"],
                        message.get("sql"),
                        message.get("query_id", ""),
                        message.get("executive_summary")
                    )


def display_results(df: pd.DataFrame, sql: str | None, query_id: str, executive_summary: str | None = None):
    """Display query results with formatting and export."""
    # Executive summary
    if executive_summary:
        st.markdown("### EXECUTIVE SUMMARY")
        st.markdown(f'<div class="query-box">{executive_summary}</div>', unsafe_allow_html=True)
        st.divider()

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

        return {
            "content": "".join(content_parts),
            "results": result.get("results"),
            "sql": result.get("sql"),
            "executive_summary": executive_summary
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
    if user_query := st.chat_input("ENTER QUERY..."):
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

            st.markdown(response["content"], unsafe_allow_html=True)

            if response["results"] is not None and not response["results"].empty:
                display_results(
                    response["results"],
                    response["sql"],
                    query_id,
                    response.get("executive_summary")
                )

        st.session_state.messages.append({
            "role": "assistant",
            "content": response["content"],
            "results": response["results"],
            "sql": response["sql"],
            "query_id": query_id,
            "executive_summary": response.get("executive_summary")
        })

    # Clear chat button
    if st.session_state.messages:
        if st.button("CLEAR HISTORY"):
            st.session_state.messages = []
            st.rerun()


def main():
    """Main application entry point."""
    init_session_state()
    render_sidebar()
    render_main_content()


if __name__ == "__main__":
    main()