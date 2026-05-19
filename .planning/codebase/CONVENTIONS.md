# Coding Conventions

**Analysis Date:** 2026-05-19

## Naming Patterns

**Files:**
- `snake_case` for all Python files: `query_router.py`, `semantic_search.py`, `embeddings.py`
- Modules in `src/` directory for core logic: `src/utils.py`, `src/ingest.py`, etc.
- App entry points at root: `app.py`, `app_brutalist.py`, `fixedapp.py`
- Configuration: `config.py` (centralized settings)
- UI design: `designui.py`

**Functions:**
- `snake_case` consistently: `setup_logging()`, `format_dataframe_for_display()`, `initialize_embedding_model()`
- Private functions prefixed with underscore: `_detect_column_type()`, `_call_azure_openai()`, `_heuristic_classify()`
- Helper functions grouped logically within modules before public APIs

**Variables:**
- `snake_case` for all variables: `max_rows`, `log_level`, `chart_requested`
- Constants in `UPPER_SNAKE_CASE`: `EMBEDDING_MODEL`, `COLLECTION_NAME`, `MAX_WORDS`, `BATCH_SIZE`, `DEFAULT_QUERY_LIMIT`
- Module-level cache variables prefixed with underscore: `_model`, `_chroma_client`, `_collection`

**Types:**
- Type hints used extensively throughout: `dict[str, Any]`, `list[str]`, `Optional[str]`, `pd.DataFrame`, `tuple[...]`
- Custom exception classes in `src/utils.py`: `QueryError`, `IngestionError`, `EmbeddingError`
- No dataclasses detected; using plain classes for exceptions with `__init__` and `message`/`details` attributes

## Code Style

**Formatting:**
- No detected linter configuration (`.eslintrc`, `.flake8`, `.pylintrc`, `pyproject.toml`)
- Imports use `from __future__ import annotations` for forward references (PEP 563)
- Module docstrings present on all files: triple-quoted strings at top
- Line length appears to follow ~80-120 character convention (typical Python)

**Linting:**
- Not enforced via configuration; conventions appear manual
- No detected code formatters (black, autopep8)

## Import Organization

**Order:**
1. `from __future__ import annotations` (future imports)
2. Standard library imports: `os`, `json`, `logging`, `datetime`, `re`, `sys`
3. Third-party imports: `pandas`, `streamlit`, `duckdb`, `chromadb`, `requests`, `altair`, `sentence_transformers`, `dotenv`
4. Local/relative imports: `from src.X import Y`, `from config import ...`

**Examples from `app.py`:**
```python
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
from src.utils import logger
```

**Examples from `src/embeddings.py`:**
```python
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
```

**Path Aliases:**
- No path aliases detected; direct imports from `config` and `src.`

## Error Handling

**Patterns:**
- Try/except blocks wrap external operations: API calls, file I/O, model loading, database operations
- Multiple encoding attempts for CSV loading (utf-8, cp1252, latin-1, iso-8859-1) with fallback
- Custom exceptions raised with message + optional details:
  ```python
  raise QueryError("Azure OpenAI API call failed", str(e))
  raise EmbeddingError(
      f"Failed to load embedding model: {EMBEDDING_MODEL}",
      str(e)
  )
  ```
- Exception re-raising with context preservation: `except QueryError: raise`
- Fallback strategies: JSON parse failures fall back to heuristic classification
- All exceptions logged with `logger.exception()` for full stack trace context

**Custom Exception Classes** (`src/utils.py`):
```python
class QueryError(Exception):
    """Custom exception for query-related errors."""
    def __init__(self, message: str, details: str | None = None):
        self.message = message
        self.details = details
        super().__init__(self.message)

class IngestionError(Exception):
    """Custom exception for data ingestion errors."""
    ...

class EmbeddingError(Exception):
    """Custom exception for embedding-related errors."""
    ...
```

## Logging

**Framework:** Python's `logging` module

**Setup** (`src/utils.py`):
```python
def setup_logging(name: str = "snow_query") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
        logger.addHandler(handler)
    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    return logger

logger = setup_logging()
```

**Usage Patterns:**
- Module-level logger created once: `logger = setup_logging()`
- Info-level: `logger.info("Starting CSV ingestion")` - major operations
- Debug-level: `logger.debug("Failed to read with encoding...")` - detailed troubleshooting
- Warning-level: `logger.warning("Classification failed, using heuristic...")` - non-critical failures
- Error-level: `logger.error("Azure OpenAI API error...")` - operation failures
- Exception-level: `logger.exception("Failed to load embedding model")` - full stack trace

