"""
Semantic search module for vector similarity queries.
Finds incidents similar to natural language descriptions.
"""
from typing import Any

import duckdb
import pandas as pd

from config import DUCKDB_PATH, TOP_K_SEMANTIC
from src.embeddings import (
    embeddings_exist,
    initialize_chroma_client,
    initialize_embedding_model,
)
from src.utils import EmbeddingError, QueryError, logger


def search_similar(
    query: str,
    top_k: int = TOP_K_SEMANTIC,
    filters: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Search for incidents similar to the query text.

    Args:
        query: Natural language query/description
        top_k: Number of results to return
        filters: Optional metadata filters (priority, assignment_group, etc.)

    Returns:
        Dict with ids, distances, documents, metadatas

    Raises:
        EmbeddingError: If search fails
    """
    if not embeddings_exist():
        raise EmbeddingError(
            "No embeddings found",
            "Please build embeddings first using the 'Rebuild Embeddings' button."
        )

    try:
        # Get model and collection
        model = initialize_embedding_model()
        _, collection = initialize_chroma_client()

        # Embed the query
        logger.info(f"Searching for: {query}")
        query_embedding = model.encode(query).tolist()

        # Build where clause for filters
        where_clause = None
        if filters:
            where_conditions = []

            # Priority filter
            if "priority" in filters:
                priority = filters["priority"]
                if isinstance(priority, list):
                    where_conditions.append({"priority": {"$in": priority}})
                else:
                    where_conditions.append({"priority": priority})

            # Assignment group filter
            if "assignment_group" in filters:
                group = filters["assignment_group"]
                if isinstance(group, list):
                    where_conditions.append({"assignment_group": {"$in": group}})
                else:
                    where_conditions.append({"assignment_group": group})

            # Combine conditions
            if len(where_conditions) == 1:
                where_clause = where_conditions[0]
            elif len(where_conditions) > 1:
                where_clause = {"$and": where_conditions}

        # Query ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause,
            include=["documents", "metadatas", "distances"]
        )

        # Extract results
        ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        logger.info(f"Found {len(ids)} similar incidents")

        return {
            "ids": ids,
            "distances": distances,
            "documents": documents,
            "metadatas": metadatas,
            "query": query,
            "filters_applied": filters
        }

    except EmbeddingError:
        raise
    except Exception as e:
        logger.exception("Error in semantic search")
        raise EmbeddingError(
            "Semantic search failed",
            str(e)
        )


def _distance_to_similarity(distance: float) -> float:
    """
    Convert ChromaDB distance to similarity score (0-1).

    For cosine distance: similarity = 1 - distance
    For L2 distance: similarity = 1 / (1 + distance)

    ChromaDB with cosine space returns cosine distance.

    Args:
        distance: Distance value from ChromaDB

    Returns:
        Similarity score (0-1, higher is more similar)
    """
    # Cosine distance is in [0, 2], similarity is 1 - distance/2
    # But ChromaDB uses squared distance, so we clamp and convert
    similarity = max(0, 1 - distance)
    return round(similarity, 4)


def enrich_results(
    search_results: dict[str, Any]
) -> pd.DataFrame:
    """
    Enrich search results with full incident data from DuckDB.

    Args:
        search_results: Results from search_similar()

    Returns:
        DataFrame with full incident data plus similarity_score

    Raises:
        QueryError: If enrichment fails
    """
    ids = search_results.get("ids", [])
    distances = search_results.get("distances", [])

    if not ids:
        return pd.DataFrame()

    if not DUCKDB_PATH.exists():
        raise QueryError(
            "No data loaded",
            "Please upload a CSV file first."
        )

    try:
        conn = duckdb.connect(str(DUCKDB_PATH), read_only=True)

        try:
            # Get column names
            columns = [col[0] for col in conn.execute("DESCRIBE incidents").fetchall()]

            # Determine ID column
            id_column = "number" if "number" in columns else "sys_id"

            # Build query
            placeholders = ", ".join(f"'{id}'" for id in ids)
            query = f"SELECT * FROM incidents WHERE {id_column} IN ({placeholders})"

            df = conn.execute(query).fetchdf()

            # Add similarity scores
            similarity_map = {
                id: _distance_to_similarity(dist)
                for id, dist in zip(ids, distances)
            }

            df["similarity_score"] = df[id_column].apply(
                lambda x: similarity_map.get(str(x), 0)
            )

            # Sort by similarity score descending
            df = df.sort_values("similarity_score", ascending=False)

            return df

        finally:
            conn.close()

    except QueryError:
        raise
    except Exception as e:
        logger.exception("Error enriching search results")
        raise QueryError(
            "Failed to enrich search results",
            str(e)
        )


def semantic_query(
    query: str,
    top_k: int = TOP_K_SEMANTIC,
    filters: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Perform semantic search and return enriched results.

    Args:
        query: Natural language query/description
        top_k: Number of results to return
        filters: Optional metadata filters

    Returns:
        Dict with results DataFrame, query info, and stats
    """
    try:
        # Search
        search_results = search_similar(query, top_k, filters)

        # Enrich with full data
        results_df = enrich_results(search_results)

        return {
            "results": results_df,
            "query": query,
            "top_k": top_k,
            "found": len(results_df),
            "filters_applied": filters,
            "error": None
        }

    except (EmbeddingError, QueryError) as e:
        return {
            "results": pd.DataFrame(),
            "query": query,
            "top_k": top_k,
            "found": 0,
            "filters_applied": filters,
            "error": e.message + (f"\n{e.details}" if e.details else "")
        }

    except Exception as e:
        logger.exception("Error in semantic_query")
        return {
            "results": pd.DataFrame(),
            "query": query,
            "top_k": top_k,
            "found": 0,
            "filters_applied": filters,
            "error": f"Unexpected error: {str(e)}"
        }


def get_similar_to_incident(
    incident_id: str,
    top_k: int = TOP_K_SEMANTIC,
    exclude_self: bool = True
) -> dict[str, Any]:
    """
    Find incidents similar to a specific incident.

    Args:
        incident_id: Incident number or sys_id
        top_k: Number of results to return
        exclude_self: Whether to exclude the source incident

    Returns:
        Dict with results DataFrame and stats
    """
    try:
        _, collection = initialize_chroma_client()

        # Get the incident's embedding
        result = collection.get(
            ids=[incident_id],
            include=["embeddings", "documents"]
        )

        if not result["ids"]:
            raise QueryError(
                "Incident not found in embeddings",
                f"No embedding exists for incident {incident_id}"
            )

        # Search with the incident's embedding
        query_embedding = result["embeddings"][0]

        search_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k + (1 if exclude_self else 0),
            include=["documents", "metadatas", "distances"]
        )

        # Filter out self if needed
        ids = search_results["ids"][0]
        distances = search_results["distances"][0]
        documents = search_results["documents"][0]
        metadatas = search_results["metadatas"][0]

        if exclude_self and incident_id in ids:
            idx = ids.index(incident_id)
            ids.pop(idx)
            distances.pop(idx)
            documents.pop(idx)
            metadatas.pop(idx)

        # Limit to top_k
        ids = ids[:top_k]
        distances = distances[:top_k]

        # Enrich results
        enriched_results = {
            "ids": ids,
            "distances": distances,
            "documents": documents[:top_k],
            "metadatas": metadatas[:top_k]
        }

        results_df = enrich_results(enriched_results)

        return {
            "results": results_df,
            "source_incident": incident_id,
            "top_k": top_k,
            "found": len(results_df),
            "error": None
        }

    except (EmbeddingError, QueryError) as e:
        return {
            "results": pd.DataFrame(),
            "source_incident": incident_id,
            "top_k": top_k,
            "found": 0,
            "error": e.message + (f"\n{e.details}" if e.details else "")
        }

    except Exception as e:
        logger.exception("Error finding similar incidents")
        return {
            "results": pd.DataFrame(),
            "source_incident": incident_id,
            "top_k": top_k,
            "found": 0,
            "error": f"Unexpected error: {str(e)}"
        }
