"""
VaultIQ — Build and query pipeline.
Run this script to build the full index from synthetic data,
then interactively query it from the command line.

Usage:
    python -m src.retrieval.build_index        # Build index only
    python -m src.retrieval.build_index --query # Build + interactive query
"""

import os
import sys
import argparse
from loguru import logger


def build_index():
    """Build the full search index from synthetic data."""
    from src.ingest.pipeline import IngestionPipeline
    from src.chunking import DocumentChunker
    from src.retrieval.embeddings import EmbeddingEngine, QdrantIndex
    from src.retrieval.bm25 import BM25Index

    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    data_dir = os.path.join(project_root, "data", "synthetic")

    # Step 1: Ingest documents
    logger.info("=" * 60)
    logger.info("STEP 1: Ingesting documents...")
    logger.info("=" * 60)
    pipeline = IngestionPipeline()
    documents = pipeline.ingest_directory(data_dir)

    # Step 2: Chunk documents
    logger.info("=" * 60)
    logger.info("STEP 2: Chunking documents...")
    logger.info("=" * 60)
    chunker = DocumentChunker(chunk_size=500, chunk_overlap=50)
    chunks = chunker.chunk_documents(documents)
    logger.info(f"Created {len(chunks)} chunks from {len(documents)} documents")

    # Step 3: Generate embeddings
    logger.info("=" * 60)
    logger.info("STEP 3: Generating embeddings...")
    logger.info("=" * 60)
    embedder = EmbeddingEngine()
    texts = [chunk.content for chunk in chunks]
    embeddings = embedder.encode(texts)
    logger.info(f"Generated {len(embeddings)} embeddings (dim={len(embeddings[0])})")

    # Step 4: Index in Qdrant
    logger.info("=" * 60)
    logger.info("STEP 4: Indexing in Qdrant...")
    logger.info("=" * 60)
    qdrant_path = os.path.join(project_root, "qdrant_storage")
    qdrant = QdrantIndex(path=qdrant_path)
    qdrant.create_collection(dim=len(embeddings[0]))
    qdrant.index_chunks(chunks, embeddings)
    logger.info(f"Qdrant: {qdrant.count()} vectors indexed")

    # Step 5: Build BM25 index
    logger.info("=" * 60)
    logger.info("STEP 5: Building BM25 index...")
    logger.info("=" * 60)
    bm25 = BM25Index()
    bm25.build_index(chunks)
    bm25_path = os.path.join(project_root, "bm25_index.pkl")
    bm25.save(bm25_path)

    logger.info("=" * 60)
    logger.info("INDEX BUILD COMPLETE!")
    logger.info(f"  Documents ingested: {len(documents)}")
    logger.info(f"  Chunks created:     {len(chunks)}")
    logger.info(f"  Vectors indexed:    {qdrant.count()}")
    logger.info(f"  BM25 index:         {bm25_path}")
    logger.info(f"  Qdrant storage:     {qdrant_path}")
    logger.info("=" * 60)

    return embedder, qdrant, bm25


def interactive_query(embedder, qdrant, bm25):
    """Run interactive query loop."""
    from src.retrieval import HybridRetriever
    from src.retrieval.rag_chain import RAGChain

    retriever = HybridRetriever(
        embedding_engine=embedder,
        qdrant_index=qdrant,
        bm25_index=bm25,
    )

    # Check for API key
    api_key = os.getenv("GROQ_API_KEY")
    rag = None
    if api_key:
        rag = RAGChain(api_key=api_key)
        logger.info("Groq API key found — LLM answers enabled")
    else:
        logger.warning(
            "GROQ_API_KEY not set — showing retrieved chunks only (no LLM answer)"
        )

    roles = ["all-employees", "engineering", "hr", "leadership"]
    print("\n" + "=" * 60)
    print("VaultIQ Interactive Query")
    print(f"Available roles: {', '.join(roles)}")
    print("Type 'quit' to exit, 'role:X' to change role")
    print("=" * 60)

    current_role = "engineering"
    print(f"Current role: {current_role}\n")

    while True:
        query = input("🔍 Query: ").strip()
        if not query:
            continue
        if query.lower() == "quit":
            break
        if query.lower().startswith("role:"):
            current_role = query.split(":", 1)[1].strip()
            print(f"  → Role changed to: {current_role}\n")
            continue

        # Retrieve
        user_roles = [current_role, "all-employees"]
        results = retriever.retrieve(query, user_roles=user_roles, top_k=5)

        if not results:
            print("  No results found.\n")
            continue

        # If RAG chain available, generate answer
        if rag:
            response = rag.generate(query, results)
            print(f"\n💡 Answer:\n{response['answer']}")
            print(f"\n📚 Sources:")
            for src in response["sources"]:
                print(f"   - {src['file']} ({src['type']}) — {src['title']}")
            if response["usage"]:
                print(f"\n📊 Tokens: {response['usage'].get('total_tokens', 'N/A')}")
        else:
            print(f"\n📄 Top {len(results)} results:")
            for i, r in enumerate(results, 1):
                score = r.get("rrf_score", r.get("score", 0))
                print(f"\n  [{i}] {r['source_file']} (score: {score:.4f})")
                print(f"      Title: {r['title']}")
                preview = r["content"][:150].replace("\n", " ")
                print(f"      {preview}...")

        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VaultIQ Index Builder")
    parser.add_argument(
        "--query", action="store_true", help="Start interactive query after building"
    )
    args = parser.parse_args()

    embedder, qdrant, bm25 = build_index()

    if args.query:
        interactive_query(embedder, qdrant, bm25)
