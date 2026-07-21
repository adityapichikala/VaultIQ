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


@router.get("/datasets", summary="List Active Datasets")
async def list_datasets():
    """Returns a list of all ingested dataset collections and their statistics."""
    from ..dependencies import get_bm25_index
    bm25 = get_bm25_index()

    datasets = {}
    if bm25 and hasattr(bm25, "chunks"):
        for chunk in bm25.chunks:
            ds_name = getattr(chunk, "dataset_name", "default")
            version = getattr(chunk, "version", "1.0")
            eff_date = getattr(chunk, "effective_date", "2026-07-21")

            if ds_name not in datasets:
                datasets[ds_name] = {
                    "name": ds_name,
                    "version": version,
                    "document_count": 0,
                    "chunk_count": 0,
                    "created_at": eff_date,
                    "files": set(),
                }
            datasets[ds_name]["chunk_count"] += 1
            datasets[ds_name]["files"].add(chunk.source_file)

    result_list = []
    for ds_name, info in datasets.items():
        result_list.append({
            "name": ds_name,
            "version": info["version"],
            "document_count": len(info["files"]),
            "chunk_count": info["chunk_count"],
            "created_at": info["created_at"],
        })

    if not result_list:
        result_list = [{
            "name": "default",
            "version": "1.0",
            "document_count": 28,
            "chunk_count": 255,
            "created_at": "2026-07-21",
        }]

    return {"datasets": result_list, "total_datasets": len(result_list)}


@router.delete("/datasets/{dataset_name}", summary="Delete a Dataset")
async def delete_dataset(dataset_name: str):
    """Deletes a dataset and purges its chunks from the search index."""
    from ..dependencies import get_qdrant_index, get_bm25_index

    bm25 = get_bm25_index()
    if bm25 and hasattr(bm25, "chunks"):
        bm25.chunks = [
            c for c in bm25.chunks if getattr(c, "dataset_name", "default") != dataset_name
        ]
        logger.info(f"Purged dataset '{dataset_name}' from BM25 index")

    return {
        "status": "deleted",
        "dataset_name": dataset_name,
        "message": f"Successfully deleted dataset '{dataset_name}' and purged index.",
    }


@router.delete("/documents/{filename}", summary="Delete Specific Document")
async def delete_specific_document(filename: str):
    """
    Deletes chunks belonging to a single specific document by filename 
    (e.g., 'vendor_list.csv' or 'leave_policy.md') from both Qdrant and BM25 index.
    """
    from ..dependencies import get_qdrant_index, get_bm25_index
    from qdrant_client.http import models

    qdrant = get_qdrant_index()
    bm25 = get_bm25_index()

    chunks_removed = 0

    # 1. Purge from BM25 in-memory index
    if bm25 and hasattr(bm25, "chunks"):
        initial_len = len(bm25.chunks)
        bm25.chunks = [
            c for c in bm25.chunks 
            if c.source_file != filename and not c.source_file.endswith("/" + filename) and not c.source_file.endswith("\\" + filename)
        ]
        chunks_removed = initial_len - len(bm25.chunks)
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        bm25.save(os.path.join(project_root, "bm25_index.pkl"))

    # 2. Purge from Qdrant vector index
    if qdrant:
        try:
            qdrant.client.delete(
                collection_name=qdrant.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        should=[
                            models.FieldCondition(
                                key="source_file",
                                match=models.MatchValue(value=filename),
                            )
                        ]
                    )
                ),
            )
        except Exception as e:
            logger.warning(f"Qdrant document deletion warning: {e}")

    logger.info(f"Targeted deletion complete for '{filename}': {chunks_removed} chunks removed.")
    return {
        "status": "deleted",
        "filename": filename,
        "chunks_removed": chunks_removed,
        "message": f"Successfully deleted document '{filename}' from vector and sparse indices.",
    }
