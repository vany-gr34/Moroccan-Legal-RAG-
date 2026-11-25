"""Health check endpoint."""

from fastapi import APIRouter
import time
import os
import torch


router = APIRouter()

START_TIME = time.time()


@router.get("/health")
async def health_check():
    """Return service health status."""
    return {
        "status": "healthy",
        "service": "Moroccan Legal RAG API",
        "version": "0.1.0",
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "embedder_mode": os.getenv("EMBEDDING_SERVICE_URL") and "remote" or "local",
        "gpu_available": torch.cuda.is_available(),
    }
