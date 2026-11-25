"""Conversations router — expose session history to the frontend.

Endpoints
---------
GET    /api/v1/conversations                          List all distinct sessions
GET    /api/v1/conversations/{session_id}/response   Reconstruct full AskResponse from DB
DELETE /api/v1/conversations/{session_id}            Delete all turns for one session
"""

import json
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...db.conversations import (
    clear_session,
    _ensure_table,
)
from ...db.session import get_connection

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------
class SessionSummary(BaseModel):
    session_id: str
    first_query: str        # content of the first user message
    turn_count: int         # total number of messages in the session
    last_active: datetime   # timestamp of the most recent message


class SessionsResponse(BaseModel):
    total: int
    sessions: List[SessionSummary]


class DeleteResponse(BaseModel):
    session_id: str
    deleted: int


# Full AskResponse-compatible model — mirrors ask.py so the frontend
# can use the same AskResponse TypeScript type for both /ask and /response.
class StoredSourceArticle(BaseModel):
    article_number: str
    law_name: str
    domain: str
    chapter_title: Optional[str] = None
    section_title: Optional[str] = None
    text_preview: str
    text_full: str
    relevance_score: float


class StoredResponse(BaseModel):
    query: str
    short_answer: str
    long_answer: str
    example: Optional[str] = None
    disclaimer: str
    sources: List[StoredSourceArticle]
    knowledge_base: List[str]
    session_id: str
    search_time_ms: float
    generation_time_ms: float
    total_time_ms: float
    model_name: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _list_sessions() -> List[SessionSummary]:
    """Return one summary row per distinct session_id, newest first."""
    _ensure_table()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    c.session_id,
                    MIN(c.content) FILTER (WHERE c.role = 'user') AS first_query,
                    COUNT(*)                                        AS turn_count,
                    MAX(c.created_at)                               AS last_active
                FROM conversations c
                GROUP BY c.session_id
                ORDER BY last_active DESC
                """
            )
            rows = cur.fetchall()
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        return []
    finally:
        conn.close()

    return [
        SessionSummary(
            session_id=r[0],
            first_query=r[1] or "",
            turn_count=r[2],
            last_active=r[3],
        )
        for r in rows
    ]


def _get_stored_response(session_id: str) -> Optional[StoredResponse]:
    """Reconstruct the full AskResponse for a session from DB."""
    _ensure_table()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT role, content, sources, metadata
                FROM conversations
                WHERE session_id = %s
                ORDER BY created_at ASC
                """,
                (session_id,),
            )
            rows = cur.fetchall()
    except Exception as e:
        logger.error(f"Failed to get stored response: {e}")
        return None
    finally:
        conn.close()

    if not rows:
        return None

    user_content = ""
    asst_sources_raw = None
    asst_metadata: dict = {}

    for role, content, sources_col, metadata_col in rows:
        if role == "user":
            user_content = content
        elif role == "assistant":
            raw = sources_col
            if isinstance(raw, str):
                raw = json.loads(raw)
            asst_sources_raw = raw or []
            asst_metadata = metadata_col if isinstance(metadata_col, dict) else {}

    # Build structured source list from stored JSONB
    sources = [
        StoredSourceArticle(
            article_number=s.get("article_number", ""),
            law_name=s.get("law_name", ""),
            domain=s.get("domain", ""),
            chapter_title=s.get("chapter_title"),
            section_title=s.get("section_title"),
            text_preview=s.get("text_preview", ""),
            text_full=s.get("text_full", s.get("text_preview", "")),
            relevance_score=s.get("relevance_score", 0.0),
        )
        for s in (asst_sources_raw or [])
    ]

    return StoredResponse(
        query=user_content,
        short_answer=asst_metadata.get("short_answer", ""),
        long_answer=asst_metadata.get("long_answer", ""),
        example=asst_metadata.get("example"),
        disclaimer=asst_metadata.get(
            "disclaimer",
            "هذه الاجابة مولدة اليا. يرجى مراجعة النصوص الاصلية.",
        ),
        sources=sources,
        knowledge_base=asst_metadata.get("knowledge_base", []),
        session_id=session_id,
        search_time_ms=asst_metadata.get("search_time_ms", 0.0),
        generation_time_ms=asst_metadata.get("gen_time_ms", 0.0),
        total_time_ms=asst_metadata.get("total_time_ms", 0.0),
        model_name=asst_metadata.get("model", "unknown"),
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.get("/conversations", response_model=SessionsResponse)
async def list_sessions():
    """Return a summary of all Q&A sessions, newest first."""
    sessions = _list_sessions()
    return SessionsResponse(total=len(sessions), sessions=sessions)


@router.get("/conversations/{session_id}/response", response_model=StoredResponse)
async def get_session_response(session_id: str):
    """Return the full stored Q&A response for a session (for history view)."""
    result = _get_stored_response(session_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No response found for session '{session_id}'",
        )
    return result


@router.delete("/conversations/{session_id}", response_model=DeleteResponse)
async def delete_session(session_id: str):
    """Delete all turns for the given session."""
    try:
        deleted = clear_session(session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return DeleteResponse(session_id=session_id, deleted=deleted)
