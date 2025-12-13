"""
Insight - AI-Powered Incident Intelligence
Natural language query interface for ServiceNow incident data.
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
    page_title="Insight",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Mode mapping for UI
MODE_OPTIONS = {
    "Auto": "auto",
    "Structured": "structured",
    "Semantic": "semantic",
    "Hybrid": "hybrid"
}


def inject_custom_css():
    """Inject modern SaaS-style CSS."""
    st.markdown("""
<style>
    /* ============================================
       INSIGHT - MODERN SAAS THEME
       Dark mode with glassmorphism & blue accents
       ============================================ */

    /* Import fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* CSS Variables */
    :root {
        --bg-primary: #0f1117;
        --bg-secondary: #1a1d24;
        --bg-tertiary: #252830;
        --bg-glass: rgba(30, 34, 42, 0.7);
        --bg-glass-hover: rgba(40, 45, 55, 0.8);
        --border-subtle: rgba(255, 255, 255, 0.06);
        --border-medium: rgba(255, 255, 255, 0.1);
        --text-primary: #f0f2f5;
        --text-secondary: #9ca3af;
        --text-muted: #6b7280;
        --accent: #3b82f6;
        --accent-hover: #60a5fa;
        --accent-glow: rgba(59, 130, 246, 0.15);
        --accent-subtle: rgba(59, 130, 246, 0.1);
        --success: #22c55e;
        --success-bg: rgba(34, 197, 94, 0.1);
        --warning: #f59e0b;
        --warning-bg: rgba(245, 158, 11, 0.1);
        --error: #ef4444;
        --error-bg: rgba(239, 68, 68, 0.1);
        --gradient-accent: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
        --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
        --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.4);
        --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.5);
        --shadow-glow: 0 0 20px rgba(59, 130, 246, 0.2);
        --radius-sm: 6px;
        --radius-md: 10px;
        --radius-lg: 14px;
        --transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }

    /* Global Styles */
    .stApp {
        background: var(--bg-primary);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .stApp * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Hide Streamlit branding */
    #MainMenu, footer, header {visibility: hidden;}

    /* ============ SIDEBAR ============ */
    [data-testid="stSidebar"] {
        background: var(--bg-secondary);
        border-right: 1px solid var(--border-subtle);
    }

    [data-testid="stSidebar"] > div:first-child {
        padding: 1.5rem 1rem;
    }

    /* Sidebar text */
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] .stMarkdown {
        color: var(--text-secondary) !important;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
    }

    /* Sidebar sections */
    [data-testid="stSidebar"] hr {
        border-color: var(--border-subtle);
        margin: 1.5rem 0;
    }

    /* ============ TYPOGRAPHY ============ */
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
    }

    p, span, label, div {
        color: var(--text-secondary);
    }

    .stMarkdown p {
        color: var(--text-secondary);
        line-height: 1.6;
    }

    /* ============ BUTTONS ============ */
    .stButton > button {
        background: var(--bg-glass) !important;
        border: 1px solid var(--border-medium) !important;
        border-radius: var(--radius-md) !important;
        color: var(--text-primary) !important;
        font-weight: 500 !important;
        padding: 0.5rem 1rem !important;
        transition: var(--transition) !important;
        backdrop-filter: blur(10px);
    }

    .stButton > button:hover {
        background: var(--bg-glass-hover) !important;
        border-color: var(--accent) !important;
        box-shadow: var(--shadow-glow) !important;
        transform: translateY(-1px);
    }

    .stButton > button[kind="primary"],
    .stButton > button[data-testid="baseButton-primary"] {
        background: var(--gradient-accent) !important;
        border: none !important;
        box-shadow: var(--shadow-md) !important;
    }

    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="baseButton-primary"]:hover {
        box-shadow: var(--shadow-glow), var(--shadow-md) !important;
        transform: translateY(-1px);
    }

    /* ============ INPUTS ============ */
    .stTextInput > div > div > input,
    .stTextArea textarea,
    .stNumberInput input {
        background: var(--bg-tertiary) !important;
        border: 1px solid var(--border-medium) !important;
        border-radius: var(--radius-md) !important;
        color: var(--text-primary) !important;
        transition: var(--transition);
    }

    .stTextInput > div > div > input:focus,
    .stTextArea textarea:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px var(--accent-subtle) !important;
    }

    /* ============ SELECT BOX ============ */
    .stSelectbox > div > div,
    [data-baseweb="select"] {
        background: var(--bg-tertiary) !important;
        border-radius: var(--radius-md) !important;
    }

    [data-baseweb="select"] > div {
        background: var(--bg-tertiary) !important;
        border: 1px solid var(--border-medium) !important;
        border-radius: var(--radius-md) !important;
    }

    [data-baseweb="select"] * {
        color: var(--text-primary) !important;
    }

    [data-baseweb="popover"] {
        background: var(--bg-secondary) !important;
        border: 1px solid var(--border-medium) !important;
        border-radius: var(--radius-md) !important;
        box-shadow: var(--shadow-lg) !important;
    }

    [data-baseweb="menu"] {
        background: var(--bg-secondary) !important;
    }

    [data-baseweb="menu"] li {
        background: transparent !important;
        transition: var(--transition);
    }

    [data-baseweb="menu"] li:hover {
        background: var(--accent-subtle) !important;
    }

    /* ============ FILE UPLOADER ============ */
    [data-testid="stFileUploader"] {
        background: var(--bg-tertiary);
        border: 2px dashed var(--border-medium);
        border-radius: var(--radius-lg);
        padding: 1.5rem;
        transition: var(--transition);
    }

    [data-testid="stFileUploader"]:hover {
        border-color: var(--accent);
        background: var(--accent-subtle);
    }

    [data-testid="stFileUploader"] * {
        color: var(--text-secondary) !important;
    }

    [data-testid="stFileUploader"] button {
        background: var(--accent) !important;
        color: white !important;
        border: none !important;
        border-radius: var(--radius-sm) !important;
    }

    /* ============ METRICS ============ */
    [data-testid="stMetric"] {
        background: var(--bg-glass);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        padding: 1rem;
        backdrop-filter: blur(10px);
    }

    [data-testid="stMetricValue"] {
        color: var(--text-primary) !important;
        font-weight: 700 !important;
        font-size: 1.75rem !important;
    }

    [data-testid="stMetricLabel"] {
        color: var(--text-muted) !important;
        font-size: 0.8rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
    }

    /* ============ EXPANDERS ============ */
    .streamlit-expanderHeader,
    [data-testid="stExpander"] summary {
        background: var(--bg-glass) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: var(--radius-md) !important;
        color: var(--text-primary) !important;
        transition: var(--transition);
    }

    .streamlit-expanderHeader:hover,
    [data-testid="stExpander"] summary:hover {
        background: var(--bg-glass-hover) !important;
        border-color: var(--accent) !important;
    }

    [data-testid="stExpander"] {
        border: none !important;
    }

    .streamlit-expanderContent {
        background: var(--bg-tertiary) !important;
        border: 1px solid var(--border-subtle) !important;
        border-top: none !important;
        border-radius: 0 0 var(--radius-md) var(--radius-md) !important;
    }

    /* ============ CHAT ============ */
    [data-testid="stChatMessage"] {
        background: var(--bg-glass) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: var(--radius-lg) !important;
        padding: 1rem 1.25rem !important;
        margin: 0.75rem 0 !important;
        backdrop-filter: blur(10px);
    }

    [data-testid="stChatMessage"] * {
        color: var(--text-secondary) !important;
    }

    [data-testid="stChatMessage"] strong,
    [data-testid="stChatMessage"] h1,
    [data-testid="stChatMessage"] h2,
    [data-testid="stChatMessage"] h3 {
        color: var(--text-primary) !important;
    }

    [data-testid="stChatInput"] {
        border-radius: var(--radius-lg) !important;
        background: var(--bg-secondary) !important;
        border: 1px solid var(--border-medium) !important;
    }

    [data-testid="stChatInput"] textarea {
        background: transparent !important;
        color: var(--text-primary) !important;
    }

    [data-testid="stChatInput"] button {
        background: var(--accent) !important;
        border-radius: var(--radius-sm) !important;
    }

    /* ============ DATAFRAME ============ */
    [data-testid="stDataFrame"] {
        border: 1px solid var(--border-subtle) !important;
        border-radius: var(--radius-md) !important;
        overflow: hidden;
    }

    [data-testid="stDataFrame"] * {
        color: var(--text-secondary) !important;
        background: var(--bg-tertiary) !important;
    }

    [data-testid="stDataFrame"] [role="columnheader"] {
        background: var(--bg-secondary) !important;
        color: var(--text-primary) !important;
        font-weight: 600 !important;
    }

    /* ============ ALERTS ============ */
    .stSuccess {
        background: var(--success-bg) !important;
        border: 1px solid rgba(34, 197, 94, 0.3) !important;
        border-radius: var(--radius-md) !important;
        color: var(--success) !important;
    }

    .stWarning {
        background: var(--warning-bg) !important;
        border: 1px solid rgba(245, 158, 11, 0.3) !important;
        border-radius: var(--radius-md) !important;
        color: var(--warning) !important;
    }

    .stError {
        background: var(--error-bg) !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
        border-radius: var(--radius-md) !important;
        color: var(--error) !important;
    }

    .stInfo {
        background: var(--accent-subtle) !important;
        border: 1px solid rgba(59, 130, 246, 0.3) !important;
        border-radius: var(--radius-md) !important;
        color: var(--accent) !important;
    }

    /* ============ SLIDERS & CHECKBOXES ============ */
    .stSlider > div > div {
        color: var(--text-secondary) !important;
    }

    .stSlider [data-baseweb="slider"] div {
        background: var(--accent) !important;
    }

    .stCheckbox label {
        color: var(--text-secondary) !important;
    }

    .stCheckbox [data-testid="stCheckbox"] > div:first-child {
        background: var(--bg-tertiary) !important;
        border: 1px solid var(--border-medium) !important;
        border-radius: var(--radius-sm) !important;
    }

    /* ============ DOWNLOAD BUTTON ============ */
    .stDownloadButton > button {
        background: var(--bg-glass) !important;
        border: 1px solid var(--accent) !important;
        color: var(--accent) !important;
    }

    .stDownloadButton > button:hover {
        background: var(--accent-subtle) !important;
    }

    /* ============ CODE BLOCKS ============ */
    .stCode, code, pre {
        background: var(--bg-tertiary) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: var(--radius-md) !important;
        color: var(--accent-hover) !important;
    }

    /* ============ PROGRESS BAR ============ */
    .stProgress > div > div {
        background: var(--bg-tertiary) !important;
        border-radius: var(--radius-sm) !important;
    }

    .stProgress > div > div > div {
        background: var(--gradient-accent) !important;
        border-radius: var(--radius-sm) !important;
    }

    /* ============ SCROLLBAR ============ */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: var(--bg-primary);
    }

    ::-webkit-scrollbar-thumb {
        background: var(--bg-tertiary);
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--text-muted);
    }

    /* ============ CUSTOM COMPONENTS ============ */
    .insight-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        padding: 1rem 0 1.5rem 0;
        border-bottom: 1px solid var(--border-subtle);
        margin-bottom: 1.5rem;
    }

    .insight-logo {
        width: 48px;
        height: 48px;
        background: var(--gradient-accent);
        border-radius: var(--radius-md);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.5rem;
        font-weight: 700;
        color: white;
        box-shadow: var(--shadow-glow);
    }

    .insight-title {
        font-size: 1.75rem;
        font-weight: 700;
        color: var(--text-primary);
        letter-spacing: -0.5px;
    }

    .insight-subtitle {
        font-size: 0.85rem;
        color: var(--text-muted);
        margin-top: 2px;
    }

    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 0.75rem;
        margin: 1rem 0;
    }

    .stat-card {
        background: var(--bg-glass);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        padding: 1rem;
        text-align: center;
        backdrop-filter: blur(10px);
    }

    .stat-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--text-primary);
    }

    .stat-label {
        font-size: 0.7rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 4px;
    }

    .mode-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.35rem 0.75rem;
        background: var(--accent-subtle);
        border: 1px solid rgba(59, 130, 246, 0.3);
        border-radius: 20px;
        font-size: 0.75rem;
        color: var(--accent);
        font-weight: 500;
    }

    .section-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 1rem;
        color: var(--text-muted);
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .section-header::after {
        content: '';
        flex: 1;
        height: 1px;
        background: var(--border-subtle);
    }

    .summary-card {
        background: var(--bg-glass);
        border: 1px solid var(--border-subtle);
        border-left: 3px solid var(--accent);
        border-radius: var(--radius-md);
        padding: 1.25rem;
        margin: 1rem 0;
        backdrop-filter: blur(10px);
    }

    .summary-title {
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--accent);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.75rem;
    }

    .summary-content {
        color: var(--text-secondary);
        line-height: 1.7;
    }
