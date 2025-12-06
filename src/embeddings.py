"""
Embedding pipeline for semantic search capability.
Builds and manages vector embeddings in ChromaDB from incident text fields.
"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Callable, Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from config import (
    CHROMA_PATH,
    DUCKDB_PATH,
    EMBEDDING_MODEL,
    TEXT_FIELDS,
)
from src.utils import EmbeddingError, logger

# Module-level cache for model and client
_model: Optional[SentenceTransformer] = None
_chroma_client: Optional[chromadb.PersistentClient] = None
_collection: Optional[chromadb.Collection] = None

# Collection name
COLLECTION_NAME = "incidents"

# Batch size for embedding generation
BATCH_SIZE = 500

# Maximum words per document (model context limit)
MAX_WORDS = 256


def initialize_embedding_model() -> SentenceTransformer:
    """
    Load and cache the sentence-transformers model.

    Returns:
        SentenceTransformer model instance

    Raises:
        EmbeddingError: If model loading fails
    """
    global _model

    if _model is not None:
        return _model

    try:
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        _model = SentenceTransformer(EMBEDDING_MODEL)
        logger.info("Embedding model loaded successfully")
        return _model
    except Exception as e:
        logger.exception("Failed to load embedding model")
        raise EmbeddingError(
            f"Failed to load embedding model: {EMBEDDING_MODEL}",
            str(e)
        )


def initialize_chroma_client() -> tuple[chromadb.PersistentClient, chromadb.Collection]:
    """
    Create or connect to ChromaDB and get/create collection.

    Returns:
        Tuple of (client, collection)

    Raises:
        EmbeddingError: If ChromaDB initialization fails
    """
    global _chroma_client, _collection

    if _chroma_client is not None and _collection is not None:
        return _chroma_client, _collection

    try:
        # Ensure directory exists
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initializing ChromaDB at: {CHROMA_PATH}")

        _chroma_client = chromadb.PersistentClient(
            path=str(CHROMA_PATH),
            settings=Settings(anonymized_telemetry=False)
        )

        _collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

        logger.info(f"ChromaDB collection '{COLLECTION_NAME}' ready")
        return _chroma_client, _collection

    except Exception as e:
        logger.exception("Failed to initialize ChromaDB")
        raise EmbeddingError(
            "Failed to initialize ChromaDB",
            str(e)
        )


def _prepare_text(row: dict[str, Any]) -> str:
    """
    Prepare text for embedding by concatenating text fields.

    Args:
        row: Dictionary with incident data

    Returns:
        Concatenated text suitable for embedding
    """
    parts = []
    for field in TEXT_FIELDS:
        value = row.get(field, "")
        if value and str(value).strip() and str(value).lower() not in ("nan", "none", "null"):
            parts.append(str(value).strip())

    text = " | ".join(parts) if parts else "No description available"

    # Truncate to max words
    words = text.split()
    if len(words) > MAX_WORDS:
        text = " ".join(words[:MAX_WORDS])

    return text


def _get_incident_id(row: dict[str, Any]) -> str:
    """
    Get unique identifier for an incident.

    Args:
        row: Dictionary with incident data

    Returns:
        Incident identifier (number or sys_id)
    """
    # Prefer 'number' field, fall back to 'sys_id'
    if row.get("number"):
        return str(row["number"])
    if row.get("sys_id"):
        return str(row["sys_id"])
    raise ValueError("Incident missing both 'number' and 'sys_id' fields")


def _get_metadata(row: dict[str, Any]) -> dict[str, str]:
    """
    Extract metadata for ChromaDB storage.

    Args:
        row: Dictionary with incident data

    Returns:
        Metadata dictionary
    """
    metadata = {}

    # Number
    if row.get("number"):
        metadata["number"] = str(row["number"])

    # Priority
    if row.get("priority"):
        metadata["priority"] = str(row["priority"])

    # Assignment group
    if row.get("assignment_group"):
        metadata["assignment_group"] = str(row["assignment_group"])

    # Opened at
    if row.get("opened_at"):
        metadata["opened_at"] = str(row["opened_at"])

    return metadata


def build_embeddings(
    force_rebuild: bool = False,
    progress_callback: Callable[[float, str], None] | None = None
) -> dict[str, Any]:
    """
    Build embeddings for all incidents in DuckDB.

    Args:
        force_rebuild: If True, delete existing embeddings and rebuild
        progress_callback: Optional callback(progress: float, message: str)

    Returns:
        Statistics dict with total_embedded, time_taken, etc.

    Raises:
        EmbeddingError: If embedding build fails
    """
    import duckdb

    start_time = time.time()

    # Initialize components
    model = initialize_embedding_model()
    client, collection = initialize_chroma_client()

    # Force rebuild if requested
    if force_rebuild:
        logger.info("Force rebuild requested, clearing collection")
        if progress_callback:
            progress_callback(0.0, "Clearing existing embeddings...")

        try:
            client.delete_collection(COLLECTION_NAME)
            _collection_ref = client.create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )
            global _collection
            _collection = _collection_ref
            collection = _collection_ref
        except Exception as e:
            logger.warning(f"Error clearing collection: {e}")

    # Check DuckDB exists
    if not DUCKDB_PATH.exists():
        raise EmbeddingError(
            "No data loaded",
            "Please upload a CSV file first."
        )

    try:
        conn = duckdb.connect(str(DUCKDB_PATH), read_only=True)

        # Get total count
        total_rows = conn.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
        logger.info(f"Found {total_rows} incidents to embed")

        if total_rows == 0:
            return {
                "total_embedded": 0,
                "time_taken": 0,
                "status": "No incidents to embed"
            }

        # Get column names
        columns = [col[0] for col in conn.execute("DESCRIBE incidents").fetchall()]

        # Process in batches
        embedded_count = 0
        batch_ids = []
        batch_texts = []
        batch_metadatas = []

        offset = 0
        while offset < total_rows:
            if progress_callback:
                progress = offset / total_rows
                progress_callback(progress, f"Processing incidents {offset + 1} to {min(offset + BATCH_SIZE, total_rows)}...")

            # Fetch batch
            rows = conn.execute(
                f"SELECT * FROM incidents LIMIT {BATCH_SIZE} OFFSET {offset}"
            ).fetchall()

            for row_tuple in rows:
                row = dict(zip(columns, row_tuple))

                try:
                    doc_id = _get_incident_id(row)
                    text = _prepare_text(row)
                    metadata = _get_metadata(row)

                    batch_ids.append(doc_id)
                    batch_texts.append(text)
                    batch_metadatas.append(metadata)

                except ValueError as e:
                    logger.warning(f"Skipping row: {e}")
                    continue

            # Embed and store batch
            if batch_texts:
                if progress_callback:
                    progress_callback(
                        offset / total_rows,
                        f"Generating embeddings for batch ({len(batch_texts)} items)..."
                    )

                embeddings = model.encode(batch_texts, show_progress_bar=False)

                collection.add(
                    ids=batch_ids,
                    embeddings=embeddings.tolist(),
                    documents=batch_texts,
                    metadatas=batch_metadatas
                )

                embedded_count += len(batch_ids)

                # Clear batches
                batch_ids = []
                batch_texts = []
                batch_metadatas = []

            offset += BATCH_SIZE

        conn.close()

        elapsed = time.time() - start_time

        if progress_callback:
            progress_callback(1.0, f"Complete! Embedded {embedded_count} incidents.")

        logger.info(f"Embedded {embedded_count} incidents in {elapsed:.1f}s")

        return {
            "total_embedded": embedded_count,
            "time_taken": round(elapsed, 2),
            "status": "success"
        }

    except EmbeddingError:
        raise
    except Exception as e:
        logger.exception("Error building embeddings")
        raise EmbeddingError(
            "Failed to build embeddings",
            str(e)
        )


def update_embeddings(
    progress_callback: Callable[[float, str], None] | None = None
) -> dict[str, Any]:
    """
    Update embeddings for new/changed incidents.

    Args:
        progress_callback: Optional callback(progress: float, message: str)

    Returns:
        Statistics dict with newly_embedded count

    Raises:
        EmbeddingError: If update fails
    """
    import duckdb

    start_time = time.time()

    model = initialize_embedding_model()
    _, collection = initialize_chroma_client()

    if not DUCKDB_PATH.exists():
        raise EmbeddingError(
            "No data loaded",
            "Please upload a CSV file first."
        )

    try:
        conn = duckdb.connect(str(DUCKDB_PATH), read_only=True)

        # Get all incident IDs from DuckDB
        columns = [col[0] for col in conn.execute("DESCRIBE incidents").fetchall()]

        # Determine ID column
        id_column = "number" if "number" in columns else "sys_id"

        db_ids = set(
            str(row[0]) for row in
            conn.execute(f"SELECT {id_column} FROM incidents").fetchall()
        )

        # Get existing IDs from ChromaDB
        existing_count = collection.count()
        if existing_count > 0:
            existing = collection.get(include=[])
            existing_ids = set(existing["ids"])
        else:
            existing_ids = set()

        # Find new IDs
        new_ids = db_ids - existing_ids
        logger.info(f"Found {len(new_ids)} new incidents to embed")

        if not new_ids:
            conn.close()
            return {
                "newly_embedded": 0,
                "time_taken": 0,
                "status": "No new incidents"
            }

        # Fetch and embed new records
        new_ids_list = list(new_ids)
        embedded_count = 0

        for i in range(0, len(new_ids_list), BATCH_SIZE):
            batch_ids_to_fetch = new_ids_list[i:i + BATCH_SIZE]

            if progress_callback:
                progress = i / len(new_ids_list)
                progress_callback(progress, f"Processing {len(batch_ids_to_fetch)} new incidents...")

            # Build IN clause
            placeholders = ", ".join(f"'{id}'" for id in batch_ids_to_fetch)
            rows = conn.execute(
                f"SELECT * FROM incidents WHERE {id_column} IN ({placeholders})"
            ).fetchall()

            batch_ids = []
            batch_texts = []
            batch_metadatas = []

            for row_tuple in rows:
                row = dict(zip(columns, row_tuple))
                try:
                    doc_id = _get_incident_id(row)
                    text = _prepare_text(row)
                    metadata = _get_metadata(row)

                    batch_ids.append(doc_id)
                    batch_texts.append(text)
                    batch_metadatas.append(metadata)
                except ValueError:
                    continue

            if batch_texts:
                embeddings = model.encode(batch_texts, show_progress_bar=False)
                collection.add(
                    ids=batch_ids,
                    embeddings=embeddings.tolist(),
                    documents=batch_texts,
                    metadatas=batch_metadatas
                )
                embedded_count += len(batch_ids)

        conn.close()

        elapsed = time.time() - start_time

        if progress_callback:
            progress_callback(1.0, f"Complete! Added {embedded_count} new embeddings.")

        return {
            "newly_embedded": embedded_count,
            "time_taken": round(elapsed, 2),
            "status": "success"
        }

    except EmbeddingError:
        raise
    except Exception as e:
        logger.exception("Error updating embeddings")
        raise EmbeddingError(
            "Failed to update embeddings",
            str(e)
        )


def get_embedding_stats() -> dict[str, Any]:
    """
    Get statistics about the current embedding collection.

    Returns:
        Statistics dict with count, model info, etc.
    """
    try:
        _, collection = initialize_chroma_client()

        count = collection.count()

        return {
            "document_count": count,
            "collection_name": COLLECTION_NAME,
            "embedding_model": EMBEDDING_MODEL,
            "chroma_path": str(CHROMA_PATH),
            "status": "ready" if count > 0 else "empty"
        }
    except Exception as e:
        logger.error(f"Error getting embedding stats: {e}")
        return {
            "document_count": 0,
            "status": "error",
            "error": str(e)
        }


def embeddings_exist() -> bool:
    """
    Check if embeddings have been built.

    Returns:
        True if embeddings exist
    """
    try:
        stats = get_embedding_stats()
        return stats.get("document_count", 0) > 0
    except Exception:
        return False


def clear_embeddings() -> bool:
    """
    Clear all embeddings from ChromaDB.

    Returns:
        True if successful
    """
    global _collection

    try:
        client, _ = initialize_chroma_client()
        client.delete_collection(COLLECTION_NAME)
        _collection = client.create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("Embeddings cleared")
        return True
    except Exception as e:
        logger.error(f"Error clearing embeddings: {e}")
        return False
