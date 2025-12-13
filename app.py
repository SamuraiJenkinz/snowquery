"""
SnowGrep - Natural Language Incident Query Tool
Main entry point for the query interface.
"""
from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path

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
    page_title="SnowGrep",
    page_icon="▣",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Mode mapping for UI
MODE_OPTIONS = {
    "AUTO": "auto",
    "REPORT [SQL]": "structured",
    "SIMILAR [VECTOR]": "semantic",
    "ANALYZE [HYBRID]": "hybrid"
}

# Geometric symbols mapping
SYMBOLS = {
    "data": "▣",
    "status": "◈",
    "embeddings": "◎",
    "settings": "☰",
    "replace": "↻",
    "append": "+",
    "rebuild": "◇",
    "update": "△",
    "structured": "▤",
    "semantic": "◉",
    "hybrid": "⬡",
    "query": "▷",
    "results": "◫",
    "export": "↓",
    "sql": "⌘",
    "schema": "▦",
    "clear": "×",
    "success": "✓",
    "warning": "!",
    "error": "×",
    "info": "○"
}


def load_logo_base64():
    """Load logo as base64 for embedding in HTML."""
    logo_path = Path(__file__).parent / "snowgrep-badge.png"
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None


# Custom CSS injection
def inject_custom_css():
    """Inject brutalist CSS styling."""
    logo_b64 = load_logo_base64()
    logo_css = ""
    if logo_b64:
        logo_css = f"""
        .logo-img {{
            height: 40px;
            margin-right: 12px;
        }}
        """

    st.markdown(f"""
<style>
    /* Import monospace font */
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700;800&display=swap');

    /* ============================================
       DARK BRUTALIST THEME
       ============================================ */

    /* Color Variables - Brutalist Green */
    :root {{
        --bg-main: #0a0a0a;
        --bg-sidebar: #111111;
        --bg-card: #1a1a1a;
        --bg-input: #2a2a2a;
        --text-primary: #ffffff;
        --text-secondary: #888888;
        --text-muted: #666666;
        --border-color: #333333;
        --accent: #00ff00;
        --accent-dim: #00cc00;
        --success: #00ff00;
        --warning: #ffcc00;
        --error: #ff4444;
    }}

    /* Global styles */
    .stApp, .stApp * {{
        font-family: 'JetBrains Mono', monospace;
    }}

    .stApp {{
        background-color: var(--bg-main);
        color: var(--text-primary);
    }}

    /* Force light text globally */
    .stApp p, .stApp span, .stApp div, .stApp label,
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6,
    .stApp li, .stApp td, .stApp th, .stApp caption,
    .stApp strong, .stApp em, .stApp b, .stApp i {{
        color: var(--text-primary) !important;
    }}

    /* Hide Streamlit branding but keep sidebar toggle */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header [data-testid="stToolbar"] {{visibility: hidden;}}
    header [data-testid="stDecoration"] {{visibility: hidden;}}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background-color: var(--bg-sidebar) !important;
        border-right: 1px solid var(--border-color) !important;
        padding-top: 1rem;
        min-width: 280px !important;
        width: 280px !important;
    }}

    [data-testid="stSidebar"] > div:first-child {{
        padding: 1rem;
        width: 100% !important;
    }}

    [data-testid="stSidebar"][aria-expanded="true"] {{
        display: block !important;
        visibility: visible !important;
    }}

    /* Sidebar collapse button */
    [data-testid="stSidebar"] button[kind="header"] {{
        color: var(--text-primary) !important;
    }}

    [data-testid="stSidebar"] * {{
        color: var(--text-primary) !important;
    }}

    [data-testid="stSidebar"] small {{
        color: var(--text-secondary) !important;
    }}

    /* Sidebar section headers */
    [data-testid="stSidebar"] h3 {{
        font-size: 0.85rem !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
        margin-bottom: 1rem !important;
        margin-top: 0.5rem !important;
        color: var(--text-primary) !important;
        display: flex !important;
        align-items: center !important;
        gap: 0.5rem !important;
    }}

    /* Sidebar section with icon styling */
    [data-testid="stSidebar"] h3::before {{
        content: '▣';
        color: var(--accent);
        font-size: 1rem;
    }}

    /* Logo styling */
    {logo_css}

    /* Brutalist Header */
    .brutalist-header {{
        display: flex;
        align-items: center;
        padding: 1rem 1.5rem;
        background: var(--bg-main);
        border: 3px solid var(--accent);
        margin-bottom: 1.5rem;
        gap: 1rem;
    }}

    .logo-box {{
        width: 60px;
        height: 60px;
        border: 3px solid var(--accent);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2rem;
        font-weight: 800;
        color: var(--accent);
        flex-shrink: 0;
    }}

    .header-text {{
        display: flex;
        flex-direction: column;
    }}

    .header-title {{
        font-size: 2rem;
        font-weight: 800;
        color: var(--text-primary);
        letter-spacing: 4px;
        text-transform: uppercase;
    }}

    .header-subtitle {{
        font-size: 0.75rem;
        color: var(--text-secondary);
        letter-spacing: 3px;
        text-transform: uppercase;
    }}

    /* Stats bar */
    .stats-bar {{
        display: flex;
        gap: 2rem;
        padding: 0.5rem 0;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: var(--text-secondary);
        border-bottom: 1px solid var(--border-color);
        margin-bottom: 1rem;
    }}

    .stats-bar span {{
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }}

    .stats-value {{
        color: var(--text-primary);
        font-weight: 700;
    }}

    /* Success box styling */
    .success-box {{
        background: rgba(0, 255, 0, 0.15);
        border: 1px solid var(--accent);
        padding: 0.75rem 1rem;
        margin: 0.5rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        color: var(--accent);
        font-size: 0.85rem;
    }}

    .success-box .checkmark {{
        color: var(--accent);
    }}

    /* File uploader styling */
    [data-testid="stFileUploader"] {{
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 0 !important;
        padding: 0.75rem !important;
    }}

    [data-testid="stFileUploader"] * {{
        color: var(--text-primary) !important;
    }}

    [data-testid="stFileUploader"] section {{
        background-color: transparent !important;
        border: 1px dashed var(--border-color) !important;
        padding: 1rem !important;
    }}

    [data-testid="stFileUploader"] section > div {{
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        gap: 0.5rem !important;
    }}

    [data-testid="stFileUploader"] button {{
        background-color: var(--bg-input) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 0 !important;
        padding: 0.5rem 1rem !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.75rem !important;
        text-transform: uppercase !important;
    }}

    [data-testid="stFileUploader"] small,
    [data-testid="stFileUploader"] span,
    [data-testid="stFileUploader"] p {{
        color: var(--text-muted) !important;
        font-size: 0.75rem !important;
    }}

    /* Drag drop icon */
    [data-testid="stFileUploader"] svg {{
        stroke: var(--text-muted) !important;
        fill: none !important;
    }}

    /* Executive summary box */
    .summary-box {{
        border: 1px solid var(--border-color);
        padding: 1.25rem;
        background: var(--bg-card);
        margin: 1rem 0;
        border-radius: 0;
    }}

    .summary-box h4 {{
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 1rem;
        color: var(--accent);
    }}

    .summary-content {{
        font-size: 0.85rem;
        line-height: 1.7;
        color: var(--text-primary);
    }}

    /* Buttons */
    .stButton > button {{
        font-family: 'JetBrains Mono', monospace !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        border-radius: 0 !important;
        border: none !important;
        background: var(--bg-input) !important;
        color: var(--text-primary) !important;
        padding: 0.5rem 1rem !important;
        font-size: 0.75rem !important;
    }}

    .stButton > button:hover {{
        background: var(--border-color) !important;
    }}

    .stButton > button[kind="secondary"] {{
        background: transparent !important;
        border: 1px solid var(--border-color) !important;
        color: var(--text-primary) !important;
    }}

    /* Inputs */
    .stTextInput > div > div > input,
    .stNumberInput input,
    .stTextArea textarea {{
        font-family: 'JetBrains Mono', monospace !important;
        border-radius: 0 !important;
        border: 1px solid var(--border-color) !important;
        background-color: var(--bg-input) !important;
        color: var(--text-primary) !important;
    }}

    /* Selectbox */
    .stSelectbox > div > div {{
        border-radius: 0 !important;
    }}

    .stSelectbox [data-baseweb="select"],
    [data-baseweb="select"] {{
        background-color: var(--bg-input) !important;
        border-radius: 0 !important;
    }}

    .stSelectbox [data-baseweb="select"] *,
    [data-baseweb="select"] * {{
        color: var(--text-primary) !important;
    }}

    /* Dropdown menu */
    [data-baseweb="popover"] {{
        border-radius: 0 !important;
    }}

    [data-baseweb="menu"] {{
        background-color: var(--bg-card) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 0 !important;
    }}

    [data-baseweb="menu"] li {{
        background-color: var(--bg-card) !important;
    }}

    [data-baseweb="menu"] li:hover {{
        background-color: var(--bg-input) !important;
    }}

    /* Chat input - brutalist green */
    [data-testid="stChatInput"] {{
        background-color: var(--bg-card) !important;
        border-radius: 0 !important;
        border: 1px solid var(--border-color) !important;
        padding: 0.5rem !important;
    }}

    [data-testid="stChatInput"] textarea {{
        font-family: 'JetBrains Mono', monospace !important;
        border-radius: 0 !important;
        border: 1px solid var(--border-color) !important;
        background-color: var(--bg-input) !important;
        color: var(--text-primary) !important;
        text-transform: uppercase !important;
        letter-spacing: 1px !important;
    }}

    [data-testid="stChatInput"] textarea::placeholder {{
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
        color: var(--text-muted) !important;
    }}

    [data-testid="stChatInput"] button {{
        background-color: var(--bg-input) !important;
        border: none !important;
        border-radius: 0 !important;
        color: var(--text-primary) !important;
    }}

    [data-testid="stChatInput"] button:hover {{
        background-color: var(--border-color) !important;
    }}

    /* Metrics */
    [data-testid="stMetricValue"] {{
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        color: var(--text-primary) !important;
    }}

    [data-testid="stMetricLabel"] {{
        font-family: 'JetBrains Mono', monospace !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        font-size: 0.7rem !important;
        color: var(--text-secondary) !important;
    }}

    /* Expanders */
    .streamlit-expanderHeader,
    [data-testid="stExpander"] summary {{
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.85rem !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 0 !important;
        background-color: var(--bg-card) !important;
        color: var(--text-primary) !important;
        padding: 0.75rem 1rem !important;
    }}

    .streamlit-expanderHeader:hover {{
        background-color: var(--bg-input) !important;
    }}

    .streamlit-expanderContent {{
        background-color: var(--bg-main) !important;
        border: 1px solid var(--border-color) !important;
        border-top: none !important;
        color: var(--text-primary) !important;
    }}

    [data-testid="stExpander"] {{
        border: 1px solid var(--border-color) !important;
        border-radius: 0 !important;
    }}

    /* Dataframe */
    .stDataFrame {{
        border: 1px solid var(--border-color);
        border-radius: 0;
    }}

    .stDataFrame th, .stDataFrame td,
    [data-testid="stDataFrame"] th,
    [data-testid="stDataFrame"] td,
    [data-testid="stDataFrame"] [role="gridcell"],
    [data-testid="stDataFrame"] [role="columnheader"] {{
        color: var(--text-primary) !important;
        background-color: var(--bg-card) !important;
    }}

    [data-testid="stDataFrame"] [role="columnheader"] {{
        background-color: var(--bg-input) !important;
        font-weight: 700 !important;
    }}

    .dvn-scroller, .dvn-scroller *,
    [data-testid="glideDataEditor"],
    [data-testid="glideDataEditor"] * {{
        color: var(--text-primary) !important;
        background-color: var(--bg-card) !important;
    }}

    /* Chat messages */
    [data-testid="stChatMessage"] {{
        font-family: 'JetBrains Mono', monospace;
        border: 1px solid var(--border-color);
        border-radius: 0 !important;
        padding: 1rem;
        margin: 0.5rem 0;
        background-color: var(--bg-card) !important;
        color: var(--text-primary) !important;
    }}

    [data-testid="stChatMessage"] * {{
        color: var(--text-primary) !important;
    }}

    /* Alerts */
    .stSuccess, .stWarning, .stError, .stInfo,
    [data-testid="stAlert"] {{
        font-family: 'JetBrains Mono', monospace;
        border-radius: 0 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-size: 0.8rem;
    }}

    .stSuccess, .stSuccess * {{ color: var(--success) !important; }}
    .stWarning, .stWarning * {{ color: var(--warning) !important; }}
    .stError, .stError * {{ color: var(--error) !important; }}

    /* Download button */
    .stDownloadButton > button {{
        font-family: 'JetBrains Mono', monospace !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        border-radius: 0 !important;
        border: 1px solid var(--border-color) !important;
        font-size: 0.75rem !important;
        background-color: var(--bg-input) !important;
        color: var(--text-primary) !important;
    }}

    /* Slider, Checkbox, Radio */
    .stSlider label, .stSlider p, .stSlider span,
    .stCheckbox label, .stCheckbox span,
    .stRadio label {{
        color: var(--text-primary) !important;
    }}

    .stCheckbox label, .stRadio label {{
        font-size: 0.8rem;
    }}

    /* Divider */
    hr {{
        border: none;
        border-top: 1px solid var(--border-color);
        margin: 1.5rem 0;
    }}

    /* Code blocks */
    .stApp code, .stApp pre {{
        background-color: var(--bg-input) !important;
        color: var(--success) !important;
        padding: 0.2em 0.4em !important;
        border-radius: 0 !important;
    }}

    /* Spinner */
    .stSpinner > div {{
        color: var(--text-primary) !important;
    }}

    /* Markdown */
    .stMarkdown, .stMarkdown * {{
        color: var(--text-primary) !important;
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        background-color: var(--bg-card) !important;
        border-radius: 0 !important;
    }}

    .stTabs [data-baseweb="tab"] {{
        color: var(--text-primary) !important;
        border-radius: 0 !important;
    }}

    /* Divider lines */
    [data-testid="stSidebar"] hr {{
        border-color: var(--border-color);
        margin: 1.5rem 0;
    }}

    /* Scrollbar */
    ::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}

    ::-webkit-scrollbar-track {{
        background: var(--bg-main);
    }}

    ::-webkit-scrollbar-thumb {{
        background: var(--border-color);
        border-radius: 0;
    }}

    ::-webkit-scrollbar-thumb:hover {{
        background: var(--text-muted);
    }}
</style>
""", unsafe_allow_html=True)


