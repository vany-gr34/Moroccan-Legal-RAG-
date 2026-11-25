"""Laws endpoint - list all ingested laws."""

from fastapi import APIRouter
from src.api.dependencies import get_connection
router = APIRouter()


@router.get("/laws")
async def list_laws():
    """Return all distinct ingested laws with article counts and domains."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            law_name,
            domain,
            COUNT(*) AS article_count,
            MIN(created_at) AS ingested_at
        FROM legal_chunks
        WHERE is_active = TRUE
        GROUP BY law_name, domain
        ORDER BY domain, law_name
    """)

    laws = []
    for row in cur.fetchall():
        laws.append({
            "law_name": row[0],
            "domain": row[1],
            "article_count": row[2],
            "ingested_at": row[3].isoformat() if row[3] else None,
        })

    cur.close()
    conn.close()

    return {
        "total_laws": len(laws),
        "laws": laws,
    }
