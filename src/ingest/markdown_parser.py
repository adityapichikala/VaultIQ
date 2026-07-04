"""
Markdown parser for VaultIQ.
Parses Confluence/Wiki-style markdown documents with heading-aware chunking.
"""

import os
import re
from . import BaseParser, Document


class MarkdownParser(BaseParser):
    """Parse markdown files into heading-aware Document chunks."""

    source_type = "wiki"

    def parse(self, file_path: str) -> list[Document]:
        """Parse a markdown file into chunks split by headings.

        Each chunk preserves its heading hierarchy as metadata.

        Args:
            file_path: Path to the markdown file.

        Returns:
            List of Document objects, one per heading section.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        title = self._extract_title(content, file_path)
        acl_roles = self._extract_acl_from_text(content)
        sections = self._split_by_headings(content)

        documents = []
        for i, section in enumerate(sections):
            if not section["content"].strip():
                continue

            # Build the full section path (e.g., "Remote Work Policy > Eligibility > Roles Not Eligible")
            heading_path = " > ".join(section["heading_path"]) if section["heading_path"] else title

            doc = Document(
                doc_id=self._generate_doc_id(file_path, i),
                content=section["content"].strip(),
                source_type=self.source_type,
                source_file=os.path.basename(file_path),
                title=title,
                acl_roles=acl_roles,
                metadata={
                    "heading_path": heading_path,
                    "heading_level": section["level"],
                    "section_index": i,
                },
            )
            documents.append(doc)

        return documents

    def _extract_title(self, content: str, file_path: str) -> str:
        """Extract the document title from the first H1 heading or filename."""
        for line in content.split("\n"):
            if line.startswith("# ") and not line.startswith("## "):
                return line.lstrip("# ").strip()
        # Fallback to filename
        return os.path.splitext(os.path.basename(file_path))[0].replace("_", " ").title()

    def _split_by_headings(self, content: str) -> list[dict]:
        """Split markdown content into sections based on headings.

        Returns a list of dicts with keys: content, heading_path, level.
        """
        lines = content.split("\n")
        sections = []
        current_content_lines = []
        heading_stack = []  # Stack of (level, heading_text)
        current_level = 0

        for line in lines:
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if heading_match:
                # Save the previous section
                if current_content_lines:
                    sections.append({
                        "content": "\n".join(current_content_lines),
                        "heading_path": [h[1] for h in heading_stack],
                        "level": current_level,
                    })
                    current_content_lines = []

                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()

                # Update heading stack — pop headings at same or deeper level
                while heading_stack and heading_stack[-1][0] >= level:
                    heading_stack.pop()
                heading_stack.append((level, heading_text))
                current_level = level

                # Include the heading in the content
                current_content_lines.append(line)
            else:
                current_content_lines.append(line)

        # Don't forget the last section
        if current_content_lines:
            sections.append({
                "content": "\n".join(current_content_lines),
                "heading_path": [h[1] for h in heading_stack],
                "level": current_level,
            })

        return sections
