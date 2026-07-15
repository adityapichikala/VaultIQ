# ADR-004: System Architecture Blueprint — VaultIQ Internal Mechanics

**Classification:** Technical Reference — For Senior Engineering Review  
**Author:** Pichikala Aditya  
**Status:** Active (reflects current codebase as of Week 3)

---

## 1. Overview

This document is a formal exposition of the **implicit engineering mechanisms** embedded within the VaultIQ codebase. It is intended for senior technical evaluators, ML infrastructure engineers, and system architects who need to understand not just *what* the system does, but *precisely how* the underlying computer science and ML subsystems operate. The document maps from high-level feature names to exact algorithmic implementations.

---

## 2. Document Ingestion & Identity Management

### 2.1 Deterministic Document ID Generation

All document identity is managed via **deterministic MD5 hashing** (`src/ingest/__init__.py`, `BaseParser._generate_doc_id`):

```python
hash_input = f"{file_path}:{chunk_index}"
short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
doc_id = f"{source_type}_{filename}_{short_hash}"
```

**Implicit mechanism:** The ID is a **composite key** embedding the source type, filename stem, and an 8-character hex truncation of the MD5 hash of the full path + chunk index. This provides:
- **Idempotency:** The same file re-ingested always produces the same document IDs, enabling upsert-safe re-indexing.
- **Namespace isolation:** Prepending `source_type` (e.g., `wiki_`, `pdf_`) prevents ID collisions across source namespaces.

**Current limitation:** MD5 is not collision-resistant at scale. For a corpus exceeding ~10M documents, this should be replaced with SHA-256 or a UUID-v5 (namespace-based) scheme.

### 2.2 In-Document ACL Parsing (Structural Metadata Extraction)

ACL roles are parsed at ingestion time via a **line-scanning pattern matcher** (`BaseParser._extract_acl_from_text`):

```python
if line_lower.startswith("**acl:") or line_lower.startswith("acl:"):
    acl_part = line.split(":", 1)[1].strip().strip("*").strip()
    roles = [r.strip() for r in acl_part.split(",")]
```

**Implicit mechanism:** This is a **front-matter emulation** pattern — similar to YAML front-matter in Jekyll or Hugo — but applied inline within the document body. The parser performs a **linear scan** (O(n) where n is line count) and short-circuits on the first ACL match. Comma-separated roles produce a **multi-label ACL list** stored as a JSON array in the Qdrant payload.

**Current limitation:** Only the *first* ACL directive in a document is respected. Documents with section-level ACL granularity (e.g., different ACLs per heading) are **not** supported by the current flat-array ACL model.

---

## 3. Text Chunking Subsystem

### 3.1 Hierarchical Separator-Based Recursive Splitting

The `DocumentChunker` (`src/chunking/__init__.py`) implements a **greedy, hierarchical boundary-priority splitting** algorithm:

```python
separators = ["\n\n", "\n", ". ", " "]
```

The algorithm cascades through the separator hierarchy. For each separator:
1. It splits the text into **parts** by that separator.
2. It attempts a **greedy merge** using `_merge_parts`: sequentially accumulates parts into a `current` buffer until `len(current) > chunk_size`.
3. On overflow, the buffer is committed as a chunk and the **overlap window** is extracted from the *tail* of the previous committed chunk.

**Overlap extraction mechanism:**
```python
overlap_text = chunks[-1][-self.chunk_overlap:]
current = overlap_text + separator + part
```

This is a **suffix-slice overlap** — not a windowed re-tokenization. The overlap is always taken from the raw character tail of the previous chunk, which means the overlap boundary may not align with word or sentence boundaries. This is a known trade-off: it is computationally O(1) vs. O(n) for boundary-aware overlap.

### 3.2 Chunk ID Hashing Scheme

