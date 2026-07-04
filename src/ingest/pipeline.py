"""
Ingestion pipeline for VaultIQ.
Orchestrates all parsers to ingest documents from the synthetic data directory.
"""

import os
import json
from loguru import logger

from . import Document
from .markdown_parser import MarkdownParser
from .pdf_parser import PDFParser
from .slack_parser import SlackParser
from .csv_parser import CSVParser


class IngestionPipeline:
    """Orchestrates document ingestion from all source types.

    Scans the data directory, routes files to the appropriate parser,
    and returns a unified list of Document objects.
    """

    def __init__(self):
        self.markdown_parser = MarkdownParser()
        self.pdf_parser = PDFParser()
        self.slack_parser = SlackParser()
        self.csv_parser = CSVParser()
        self._documents: list[Document] = []

    @property
    def documents(self) -> list[Document]:
        """Return all ingested documents."""
        return self._documents

    def ingest_directory(self, data_dir: str) -> list[Document]:
        """Ingest all documents from a data directory.

        Expects the directory structure:
            data_dir/
            ├── wiki/     (*.md files)
            ├── pdfs/     (*.pdf files)
            ├── slack/    (*.json files)
            └── csv/      (*.csv files)

        Args:
            data_dir: Path to the root data directory.

        Returns:
            List of all parsed Document objects.
        """
        self._documents = []

        # Ingest wiki/markdown files
        wiki_dir = os.path.join(data_dir, "wiki")
        if os.path.isdir(wiki_dir):
            self._ingest_wiki(wiki_dir)

        # Ingest PDF files
        pdf_dir = os.path.join(data_dir, "pdfs")
        if os.path.isdir(pdf_dir):
            self._ingest_pdfs(pdf_dir)

        # Ingest Slack threads
        slack_dir = os.path.join(data_dir, "slack")
        if os.path.isdir(slack_dir):
            self._ingest_slack(slack_dir)

        # Ingest CSV/Excel files
        csv_dir = os.path.join(data_dir, "csv")
        if os.path.isdir(csv_dir):
            self._ingest_csv(csv_dir)

        logger.info(
            f"Ingestion complete: {len(self._documents)} documents from {data_dir}"
        )
        self._print_summary()

        return self._documents

    def _ingest_wiki(self, wiki_dir: str):
        """Ingest all markdown files from the wiki directory."""
        md_files = [
            f for f in os.listdir(wiki_dir) if f.endswith(".md") and f != "README.md"
        ]
        logger.info(f"Found {len(md_files)} wiki/markdown files")

        for filename in sorted(md_files):
            file_path = os.path.join(wiki_dir, filename)
            try:
                docs = self.markdown_parser.parse(file_path)
                self._documents.extend(docs)
                logger.debug(f"  ✓ {filename} → {len(docs)} chunks")
            except Exception as e:
                logger.error(f"  ✗ {filename} — {e}")

    def _ingest_pdfs(self, pdf_dir: str):
        """Ingest all PDF files from the pdfs directory."""
        pdf_files = [f for f in os.listdir(pdf_dir) if f.endswith(".pdf")]
        logger.info(f"Found {len(pdf_files)} PDF files")

        for filename in sorted(pdf_files):
            file_path = os.path.join(pdf_dir, filename)
            try:
                docs = self.pdf_parser.parse(file_path)
                self._documents.extend(docs)
                logger.debug(f"  ✓ {filename} → {len(docs)} chunks")
            except Exception as e:
                logger.error(f"  ✗ {filename} — {e}")

    def _ingest_slack(self, slack_dir: str):
        """Ingest all JSON thread files from the slack directory."""
        json_files = [f for f in os.listdir(slack_dir) if f.endswith(".json")]
        logger.info(f"Found {len(json_files)} Slack thread files")

        for filename in sorted(json_files):
            file_path = os.path.join(slack_dir, filename)
            try:
                docs = self.slack_parser.parse(file_path)
                self._documents.extend(docs)
                logger.debug(f"  ✓ {filename} → {len(docs)} chunks")
            except Exception as e:
                logger.error(f"  ✗ {filename} — {e}")

    def _ingest_csv(self, csv_dir: str):
        """Ingest all CSV files from the csv directory."""
        csv_files = [
            f
            for f in os.listdir(csv_dir)
            if f.endswith(".csv") or f.endswith(".xlsx")
        ]
        logger.info(f"Found {len(csv_files)} CSV/Excel files")

        for filename in sorted(csv_files):
            file_path = os.path.join(csv_dir, filename)
            try:
                docs = self.csv_parser.parse(file_path)
                self._documents.extend(docs)
                logger.debug(f"  ✓ {filename} → {len(docs)} chunks")
            except Exception as e:
                logger.error(f"  ✗ {filename} — {e}")

    def _print_summary(self):
        """Print a summary of ingested documents by source type."""
        from collections import Counter

        type_counts = Counter(d.source_type for d in self._documents)
        logger.info("=" * 50)
        logger.info("Ingestion Summary:")
        for source_type, count in sorted(type_counts.items()):
            logger.info(f"  {source_type:10s}: {count:4d} chunks")
        logger.info(f"  {'TOTAL':10s}: {len(self._documents):4d} chunks")
        logger.info("=" * 50)

    def save_documents(self, output_path: str):
        """Save all ingested documents to a JSON file for inspection."""
        docs_as_dicts = [d.to_dict() for d in self._documents]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(docs_as_dicts, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(docs_as_dicts)} documents to {output_path}")


def main():
    """Run the ingestion pipeline on the synthetic data directory."""
    import sys

    # Determine the data directory
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(project_root, "data", "synthetic")

    if not os.path.isdir(data_dir):
        logger.error(f"Data directory not found: {data_dir}")
        sys.exit(1)

    logger.info(f"Starting ingestion from: {data_dir}")
    pipeline = IngestionPipeline()
    documents = pipeline.ingest_directory(data_dir)

    # Save the output for inspection
    output_path = os.path.join(project_root, "data", "ingested_documents.json")
    pipeline.save_documents(output_path)

    # Print sample documents
    logger.info("\n--- Sample Documents ---")
    for doc in documents[:3]:
        logger.info(f"\n{doc}")
        logger.info(f"  ACL: {doc.acl_roles}")
        logger.info(f"  Metadata: {doc.metadata}")


if __name__ == "__main__":
    main()
