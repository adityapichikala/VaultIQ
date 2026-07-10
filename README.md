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

## License
MIT License
