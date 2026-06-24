# Design Doc — AskTheCompany (E3)

**Author:** Pichikala Aditya 
**Date:** June 2026  
**Status:** Draft

---

## Problem

Enterprise knowledge is split across 4+ source types with different formats,
structure, and access permissions. Standard RAG pipelines fail because:
- PDFs have tables and scanned pages needing OCR
- Slack threads have context spread across replies
- Documents have near-duplicates with slight differences
- Users should only retrieve what they're permitted to see

---

## Data sources (4 types)

| Source | Format | Parsing approach |
|--------|--------|-----------------|
| Wiki pages | Markdown | Heading-aware recursive splitting |
| Internal PDFs | PDF | PyMuPDF for text, EasyOCR for scans |
| Team threads | JSON | Thread-aware chunking (keep reply context) |
| Structured data | CSV/Excel | Row + column context preserved |

All documents will carry metadata: `source_type`, `doc_id`, `acl_roles`, `created_at`.

---

## Chunking strategy

- **Markdown:** Split on headings (H1/H2/H3), then recursively by paragraph.
  Each chunk keeps its heading path as metadata.
- **PDF:** Split by page first, then by paragraph within page. Scanned pages
  get OCR'd before chunking.
- **JSON threads:** Each thread is one chunk. Long threads split at reply
  boundaries, keeping the parent message in each chunk.
- **CSV:** Each row is a chunk. Column headers prepended to every chunk for context.

Target chunk size: 400 tokens. Overlap: 50 tokens.

---

## Retrieval architecture

1. **Query rewriting** — HyDE (generate a hypothetical answer, embed it)
2. **Dense retrieval** — Qdrant with all-MiniLM-L6-v2 embeddings, top-20
3. **Sparse retrieval** — BM25 on same corpus, top-20
4. **Fusion** — Reciprocal Rank Fusion (RRF) to merge both lists → top-10
5. **Reranking** — cross-encoder/ms-marco-MiniLM on top-10 → top-5
6. **ACL filter** — applied at step 2 and 3, before any results are returned

---

## Permissions model

Every document has an `acl_roles` field: a list of roles that can access it.
Example: `["engineering", "hr"]` means only engineering and HR users see it.

At retrieval time, Qdrant filters on `acl_roles` using a payload filter.
BM25 index is partitioned per role.

For the demo: 3 simulated roles — `engineering`, `hr`, `leadership`.

---

## Citations

Every answer chunk gets: source type icon, document title, and
page/section/row reference. Format: `[📄 HR_Manual.pdf · page 4]`

---

## Eval plan

100 Q&A pairs across 4 difficulty levels:
- Factual (single document lookup)
- Multi-hop (answer requires 2+ documents)
- Table lookup (answer is in a CSV row)
- Ambiguous (multiple plausible answers)

Metrics: answer accuracy, citation precision, retrieval recall @ 5.
Tool: RAGAS.

---

## Open questions

- OCR quality on low-resolution scans — may need preprocessing
- Dedup threshold — cosine similarity cutoff TBD after first run
- LLM choice — Groq (Llama-3-8b) vs Gemini free tier
