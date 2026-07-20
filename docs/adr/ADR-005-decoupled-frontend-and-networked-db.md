# ADR-005: Decoupled Frontend and Networked Database Architecture

**Status:** Proposed  
**Author:** Pichikala Aditya  
**Date:** 2026-07-20  
**Replaces:** Parts of ADR-001 (monolithic Streamlit + local file storage)

---

## 1. Context

The current VaultIQ prototype operates as a **tightly coupled monolith**:

| Layer | Current Implementation | Problem |
|---|---|---|
| Frontend | Streamlit (`src/app/streamlit_app.py`) | Not independently deployable; shares Python process with backend; no real auth |
| Vector DB | `QdrantClient(path="./qdrant_storage")` | File-locked; cannot be accessed by multiple processes/workers simultaneously |
| Sparse Index | `bm25_index.pkl` — `pickle` file on disk | Not queryable by remote workers; no concurrent read safety |
| Authentication | Simulated — a dropdown selector in the UI | Zero security; ACL roles trivially spoofable by the user |
| API Surface | None — UI calls Python functions directly | Not accessible by mobile, CLI, or any non-Streamlit client |

To evolve VaultIQ from a demo into a production system (multiple concurrent users, CI/CD, API clients), these layers must be **decoupled**, independently scalable, and network-addressable.

---

## 2. Decision

We adopt a **three-tier service architecture**:

```
┌─────────────────────────────────────────────────────────┐
│              TIER 1: NEXT.JS FRONTEND (Client)          │
│  React + Tailwind + shadcn/ui                           │
│  JWT Auth (NextAuth.js + OIDC provider)                 │
│  SSE streaming consumer                                 │
└───────────────────┬─────────────────────────────────────┘
                    │ HTTPS + REST + SSE
┌───────────────────▼─────────────────────────────────────┐
│           TIER 2: FASTAPI BACKEND (API Server)          │
│  POST /api/v1/query       → sync RAG query              │
│  POST /api/v1/query/stream → SSE streaming tokens       │
│  POST /api/v1/ingest      → async ingestion trigger     │
│  JWT validation middleware (ACL roles from token claims)│
└───────────┬─────────────────────┬───────────────────────┘
            │                     │
┌───────────▼───────┐   ┌─────────▼───────────────────────┐
│  TIER 3A: QDRANT  │   │  TIER 3B: PostgreSQL             │
│  (Managed Cloud)  │   │  Chat logs, session state,       │
│  Dense+Sparse     │   │  ingestion job queue             │
│  Vectors          │   └─────────────────────────────────┘
└───────────────────┘
```

---

## 3. Frontend: Streamlit → Next.js

### 3.1 Why Replace Streamlit?

Streamlit is a rapid prototyping tool optimized for data scientists. Its limitations at production scale:

- **Single-threaded execution model:** All users share one Python event loop
- **No composable component architecture:** Cannot build complex auth flows, routing, or layouts
- **Server-side session state only:** Chat history lives in Python memory; lost on restart
- **No JWT/OAuth support natively:** Cannot validate OIDC tokens or parse JWT claims

### 3.2 Next.js Architecture

```
frontend/
├── app/
│   ├── layout.tsx           # Root layout with NextAuth SessionProvider
│   ├── page.tsx             # Main chat page
│   ├── api/
│   │   └── auth/[...nextauth]/route.ts   # NextAuth OIDC handler
│   └── chat/
│       └── page.tsx         # Chat interface
├── components/
│   ├── ChatWindow.tsx       # SSE-consuming chat component
│   ├── RoleDisplay.tsx      # Shows JWT-derived roles
│   └── SourceCard.tsx       # Citation display
├── lib/
│   └── api.ts               # Typed API client for FastAPI backend
└── middleware.ts            # Route protection — redirect unauthenticated users
```

### 3.3 SSE Streaming

Instead of waiting for the full LLM response, the client opens a persistent HTTP connection to `POST /api/v1/query/stream`. The FastAPI backend streams tokens as SSE events:

```
data: {"token": "BigCorp", "done": false}
data: {"token": "'s remote", "done": false}
data: {"token": " work policy", "done": false}
data: {"sources": [...], "done": true}
```

The React component appends each token to the display in real-time, creating a ChatGPT-like streaming effect.

---

## 4. Authentication: Simulated Dropdown → OIDC + JWT

### 4.1 Current Problem

The existing Streamlit UI uses a `st.selectbox()` to select ACL roles. This is a **security theater** — any user can select "leadership" and read confidential executive documents. In production, this is a critical vulnerability.

### 4.2 NextAuth + JWT Claims Architecture

