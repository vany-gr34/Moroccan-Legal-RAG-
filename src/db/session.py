"""
Centralized database connection module.

All PostgreSQL connections in the project should use this module
to avoid duplicated connection logic across the codebase.
"""

import os
import logging
from typing import Optional
import psycopg2
from psycopg2.extras import execute_values, Json

logger = logging.getLogger(__name__)


def get_connection(
    host: Optional[str] = None,
    port: Optional[str] = None,
    dbname: Optional[str] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    connect_timeout: int = 10,
):
    """Get a database connection using environment variables with sensible defaults.

    All parameters are optional — they default to the corresponding
    POSTGRES_* environment variable, then to a hardcoded default.

    Args:
        host: Database host (default: POSTGRES_HOST env or 'localhost')
        port: Database port (default: POSTGRES_PORT env or '5432')
        dbname: Database name (default: POSTGRES_DB env or 'legal_rag')
        user: Database user (default: POSTGRES_USER env or 'legal_rag_user')
        password: Database password (default: POSTGRES_PASSWORD env or 'legal_rag_pass')
        connect_timeout: Connection timeout in seconds (default: 10)

    Returns:
        psycopg2 connection object.
    """
    return psycopg2.connect(
        host=host or os.getenv("POSTGRES_HOST", "localhost"),
        port=port or os.getenv("POSTGRES_PORT", "5432"),
        dbname=dbname or os.getenv("POSTGRES_DB", "legal_rag"),
        user=user or os.getenv("POSTGRES_USER", "legal_rag_user"),
        password=password or os.getenv("POSTGRES_PASSWORD", "legal_rag_pass"),
        connect_timeout=connect_timeout,
    )


def execute_batch(cur, query: str, values: list, template=None):
    """Execute a batch insert using execute_values.

    Args:
        cur: Database cursor.
        query: SQL query with %s placeholders.
        values: List of tuples to insert.
        template: Optional template for execute_values.
    """
    execute_values(cur, query, values, template=template)


def json(value: dict) -> Json:
    """Wrap a dict as a JSON-compatible psycopg2 object."""
    return Json(value)
