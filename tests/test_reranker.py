"""
Unit tests for Cross-Encoder Reranker module.
"""

import pytest
from src.retrieval.reranker import CrossEncoderReranker


def test_cross_encoder_reranker_basic():
    reranker = CrossEncoderReranker()
    query = "What is our remote work policy?"
    candidates = [
        {"chunk_id": "c1", "content": "Our office hours are 9am to 5pm in New York.", "rrf_score": 0.05},
        {"chunk_id": "c2", "content": "Remote work policy allows employees up to 3 days remote work per week.", "rrf_score": 0.03},
        {"chunk_id": "c3", "content": "Engineering team structure includes frontend and backend teams.", "rrf_score": 0.04},
    ]

    reranked = reranker.rerank(query, candidates, top_k=2)
    assert len(reranked) <= 2
    assert "cross_encoder_score" in reranked[0]
    assert "final_combined_score" in reranked[0]
    # The remote work candidate (c2) should be ranked first due to query relevance match
    assert reranked[0]["chunk_id"] == "c2"


def test_cross_encoder_empty_candidates():
    reranker = CrossEncoderReranker()
    reranked = reranker.rerank("test query", [], top_k=5)
    assert reranked == []
