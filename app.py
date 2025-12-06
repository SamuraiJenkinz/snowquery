"""
ServiceNow Incident Query Tool - Streamlit Application.
Main entry point for the natural language query interface.
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
from src.query_router import get_mode_description, route_query
from src.utils import (
    dataframe_to_csv_bytes,
    format_dataframe_for_display,
    format_error_message,
    generate_export_filename,
    logger,
)

# Page configuration
st.set_page_config(
    page_title="ServiceNow Incident Query Tool",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Mode mapping for UI
MODE_OPTIONS = {
    "Auto": "auto",
    "Report (SQL)": "structured",
    "Find Similar": "semantic",
    "Analyze (Hybrid)": "hybrid"
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


def render_sidebar():
    """Render the sidebar with data management controls."""
    with st.sidebar:
        st.header("📁 Data Management")

        # CSV Upload
        uploaded_file = st.file_uploader(
            "Upload ServiceNow CSV Export",
            type=["csv"],
            help="Upload a CSV export from ServiceNow containing incident data"
        )

        if uploaded_file is not None:
            if st.button("📤 Load Data", type="primary", use_container_width=True):
                with st.spinner("Loading CSV data..."):
                    try:
                        schema = load_csv(uploaded_file)
                        st.session_state.schema = schema
                        st.session_state.data_loaded = True
                        st.success(
                            f"✅ Loaded {schema['row_count']:,} incidents "
                            f"with {len(schema['columns'])} columns"
                        )
                        logger.info(
                            f"Successfully loaded {schema['row_count']} rows"
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(format_error_message(e))
                        logger.exception("Failed to load CSV")

        st.divider()

        # Display current data status
        st.subheader("📊 Data Status")

        if st.session_state.schema:
            schema = st.session_state.schema
            st.metric("Incidents Loaded", f"{schema['row_count']:,}")
            st.metric("Columns", len(schema['columns']))
        elif table_exists():
            # Try to load existing schema
            schema = get_schema_summary()
            if schema:
                st.session_state.schema = schema
                st.session_state.data_loaded = True
                st.metric("Incidents Loaded", f"{schema['row_count']:,}")
                st.metric("Columns", len(schema['columns']))
            else:
                st.info("No data loaded")
        else:
            st.info("No data loaded. Upload a CSV to get started.")

        st.divider()

        # Embeddings management
        st.subheader("🔮 Embeddings")

        # Check embedding status
        if embeddings_exist():
            stats = get_embedding_stats()
            st.session_state.embeddings_ready = True
            st.success(f"✅ {stats['document_count']:,} documents indexed")
        else:
            st.session_state.embeddings_ready = False
            st.warning("No embeddings built")

        # Build embeddings button
        if st.session_state.data_loaded:
            col1, col2 = st.columns(2)

            with col1:
                if st.button("🔄 Rebuild", use_container_width=True):
                    _build_embeddings_with_progress(force=True)

            with col2:
                if st.button("➕ Update", use_container_width=True):
                    _build_embeddings_with_progress(force=False)

        st.divider()

        # Settings
        st.subheader("⚙️ Settings")

        with st.expander("Query Settings"):
            st.session_state.top_k = st.slider(
                "Results (semantic)",
                min_value=5,
                max_value=50,
                value=10,
                help="Number of results for semantic search"
            )

            st.session_state.show_sql = st.checkbox(
                "Show generated SQL",
                value=True,
                help="Display the SQL query when using structured search"
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

    with st.expander("📋 Schema Details", expanded=False):
        st.write(f"**Table:** {schema['table_name']}")
        st.write(f"**Row Count:** {schema['row_count']:,}")

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
                        message.get("query_id", "")
                    )


def display_results(df: pd.DataFrame, sql: str | None, query_id: str):
    """Display query results with formatting and export."""
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
            label="📥 Export CSV",
            data=csv_data,
            file_name=generate_export_filename("incidents"),
            mime="text/csv",
            key=f"export_{query_id}"
        )

    with col2:
        if sql and st.session_state.get("show_sql", True):
            with st.expander("🔍 Generated SQL"):
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

        # Format route display
        route_emoji = {
            "structured": "📊",
            "semantic": "🔮",
            "hybrid": "🔄"
        }.get(route_used, "❓")

        content_parts = [
            f"{route_emoji} **Route:** {route_used.title()} (confidence: {confidence:.0%})"
        ]

        if reasoning:
            content_parts.append(f"💡 **Reasoning:** {reasoning}")

        if explanation:
            content_parts.append(f"📝 **Query:** {explanation}")

        content_parts.append(f"📈 **Results:** {row_count:,} incidents found")

        if row_count == 0:
            content_parts.append("\n_No results found. Try a different query or adjust the search mode._")

        return {
            "content": "\n\n".join(content_parts),
            "results": result.get("results"),
            "sql": result.get("sql")
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
    st.title("🔍 ServiceNow Incident Query Tool")

    if not st.session_state.data_loaded:
        st.info(
            "👋 Welcome! Upload a ServiceNow incident CSV export using the "
            "sidebar to get started."
        )

        # Show example queries
        st.subheader("Example Queries")
        st.markdown("""
        Once data is loaded, you can ask questions like:
        - "Show all P1 incidents from last month"
        - "Find incidents similar to Outlook crashes"
        - "What are the top 5 assignment groups by incident volume?"
        - "How many incidents were opened this week?"
        """)
        return

    # Show schema details
    render_schema_details()

    st.divider()

    # Mode selection
    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader("💬 Query Interface")

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
                    query_id
                )

        # Save assistant message
        st.session_state.messages.append({
            "role": "assistant",
            "content": response["content"],
            "results": response["results"],
            "sql": response["sql"],
            "query_id": query_id
        })

    # Clear chat button
    if st.session_state.messages:
        if st.button("🗑️ Clear Chat", type="secondary"):
            st.session_state.messages = []
            st.rerun()


def main():
    """Main application entry point."""
    init_session_state()
    render_sidebar()
    render_main_content()


if __name__ == "__main__":
    main()
