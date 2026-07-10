# ADR-003: Hybrid Retrieval Pipeline

## Context
Enterprise data contains a mix of semantic intent and exact terminology. 
For example, if a user searches for "P0 incident connection pool," they are looking for an exact keyword match. If they search for "how to take sick leave," they are looking for a semantic match (even if the document says "medical absence").
Relying solely on dense vector search (embeddings) often fails on domain-specific acronyms, IDs, or exact names.

## Decision
We implemented a **Hybrid Retrieval Pipeline** utilizing Reciprocal Rank Fusion (RRF).

1. **Dense Retrieval:** We use `Qdrant` with `all-MiniLM-L6-v2` embeddings for semantic search (captures intent).
2. **Sparse Retrieval:** We use `rank-bm25` (TF-IDF based) for exact keyword matching.
3. **Fusion Strategy:** 
   - We query both systems to retrieve the top $K$ results.
   - We merge the lists using Reciprocal Rank Fusion (RRF): `RRF_Score = sum(1 / (60 + rank))`.
   - We return the highest-scoring combined results.
4. **ACL Filtering:** Finally, we filter the fused results against the user's roles before passing them to the LLM.

## Consequences
- **Positive:** Dramatically improves recall. We catch exact product names, error codes, and employee names via BM25, while handling natural language questions via Qdrant.
- **Positive:** RRF does not require calibrating scores. Since BM25 and cosine similarity output different scales, RRF elegantly bypasses the normalization problem by only using rank.
- **Negative:** Query latency is slightly higher since we perform two independent searches, and BM25 requires keeping an inverted index in memory.

## Alternatives considered
- **Convex Combination of Scores:** (e.g., `0.7 * Dense + 0.3 * Sparse`). Rejected because it requires score normalization (MinMax or Z-score) which is notoriously brittle across different query types.
- **Qdrant Native Sparse Vectors (SPLADE):** Rejected due to the added complexity of generating sparse vectors at ingestion time vs. a simple local BM25 index.
