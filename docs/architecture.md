# VaultIQ — Architecture Overview (C4 Level 1)

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER (Browser)                           │
│                     Asks a question +                           │
│                   selects their role                            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    STREAMLIT WEB APP                             │
│              Chat UI · Role selector · Citations                │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      QUERY ENGINE                               │
│                                                                 │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐    │
│  │ Query        │   │ HyDE         │   │ Multi-Query      │    │
│  │ Rewriting    │──▶│ (Hypothetical│──▶│ Generation       │    │
│  │              │   │  Answer)     │   │                  │    │
│  └──────────────┘   └──────────────┘   └────────┬─────────┘    │
│                                                  │              │
│  ┌───────────────────────────────────────────────▼───────────┐  │
│  │              HYBRID RETRIEVAL                             │  │
│  │                                                           │  │
│  │  ┌─────────────────┐     ┌─────────────────┐             │  │
│  │  │  Dense Search    │     │  Sparse Search   │             │  │
│  │  │  (Qdrant)        │     │  (BM25)          │             │  │
│  │  │  all-MiniLM-L6   │     │  rank-bm25       │             │  │
│  │  │  384-dim vectors │     │  TF-IDF scoring   │             │  │
│  │  └────────┬────────┘     └────────┬──────────┘             │  │
│  │           │       top-20 each     │                        │  │
│  │           └───────────┬───────────┘                        │  │
│  │                       ▼                                    │  │
│  │            ┌─────────────────────┐                         │  │
│  │            │  RRF Fusion         │  Reciprocal Rank        │  │
│  │            │  → top-10 merged    │  Fusion                 │  │
│  │            └─────────┬───────────┘                         │  │
│  │                      ▼                                     │  │
│  │            ┌─────────────────────┐                         │  │
│  │            │  Cross-Encoder      │  ms-marco-MiniLM        │  │
│  │            │  Re-ranker → top-5  │                         │  │
│  │            └─────────┬───────────┘                         │  │
│  │                      ▼                                     │  │
│  │            ┌─────────────────────┐                         │  │
│  │            │  ACL Filter         │  Only docs matching     │  │
│  │            │  (Role-based)       │  user's role pass       │  │
│  │            └─────────────────────┘                         │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                  │              │
│                                                  ▼              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              LLM GENERATION (Groq — Llama-3-8B)           │  │
│  │  Prompt: "Answer using ONLY the provided context.         │  │
│  │           Cite sources inline as [📄 source · location]"  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   DATA INGESTION LAYER                           │
│                                                                 │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │
│  │  Markdown   │ │    PDF     │ │   Slack    │ │   CSV      │   │
│  │  Parser     │ │  Parser    │ │  Parser    │ │  Parser    │   │
│  │ (12 files)  │ │ (4 files)  │ │ (8 threads)│ │ (4 files)  │   │
│  │ 122 chunks  │ │  9 chunks  │ │  8 chunks  │ │ 84 chunks  │   │
│  └──────┬─────┘ └──────┬─────┘ └──────┬─────┘ └──────┬─────┘   │
│         └──────────────┴──────────────┴──────────────┘          │
│                              │                                  │
│                    ┌─────────▼──────────┐                       │
│                    │  223 Document      │                       │
│                    │  Chunks            │                       │
│                    │  (with ACL +       │                       │
│                    │   metadata)        │                       │
│                    └────────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘

Data Sources:
  📝 Wiki/Confluence (Markdown) — policies, guides, team docs
  📄 PDFs — handbook, financials, architecture, security
  💬 Slack Threads (JSON) — team conversations, incidents
  📊 CSV/Excel — employee dir, vendors, projects, budgets

ACL Roles: all-employees | engineering | hr | leadership
```

## Component Summary

| Layer | Component | Technology | Status |
|-------|-----------|------------|--------|
| **Data** | Synthetic data | 4 source types, 28 files | ✅ Done |
| **Ingestion** | 4 parsers + pipeline | Python, PyMuPDF, pandas | ✅ Done |
| **Chunking** | Semantic + structural | LangChain splitters | 🔲 Week 2 |
| **Embedding** | Dense vectors | all-MiniLM-L6-v2 | 🔲 Week 2 |
| **Vector DB** | Dense search + ACL | Qdrant (local) | 🔲 Week 2 |
| **Sparse** | BM25 keyword search | rank-bm25 | 🔲 Week 2 |
| **Fusion** | RRF merge | Custom Python | 🔲 Week 2 |
| **Re-ranking** | Cross-encoder | ms-marco-MiniLM | 🔲 Week 2 |
| **LLM** | Answer generation | Groq (Llama-3-8B) | 🔲 Week 2 |
| **UI** | Chat interface | Streamlit | 🔲 Week 2 |
| **Eval** | 100 Q&A pairs | RAGAS | 🔲 Week 3 |