</style>
""", unsafe_allow_html=True)


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
    mode_text = "Appending to" if append else "Loading"
    with st.spinner(f"{mode_text} CSV data..."):
        try:
            schema = load_csv(uploaded_file, append=append)
            st.session_state.schema = schema
            st.session_state.data_loaded = True

            if append:
                st.success(
                    f"✅ Appended data - now {schema['row_count']:,} total incidents"
                )
                logger.info(f"Appended data, total: {schema['row_count']} rows")
            else:
                st.success(
                    f"✅ Loaded {schema['row_count']:,} incidents "
                    f"with {len(schema['columns'])} columns"
                )
                logger.info(f"Successfully loaded {schema['row_count']} rows")

            st.rerun()
        except Exception as e:
            st.error(format_error_message(e))
            logger.exception("Failed to load CSV")


def render_sidebar():
    """Render the sidebar with data management controls."""
    with st.sidebar:
        # Sidebar header with branding
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1.5rem;">
            <div style="width: 36px; height: 36px; background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: 700; color: white; font-size: 1.1rem;">◆</div>
            <div>
                <div style="font-size: 1.1rem; font-weight: 600; color: #f0f2f5;">Insight</div>
                <div style="font-size: 0.7rem; color: #6b7280;">Incident Intelligence</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Data section header
        st.markdown('<div class="section-header">Data Source</div>', unsafe_allow_html=True)

        # CSV Upload
        uploaded_file = st.file_uploader(
            "Drop CSV or click to browse",
            type=["csv"],
            help="Upload a ServiceNow incident export",
            label_visibility="collapsed"
        )

        if uploaded_file is not None:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Replace", type="primary", use_container_width=True):
                    _load_csv_data(uploaded_file, append=False)
            with col2:
                if st.button("Append", use_container_width=True):
                    _load_csv_data(uploaded_file, append=True)

        st.divider()

        # Data status with custom stats grid
        st.markdown('<div class="section-header">Status</div>', unsafe_allow_html=True)

        if st.session_state.schema:
            schema = st.session_state.schema
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Incidents", f"{schema['row_count']:,}")
            with col2:
                st.metric("Fields", len(schema['columns']))
        elif table_exists():
            schema = get_schema_summary()
            if schema:
                st.session_state.schema = schema
                st.session_state.data_loaded = True
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Incidents", f"{schema['row_count']:,}")
                with col2:
                    st.metric("Fields", len(schema['columns']))
            else:
                st.caption("No data loaded yet")
        else:
            st.caption("Upload a CSV to get started")

        st.divider()

        # Embeddings section
        st.markdown('<div class="section-header">Vector Index</div>', unsafe_allow_html=True)

        if embeddings_exist():
            stats = get_embedding_stats()
            st.session_state.embeddings_ready = True
            st.success(f"{stats['document_count']:,} documents indexed")
        else:
            st.session_state.embeddings_ready = False
            st.warning("Index not built")

        if st.session_state.data_loaded:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Rebuild", use_container_width=True, help="Full rebuild"):
                    _build_embeddings_with_progress(force=True)
            with col2:
                if st.button("Update", use_container_width=True, help="Add new only"):
                    _build_embeddings_with_progress(force=False)

        st.divider()

        # Settings section
        st.markdown('<div class="section-header">Settings</div>', unsafe_allow_html=True)

        with st.expander("Query Options", expanded=False):
            st.session_state.top_k = st.slider(
                "Result limit",
                min_value=5,
                max_value=50,
                value=10,
                help="Max results for semantic search"
            )

            st.session_state.show_sql = st.checkbox(
                "Show SQL queries",
                value=True
            )

            st.session_state.show_summary = st.checkbox(
                "Generate summaries",
                value=True
            )


def _build_embeddings_with_progress(force: bool = False):
    """Build embeddings with progress display."""
    progress_bar = st.progress(0)
    status_text = st.empty()

    def progress_callback(progress: float, message: str):
        progress_bar.progress(progress)
        status_text.text(message)

    try:
        stats = build_embeddings(
            force_rebuild=force,
            progress_callback=progress_callback
        )
        st.session_state.embeddings_ready = True
        st.success(
            f"✅ Embedded {stats['total_embedded']:,} incidents "
            f"in {stats['time_taken']:.1f}s"
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

    with st.expander("Schema Details", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.caption("TABLE")
            st.markdown(f"**{schema['table_name']}**")
        with col2:
            st.caption("ROWS")
            st.markdown(f"**{schema['row_count']:,}**")

        # Create columns DataFrame
        cols_data = [
            {
                "Column": col["name"],
                "Type": col["type"],
                "Sample Value": col["sample"][:50] + "..." if len(col["sample"]) > 50 else col["sample"]
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

            # Display results if present
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
    # Executive summary with custom styling
    if executive_summary:
        st.markdown(f"""
        <div class="summary-card">
            <div class="summary-title">Executive Summary</div>
            <div class="summary-content">{executive_summary}</div>
        </div>
        """, unsafe_allow_html=True)

    # Results table
    display_df = format_dataframe_for_display(df)

    # Prioritize key columns
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
            label="Export CSV",
            data=csv_data,
            file_name=generate_export_filename("incidents"),
            mime="text/csv",
            key=f"export_{query_id}"
        )

    with col2:
        if sql and st.session_state.get("show_sql", True):
            with st.expander("View Generated SQL"):
                st.code(sql, language="sql")


def process_query(user_query: str, mode: str):
    """Process a user query and return formatted response."""
    if not st.session_state.schema:
        return {
            "content": "⚠️ No data loaded. Please upload a CSV file first.",
            "results": None,
            "sql": None
        }

    # Check for semantic queries without embeddings
    if mode in ["semantic", "hybrid", "auto"] and not st.session_state.embeddings_ready:
        if mode == "semantic":
            return {
                "content": "⚠️ No embeddings found. Please build embeddings first using the sidebar.",
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

        # Handle errors
        if result.get("error"):
            return {
                "content": f"❌ Error: {result['error']}",
                "results": None,
                "sql": result.get("sql")
            }

        # Build response content
        route_used = result.get("route_used", "unknown")
        classification = result.get("classification", {})
        confidence = classification.get("confidence", 0)
        reasoning = classification.get("reasoning", "")
        row_count = result.get("row_count", 0)
        explanation = result.get("explanation", "")

        # Format route display - clean, modern style
        route_labels = {
            "structured": "Structured",
            "semantic": "Semantic",
            "hybrid": "Hybrid"
        }

        content_parts = [
            f"**{route_labels.get(route_used, 'Unknown')}** route • {confidence:.0%} confidence"
        ]

        if reasoning:
            content_parts.append(f"*{reasoning}*")

        if row_count > 0:
            content_parts.append(f"Found **{row_count:,}** incidents")
        else:
            content_parts.append("No results found. Try adjusting your query or search mode.")

        # Generate executive summary if we have results
        executive_summary = None
        if row_count > 0 and st.session_state.get("show_summary", True):
            executive_summary = generate_executive_summary(
                user_query,
                result.get("results"),
                route_used
            )

        return {
            "content": "\n\n".join(content_parts),
            "results": result.get("results"),
            "sql": result.get("sql"),
            "executive_summary": executive_summary
        }

    except Exception as e:
        logger.exception("Error processing query")
        return {
            "content": f"❌ Error processing query: {str(e)}",
            "results": None,
            "sql": None
        }


def render_main_content():
    """Render the main content area."""
    # Custom header
    st.markdown("""
    <div class="insight-header">
        <div class="insight-logo">◆</div>
        <div>
            <div class="insight-title">Insight</div>
            <div class="insight-subtitle">AI-Powered Incident Intelligence</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.data_loaded:
        # Welcome state
        st.markdown("""
        <div style="text-align: center; padding: 3rem 1rem;">
            <div style="font-size: 3rem; margin-bottom: 1rem;">◇</div>
            <h2 style="margin-bottom: 0.5rem;">Welcome to Insight</h2>
            <p style="color: #9ca3af; max-width: 400px; margin: 0 auto 2rem auto;">
                Upload your ServiceNow incident data to unlock AI-powered natural language queries and analysis.
            </p>
        </div>
        """, unsafe_allow_html=True)

        # Example queries in a nice grid
        st.markdown("#### Try asking questions like:")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            - Show all P1 incidents from last month
            - How many incidents were opened this week?
            """)
        with col2:
            st.markdown("""
            - Find incidents similar to Outlook crashes
            - Top 5 assignment groups by volume
            """)
        return

    # Schema details
    render_schema_details()

    # Query interface header with mode selector
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("### Query Interface")

    with col2:
        selected_mode_label = st.selectbox(
            "Mode",
            options=list(MODE_OPTIONS.keys()),
            index=0,
            label_visibility="collapsed"
        )
        selected_mode = MODE_OPTIONS[selected_mode_label]

    # Mode badge
    mode_descriptions = {
        "auto": "AI selects the best approach",
        "structured": "SQL-based data retrieval",
        "semantic": "Vector similarity search",
        "hybrid": "Combined SQL + semantic"
    }
    st.markdown(f'<div class="mode-badge">{selected_mode_label} — {mode_descriptions.get(selected_mode, "")}</div>', unsafe_allow_html=True)

    # Chat history
    render_chat_history()

    # Query input
    if user_query := st.chat_input("Ask a question about your incidents..."):
        # Generate unique query ID
        query_id = datetime.now().strftime("%Y%m%d%H%M%S%f")

        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": user_query
        })

        # Display user message
        with st.chat_message("user"):
            st.markdown(user_query)

        # Process and display response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing your query..."):
                response = process_query(user_query, selected_mode)

            st.markdown(response["content"])

            if response["results"] is not None and not response["results"].empty:
                display_results(
                    response["results"],
                    response["sql"],
                    query_id,
                    response.get("executive_summary")
                )

        # Save assistant message
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
        st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)
        if st.button("Clear conversation", type="secondary"):
            st.session_state.messages = []
            st.rerun()


def main():
    """Main application entry point."""
    inject_custom_css()
    init_session_state()
    render_sidebar()
    render_main_content()


if __name__ == "__main__":
    main()
