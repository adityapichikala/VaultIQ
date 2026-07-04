# Synthetic Data — VaultIQ

This directory contains synthetic enterprise data simulating BigCorp's internal knowledge base.

## Data Sources

| Source Type | Directory | Count | ACL Roles |
|-------------|-----------|-------|-----------|
| Wiki/Confluence pages | `wiki/` | 10 markdown files | Varies per doc |
| Internal PDFs | `pdfs/` | 4 PDF documents | Varies per doc |
| Slack-like threads | `slack/` | 8 threaded conversations | Varies per thread |
| Structured data | `csv/` | 4 CSV files | hr, leadership, engineering |

## ACL Roles

Documents are tagged with one or more of these simulated access roles:

- `all-employees` — Visible to everyone
- `engineering` — Engineering team only
- `hr` — HR department only
- `leadership` — Directors, VPs, CTO only

## Schema

### Wiki Pages (Markdown)
Each markdown file contains a YAML-like header with metadata:
- `Owner` — Team that owns the document
- `ACL` — Comma-separated roles that can access this document
- Headings, tables, and structured content throughout

### Slack Threads (JSON)
```json
{
  "thread_id": "T001",
  "channel": "#channel-name",
  "acl_roles": ["engineering"],
  "messages": [
    {
      "user": "username",
      "timestamp": "ISO 8601",
      "text": "message content"
    }
  ]
}
```

### CSV Files
Standard CSV with headers. Schema documented in column names.

### PDFs
Generated using `generate_pdfs.py`. Run:
```bash
pip install fpdf2
python data/synthetic/generate_pdfs.py
```

## Data Generation

All data is entirely synthetic. Names, figures, and scenarios are fictional.
No real company data is used. Content is designed to test:
- Multi-format ingestion
- Table extraction
- Thread-aware chunking
- ACL-based filtering
- Cross-source question answering
