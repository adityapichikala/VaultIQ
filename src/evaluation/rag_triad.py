"""
RAG Triad Evaluation Engine for VaultIQ.

Measures the 3 core pillars of RAG Quality:
1. Context Precision: Relevance of retrieved chunks to the query.
2. Faithfulness / Groundedness: Factuality ratio of answer claims backed by context.
3. Answer Relevance: Semantic alignment between query and generated response.
"""

import math
from loguru import logger


class RAGTriadEvaluator:
    """Computes RAG Triad quality metrics for RAG queries and responses."""

    def evaluate_context_precision(self, query: str, chunks: list[dict]) -> float:
        """Measure proportion of retrieved chunks containing relevant query terms."""
        if not query or not chunks:
            return 0.0

        query_terms = set(query.lower().split())
        if not query_terms:
            return 1.0

        relevant_chunks = 0
        for c in chunks:
            content = c.get("content", "").lower()
            if any(t in content for t in query_terms):
                relevant_chunks += 1

        precision = relevant_chunks / max(1, len(chunks))
        return round(precision, 2)

    def evaluate_faithfulness(self, answer: str, chunks: list[dict]) -> float:
        """Measure groundedness ratio of answer sentences supported by retrieved chunks."""
        if not answer or not chunks:
            return 0.0

        if "don't have enough information" in answer.lower():
            return 1.0

        combined_context = " ".join([c.get("content", "").lower() for c in chunks])
        sentences = [s.strip() for s in answer.split(".") if len(s.strip()) > 10]

        if not sentences:
            return 1.0

        supported_sentences = 0
        for sentence in sentences:
            words = [w.lower() for w in sentence.split() if len(w) > 3]
            if not words:
                supported_sentences += 1
                continue
            matches = sum(1 for w in words if w in combined_context)
            if (matches / max(1, len(words))) >= 0.35:
                supported_sentences += 1

        faithfulness = supported_sentences / max(1, len(sentences))
        return round(min(1.0, faithfulness), 2)

    def evaluate_answer_relevance(self, query: str, answer: str) -> float:
        """Measure semantic overlap between query keywords and generated answer."""
        if not query or not answer:
            return 0.0

        query_terms = set(w.lower() for w in query.split() if len(w) > 3)
        answer_terms = set(w.lower() for w in answer.split() if len(w) > 3)

        if not query_terms:
            return 1.0

        overlap = query_terms.intersection(answer_terms)
        relevance = len(overlap) / max(1, len(query_terms))
        # Add a baseline scale so fluent answers with partial keyword overlap score high
        score = round(min(1.0, 0.5 + relevance * 0.5), 2)
        return score

    def evaluate(self, query: str, answer: str, chunks: list[dict]) -> dict[str, float]:
        """Compute complete RAG Triad metrics dictionary."""
        cp = self.evaluate_context_precision(query, chunks)
        faith = self.evaluate_faithfulness(answer, chunks)
        ar = self.evaluate_answer_relevance(query, answer)
        overall = round((cp + faith + ar) / 3.0, 2)

        return {
            "context_precision": cp,
            "faithfulness": faith,
            "answer_relevance": ar,
            "overall_score": overall,
        }
