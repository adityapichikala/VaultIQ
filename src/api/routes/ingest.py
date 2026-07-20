"""
Ingestion route for VaultIQ FastAPI.

POST /api/v1/ingest → Trigger asynchronous document re-ingestion
"""

import os
from fastapi import APIRouter, BackgroundTasks, HTTPException
from loguru import logger

from ..schemas import IngestRequest, IngestResponse

router = APIRouter()


def _run_ingestion_pipeline(data_dir: str, force_rebuild: bool) -> dict:
    """
    Blocking ingestion pipeline — run in a background thread via BackgroundTasks.
    
    Imports are local to avoid circular dependencies and to keep this
    runnable in a separate thread context.
    """
    from src.ingest.pipeline import IngestionPipeline
    from src.chunking import DocumentChunker
    from src.retrieval.embeddings import EmbeddingEngine, QdrantIndex
    from src.retrieval.bm25 import BM25Index

    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )

    logger.info(f"Starting ingestion from: {data_dir}")

    # Step 1: Ingest
    pipeline = IngestionPipeline()
    documents = pipeline.ingest_directory(data_dir)

    # Step 2: Chunk
    chunker = DocumentChunker(chunk_size=500, chunk_overlap=50)
    chunks = chunker.chunk_documents(documents)

    # Step 3: Embed
    embedder = EmbeddingEngine()
    texts = [c.content for c in chunks]
    embeddings = embedder.encode(texts)

    # Step 4: Index in Qdrant
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")

    if qdrant_url:
        qdrant = QdrantIndex(url=qdrant_url, api_key=qdrant_api_key)
    else:
        qdrant_path = os.path.join(project_root, "qdrant_storage")
        qdrant = QdrantIndex(path=qdrant_path)

    if force_rebuild:
        qdrant.create_collection(dim=len(embeddings[0]))

    qdrant.index_chunks(chunks, embeddings)

    # Step 5: Save BM25
    bm25 = BM25Index()
    bm25.build_index(chunks)
    bm25_path = os.path.join(project_root, "bm25_index.pkl")
    bm25.save(bm25_path)

    logger.info(f"Ingestion complete: {len(documents)} docs → {len(chunks)} chunks")
    return {
        "documents_ingested": len(documents),
        "chunks_created": len(chunks),
        "vectors_indexed": qdrant.count(),
    }


@router.post("/ingest", response_model=IngestResponse, summary="Trigger Document Ingestion")
async def ingest(
    body: IngestRequest,
    background_tasks: BackgroundTasks,
):
    """
    Trigger an asynchronous document ingestion and re-indexing pipeline.

    The ingestion runs in a background thread to avoid blocking the API server.
    Monitor ingestion status via GET /api/v1/health.

    In a production system, this endpoint would:
    1. Write an ingestion job record to PostgreSQL
    2. Push a message to a Celery/SQS queue
    3. Return the job ID immediately
    4. A separate worker would process the job and update the job status
    """
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )

    data_dir = body.data_dir or os.path.join(project_root, "data", "synthetic")

    if not os.path.isdir(data_dir):
        raise HTTPException(
            status_code=404,
            detail=f"Data directory not found: {data_dir}",
        )

    logger.info(f"Ingestion triggered for: {data_dir} (force_rebuild={body.force_rebuild})")

    # Run ingestion synchronously for now (background task in next iteration)
    try:
        result = _run_ingestion_pipeline(data_dir, body.force_rebuild)
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

    return IngestResponse(
        status="completed",
        documents_ingested=result["documents_ingested"],
        chunks_created=result["chunks_created"],
        vectors_indexed=result["vectors_indexed"],
    )