```
User → Google/Auth0/Okta OIDC Provider → ID Token (JWT)
JWT Payload contains:
{
  "sub": "user-123",
  "email": "aditya@bigcorp.com",
  "groups": ["engineering", "all-employees"]  ← ACL roles
}
```

The Next.js frontend extracts `groups` from the JWT and passes them as an HTTP header to the FastAPI backend:

```
POST /api/v1/query
Authorization: Bearer <JWT>
X-User-Roles: engineering,all-employees
```

The FastAPI middleware **validates the JWT signature** against the OIDC provider's public key before trusting the role claims. ACL roles can no longer be spoofed by the client.

---

## 5. Vector Database: Local File → Networked Qdrant

### 5.1 Current Problem

```python
# Current: file-locked, single-process only
self.client = QdrantClient(path="./qdrant_storage")
```

A file-based Qdrant store uses SQLite under the hood and applies process-level file locks. Only **one Python process** can write to it at a time. In a multi-worker FastAPI deployment (e.g., `uvicorn --workers 4`), this causes `LockError` exceptions.

### 5.2 Migration: Environment-Driven Client

```python
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

if QDRANT_URL:
    # Production: connect to managed Qdrant Cloud cluster
    self.client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
else:
    # Development/CI: fall back to local file mode
    self.client = QdrantClient(path=path)
```

The `.env` file controls the deployment target:

```bash
# .env.local (development)
QDRANT_URL=          # empty → use local file

# .env.production
QDRANT_URL=https://xxxxxx.qdrant.io
QDRANT_API_KEY=your-qdrant-cloud-key
```

---

## 6. Sparse Index: BM25 pkl → Qdrant Native Sparse Vectors

### 6.1 Current Problem

The `bm25_index.pkl` is a Python pickle file that must be entirely loaded into the API server's RAM at startup. At 255 documents, this is ~5MB. At 1M enterprise documents, this becomes **~20GB** — exceeding the memory of a typical API server.

### 6.2 Migration Path

**Option A (Recommended for Phase 2):** Use Qdrant's native sparse vector support. Qdrant supports SPLADE or BM25-encoded sparse vectors stored alongside dense vectors in the same collection.

```python
client.create_collection(
    collection_name="vaultiq_docs",
    vectors_config={
        "dense": VectorParams(size=384, distance=Distance.COSINE),
    },
    sparse_vectors_config={
        "sparse": SparseVectorParams(),
    }
)
```

This eliminates the BM25 pkl file entirely — both dense and sparse indices live in the managed Qdrant cluster, queryable over the network by any worker.

**Option B (Intermediate):** Replace pickle with a persisted BM25 model stored in PostgreSQL as a binary blob or in object storage (S3/GCS).

---

## 7. Operational State: PostgreSQL

A PostgreSQL database is introduced to manage all **stateful application concerns**:

```sql
-- Chat session memory
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    role_snapshot TEXT[]  -- ACL roles at session creation time
);

-- Individual chat turns
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES chat_sessions(id),
    role TEXT CHECK (role IN ('user', 'assistant')),
    content TEXT,
    sources JSONB,          -- retrieved citations
    token_usage JSONB,      -- Groq usage stats
    created_at TIMESTAMP DEFAULT NOW()
);

-- Async ingestion job tracking
CREATE TABLE ingestion_jobs (
    id UUID PRIMARY KEY,
    file_name TEXT,
    status TEXT CHECK (status IN ('queued', 'processing', 'done', 'failed')),
    chunks_created INT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

---

## 8. Consequences

### Positive
- **Independent scaling:** Next.js frontend, FastAPI workers, and Qdrant can each be scaled horizontally without affecting the others
- **Real security:** JWT-validated ACL roles cannot be spoofed by the client
- **Concurrent access:** Networked Qdrant serves all API workers simultaneously
- **Observability:** PostgreSQL provides a full audit trail of all queries and ingestion jobs

### Negative / Trade-offs
- **Operational complexity:** Three network services must be deployed, monitored, and maintained vs. one Python process
- **Latency overhead:** Network calls to Qdrant add ~1-5ms vs. local file access
- **Development friction:** Developers need Docker Compose to run the full stack locally

---

## 9. Alternatives Rejected

| Alternative | Reason Rejected |
|---|---|
| Keep Streamlit, add st-auth | Auth is bolt-on; single-process limitation remains |
| Use Redis for BM25 | Redis is not optimized for inverted index structures; Qdrant native sparse is a better fit |
| SQLite instead of PostgreSQL | No concurrent write support; no JSONB; not production-grade |
| GraphQL instead of REST+SSE | Adds schema complexity without meaningful benefit for a chat API |