**Configuration:**
- Log level controlled via `LOG_LEVEL` env var (default: `"INFO"`)
- Format: `"%(asctime)s - %(name)s - %(levelname)s - %(message)s"`
- Output to stdout via StreamHandler

## Comments

**When to Comment:**
- Complex algorithms: e.g., regex patterns for date detection (DATE_PATTERNS list)
- Workarounds and reasoning: e.g., "visually hide raw text content (safe technique)" in CSS
- Intent of non-obvious logic: fallback strategies, encoding detection loops
- Section headers for large blocks: `# ===== GLOBAL RESET =====`

**Density:**
- Moderate comment density; comments explain "why" rather than "what"
- Code is self-documenting with clear variable names
- Inline comments rare; docstrings preferred

**Docstring/JSDoc:**
- Module docstrings: All modules have triple-quoted string at top
- Function docstrings: Args: section documents parameters, Returns: section documents output, Raises: section documents exceptions
- Example from `src/ingest.py`:
  ```python
  def load_csv(
      file: str | Path | BinaryIO | BytesIO,
      table_name: str = "incidents",
      append: bool = False
  ) -> dict[str, Any]:
      """
      Load a CSV file into DuckDB with automatic type inference.

      Args:
          file: File path, BytesIO, or file-like object
          table_name: Name of the table to create
          append: If True, append to existing table instead of replacing

      Returns:
          Schema summary dictionary

      Raises:
          IngestionError: If CSV loading fails
      """
  ```

## Function Design

**Size:**
- Functions range from 10-50 lines typically
- Larger functions (100+ lines) exist for complex orchestration: `app.py:process_query()`, `app.py:render_main_content()`
- Average: ~20-30 lines per function

**Parameters:**
- Explicit parameter passing preferred over global state
- Optional parameters have sensible defaults: `max_rows: int = 100`, `top_k: int = TOP_K_SEMANTIC`
- Use of unpacking for imports in calling modules: `from src.embeddings import (build_embeddings, embeddings_exist, ...)`

**Return Values:**
- Consistent return types matching docstrings
- Dict return for complex multi-value results: `dict[str, Any]`
- Tuples for fixed-length multi-value returns: `tuple[bool, str | None]` (chart detection)
- None for side-effect-only functions
- None values explicitly documented: `Optional[str]`

## Module Design

**Exports:**
- Public functions defined first, private functions with underscore prefix follow
- Module `src/utils.py` exports: `setup_logging()`, `QueryError`, `IngestionError`, `EmbeddingError`, `format_dataframe_for_display()`, `truncate_text()`, etc.
- Module-level cache variables (private): `_model`, `_chroma_client`, `_collection` in `src/embeddings.py`

**Barrel Files:**
- `src/__init__.py` exists but appears empty (3 lines)
- No barrel file exports detected; direct imports from modules preferred: `from src.embeddings import build_embeddings`

**Module Organization:**
- `config.py`: All configuration constants centralized
- `src/utils.py`: Logging, custom exceptions, formatting utilities
- `src/ingest.py`: CSV loading, schema detection
- `src/embeddings.py`: Model initialization, embedding generation, caching
- `src/semantic_search.py`: Vector similarity search
- `src/sql_generator.py`: Natural language to SQL conversion
- `src/query_router.py`: Intent classification, routing logic
- `src/chart_generator.py`: Chart type inference and generation
- `app*.py`: Streamlit UI entry points (multiple variants)

## Type Hints

**Presence:**
- Comprehensive type hints on function signatures throughout
- Return types specified: `-> dict[str, Any]`, `-> pd.DataFrame`, `-> None`
- Parameter types specified with modern union syntax: `str | Path | BinaryIO | BytesIO`, `str | None`

**Examples:**
```python
def format_schema_for_llm(schema_summary: dict[str, Any]) -> str:
def safe_get(data: dict, *keys: str, default: Any = None) -> Any:
def search_similar(query: str, top_k: int = TOP_K_SEMANTIC, filters: dict[str, Any] | None = None) -> dict[str, Any]:
```

**Modern Python Features:**
- `from __future__ import annotations` used in all core modules (future-proofs forward references)
- Union types with pipe operator: `str | None` instead of `Optional[str]` (Python 3.10+)
- Type narrowing patterns: isinstance checks preserve type information

---

*Convention analysis: 2026-05-19*