def render_header():
    """Render the brutalist header with S logo box."""
    st.markdown("""
<div class="brutalist-header">
    <div class="logo-box">S</div>
    <div class="header-text">
        <div class="header-title">SNOWGREP</div>
        <div class="header-subtitle">SERVICENOW INCIDENT QUERY</div>
    </div>
</div>
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
    mode_text = "APPENDING" if append else "LOADING"
    with st.spinner(f"{mode_text} DATA..."):
        try:
            schema = load_csv(uploaded_file, append=append)
            st.session_state.schema = schema
            st.session_state.data_loaded = True

            if append:
                st.success(
                    f"{SYMBOLS['success']} APPENDED — {schema['row_count']:,} TOTAL INCIDENTS"
                )
                logger.info(f"Appended data, total: {schema['row_count']} rows")
            else:
                st.success(
                    f"{SYMBOLS['success']} LOADED {schema['row_count']:,} INCIDENTS / "
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
        # Data Management section
        st.markdown("### Data Management")
        st.caption("Upload ServiceNow CSV Export")

        # CSV Upload
        uploaded_file = st.file_uploader(
            "Upload CSV",
            type=["csv"],
            help="Drag and drop file here. Limit 200MB per file - CSV",
            label_visibility="collapsed"
        )

        if uploaded_file is not None:
            # Load mode selection - side-by-side buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Replace", use_container_width=True, help="Replace existing data"):
                    _load_csv_data(uploaded_file, append=False)
            with col2:
                if st.button("+ Append", use_container_width=True, help="Add to existing data"):
                    _load_csv_data(uploaded_file, append=True)

        st.divider()

        # Embeddings section with status
        st.markdown("### Embeddings")

        # Check embedding status
        if embeddings_exist():
            stats = get_embedding_stats()
            st.session_state.embeddings_ready = True
            # Green success box like trynow.png
            st.markdown(f"""
<div class="success-box">
    <span class="checkmark">✓</span>
    <span>{stats['document_count']:,} documents indexed</span>
</div>
""", unsafe_allow_html=True)
        else:
            st.session_state.embeddings_ready = False
            st.warning("No embeddings built")

        # Check if data is loaded from existing table
        if not st.session_state.schema and table_exists():
            schema = get_schema_summary()
            if schema:
                st.session_state.schema = schema
                st.session_state.data_loaded = True

        # Build embeddings buttons - side-by-side with icons
        col1, col2 = st.columns(2)
        with col1:
            rebuild_disabled = not st.session_state.data_loaded
            if st.button("◇ Rebuild", use_container_width=True, help="Rebuild all embeddings", disabled=rebuild_disabled):
                _build_embeddings_with_progress(force=True)
        with col2:
            update_disabled = not st.session_state.data_loaded
            if st.button("+ Update", use_container_width=True, help="Update new embeddings only", disabled=update_disabled):
                _build_embeddings_with_progress(force=False)

        st.divider()

        # Settings
        st.markdown("### Settings")

        with st.expander("Query Options"):
            st.session_state.top_k = st.slider(
                "SEMANTIC RESULTS",
                min_value=5,
                max_value=50,
                value=10,
                help="Number of results for semantic search"
            )

            st.session_state.show_sql = st.checkbox(
                "SHOW SQL",
                value=True,
                help="Display the SQL query when using structured search"
            )

            st.session_state.show_summary = st.checkbox(
                "SHOW SUMMARY",
                value=True,
                help="Generate AI-powered executive summary of results"
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
            f"{SYMBOLS['success']} EMBEDDED {stats['total_embedded']:,} INCIDENTS "
            f"IN {stats['time_taken']:.1f}s"
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
        st.markdown(f"**Table:** `{schema['table_name']}`")
        st.markdown(f"**Rows:** `{schema['row_count']:,}`")

        # Create columns DataFrame
        cols_data = [
            {
                "Column": col["name"],
                "Type": col["type"],
                "Sample": col["sample"][:50] + "..." if len(col["sample"]) > 50 else col["sample"]
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
    # Executive summary (shown first if available)
    if executive_summary:
        st.markdown(f"""
<div class="summary-box">
    <h4>{SYMBOLS['results']} EXECUTIVE SUMMARY</h4>
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
            label=f"{SYMBOLS['export']} EXPORT CSV",
            data=csv_data,
            file_name=generate_export_filename("incidents"),
            mime="text/csv",
            key=f"export_{query_id}"
        )

    with col2:
        if sql and st.session_state.get("show_sql", True):
            with st.expander(f"{SYMBOLS['sql']} GENERATED SQL"):
                st.code(sql, language="sql")


