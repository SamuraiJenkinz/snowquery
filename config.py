"""
Configuration settings for ServiceNow Incident Query Tool.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")

# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
API_VERSION: str = os.getenv("API_VERSION", "2023-05-15")

# Embedding Configuration
# Multilingual SBERT — XLM-R distilled to MiniLM-L12, fine-tuned on ~50 languages
# (German, Japanese, French, Spanish, Portuguese, etc.). 384-dim, drop-in
# compatible with the prior all-MiniLM-L6-v2 collection dimensionality.
# Force-rebuild embeddings after changing this constant.
EMBEDDING_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"

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
