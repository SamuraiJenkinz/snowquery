"""
Configuration settings for ServiceNow Incident Query Tool.
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# OpenAI Configuration
OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

# Embedding Configuration
EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

# Database Paths
DATA_DIR: Path = BASE_DIR / "data"
DB_DIR: Path = BASE_DIR / "db"
DUCKDB_PATH: Path = DB_DIR / "incidents.duckdb"
CHROMA_PATH: Path = DB_DIR / "chroma"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
DB_DIR.mkdir(exist_ok=True)

# Text fields to embed for semantic search
TEXT_FIELDS: list[str] = ["short_description", "description", "close_notes"]

# Semantic search defaults
TOP_K_SEMANTIC: int = 10

# Known ServiceNow date fields
DATE_FIELDS: list[str] = [
    "opened_at",
    "closed_at",
    "resolved_at",
    "sys_created_on",
    "sys_updated_on",
    "due_date",
    "expected_start",
    "work_start",
    "work_end",
]

# Known ServiceNow category fields
CATEGORY_FIELDS: list[str] = [
    "priority",
    "state",
    "category",
    "subcategory",
    "assignment_group",
    "assigned_to",
    "contact_type",
    "impact",
    "urgency",
    "severity",
]

# Logging configuration
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# Query limits
DEFAULT_QUERY_LIMIT: int = 1000
MAX_QUERY_LIMIT: int = 10000
