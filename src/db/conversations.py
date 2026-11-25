"""Conversation history repository.

Stores and retrieves chat sessions from the `conversations` table.
Each exchange (user question + assistant answer) is stored as two rows
linked by a common `session_id`.

The table is auto-created on first use if it does not exist.
"""

import json
import logging
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field, asdict

from .session import get_connection

logger = logging.getLogger(__name__)

MAX_HISTORY_TURNS = 10  # number of past Q/A pairs to include in context

# ── Auto-create table ────────────────────────────────────────────────
_TABLE_EXISTS = False


def _ensure_table():
    """Create the conversations table if it does not exist (lazy, once)."""
    global _TABLE_EXISTS
    if _TABLE_EXISTS:
        return

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id          SERIAL PRIMARY KEY,
                    session_id  VARCHAR(64) NOT NULL,
                    role        VARCHAR(16) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
                    content     TEXT NOT NULL,
                    sources     JSONB,
                    metadata    JSONB DEFAULT '{}',
                    created_at  TIMESTAMP DEFAULT NOW()
                )
                """
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_conversations_session "
                "ON conversations(session_id)"
            )
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_conversations_created "
                "ON conversations(created_at)"
            )
            conn.commit()
            _TABLE_EXISTS = True
            logger.info("✓ conversations table ready")
    except Exception as e:
        conn.rollback()
        logger.warning(f"Could not create conversations table: {e}")
        raise
    finally:
        conn.close()


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""
    id: int
    session_id: str
    role: str  # 'user' | 'assistant' | 'system'
    content: str
    sources: Optional[list] = None
    metadata: dict = field(default_factory=dict)
    created_at: Optional[datetime] = None


def save_message(
    session_id: str,
    role: str,
    content: str,
    sources: Optional[list] = None,
    metadata: Optional[dict] = None,
) -> int:
    """Insert a single message into the conversation history.

    Args:
        session_id: Unique session identifier.
        role: 'user', 'assistant', or 'system'.
        content: Message text.
        sources: Optional list of source articles (for assistant messages).
        metadata: Optional extra metadata dict.

    Returns:
        The inserted row ID.
    """
    _ensure_table()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO conversations (session_id, role, content, sources, metadata)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    session_id,
                    role,
                    content,
                    json.dumps(sources) if sources else None,
                    json.dumps(metadata) if metadata else None,
                ),
            )
            conn.commit()
            row_id = cur.fetchone()[0]
            logger.debug(
                f"Saved {role} message {row_id} in session {session_id}")
            return row_id
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to save message: {e}")
        raise
    finally:
        conn.close()


def save_exchange(
    session_id: str,
    user_query: str,
    assistant_response: str,
    sources: Optional[list] = None,
    metadata: Optional[dict] = None,
) -> tuple[int, int]:
    """Save a Q/A pair (user + assistant) in a single call.

    Args:
        session_id: Unique session identifier.
        user_query: The user's question.
        assistant_response: The LLM's answer.
        sources: Source articles the answer was based on.
        metadata: Optional metadata for the assistant message.

    Returns:
        Tuple of (user_message_id, assistant_message_id).
    """
    user_id = save_message(session_id, "user", user_query)
    asst_id = save_message(
        session_id, "assistant", assistant_response, sources=sources, metadata=metadata
    )
    return user_id, asst_id


def get_history(
    session_id: str,
    max_turns: int = MAX_HISTORY_TURNS,
) -> List[ConversationTurn]:
    """Retrieve the most recent conversation turns for a session.

    Args:
        session_id: Unique session identifier.
        max_turns: Maximum number of past exchanges to return.

    Returns:
        List of ConversationTurn objects, oldest first.
    """
    _ensure_table()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, session_id, role, content, sources, metadata, created_at
                FROM conversations
                WHERE session_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (session_id, max_turns * 2),
            )
            rows = cur.fetchall()
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        return []
    finally:
        conn.close()

    # Reverse so oldest is first (chronological order for the prompt)
    turns = [
        ConversationTurn(
            id=r[0],
            session_id=r[1],
            role=r[2],
            content=r[3],
            sources=json.loads(r[4]) if isinstance(r[4], str) else r[4],
            metadata=r[5] if r[5] else {},
            created_at=r[6],
        )
        for r in reversed(rows)
    ]
    return turns


def format_history_for_prompt(turns: List[ConversationTurn]) -> str:
    """Format conversation history as text to inject into the LLM prompt.

    Args:
        turns: List of ConversationTurn objects (chronological).

    Returns:
        Formatted history string, or empty string if no history.
    """
    if not turns:
        return ""

    lines = ["--- تاريخ المحادثة ---"]
    for turn in turns:
        if turn.role == "user":
            lines.append(f"المستخدم: {turn.content}")
        elif turn.role == "assistant":
            lines.append(f"المساعد: {turn.content}")
    lines.append("--- نهاية تاريخ المحادثة ---")
    return "\n".join(lines)


def clear_session(session_id: str) -> int:
    """Delete all messages for a session.

    Args:
        session_id: Unique session identifier.

    Returns:
        Number of deleted rows.
    """
    _ensure_table()
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM conversations WHERE session_id = %s",
                (session_id,),
            )
            conn.commit()
            deleted = cur.rowcount
            logger.info(f"Cleared {deleted} messages for session {session_id}")
            return deleted
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to clear session {session_id}: {e}")
        raise
    finally:
        conn.close()
