# ADR-007: Production Cross-Encoder Reranking, PII Governance, and RAG Triad Evaluation

**Status:** Approved  
**Author:** Pichikala Aditya (Staff Systems Architect)  
**Date:** 2026-07-21  
**Extends:** ADR-003 (Hybrid Retrieval), ADR-005 (Microservice API), ADR-006 (Temporal Recency Decay)

---

## 1. Context & Problem Statement

VaultIQ has successfully deployed microservice APIs, managed hybrid retrieval (Qdrant + BM25), and temporal recency decay scoring. However, enterprise readiness requires addressing four key architectural gaps:

1. **Top-K Retrieval Precision Gap:** Reciprocal Rank Fusion (RRF) relies on independent dense cosine distance and sparse BM25 term frequency. Bi-encoder embeddings do not model token-level cross-attention between query and passage, allowing false positives to slip into LLM context windows.
2. **Data Governance & PII Exposure Risk:** Sensitive enterprise documents (CSVs, vendor lists, support logs) may contain API keys, SSNs, credit card numbers, or internal credentials. Passing un-sanitized context to external LLM providers creates compliance and security risks (HIPAA, GDPR, SOC-2).
3. **Lack of Automated RAG Quality Metrics:** Without an inline evaluation harness measuring Groundedness/Faithfulness, Context Precision, and Answer Relevance (the RAG Triad), system performance cannot be systematically monitored or benchmarked.
4. **Ingestion Resiliency & Duplicate Ingestion:** Processing duplicate files or corrupt Markdown/CSV sources wastes vector database storage and compute resources.

---

## 2. Decision & Architecture Strategy

We implement four core system upgrades across VaultIQ:

### 2.1 Cross-Encoder Reranking Layer (`src/retrieval/reranker.py`)

We introduce a 2nd-stage Cross-Encoder Reranker (`cross-encoder/ms-marco-MiniLM-L-6-v2` or local lightweight cross-attention model). 

- **Workflow:**
  1. 1st Stage: Qdrant (top-20) + BM25 (top-20) fused via RRF $\to$ Top-15 candidate chunks.
  2. 2nd Stage: Cross-Encoder evaluates joint `(query, chunk_text)` pairs through full cross-attention transformer layers, producing fine-grained relevance logits.
  3. Final Top-$K$ (e.g. 5) highest scoring chunks are selected for LLM context assembly.

### 2.2 Security & PII Redaction Middleware (`src/security/pii_sanitizer.py`)

We deploy an asynchronous PII Redaction Pipeline that inspects and sanitizes text prior to vector indexing and LLM prompt generation.

- **Redaction Targets:**
  - Social Security Numbers (SSNs): `\b\d{3}-\d{2}-\d{4}\b` $\to$ `[REDACTED_SSN]`
  - API / Secret Keys (AWS, Bearer, Generic Hex): `(AKIA[0-9A-Z]{16}|sk-[a-zA-Z0-9]{32,})` $\to$ `[REDACTED_API_KEY]`
  - Credit Card Numbers: `\b(?:\d[ -]*?){13,16}\b` $\to$ `[REDACTED_CREDIT_CARD]`
  - Email Addresses & IP Addresses: `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b` $\to$ `[REDACTED_EMAIL]`

- **Placement:** Placed in `IngestionPipeline` (pre-vectorization) and `RAGChain` (pre-prompt assembly).

### 2.3 RAG Triad Evaluation Engine (`src/evaluation/rag_triad.py`)

We build an automated evaluation engine measuring three core RAG Triad metrics for every response:

1. **Context Precision (0.0 – 1.0):** Proportion of retrieved chunks containing relevant keywords/concepts matching the query.
2. **Faithfulness / Groundedness (0.0 – 1.0):** Verification ratio of claims in the generated answer backed directly by retrieved context sentences.
3. **Answer Relevance (0.0 – 1.0):** Semantic embedding similarity between user query and generated response.

Metrics are returned in API metadata and displayed in the RAG Visualizer UI tab.

### 2.4 Streamlined Event-Driven Ingestion with SHA-256 Deduplication (`src/ingest/pipeline.py`)

- **Document Deduplication:** SHA-256 content hashes are calculated for each file. Duplicate file ingestion requests skip redundant chunking and vector embedding computations.
- **Resilient Fallback:** Parsing errors in malformed files are caught, logged, and isolated without crashing the ingestion job.

---

## 3. Consequences

### Positive
- **Drastic Precision Improvement:** Cross-Encoder reranking eliminates false positive context chunks.
- **SOC-2 & GDPR Compliance:** Zero PII or API secrets leak to external LLM providers or logs.
- **Automated Observability:** RAG Triad scores provide real-time quality assurance metrics on every answer.
- **Ingestion Efficiency:** File hash deduplication prevents duplicate vector overhead.

### Trade-offs
- **Latency Overhead:** Cross-encoder reranking adds ~15-30ms to query execution, mitigated by scoring only top-15 RRF candidates.
