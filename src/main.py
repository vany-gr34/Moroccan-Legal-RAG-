"""Moroccan Legal RAG API - Main Application."""

from src.api.routers import health, search, laws, ask, upload, conversations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from dotenv import load_dotenv
load_dotenv()


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting Moroccan Legal RAG API...")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Moroccan Legal RAG API",
    description="Retrieval-Augmented Generation for Moroccan Legal Texts",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS - allow all origins during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Register routers
app.include_router(health.router, tags=["Health"], prefix="/api/v1")
app.include_router(search.router, tags=["Search"], prefix="/api/v1")
app.include_router(laws.router, tags=["Laws"], prefix="/api/v1")
app.include_router(ask.router, tags=["Ask"], prefix="/api/v1")
app.include_router(upload.router, tags=["Upload"], prefix="/api/v1")
app.include_router(conversations.router, tags=["Conversations"], prefix="/api/v1")