def process_query(user_query: str, mode: str):
    """Process a user query and return formatted response."""
    if not st.session_state.schema:
        return {
            "content": f"{SYMBOLS['warning']} NO DATA LOADED. UPLOAD A CSV FILE FIRST.",
            "results": None,
            "sql": None
        }

    # Check for semantic queries without embeddings
    if mode in ["semantic", "hybrid", "auto"] and not st.session_state.embeddings_ready:
        if mode == "semantic":
            return {
                "content": f"{SYMBOLS['warning']} NO EMBEDDINGS. BUILD EMBEDDINGS FIRST.",
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
                "content": f"{SYMBOLS['error']} ERROR: {result['error']}",
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

        # Format route display with geometric symbols
        route_symbol = {
            "structured": SYMBOLS["structured"],
            "semantic": SYMBOLS["semantic"],
            "hybrid": SYMBOLS["hybrid"]
        }.get(route_used, "?")

        content_parts = [
            f"**{route_symbol} ROUTE:** {route_used.upper()} ({confidence:.0%} CONFIDENCE)"
        ]

        if reasoning:
            content_parts.append(f"**{SYMBOLS['info']} REASONING:** {reasoning}")

        if explanation:
            content_parts.append(f"**{SYMBOLS['query']} QUERY:** {explanation}")

        content_parts.append(f"**{SYMBOLS['results']} RESULTS:** {row_count:,} INCIDENTS")

        if row_count == 0:
            content_parts.append(f"\n_{SYMBOLS['info']} NO RESULTS. TRY A DIFFERENT QUERY OR MODE._")

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
            "content": f"{SYMBOLS['error']} ERROR: {str(e)}",
            "results": None,
            "sql": None
        }


