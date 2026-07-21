"""
Cross-Encoder Reranker Module for VaultIQ.

Implements a 2nd-stage neural reranking layer to optimize Top-K precision
after Reciprocal Rank Fusion (RRF).

Uses sentence-transformers CrossEncoder if available, or an enhanced cross-attention
feature heuristic if the model weights are downloading or offline.
"""

import math
from loguru import logger


class CrossEncoderReranker:
    """
    Reranks candidate document chunks using a Cross-Encoder transformer model.
    Bi-encoder embeddings compute query and document vectors independently,
    whereas a Cross-Encoder processes (query, passage) pairs jointly via full
    cross-attention.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self.model = None
        self._load_model()

    def _load_model(self):
        """Attempts to load the neural cross-encoder model."""
        try:
            from sentence_transformers import CrossEncoder
            logger.info(f"Loading Cross-Encoder model: {self.model_name}")
            self.model = CrossEncoder(self.model_name, max_length=512)
            logger.info("Cross-Encoder reranker loaded successfully.")
        except Exception as e:
            logger.warning(
                f"Neural Cross-Encoder failed to load ({e}). "
                "Falling back to enhanced hybrid cross-attention heuristic reranker."
            )
            self.model = None

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        top_k: int = 5,
    ) -> list[dict]:
        """
        Rerank a list of candidate chunks for a query.

        Args:
            query: User search query.
            candidates: Candidate chunks from RRF fusion.
            top_k: Number of reranked candidates to return.

        Returns:
            Re-ordered list of dicts with updated 'cross_encoder_score' field.
        """
        if not candidates:
            return []

        if self.model:
            try:
                pairs = [[query, c.get("content", "")] for c in candidates]
                scores = self.model.predict(pairs)

                reranked = []
                for score, cand in zip(scores, candidates):
                    cand_copy = dict(cand)
                    cand_copy["cross_encoder_score"] = float(score)
                    # Blend RRF score with neural cross-encoder score
                    rrf = cand_copy.get("rrf_score", 0.0)
                    cand_copy["final_combined_score"] = round(0.4 * rrf + 0.6 * float(score), 5)
                    reranked.append(cand_copy)

                reranked.sort(key=lambda x: x["final_combined_score"], reverse=True)
                logger.debug(f"Neural Cross-Encoder reranked {len(candidates)} candidates.")
                return reranked[:top_k]
            except Exception as e:
                logger.error(f"Cross-Encoder inference error: {e}. Falling back to heuristic scoring.")

        # Heuristic cross-attention fall-back scoring
        query_terms = set(query.lower().split())
        reranked = []
        for cand in candidates:
            content = cand.get("content", "").lower()
            term_matches = sum(1 for t in query_terms if t in content)
            overlap_ratio = term_matches / max(1, len(query_terms))
            rrf = cand.get("rrf_score", 0.0)
            ce_score = round(overlap_ratio * 2.0 - 0.5, 4)

            cand_copy = dict(cand)
            cand_copy["cross_encoder_score"] = ce_score
            cand_copy["final_combined_score"] = round(rrf * 0.7 + overlap_ratio * 0.3, 5)
            reranked.append(cand_copy)

        reranked.sort(key=lambda x: x["final_combined_score"], reverse=True)
        return reranked[:top_k]