Each chunk receives a deterministic ID:
```python
raw = f"{doc_id}:chunk:{index}"
short_hash = hashlib.md5(raw.encode()).hexdigest()[:8]
chunk_id = f"{doc_id}_c{index}_{short_hash}"
```

The resulting ID encodes:
- Parent document identity (`doc_id`)
- Ordinal position within the parent (`c{index}`)
- A short hash for global uniqueness disambiguation

This enables **chunk-level lineage tracing** — given any chunk ID, you can reconstruct its parent doc ID and position.

### 3.3 Absent Features: Quantization, Tokenization, Semantic Splitting

| Feature | Status | Notes |
|---|---|---|
| **Vector Quantization (PQ/SQ)** | ❌ Not implemented | Qdrant supports Product Quantization; not configured in `VectorParams` |
| **Custom Tokenizer** | ❌ Not used for chunking | The chunker uses raw character count, not token count. This means chunk size in tokens will vary with vocabulary density. |
| **Semantic Chunking** | ❌ Not implemented | No cross-encoder or embedding-based split-point detection |
| **Sliding Window Chunking** | ❌ Not used | The current model is greedy merge, not a sliding window |
| **Token-Aware Splitting** | ❌ Not used | A 500-character chunk averages ~100-120 BERT tokens, well within the 256-token max of `all-MiniLM-L6-v2`, but not guaranteed |

---

## 4. Embedding Subsystem & Vector Space Mechanics

### 4.1 Model Architecture

The embedding model `all-MiniLM-L6-v2` is a **distilled BERT variant** with the following properties:
- **Architecture:** 6-layer, 384-hidden-dim BERT transformer
- **Training:** Sentence-pair classification distilled from a larger cross-encoder teacher
- **Max Sequence Length:** 256 WordPiece tokens (texts longer than this are **silently truncated**)
- **Output Vector:** Mean-pooled CLS + token representations, L2-normalized to unit sphere

### 4.2 L2 Normalization & Cosine Equivalence

All embeddings are generated with `normalize_embeddings=True`:
```python
embeddings = self.model.encode(texts, normalize_embeddings=True)
```

**Critical implicit consequence:** Once all vectors are L2-normalized to lie on the unit hypersphere (‖v‖₂ = 1), **cosine similarity is mathematically equivalent to dot product**:

```
cosine_similarity(u, v) = (u · v) / (‖u‖ · ‖v‖)
                        = (u · v) / (1 · 1)   [since ‖u‖ = ‖v‖ = 1]
                        = u · v
```

The Qdrant collection is configured with `Distance.COSINE`. Since vectors are pre-normalized, the effective distance computation is a **dot product in 384-dimensional Euclidean space**, which is BLAS-accelerated. This is the most efficient metric for normalized sentence embeddings.

### 4.3 Qdrant Index Construction

The Qdrant collection is configured as:
```python
VectorParams(size=384, distance=Distance.COSINE)
```

**Implicit HNSW indexing:** Qdrant automatically builds an **HNSW (Hierarchical Navigable Small World)** graph index on the stored vectors. HNSW is an approximate nearest-neighbor (ANN) algorithm with the following properties:
- **Construction:** O(n log n) expected time
- **Query:** O(log n) expected time — far faster than exact brute-force O(n·d) for large corpora
- **Trade-off:** ANN introduces a **recall-precision trade-off**. At default Qdrant settings, recall@10 is typically 95-99% vs. brute-force, but is not guaranteed to return the single globally-nearest neighbor.

**Payload storage:** Each Qdrant point stores the full document payload (content, ACL, metadata) embedded directly into the point record. This enables **zero-join retrieval** — a single ANN query returns both the vector similarity score and the full document content in one database call.

---

## 5. Sparse Retrieval: BM25 Internals

### 5.1 Tokenization

The BM25 tokenizer (`BM25Index._tokenize`) applies:
1. **Lowercasing** — maps all text to lowercase
2. **Regex punctuation stripping** — `re.sub(r"[^\w\s]", " ", text)`
3. **Whitespace splitting** — `str.split()` on result
4. **Short-token filtering** — tokens of length ≤ 1 are discarded

