"""
PDF parser for VaultIQ.
Parses text-based and scanned PDFs using PyMuPDF (fitz).
"""

import os
from . import BaseParser, Document

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


class PDFParser(BaseParser):
    """Parse PDF files into page-level Document chunks.

    Uses PyMuPDF for text extraction. Falls back to basic text
    extraction for scanned pages (OCR integration planned).
    """

    source_type = "pdf"

    def parse(self, file_path: str) -> list[Document]:
        """Parse a PDF file into per-page Document chunks.

        Args:
            file_path: Path to the PDF file.

        Returns:
            List of Document objects, one per page with content.
        """
        if fitz is None:
            raise ImportError(
                "PyMuPDF is required for PDF parsing. Install with: pip install pymupdf"
            )

        doc = fitz.open(file_path)
        title = self._extract_title(doc, file_path)
        documents = []

        full_text = ""
        for page in doc:
            full_text += page.get_text()

        acl_roles = self._extract_acl_from_text(full_text)

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").strip()

            if not text or len(text) < 20:
                # Page has very little text — might be a scanned page
                # For now, mark it as needing OCR
                text = f"[Page {page_num + 1}: Image-based content — OCR required]"

            document = Document(
                doc_id=self._generate_doc_id(file_path, page_num),
                content=text,
                source_type=self.source_type,
                source_file=os.path.basename(file_path),
                title=title,
                acl_roles=acl_roles,
                metadata={
                    "page_number": page_num + 1,
                    "total_pages": len(doc),
                    "has_images": len(page.get_images()) > 0,
                    "has_tables": "table" in text.lower() or "|" in text,
                },
            )
            documents.append(document)

        doc.close()
        return documents

    def _extract_title(self, doc, file_path: str) -> str:
        """Extract title from PDF metadata or first page text."""
        # Try PDF metadata first
        metadata = doc.metadata
        if metadata and metadata.get("title"):
            return metadata["title"]

        # Try first page first line
        if len(doc) > 0:
            first_page_text = doc[0].get_text("text").strip()
            if first_page_text:
                first_line = first_page_text.split("\n")[0].strip()
                if len(first_line) > 5 and len(first_line) < 100:
                    return first_line

        # Fallback to filename
        return os.path.splitext(os.path.basename(file_path))[0].replace("_", " ").title()
