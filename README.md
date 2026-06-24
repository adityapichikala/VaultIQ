# VaultIQ — Enterprise RAG over Messy Multi-Modal Data

> Segment 5 · Problem E3 · LLM Systems & Applied GenAI  
> Built by: YOUR NAME | Target role: LLM Engineer

---

## What this is

Most enterprises have 15 years of knowledge scattered across Confluence pages,
PDFs (some scanned), Slack threads, and Excel sheets. Off-the-shelf RAG fails
on this data because it has tables, OCR requirements, threaded conversations,
near-duplicate documents, and permission boundaries.

**VaultIQ** is an enterprise RAG system that handles all of this — with
hybrid retrieval, ACL-based permissions, inline citations, and a 100 Q&A eval.

---

## Demo

> Loom walkthrough — coming Week 1  
> Live URL — coming Week 4

---

## Problem statement

Build a "ask the company anything" internal tool over 4 source types:
Confluence-like markdown pages, PDFs (text + scanned), Slack-like JSON threads,
and Excel/CSV tables. With permissions, deduplication, citations, and eval.

**Problem code:** E3  
**Segment:** LLM Systems & Applied GenAI

---

## Architecture

> Diagram coming Day 5

---

## Tech stack

| Component | Tool | Why |
|-----------|------|-----|
| PDF parsing | PyMuPDF | Fast, handles text + image PDFs |
| OCR | EasyOCR | Free, accurate on printed text |
| Markdown parsing | python-markdown | Heading-aware structure |
| Table extraction | pandas | CSV/Excel ingestion |
| Chunking | LangChain text splitters | Semantic + structural splits |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | Free, runs locally |
| Vector DB | Qdrant (local) | Hybrid search, open source |
| BM25 | rank-bm25 | Sparse retrieval, no infra needed |
| Reranker | cross-encoder/ms-marco-MiniLM | Improves retrieval precision |
| LLM | Groq API (Llama-3-8b) | Free tier, fast inference |
| UI | Streamlit | Rapid prototyping |

---

## Quickstart

```bash
git clone https://github.com/YOUR_GITHUB_USERNAME/vaultiq
cd vaultiq
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # add your Groq API key
streamlit run src/app/main.py
```

> Full setup instructions coming after Week 1 build.

---

## Data sources

| Source type | Format | Example |
|-------------|--------|---------|
| Wiki/Confluence pages | Markdown (.md) | Company policies, onboarding docs |
| Internal documents | PDF (text + scanned) | HR manuals, legal contracts |
| Team conversations | JSON (Slack-like threads) | Project discussions, decisions |
| Structured data | CSV/Excel | Org charts, vendor lists |

All data is **synthetic** — generated to simulate realistic enterprise content.
See `data/synthetic/README.md` for schema and generation instructions.

---

## Project structure

vaultiq/

├── src/

│   ├── ingest/        # per-source parsers

│   ├── chunking/      # semantic + structural chunking

│   ├── retrieval/     # BM25 + dense + reranker

│   └── app/           # Streamlit UI

├── data/synthetic/    # generated test documents

├── docs/

│   ├── architecture.png

│   ├── design_doc.md

│   └── adr/           # architecture decision records

└── tests/

---

## ADRs

- ADR-001: Vector DB choice — coming Week 2
- ADR-002: Chunking strategy — coming Week 2
- ADR-003: Retrieval architecture — coming Week 2

---

## Known limitations

- Currently uses synthetic data only (no live connectors)
- Single-user ACL simulation (no real auth)

---

## License

MIT
