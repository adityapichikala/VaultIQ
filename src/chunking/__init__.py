"""
Chunking module for VaultIQ.
Splits parsed Document objects into smaller, semantically meaningful chunks
suitable for embedding and retrieval.
"""

import hashlib
from dataclasses import dataclass, field
from src.ingest import Document


@dataclass
class Chunk:
    """A chunk of text ready for embedding and indexing."""

    chunk_id: str
    content: str
    doc_id: str  # Parent document ID
    source_type: str
    source_file: str
    title: str
    acl_roles: list[str] = field(default_factory=lambda: ["all-employees"])
    metadata: dict = field(default_factory=dict)
    effective_date: str = "2026-07-21"
    version: str = "1.0"
    dataset_name: str = "default"

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "content": self.content,
            "doc_id": self.doc_id,
            "source_type": self.source_type,
            "source_file": self.source_file,
            "title": self.title,
            "acl_roles": self.acl_roles,
            "metadata": self.metadata,
            "effective_date": self.effective_date,
            "version": self.version,
            "dataset_name": self.dataset_name,
        }


class DocumentChunker:
    """Splits documents into overlapping chunks of target size.

    Uses a simple recursive character-based splitting strategy:
    1. Try splitting on paragraph boundaries (double newline)
    2. If paragraphs are too large, split on single newlines
    3. If still too large, split on sentence boundaries
    4. Last resort: split on word boundaries

    Each chunk preserves the parent document's metadata, ACL, and source info.
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        min_chunk_size: int = 50,
    ):
        """
        Args:
            chunk_size: Target number of characters per chunk.
            chunk_overlap: Number of characters to overlap between chunks.
            min_chunk_size: Minimum chunk size — smaller chunks are merged with neighbors.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_documents(self, documents: list[Document]) -> list[Chunk]:
        """Chunk a list of Documents into smaller Chunks.

        Args:
            documents: List of Document objects from the ingestion pipeline.

        Returns:
            List of Chunk objects ready for embedding.
        """
        all_chunks = []
        for doc in documents:
            chunks = self._chunk_single_document(doc)
            all_chunks.extend(chunks)
        return all_chunks

    def _chunk_single_document(self, doc: Document) -> list[Chunk]:
        """Split a single document into chunks."""
        text = doc.content.strip()

        effective_date = getattr(doc, "effective_date", "2026-07-21")
        version = getattr(doc, "version", "1.0")
        dataset_name = getattr(doc, "dataset_name", "default")

        # If the document is already small enough, return as-is
        if len(text) <= self.chunk_size:
            chunk = Chunk(
                chunk_id=self._make_chunk_id(doc.doc_id, 0),
                content=text,
                doc_id=doc.doc_id,
                source_type=doc.source_type,
                source_file=doc.source_file,
                title=doc.title,
                acl_roles=doc.acl_roles,
                metadata={**doc.metadata, "chunk_index": 0, "total_chunks": 1},
                effective_date=effective_date,
                version=version,
                dataset_name=dataset_name,
            )
            return [chunk]

        # Split into text segments
        segments = self._split_text(text)

        # Build overlapping chunks from segments
        chunks = []
        for i, segment in enumerate(segments):
            chunk = Chunk(
                chunk_id=self._make_chunk_id(doc.doc_id, i),
                content=segment,
                doc_id=doc.doc_id,
                source_type=doc.source_type,
                source_file=doc.source_file,
                title=doc.title,
                acl_roles=doc.acl_roles,
                metadata={
                    **doc.metadata,
                    "chunk_index": i,
                    "total_chunks": len(segments),
                },
                effective_date=effective_date,
                version=version,
                dataset_name=dataset_name,
            )
            chunks.append(chunk)

        return chunks

    def _split_text(self, text: str) -> list[str]:
        """Recursively split text into chunks with overlap."""
        separators = ["\n\n", "\n", ". ", " "]

        for sep in separators:
            parts = text.split(sep)
            if len(parts) > 1:
                return self._merge_parts(parts, sep)

        # Last resort: hard split by character count
        return self._hard_split(text)

    def _merge_parts(self, parts: list[str], separator: str) -> list[str]:
        """Merge small parts into chunks of target size with overlap."""
        chunks = []
        current = ""

        for part in parts:
            candidate = current + separator + part if current else part

            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current.strip())
                # Start new chunk — include overlap from the end of previous
                if chunks and self.chunk_overlap > 0:
                    overlap_text = chunks[-1][-self.chunk_overlap :]
                    current = overlap_text + separator + part
                else:
                    current = part

                # If a single part exceeds chunk_size, force-add it
                if len(current) > self.chunk_size * 1.5:
                    chunks.append(current.strip())
                    current = ""

        if current.strip():
            chunks.append(current.strip())

        # Filter out chunks that are too small
        chunks = [c for c in chunks if len(c) >= self.min_chunk_size]

        return chunks

    def _hard_split(self, text: str) -> list[str]:
        """Hard split by character count as last resort."""
        chunks = []
        for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
            chunk = text[i : i + self.chunk_size]
            if len(chunk) >= self.min_chunk_size:
                chunks.append(chunk)
        return chunks

    @staticmethod
    def _make_chunk_id(doc_id: str, index: int) -> str:
        """Generate a unique chunk ID."""
        raw = f"{doc_id}:chunk:{index}"
        short_hash = hashlib.md5(raw.encode()).hexdigest()[:8]
        return f"{doc_id}_c{index}_{short_hash}"