**Implicit consequence:** This tokenizer does **not** perform:
- Stemming or lemmatization (e.g., "running" ≠ "run")
- Stopword removal (common words like "the", "is" receive low IDF naturally but still consume index space)
- Subword tokenization (compound words are treated atomically)

This is a **whitespace + regex tokenizer**, sufficient for prototype use, but a production system would use a stemming tokenizer (e.g., NLTK Porter Stemmer or a spaCy pipeline).

### 5.2 BM25 Scoring Formula

The `BM25Okapi` implementation scores each document d for query q as:

```
BM25(d, q) = Σ_{t∈q} IDF(t) · [ tf(t,d) · (k1 + 1) ]
                                 / [ tf(t,d) + k1 · (1 - b + b · |d|/avgdl) ]
```

Where:
- `k1 = 1.5` (term frequency saturation; default in `rank_bm25`)
- `b = 0.75` (document length normalization)
- `IDF(t) = log[(N - df(t) + 0.5) / (df(t) + 0.5) + 1]` (Okapi IDF, non-negative)
- `|d|` = document length in tokens; `avgdl` = average document length in corpus

**Okapi IDF variant:** Unlike classic IDF which can produce negative scores for extremely common terms (df > N/2), the Okapi IDF adds a constant `+1` inside the log, ensuring all IDF scores are non-negative. This is why the class is `BM25Okapi`, not `BM25`.

### 5.3 Persistence Mechanism

The BM25 index is serialized via `pickle`:
```python
data = {"chunks": [...], "tokenized_corpus": [...]}
pickle.dump(data, f)
```

On load, `BM25Okapi(tokenized_corpus)` is reconstructed from the saved tokenized corpus. **The IDF statistics are recomputed** at load time (not saved), which means disk space is saved at the cost of ~O(n·V) recomputation at startup, where V is vocabulary size.

---

## 6. Hybrid Fusion: Reciprocal Rank Fusion (RRF)

### 6.1 Mathematical Formulation

RRF is defined in the original Cormack et al. (2009) paper as:

```
RRF_Score(d) = Σ_{r ∈ R} 1 / (k + rank_r(d))
```

Where `R` is the set of ranked lists (dense, sparse), `rank_r(d)` is the 1-indexed rank of document `d` in list `r`, and `k = 60` (the "magic constant" from the original paper, empirically chosen for robustness).

**Implementation:** (`reciprocal_rank_fusion`, `src/retrieval/__init__.py`):
```python
score = 1.0 / (k + rank + 1)   # rank is 0-indexed, so +1 to convert to 1-indexed
```

### 6.2 Why RRF Instead of Score Normalization

The RRF constant `k = 60` was specifically chosen in the paper to make the formula **insensitive to outlier scores at the top of each list**. If a dense retriever assigns a very high similarity score to its top result, that information is discarded — only the *rank* matters.

This is critical for VaultIQ because BM25 scores (unbounded, query-length-dependent) and cosine similarities (bounded [-1, 1]) operate on **completely different numerical scales**. Any convex combination `α·dense + (1-α)·sparse` would require careful MinMax or Z-score normalization that breaks down when query-length distributions shift.

### 6.3 Pre-filter Expansion for ACL Safety

```python
fused = reciprocal_rank_fusion(dense_results, sparse_results, top_n=top_k * 3)
filtered = acl_filter(fused, user_roles)
return filtered[:top_k]
```

The fusion retrieves **3× the requested top_k** before ACL filtering. This is a **pre-filter expansion buffer** to compensate for ACL attrition — if a user only has access to 30% of documents, without the 3× buffer, the system would frequently return fewer than `top_k` results.

---

## 7. ACL Enforcement: Set-Intersection Gate

### 7.1 In-Memory Post-Filter Mechanism

