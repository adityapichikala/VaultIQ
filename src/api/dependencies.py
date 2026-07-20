"""
Shared dependency injection for VaultIQ FastAPI routes.

All retrieval components (EmbeddingEngine, QdrantIndex, BM25Index, RAGChain)
are initialized once at server startup and shared across requests via
FastAPI's dependency injection system.
"""

import os
from loguru import logger

from src.retrieval.embeddings import EmbeddingEngine, QdrantIndex
from src.retrieval.bm25 import BM25Index
from src.retrieval import HybridRetriever
from src.retrieval.rag_chain import RAGChain

# Global singletons — populated by init_retrieval_components() at startup
_embedding_engine: EmbeddingEngine | None = None
_qdrant_index: QdrantIndex | None = None
_bm25_index: BM25Index | None = None
_rag_chain: RAGChain | None = None


async def init_retrieval_components():
    """
    Load all retrieval components into global singletons.
    Called once during FastAPI lifespan startup.

    Supports both local file mode (development) and remote Qdrant
    Cloud (production) via environment variables.
    """
    global _embedding_engine, _qdrant_index, _bm25_index, _rag_chain

    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )

    # 1. Load embedding model
    logger.info("Loading embedding model...")
    _embedding_engine = EmbeddingEngine()

    # 2. Connect to Qdrant (remote or local — controlled by env)
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")

    if qdrant_url:
        logger.info(f"Connecting to remote Qdrant: {qdrant_url}")
        _qdrant_index = QdrantIndex(url=qdrant_url, api_key=qdrant_api_key)
    else:
        qdrant_path = os.path.join(project_root, "qdrant_storage")
        logger.info(f"Using local Qdrant storage: {qdrant_path}")
        _qdrant_index = QdrantIndex(path=qdrant_path)

    # 3. Load BM25 index
    bm25_path = os.path.join(project_root, "bm25_index.pkl")
    if os.path.exists(bm25_path):
        logger.info(f"Loading BM25 index from: {bm25_path}")
        _bm25_index = BM25Index()
        _bm25_index.load(bm25_path)
    else:
        logger.warning(
            f"BM25 index not found at {bm25_path}. "
            "Run `python -m src.retrieval.build_index` first."
        )

    # 4. Initialize RAG chain (requires GROQ_API_KEY)
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key:
        logger.info("Groq API key found — RAG chain initialized.")
        _rag_chain = RAGChain(api_key=groq_api_key)
    else:
        logger.warning("GROQ_API_KEY not set — LLM generation will be unavailable.")


def get_retriever() -> HybridRetriever:
    """Dependency: returns a configured HybridRetriever."""
    if _embedding_engine is None or _qdrant_index is None or _bm25_index is None:
        raise RuntimeError(
            "Retrieval components not initialized. "
            "Ensure init_retrieval_components() ran during startup."
        )
    return HybridRetriever(
        embedding_engine=_embedding_engine,
        qdrant_index=_qdrant_index,
        bm25_index=_bm25_index,
    )


def get_rag_chain() -> RAGChain | None:
    """Dependency: returns the RAGChain if initialized, else None."""
    return _rag_chain


def get_qdrant_index() -> QdrantIndex | None:
    """Dependency: returns the QdrantIndex for health/info endpoints."""
    return _qdrant_index


def get_bm25_index() -> BM25Index | None:
    """Dependency: returns the BM25Index for health/info endpoints."""
    return _bm25_index
