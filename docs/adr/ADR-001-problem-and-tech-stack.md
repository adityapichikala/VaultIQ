# ADR-001: Problem Statement & Tech Stack Choice

**Date:** June 24, 2026  
**Status:** Accepted  
**Author:** Pichikala Aditya

---

## Context

We are building **VaultIQ**, an enterprise RAG (Retrieval-Augmented Generation) system
as part of Problem E3 — "RAG over Enterprise Mess" in the LLM Systems & Applied GenAI
segment. The core challenge is building a system that handles **4 different document
formats** (Markdown, PDF, Slack JSON, CSV) with varying structures, quality levels,
and access permissions.

Key requirements:
1. Multi-format ingestion with format-specific parsers
2. Hybrid retrieval (dense + sparse) for robust search
3. ACL-based document access control
4. Inline citations in generated answers
5. 100 Q&A evaluation pairs across difficulty levels
6. Must run locally on a laptop (no cloud dependency for dev)

## Decision

### Tech Stack

| Component | Choice | Justification |
|-----------|--------|---------------|
| **PDF Parsing** | PyMuPDF (fitz) | Fast C-based parser, handles both text and image PDFs, extracts page structure |
| **OCR** | EasyOCR | Free, supports Indian languages, accurate on printed text |
| **Embeddings** | sentence-transformers (all-MiniLM-L6-v2) | Free, runs locally, 384-dim embeddings, good quality for its size |
| **Vector DB** | Qdrant (local mode) | Native hybrid search (dense + sparse), excellent payload filtering for ACLs, open source |
| **Sparse Retrieval** | rank-bm25 | Simple, no infrastructure needed, effective for keyword matching |
| **Reranker** | cross-encoder/ms-marco-MiniLM-L6-v2 | Improves precision on top-k results, small enough to run locally |
| **LLM** | Groq API (Llama-3-8B) | Free tier available, fast inference (~500 tokens/sec), good instruction following |
| **UI** | Streamlit | Rapid prototyping, built-in components for chat UIs, easy deployment |
| **Orchestration** | Python (custom) | No need for LangChain/LlamaIndex overhead for our use case |
| **Logging** | Loguru | Better defaults than stdlib logging, structured output |

### Architecture Pattern

We chose a **modular pipeline architecture** over a framework-based approach (LangChain,
LlamaIndex). Reasons:

1. **Transparency**: Every step is debuggable without framework abstractions
2. **Flexibility**: Easy to swap components (e.g., change vector DB, change LLM)
3. **Interview-defensibility**: Can explain every line of code, no "it's a LangChain thing"
4. **Performance**: No unnecessary serialization or abstraction overhead

## Consequences

### Positive
- Entire stack runs locally on a laptop (no cloud costs during development)
- Every component has a free tier or is open source
- No vendor lock-in — can switch any component independently
- Architecture is interview-defensible — no black boxes

### Negative
- More code to write (no framework magic)
- all-MiniLM-L6-v2 is not the best embedding model (but it's free and fast)
- Groq free tier has rate limits (30 req/min) — may need caching for demo
- No streaming support initially

## Alternatives Considered

| Alternative | Why Rejected |
|------------|-------------|
| **pgvector** for vector DB | No native hybrid search, slower at scale, less flexible filtering |
| **Weaviate** for vector DB | Heavier infrastructure, overkill for our scale |
| **OpenAI API** for embeddings/LLM | Costs money, adds API dependency, harder to demo offline |
| **LangChain** for orchestration | Too much abstraction, harder to debug, overkill for this project |
| **Chroma** for vector DB | Limited filtering, no native hybrid search |
| **Gemini** for LLM | Considered as backup; Groq is faster for Llama models |

---

*This ADR will be reviewed after Week 1 to validate that the chosen stack meets
performance and usability requirements.*
