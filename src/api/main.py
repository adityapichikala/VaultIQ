"""
VaultIQ FastAPI Backend — Entry Point

Run:
    uvicorn src.api.main:app --reload --port 8000

Endpoints:
    POST /api/v1/query          → synchronous RAG query
    POST /api/v1/query/stream   → SSE streaming RAG query
    POST /api/v1/ingest         → trigger async document ingestion
    GET  /api/v1/health         → health + index stats
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .routes import query, ingest, health
from .dependencies import init_retrieval_components


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all retrieval components once at server startup."""
    logger.info("VaultIQ API server starting up...")
    await init_retrieval_components()
    logger.info("Retrieval components loaded. Server ready.")
    yield
    logger.info("VaultIQ API server shutting down.")


app = FastAPI(
    title="VaultIQ API",
    description=(
        "Enterprise RAG system over multi-modal data with "
        "role-based access control (ACL) and hybrid retrieval."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# --- CORS Middleware ---
# Allow the Next.js frontend (running on port 3000) to call this API.
# Restrict origins in production via ALLOWED_ORIGINS env var.
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8501"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(query.router, prefix="/api/v1", tags=["query"])
app.include_router(ingest.router, prefix="/api/v1", tags=["ingest"])
