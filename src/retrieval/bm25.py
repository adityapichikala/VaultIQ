"""
BM25 sparse retrieval module for VaultIQ.
Provides keyword-based search as a complement to dense vector search.
"""

import pickle
import os
from loguru import logger

from src.chunking import Chunk

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None


class BM25Index:
    """BM25 sparse retrieval index for keyword matching.

    Complements the dense Qdrant search by handling exact keyword
    matches, acronyms, and terminology that embedding models may miss.
    """

    def __init__(self):
        if BM25Okapi is None:
            raise ImportError(
                "rank-bm25 required. Install: pip install rank-bm25"
            )
        self.index: BM25Okapi | None = None
        self.chunks: list[Chunk] = []
        self._tokenized_corpus: list[list[str]] = []

    def build_index(self, chunks: list[Chunk]):
        """Build BM25 index from chunks.

        Args:
            chunks: List of Chunk objects to index.
        """
        self.chunks = chunks
        self._tokenized_corpus = [
            self._tokenize(chunk.content) for chunk in chunks
        ]
        self.index = BM25Okapi(self._tokenized_corpus)
        logger.info(f"BM25 index built with {len(chunks)} documents")

    def search(
        self,
        query: str,
        top_k: int = 20,
        acl_roles: list[str] | None = None,
    ) -> list[dict]:
        """Search the BM25 index.

        Args:
            query: Search query string.
            top_k: Number of results to return.
            acl_roles: Filter by ACL roles (applied after scoring).

        Returns:
            List of dicts with 'content', 'score', etc.
        """
        if self.index is None:
            raise ValueError("Index not built. Call build_index() first.")

        tokenized_query = self._tokenize(query)
        scores = self.index.get_scores(tokenized_query)

        # Create (index, score) pairs and sort by score descending
        scored = [(i, float(s)) for i, s in enumerate(scores) if s > 0]
        scored.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in scored:
            chunk = self.chunks[idx]

            # Apply ACL filter
            if acl_roles:
                if not any(role in chunk.acl_roles for role in acl_roles):
                    continue

            results.append({
                "content": chunk.content,
                "score": score,
                "source_file": chunk.source_file,
                "title": chunk.title,
                "source_type": chunk.source_type,
                "acl_roles": chunk.acl_roles,
                "chunk_id": chunk.chunk_id,
                "metadata": chunk.metadata,
            })

            if len(results) >= top_k:
                break

        return results

    def save(self, path: str):
        """Save BM25 index to disk.

        Args:
            path: File path to save the index.
        """
        data = {
            "chunks": [c.to_dict() for c in self.chunks],
            "tokenized_corpus": self._tokenized_corpus,
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)
        logger.info(f"BM25 index saved to {path}")

    def load(self, path: str):
        """Load BM25 index from disk.

        Args:
            path: File path to load the index from.
        """
        with open(path, "rb") as f:
            data = pickle.load(f)

        self.chunks = [
            Chunk(**d) for d in data["chunks"]
        ]
        self._tokenized_corpus = data["tokenized_corpus"]
        self.index = BM25Okapi(self._tokenized_corpus)
        logger.info(f"BM25 index loaded from {path} ({len(self.chunks)} docs)")

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Simple whitespace + lowercase tokenizer.

        Args:
            text: Input text to tokenize.

        Returns:
            List of lowercase tokens.
        """
        # Remove common punctuation, lowercase, split
        import re
        text = text.lower()
        text = re.sub(r"[^\w\s]", " ", text)
        tokens = text.split()
        # Remove very short tokens
        tokens = [t for t in tokens if len(t) > 1]
        return tokens