```python
roles_set = set(user_roles) | {"all-employees"}
for result in results:
    doc_roles = set(result.get("acl_roles", ["all-employees"]))
    if doc_roles & roles_set:  # Set intersection — any overlap passes
        filtered.append(result)
```

The ACL check is a **non-empty set intersection test** — the result passes if `doc_roles ∩ roles_set ≠ ∅`. The `"all-employees"` role is **always implicitly injected** into the user's role set, meaning all documents tagged `"all-employees"` are visible to every user.

This is a **post-retrieval, in-memory filter** applied after RRF fusion. It is correct but has a scaling weakness: if the user has no matching roles for many documents, significant query compute is "wasted" on retrieving vectors that are later discarded.

### 7.2 Dual ACL Enforcement (Defense-in-Depth)

VaultIQ employs **two independent ACL enforcement points**:

| Layer | Location | Mechanism |
|---|---|---|
| **Layer 1** (Optional) | `QdrantIndex.search()` | Qdrant `MatchAny` payload filter — database-level, pre-ANN |
| **Layer 2** (Always active) | `acl_filter()` in `HybridRetriever` | In-memory Python set intersection — post-fusion |

The Qdrant payload filter (`MatchAny`) uses Qdrant's internal inverted index on the `acl_roles` array field. When active, it **prunes the HNSW graph traversal** before similarity computation, eliminating unauthorized vectors from the ANN search space entirely. This is the more efficient enforcement path.

Layer 2 exists as a **safety net** for BM25 results (which have no database-level filtering) and as a correctness guarantee regardless of whether Layer 1 was applied.

---

## 8. Generation Layer: LLM Grounding Mechanics

### 8.1 Context Window Construction

```python
f"[Source {i}] {source} ({source_type}) — {title}\n{content}"
```

Retrieved chunks are concatenated into a **numbered source list** with document provenance headers. The separator `\n\n---\n\n` creates a clear visual boundary that helps the LLM parse individual sources as discrete evidence units.

### 8.2 Low-Temperature Factual Anchoring

```python
response = client.chat.completions.create(temperature=0.1, ...)
```

Temperature `0.1` pushes the LLM toward **greedy decoding** (the highest-probability token at each step). This minimizes creative hallucination and keeps the model closely anchored to the provided context. The trade-off is reduced response diversity.

### 8.3 Grounded Generation via System Prompt Constraints

The system prompt enforces **closed-book constraint**:
> *"Only use information from the provided context. If the context doesn't contain the answer, say 'I don't have enough information...'"*

This transforms the LLM from an open-domain generation model into a **constrained, citation-required extraction engine**. The inline citation format `[📄 source_file · section]` is injected into both the system prompt and the user message template to maximize compliance via prompt priming.

---

## 9. Known Engineering Gaps & Production Upgrade Path

| Gap | Severity | Recommended Fix |
|---|---|---|
| **Character-count chunking** (not token-count) | Medium | Use `tiktoken` or HuggingFace tokenizer to chunk by token count, guaranteeing no truncation in `all-MiniLM-L6-v2` (256-token max) |
| **No vector quantization** | Low (at 255 vectors) | Enable `ScalarQuantization` in Qdrant `VectorParams` for production corpora >100K vectors |
| **MD5 chunk IDs** | Low (at 255 vectors) | Replace with SHA-256 or UUID-v5 for collision resistance at scale |
| **BM25 vocabulary not persisted** | Low | Save the `BM25Okapi` object directly (with vocabulary) to avoid recomputation latency at startup |
| **Flat ACL array** | High (for real enterprise) | Implement hierarchical ACL (RBAC with role inheritance) using a dedicated entitlement graph |
| **No staleness handling** | High (for production) | Implement chunk versioning + tombstone markers; trigger re-indexing on document update |
| **BM25 lacks stemming** | Medium | Integrate `nltk.stem.PorterStemmer` into `_tokenize()` |
