# VaultIQ — Enterprise RAG over Messy Multi-Modal Data

> Segment 5 · Problem E3 · LLM Systems & Applied GenAI  
> Built by: Pichikala Aditya | Target role: LLM Engineer / GenAI Engineer

---

## What is VaultIQ?

VaultIQ is a modular Retrieval-Augmented Generation (RAG) system built to handle unstructured enterprise data. It ingests PDFs, Slack JSON exports, Markdown wikis, and CSVs, applying role-based access control (ACL) to ensure users only see answers generated from documents they have permission to view.

## Live Demo
- **Demo Video:** [Loom Demo Link]
- **Live URL:** [Deployed Streamlit URL]

## Architecture

VaultIQ uses a hybrid search pipeline with Reciprocal Rank Fusion (RRF) to merge semantic intent (dense vectors) with exact keyword matching (sparse vectors), re-ranked and filtered by ACL before passing to a Groq-powered LLM.

![Architecture Diagram](docs/architecture.md)

## Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| **Data Types** | PDF, MD, CSV, JSON | Realistic mix of enterprise messiness |
| **Parsing** | PyMuPDF, custom | Fast, robust, handles edge cases |
| **Chunking** | Custom recursive | Retains parent metadata across splits |
| **Embedding** | all-MiniLM-L6-v2 | 384-dim, extremely fast, runs locally |
| **Dense Store** | Qdrant | Self-hostable, fast cosine search |
| **Sparse Index** | rank-bm25 | Essential for exact acronyms/IDs |
| **Fusion** | RRF | Combines dense/sparse without score normalization |
| **LLM** | Groq (Llama-3-8B) | Low-latency generation, open weights |
| **UI** | Streamlit | Rapid prototyping for data apps |
| **Testing** | pytest | Ensuring robust ingestion and retrieval |
| **CI/CD** | GitHub Actions | Automated tests on every push |

---

## Quickstart (Setup in < 5 mins)

### 1. Prerequisites
- Python 3.10+
- A [Groq API Key](https://console.groq.com) (free)

### 2. Install & Configure
```bash
git clone https://github.com/adityapichikala/VaultIQ.git
cd VaultIQ

# Setup virtual environment
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API Key
echo "GROQ_API_KEY=your_key_here" > .env
```

### 3. Build the Index
This command ingests the synthetic dataset (4 PDFs, 12 MD files, 8 Slack threads, 4 CSVs), chunks them, generates vectors, and builds the Qdrant + BM25 databases locally.
```bash
python -m src.retrieval.build_index
```

### 4. Run the App
Launch the Streamlit Chat UI to interact with the system.
```bash
streamlit run src/app/streamlit_app.py
```

### 5. Run Tests
```bash
python -m pytest tests/ -v
```

---

## Data

The `/data/synthetic/` folder contains 28 synthetic files generating 255 text chunks simulating a real enterprise (BigCorp). It includes HR policies, engineering guides, database schemas, Slack incidents, and budgeting spreadsheets.

## ADRs
- [ADR-001: Problem Statement & Tech Stack](docs/adr/ADR-001-problem-and-tech-stack.md)
- [ADR-002: Chunking Strategy](docs/adr/ADR-002-chunking-strategy.md)
- [ADR-003: Hybrid Retrieval Pipeline](docs/adr/ADR-003-hybrid-retrieval.md)

## Project Timeline & Weekly Progress

This project is built over a **4-week timeline**, with specific deliverables and milestones achieved each week.

### ✅ Week 1: Foundation & Data Layer
- Defined problem statement and selected tech stack.
- Generated synthetic enterprise dataset (PDFs, Markdown, CSVs, Slack JSONs).
- Built initial ingestion parsers to handle multi-modal data.

### ✅ Week 2: Core RAG Pipeline & UI
- Built the document chunking module with recursive splitting.
- Implemented vector embeddings using `all-MiniLM-L6-v2` and indexed into **Qdrant**.
- Built a sparse retrieval index using **BM25**.
- Implemented **Reciprocal Rank Fusion (RRF)** for hybrid search.
- Added **Role-Based Access Control (ACL)** filtering.
- Connected the **Groq Llama-3-8B** LLM for generation with inline citations.
- Built the interactive **Streamlit Chat UI**.

### ✅ Week 3: Hardening & Testing
- Added `pytest` suite for unit and integration testing.
- Set up **GitHub Actions (CI)** for automated testing on every push.
- Audited the pipeline for robust error handling and logging (`loguru`).
- Documented key architectural decisions in ADRs (Chunking, Hybrid Retrieval).

### ⏳ Week 4: Deployment & Polish (Upcoming)
- Deploy the Streamlit app to a public URL.
- Write a deep-dive technical blog post / Thinking Artifact.
- Finalize documentation, Loom walkthroughs, and Milestone 2 submission.

## License
MIT License
