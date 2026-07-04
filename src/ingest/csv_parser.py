"""
CSV/Excel parser for VaultIQ.
Parses structured data files with column headers prepended for context.
"""

import os
from . import BaseParser, Document

try:
    import pandas as pd
except ImportError:
    pd = None


class CSVParser(BaseParser):
    """Parse CSV/Excel files into row-level Document chunks.

    Each row becomes one document with column headers prepended
    for context, making the content searchable and self-describing.
    """

    source_type = "csv"

    def parse(self, file_path: str) -> list[Document]:
        """Parse a CSV or Excel file into row-level Document chunks.

        Args:
            file_path: Path to the CSV or Excel file.

        Returns:
            List of Document objects, one per row.
        """
        if pd is None:
            raise ImportError("pandas is required for CSV parsing. Install with: pip install pandas")

        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)

        title = os.path.splitext(os.path.basename(file_path))[0].replace("_", " ").title()
        columns = list(df.columns)

        # Determine ACL from filename or content
        acl_roles = self._infer_acl(file_path, columns)

        documents = []

        # Create a summary document for the entire table
        summary = self._create_table_summary(df, title, columns)
        summary_doc = Document(
            doc_id=self._generate_doc_id(file_path, 0),
            content=summary,
            source_type=self.source_type,
            source_file=os.path.basename(file_path),
            title=f"{title} (Summary)",
            acl_roles=acl_roles,
            metadata={
                "columns": columns,
                "row_count": len(df),
                "is_summary": True,
            },
        )
        documents.append(summary_doc)

        # Create per-row documents
        for idx, row in df.iterrows():
            content = self._format_row(columns, row)

            doc = Document(
                doc_id=self._generate_doc_id(file_path, idx + 1),
                content=content,
                source_type=self.source_type,
                source_file=os.path.basename(file_path),
                title=title,
                acl_roles=acl_roles,
                metadata={
                    "row_index": int(idx),
                    "columns": columns,
                    "primary_value": str(row.iloc[0]) if len(row) > 0 else "",
                },
            )
            documents.append(doc)

        return documents

    def _format_row(self, columns: list[str], row) -> str:
        """Format a single row with column names for context.

        Example output:
            employee_id: EMP001
            full_name: Vikram Mehta
            department: Engineering
            role: VP Engineering
        """
        lines = []
        for col in columns:
            value = row[col]
            if pd.notna(value):
                lines.append(f"{col}: {value}")
        return "\n".join(lines)

    def _create_table_summary(self, df, title: str, columns: list[str]) -> str:
        """Create a summary description of the table."""
        lines = [
            f"Table: {title}",
            f"Columns: {', '.join(columns)}",
            f"Total rows: {len(df)}",
            "",
        ]

        # Add some descriptive stats for key columns
        for col in columns:
            if df[col].dtype == "object":
                unique = df[col].nunique()
                if unique <= 10:
                    values = df[col].value_counts().head(5)
                    lines.append(f"{col} — {unique} unique values: {', '.join(str(v) for v in values.index)}")
            elif df[col].dtype in ("int64", "float64"):
                lines.append(f"{col} — min: {df[col].min()}, max: {df[col].max()}, mean: {df[col].mean():.1f}")

        return "\n".join(lines)

    def _infer_acl(self, file_path: str, columns: list[str]) -> list[str]:
        """Infer ACL roles from file name and column content."""
        name = os.path.basename(file_path).lower()

        if "employee" in name or "salary" in name or "hr" in name:
            return ["hr", "leadership"]
        elif "vendor" in name or "budget" in name or "financial" in name:
            return ["leadership"]
        elif "project" in name:
            return ["engineering", "leadership"]
        else:
            return ["all-employees"]
