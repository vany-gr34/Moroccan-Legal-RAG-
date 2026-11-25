"""Search endpoint."""

import asyncio
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional
from ..dependencies import get_retrieval_strategy

router = APIRouter()


class SearchRequest(BaseModel):
    query: str = Field(..., description="Arabic legal question")
    domain: Optional[str] = Field(None, description="Legal domain filter")
    top_k: int = Field(5, ge=1, le=20, description="Number of results")
    strategy: Optional[str] = Field(
        None, description="Retrieval strategy: dense, bm25, rrf")


@router.post("/search")
async def search_endpoint(request: SearchRequest):
    """Search legal articles by Arabic query."""
    strategy = get_retrieval_strategy(request.strategy or "rrf")
    return await asyncio.to_thread(
        strategy.search,
        query=request.query,
        domain=request.domain,
        top_k=request.top_k,
    )
