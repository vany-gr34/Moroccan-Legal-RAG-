"""Database connection and models for Moroccan Legal RAG."""

from .session import get_connection

__all__ = ["get_connection"]
