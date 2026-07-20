"""
Embedding and vector indexing module for VaultIQ.
Encodes chunks with sentence-transformers and stores them in Qdrant.
"""

import os
from loguru import logger

from src.chunking import Chunk

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        VectorParams,
        PointStruct,
        Filter,
        FieldCondition,
        MatchAny,
    )
except ImportError:
    QdrantClient = None


EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
COLLECTION_NAME = "vaultiq_docs"


class EmbeddingEngine:
    """Encodes text chunks into dense vectors using sentence-transformers."""

    def __init__(self, model_name: str = EMBEDDING_MODEL):
        if SentenceTransformer is None:
            raise ImportError(
                "sentence-transformers required. Install: pip install sentence-transformers"
            )
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded. Dimension: {self.dim}")

    def encode(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        """Encode a list of texts into vectors.

        Args:
            texts: List of text strings to encode.
            batch_size: Batch size for encoding.

        Returns:
            List of embedding vectors (list of floats).
        """
        logger.info(f"Encoding {len(texts)} texts...")
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=True,  # For cosine similarity
        )
        return embeddings.tolist()

    def encode_query(self, query: str) -> list[float]:
        """Encode a single query string.

        Args:
            query: The search query.

        Returns:
            Embedding vector for the query.
        """
        embedding = self.model.encode(
            query, normalize_embeddings=True
        )
        return embedding.tolist()


class QdrantIndex:
    """Manages the Qdrant vector store for VaultIQ.

    Supports two connection modes, controlled by environment variables:

    **Remote (production):**
        Set QDRANT_URL and QDRANT_API_KEY environment variables.
        Connects to a managed Qdrant Cloud cluster over HTTPS.
        Supports concurrent access from multiple API worker processes.

    **Local (development):**
        Leave QDRANT_URL unset (or pass `path` explicitly).
        Uses local file-based storage via SQLite under the hood.
        Single-process only — not safe for multi-worker deployments.
    """

    def __init__(
        self,
        path: str = "./qdrant_storage",
        url: str | None = None,
        api_key: str | None = None,
    ):
        """Initialize Qdrant client.

        Connection priority:
        1. `url` argument (if provided) → remote/managed Qdrant
        2. QDRANT_URL environment variable → remote/managed Qdrant
        3. `path` argument → local file-based Qdrant (default)

        Args:
            path: Local directory path for file-based Qdrant storage.
            url: URL of a managed Qdrant instance (e.g., Qdrant Cloud).
            api_key: API key for the managed Qdrant instance.
        """
        if QdrantClient is None:
            raise ImportError(
                "qdrant-client required. Install: pip install qdrant-client"
            )

        # Resolve connection target: argument > env var > local file
        qdrant_url = url or os.getenv("QDRANT_URL")
        qdrant_api_key = api_key or os.getenv("QDRANT_API_KEY")

        if qdrant_url:
            self.client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
            self.collection_name = COLLECTION_NAME
            logger.info(f"Qdrant connected to remote cluster: {qdrant_url}")
        else:
            self.client = QdrantClient(path=path)
            self.collection_name = COLLECTION_NAME
            logger.info(f"Qdrant initialized at local path: {path}")

    def create_collection(self, dim: int = EMBEDDING_DIM):
        """Create or recreate the vector collection.

        Args:
            dim: Embedding vector dimension.
        """
        # Check if collection already exists
        collections = self.client.get_collections().collections
        existing = [c.name for c in collections]

        if self.collection_name in existing:
            logger.warning(f"Collection '{self.collection_name}' exists. Recreating...")
            self.client.delete_collection(self.collection_name)

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=dim,
                distance=Distance.COSINE,
            ),
        )
        logger.info(
            f"Created collection '{self.collection_name}' (dim={dim}, cosine)"
        )

    def index_chunks(
        self,
        chunks: list[Chunk],
        embeddings: list[list[float]],
        batch_size: int = 100,
    ):
        """Index chunks with their embeddings into Qdrant.

        Args:
            chunks: List of Chunk objects.
            embeddings: Corresponding embedding vectors.
            batch_size: Number of points per upsert batch.
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings"
            )

        points = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            point = PointStruct(
                id=i,
                vector=embedding,
                payload={
                    "chunk_id": chunk.chunk_id,
                    "content": chunk.content,
                    "doc_id": chunk.doc_id,
                    "source_type": chunk.source_type,
                    "source_file": chunk.source_file,
                    "title": chunk.title,
                    "acl_roles": chunk.acl_roles,
                    "metadata": chunk.metadata,
                },
            )
            points.append(point)

        # Upsert in batches
        for batch_start in range(0, len(points), batch_size):
            batch = points[batch_start : batch_start + batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch,
            )

        logger.info(f"Indexed {len(points)} chunks into Qdrant")

    def search(
        self,
        query_vector: list[float],
        top_k: int = 20,
        acl_roles: list[str] | None = None,
    ) -> list[dict]:
        """Search for similar chunks.

        Args:
            query_vector: Query embedding vector.
            top_k: Number of results to return.
            acl_roles: Filter results to only these ACL roles.

        Returns:
            List of dicts with 'chunk', 'score' keys.
        """
        # Build ACL filter if roles specified
        query_filter = None
        if acl_roles:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="acl_roles",
                        match=MatchAny(any=acl_roles),
                    )
                ]
            )

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=top_k,
            with_payload=True,
        )

        return [
            {
                "content": hit.payload["content"],
                "score": hit.score,
                "source_file": hit.payload["source_file"],
                "title": hit.payload["title"],
                "source_type": hit.payload["source_type"],
                "acl_roles": hit.payload["acl_roles"],
                "chunk_id": hit.payload["chunk_id"],
                "metadata": hit.payload.get("metadata", {}),
            }
            for hit in results.points
        ]

    def count(self) -> int:
        """Return the number of indexed points."""
        info = self.client.get_collection(self.collection_name)
        return info.points_count
