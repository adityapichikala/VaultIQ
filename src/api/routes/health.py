"""
Health check route for VaultIQ FastAPI.

GET /api/v1/health → System status and index statistics
"""

import os
from fastapi import APIRouter, Depends
from loguru import logger

from src.retrieval.embeddings import QdrantIndex
from src.retrieval.bm25 import BM25Index
from src.retrieval.rag_chain import RAGChain
from ..dependencies import get_qdrant_index, get_bm25_index, get_rag_chain
from ..schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="Health Check")
async def health(
    qdrant: QdrantIndex | None = Depends(get_qdrant_index),
    bm25: BM25Index | None = Depends(get_bm25_index),
    rag_chain: RAGChain | None = Depends(get_rag_chain),
):
    """
    Returns the health status of all VaultIQ subsystems.
    Used by deployment platforms (Railway, Render, AWS ECS) for liveness probes.
    """
    qdrant_vectors = 0
    bm25_docs = 0
    qdrant_mode = "unavailable"

    if qdrant:
        try:
            qdrant_vectors = qdrant.count()
            qdrant_url = os.getenv("QDRANT_URL")
            qdrant_mode = "remote" if qdrant_url else "local"
        except Exception as e:
            logger.warning(f"Qdrant health check failed: {e}")

    if bm25:
        bm25_docs = len(bm25.chunks)

    status = "ok" if (qdrant_vectors > 0 and bm25_docs > 0) else "degraded"

    return HealthResponse(
        status=status,
        qdrant_vectors=qdrant_vectors,
        bm25_documents=bm25_docs,
        llm_available=rag_chain is not None,
        qdrant_mode=qdrant_mode,
    )
