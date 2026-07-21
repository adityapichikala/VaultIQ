import math
from datetime import datetime
from loguru import logger


def compute_temporal_decay_multiplier(
    effective_date_str: str,
    half_life_days: float = 180.0,
) -> float:
    """Compute exponential decay multiplier based on document age.

    Multiplier = exp(-lambda * delta_days), where lambda = ln(2) / half_life_days.
    A document with age = half_life_days gets a score multiplier of 0.5.
    """
    if not effective_date_str:
        return 1.0

    try:
        eff_date = datetime.strptime(effective_date_str[:10], "%Y-%m-%d")
        now = datetime.now()
        delta_days = max(0.0, (now - eff_date).days)
        decay_lambda = math.log(2) / max(1.0, half_life_days)
        return math.exp(-decay_lambda * delta_days)
    except Exception:
        return 1.0


def reciprocal_rank_fusion(
    dense_results: list[dict],
    sparse_results: list[dict],
    k: int = 60,
    top_n: int = 10,
    apply_temporal_decay: bool = True,
    decay_half_life_days: float = 180.0,
) -> list[dict]:
    """Merge dense and sparse results using Reciprocal Rank Fusion (RRF).

    Optionally applies exponential temporal decay weighting to boost newer documents.

    RRF score = sum(1 / (k + rank)) * decay_multiplier across all result lists.

    Args:
        dense_results: Results from dense (Qdrant) search.
        sparse_results: Results from sparse (BM25) search.
        k: RRF constant (default 60).
        top_n: Number of merged results to return.
        apply_temporal_decay: If True, applies recency weighting.
        decay_half_life_days: Half-life in days for temporal decay.

    Returns:
        Merged and re-ranked results sorted by final score.
    """
    rrf_scores = {}  # chunk_id -> (score, result_dict)

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

    # Calculate final scores with optional temporal decay multiplier
    final_scored = []
    for cid, (base_rrf_score, result) in rrf_scores.items():
        decay_mult = 1.0
        if apply_temporal_decay:
            eff_date = result.get("effective_date", "2026-07-21")
            decay_mult = compute_temporal_decay_multiplier(eff_date, decay_half_life_days)

        final_score = base_rrf_score * decay_mult
        result_copy = dict(result)
        result_copy["rrf_score"] = final_score
        result_copy["decay_multiplier"] = decay_mult
        final_scored.append((final_score, result_copy))

    # Sort by final score descending
    final_scored.sort(key=lambda x: x[0], reverse=True)

    merged = [res for _, res in final_scored[:top_n]]

    logger.debug(
        f"RRF fusion (decay={apply_temporal_decay}): {len(dense_results)} dense + {len(sparse_results)} sparse → {len(merged)} merged"
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
    """Orchestrates hybrid retrieval: dense + sparse + RRF fusion + temporal decay + reranking + ACL.

    Pipeline:
    1. Dense search via Qdrant (top-20)
    2. Sparse search via BM25 (top-20)
    3. RRF fusion with temporal decay
    4. ACL filtering → authorized results only
    5. 2nd-stage Neural Cross-Encoder Reranking (top-k)
    """

    def __init__(self, embedding_engine, qdrant_index, bm25_index, reranker=None):
        """
        Args:
            embedding_engine: EmbeddingEngine instance for query encoding.
            qdrant_index: QdrantIndex instance for dense search.
            bm25_index: BM25Index instance for sparse search.
            reranker: CrossEncoderReranker instance (optional).
        """
        self.embedding_engine = embedding_engine
        self.qdrant_index = qdrant_index
        self.bm25_index = bm25_index
        if reranker is None:
            from .reranker import CrossEncoderReranker
            self.reranker = CrossEncoderReranker()
        else:
            self.reranker = reranker

    def retrieve(
        self,
        query: str,
        user_roles: list[str] | None = None,
        top_k: int = 5,
        dense_top_k: int = 20,
        sparse_top_k: int = 20,
        apply_temporal_decay: bool = True,
        decay_half_life_days: float = 180.0,
        enable_reranker: bool = True,
    ) -> list[dict]:
        """Run the full hybrid retrieval pipeline.

        Args:
            query: User's search query.
            user_roles: User's ACL roles for filtering.
            top_k: Final number of results to return.
            dense_top_k: Number of results from dense search.
            sparse_top_k: Number of results from sparse search.
            apply_temporal_decay: Whether to weight results by recency.
            decay_half_life_days: Half-life parameter in days for recency decay.
            enable_reranker: Whether to run 2nd-stage neural cross-encoder reranking.

        Returns:
            List of top-k relevant, ACL-filtered, reranked results.
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

        # 3. RRF fusion with temporal decay
        fused = reciprocal_rank_fusion(
            dense_results,
            sparse_results,
            top_n=top_k * 3,  # Get extra for ACL filtering & reranking
            apply_temporal_decay=apply_temporal_decay,
            decay_half_life_days=decay_half_life_days,
        )

        # 4. ACL filter
        filtered = acl_filter(fused, user_roles)

        # 5. 2nd-Stage Cross-Encoder Reranking
        if enable_reranker and self.reranker and filtered:
            reranked = self.reranker.rerank(query, filtered, top_k=top_k)
            return reranked

        # Return top-k if reranker disabled
        return filtered[:top_k]
