"""
Hybrid retrieval module for VaultIQ.
Combines dense (Qdrant) + sparse (BM25) search with RRF fusion and re-ranking.
"""

from loguru import logger


def reciprocal_rank_fusion(
    dense_results: list[dict],
    sparse_results: list[dict],
    k: int = 60,
    top_n: int = 10,
) -> list[dict]:
    """Merge dense and sparse results using Reciprocal Rank Fusion (RRF).

    RRF score = sum(1 / (k + rank)) across all result lists.
    This is robust and doesn't require score normalization.

    Args:
        dense_results: Results from dense (Qdrant) search.
        sparse_results: Results from sparse (BM25) search.
        k: RRF constant (default 60 — standard value from the paper).
        top_n: Number of merged results to return.

    Returns:
        Merged and re-ranked results sorted by RRF score.
    """
    rrf_scores = {}  # chunk_id -> (rrf_score, result_dict)

    for rank, result in enumerate(dense_results):
        cid = result["chunk_id"]
        score = 1.0 / (k + rank + 1)
        if cid in rrf_scores:
            rrf_scores[cid] = (rrf_scores[cid][0] + score, result)
        else:
            rrf_scores[cid] = (score, result)

    for rank, result in enumerate(sparse_results):
        cid = result["chunk_id"]
        score = 1.0 / (k + rank + 1)
        if cid in rrf_scores:
            rrf_scores[cid] = (rrf_scores[cid][0] + score, result)
        else:
            rrf_scores[cid] = (score, result)

    # Sort by RRF score descending
    sorted_results = sorted(rrf_scores.values(), key=lambda x: x[0], reverse=True)

    # Attach the RRF score to the result dict
    merged = []
    for rrf_score, result in sorted_results[:top_n]:
        result["rrf_score"] = rrf_score
        merged.append(result)

    logger.debug(
        f"RRF fusion: {len(dense_results)} dense + {len(sparse_results)} sparse → {len(merged)} merged"
    )
    return merged


def acl_filter(results: list[dict], user_roles: list[str]) -> list[dict]:
    """Filter results based on user's ACL roles.

    A result passes if ANY of the user's roles match ANY of the
    document's acl_roles, OR if the document has 'all-employees'.

    Args:
        results: List of search results.
        user_roles: List of roles the user has.

    Returns:
        Filtered results the user is authorized to see.
    """
    filtered = []
    roles_set = set(user_roles) | {"all-employees"}

    for result in results:
        doc_roles = set(result.get("acl_roles", ["all-employees"]))
        if doc_roles & roles_set:  # Set intersection — any overlap passes
            filtered.append(result)

    logger.debug(
        f"ACL filter: {len(results)} → {len(filtered)} (roles: {user_roles})"
    )
    return filtered


class HybridRetriever:
    """Orchestrates hybrid retrieval: dense + sparse + fusion + ACL.

    Pipeline:
    1. Dense search via Qdrant (top-20)
    2. Sparse search via BM25 (top-20)
    3. RRF fusion → top-10
    4. ACL filtering → authorized results only
    """

    def __init__(self, embedding_engine, qdrant_index, bm25_index):
        """
        Args:
            embedding_engine: EmbeddingEngine instance for query encoding.
            qdrant_index: QdrantIndex instance for dense search.
            bm25_index: BM25Index instance for sparse search.
        """
        self.embedding_engine = embedding_engine
        self.qdrant_index = qdrant_index
        self.bm25_index = bm25_index

    def retrieve(
        self,
        query: str,
        user_roles: list[str] | None = None,
        top_k: int = 5,
        dense_top_k: int = 20,
        sparse_top_k: int = 20,
    ) -> list[dict]:
        """Run the full hybrid retrieval pipeline.

        Args:
            query: User's search query.
            user_roles: User's ACL roles for filtering.
            top_k: Final number of results to return.
            dense_top_k: Number of results from dense search.
            sparse_top_k: Number of results from sparse search.

        Returns:
            List of top-k relevant, ACL-filtered results.
        """
        if user_roles is None:
            user_roles = ["all-employees"]

        logger.info(f"Retrieving for: '{query}' (roles: {user_roles})")

        # 1. Dense search (Qdrant)
        query_vector = self.embedding_engine.encode_query(query)
        dense_results = self.qdrant_index.search(
            query_vector=query_vector,
            top_k=dense_top_k,
        )
        logger.debug(f"Dense search: {len(dense_results)} results")

        # 2. Sparse search (BM25)
        sparse_results = self.bm25_index.search(
            query=query,
            top_k=sparse_top_k,
        )
        logger.debug(f"Sparse search: {len(sparse_results)} results")

        # 3. RRF fusion
        fused = reciprocal_rank_fusion(
            dense_results,
            sparse_results,
            top_n=top_k * 3,  # Get extra for ACL filtering
        )

        # 4. ACL filter
        filtered = acl_filter(fused, user_roles)

        # Return top-k
        return filtered[:top_k]