def render_stats_bar():
    """Render the stats bar showing current data status."""
    if st.session_state.schema:
        schema = st.session_state.schema
        incidents = schema['row_count']
        columns = len(schema['columns'])

        # Get embeddings count
        if embeddings_exist():
            stats = get_embedding_stats()
            embeddings = stats.get('document_count', 0)
            status = "READY"
        else:
            embeddings = 0
            status = "NO EMBEDDINGS"
    else:
        incidents = 0
        columns = 0
        embeddings = 0
        status = "NO DATA"

    st.markdown(f"""
<div class="stats-bar">
    <span>INCIDENTS: <span class="stats-value">{incidents:,}</span></span>
    <span>COLUMNS: <span class="stats-value">{columns}</span></span>
    <span>EMBEDDINGS: <span class="stats-value">{embeddings:,}</span></span>
    <span>STATUS: <span class="stats-value">{status}</span></span>
</div>
""", unsafe_allow_html=True)


def render_main_content():
    """Render the main content area."""
    # Brutalist header
    render_header()

    # Stats bar
    render_stats_bar()

    if not st.session_state.data_loaded:
        st.info("Upload a ServiceNow CSV export using the sidebar to get started.")
        return

    # Schema Details expander
    render_schema_details()

    # Query Interface section
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("### Query Interface")

    with col2:
        selected_mode_label = st.selectbox(
            "Mode",
            options=list(MODE_OPTIONS.keys()),
            index=0,
            help=get_mode_description(MODE_OPTIONS[list(MODE_OPTIONS.keys())[0]]),
            label_visibility="collapsed"
        )
        selected_mode = MODE_OPTIONS[selected_mode_label]

    # Display mode description
    st.caption(f"_{get_mode_description(selected_mode)}_")

    # Chat history
    render_chat_history()

    # Query input
    if user_query := st.chat_input("ENTER QUERY..."):
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
            with st.spinner("PROCESSING..."):
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
        if st.button(f"{SYMBOLS['clear']} CLEAR CHAT", type="secondary"):
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
