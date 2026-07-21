# VaultIQ — Enterprise Hybrid RAG Search & Governance Engine

VaultIQ is a production-grade, secure **Retrieval-Augmented Generation (RAG)** platform designed for enterprise knowledge management. It integrates multi-source document ingestion, hybrid semantic-lexical search, temporal recency decay scoring, neural Cross-Encoder reranking, role-based Access Control Lists (ACLs), automated PII sanitization, and inline RAG Triad metrics evaluation.

Built with a microservice architecture consisting of a **FastAPI backend** and a **Reflex modern web app**, VaultIQ ensures data governance and lightning-fast search latency.

---

## 🏗️ System Architecture Flow

The following diagram illustrates how user queries and documents traverse the ingestion and retrieval pipelines:

```
                      [ INGESTION PIPELINE ]
                      
  Markdown Wiki       PDF Files       Slack JSON       CSV Sheets
        │                 │                │                │
        ▼                 ▼                ▼                ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                  Multi-Format Parser Module                 │
   └──────────────────────────────┬──────────────────────────────┘
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │            Asynchronous PII Redaction Middleware            │
   │      (Scrubs SSNs, API Keys, Credit Cards, and Emails)      │
   └──────────────────────────────┬──────────────────────────────┘
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │         SHA-256 Content Deduplication Hash Registry         │
   └──────────────────────────────┬──────────────────────────────┘
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │            Recursive Chunk Splitter (500 chars)             │
   └──────────────────────────────┬──────────────────────────────┘
                                  ├──────────────────────────────┐
                                  ▼                              ▼
                       ┌────────────────────┐          ┌───────────────────┐
                       │ SentenceTransformer│          │    Lexical BM25   │
                       │ (all-MiniLM-L6-v2) │          │    Okapi Index    │
                       └──────────┬─────────┘          └─────────┬─────────┘
                                  ▼                              ▼
                       ┌────────────────────┐          ┌───────────────────┐
                       │ Qdrant Vector DB   │          │ BM25 serialized   │
                       │ (HNSW Dense Index) │          │    Pickle file    │
                       └────────────────────┘          └───────────────────┘

─────────────────────────────────────────────────────────────────────────

                      [ RETRIEVAL & RAG CHAIN ]

                              User Query
                                  │
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                  Role-Based JWT Scope (ACL)                 │
   └──────────────────────────────┬──────────────────────────────┘
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │          PII Query Scrubber (Saves prompt privacy)          │
   └──────────────────────────────┬──────────────────────────────┘
                                  ▼
                        Dual-Index Retrieval
                        ├── Dense Search (Qdrant Cosine top-20)
                        └── Sparse Search (BM25 term-freq top-20)
                                  │
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │               Reciprocal Rank Fusion (RRF)                  │
   └──────────────────────────────┬──────────────────────────────┘
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │             Temporal Recency Decay Weighting                │
   │                   exp(-λ * Age_in_Days)                     │
   └──────────────────────────────┬──────────────────────────────┘
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │           Role-Based Access Control Filtering (ACL)         │
   └──────────────────────────────┬──────────────────────────────┘
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │         2nd-Stage Neural Cross-Encoder Reranking            │
   │             (Re-scores top-15 RRF candidates)               │
   └──────────────────────────────┬──────────────────────────────┘
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │               LLaMA-3.1 8B Instant via Groq LPU             │
   └──────────────────────────────┬──────────────────────────────┘
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                RAG Triad Metric Evaluator                   │
   │      - Groundedness / Faithfulness (claims vs context)      │
   │      - Context Precision (relevant retrieved ratio)          │
   │      - Answer Relevance (semantic overlap with query)       │
   └──────────────────────────────┬──────────────────────────────┘
                                  ▼
                    Real-time SSE Token Stream
```

---

## 🌟 Key Features

1. **Dual-Stage Hybrid Search & Neural Reranking:**
   - **Stage 1:** Combines dense semantics (`all-MiniLM-L6-v2` in Qdrant) with lexical precision (`BM25Okapi`) fused via **Reciprocal Rank Fusion (RRF)**.
   - **Stage 2:** A neural Cross-Encoder (`ms-marco-MiniLM-L-6-v2`) evaluates joint query-passage cross-attention to filter false positives.
   - **Snappy Fallback:** Falls back to an optimized keyword-overlap heuristic if neural weights are offline, ensuring zero presentation delays.

2. **Data Governance & PII Redaction Middleware:**
   - Regex-based high-performance scrubbing scrubs Social Security Numbers (SSNs), Credit Card Numbers, Email Addresses, and API Secrets/Keys (e.g. AWS credentials) from ingested documents and incoming queries before LLM prompt submission.

3. **Role-Based Access Control Lists (ACLs):**
   - Restricts retrieved paragraphs dynamically based on user identity (e.g., leadership, engineering, HR, or all-employees).

4. **Temporal Recency Decay:**
   - Integrates exponential age-decay parameters ($S_{\text{decay}} = S_{\text{base}} \times e^{-\lambda \Delta t}$) to rank active, updated documents higher than stale ones.

5. **Live RAG Triad Metrics Governance:**
   - Real-time quality evaluation: computes Groundedness/Faithfulness, Context Precision, and Answer Relevance. Displays these scores as color-coded badges in the UI.

---

## 📂 Project Structure

```
VaultIQ/
├── docs/                     # ADRs and design decisions
├── src/
│   ├── api/                  # FastAPI endpoints & routes
│   ├── evaluation/           # RAG Triad evaluation metrics
│   ├── ingest/               # Parsers for MD, PDF, Slack JSON, CSV
│   ├── retrieval/            # Hybrid retriever, RRF, decay, reranker
│   └── security/             # PII sanitization regex middleware
├── tests/                    # Pytest unit & integration tests
├── vaultiq_app/              # Reflex frontend & application state
├── requirements.txt          # Python dependencies
└── README.md                 # Project documentation
```

---

## 🚀 Getting Started

### 📋 Prerequisites
- **Python 3.10 – 3.14**
- A free **Groq API Key** (from [console.groq.com](https://console.groq.com))

### 🔧 Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/adityapichikala/VaultIQ.git
   cd VaultIQ
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On Mac/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   Create a `.env` file in the project root:
   ```text
   GROQ_API_KEY=gsk_your_api_key_here
   ```

5. **Build the hybrid indexes:**
   Parse raw documents and populate Qdrant & BM25 indexes:
   ```bash
   python -m src.retrieval.build_index
   ```

---

## 🏃 Running the Platform

To run the full stack, you need to spin up the FastAPI backend and the Reflex web application.

### 1. Launch FastAPI Backend
```bash
python -m uvicorn src.api.main:app --port 8000
```
*API Swagger Documentation is available at: [http://localhost:8000/docs](http://localhost:8000/docs)*

### 2. Launch Reflex Web UI App
```bash
python -m reflex run
```
*Open **[http://localhost:3000](http://localhost:3000)** in your browser.*

---

## 🧪 Testing

Run the automated test suite covering parsing, security redaction, reranking, and evaluation metrics:
```bash
python -m pytest tests/ -v
```

---

## 📜 License
This project is licensed under the MIT License.
