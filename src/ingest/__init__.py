"""
Base document model and parser interface for VaultIQ.
All parsers inherit from BaseParser and return Document objects.
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Document:
    """Represents a parsed document chunk ready for embedding."""

    doc_id: str
    content: str
    source_type: str  # "wiki", "pdf", "slack", "csv"
    source_file: str  # Original file path
    title: str
    acl_roles: list[str] = field(default_factory=lambda: ["all-employees"])
    metadata: dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def __repr__(self):
        preview = self.content[:80].replace("\n", " ")
        return f"Document(id={self.doc_id}, type={self.source_type}, title={self.title}, content='{preview}...')"

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "doc_id": self.doc_id,
            "content": self.content,
            "source_type": self.source_type,
            "source_file": self.source_file,
            "title": self.title,
            "acl_roles": self.acl_roles,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


class BaseParser:
    """Abstract base class for all document parsers."""

    source_type: str = "unknown"

    def parse(self, file_path: str) -> list[Document]:
        """Parse a file and return a list of Document objects.

        Args:
            file_path: Absolute or relative path to the file.

        Returns:
            List of Document objects extracted from the file.
        """
        raise NotImplementedError("Subclasses must implement parse()")

    def _generate_doc_id(self, file_path: str, chunk_index: int = 0) -> str:
        """Generate a unique document ID from file path and chunk index."""
        import hashlib
        import os

        base = os.path.basename(file_path)
        name = os.path.splitext(base)[0]
        hash_input = f"{file_path}:{chunk_index}"
        short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        return f"{self.source_type}_{name}_{short_hash}"

    def _extract_acl_from_text(self, text: str) -> list[str]:
        """Extract ACL roles from document text (looks for 'ACL:' line)."""
        for line in text.split("\n"):
            line_lower = line.lower().strip()
            if line_lower.startswith("**acl:") or line_lower.startswith("acl:"):
                # Extract the value after "ACL:"
                acl_part = line.split(":", 1)[1].strip().strip("*").strip()
                roles = [r.strip() for r in acl_part.split(",")]
                return roles
        return ["all-employees"]
