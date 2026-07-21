"""
Unit tests for RAG Triad Evaluator module.
"""

import pytest
from src.evaluation import RAGTriadEvaluator


def test_rag_triad_evaluator():
    evaluator = RAGTriadEvaluator()
    query = "What is the remote work policy?"
    answer = "Employees are allowed up to 3 days of remote work per week."
    chunks = [
        {"content": "Remote work policy allows up to 3 days remote work per week for eligible staff."},
        {"content": "Office hours are from 9am to 5pm Monday through Friday."},
    ]

    metrics = evaluator.evaluate(query, answer, chunks)

    assert "context_precision" in metrics
    assert "faithfulness" in metrics
    assert "answer_relevance" in metrics
    assert "overall_score" in metrics
    assert metrics["context_precision"] > 0.0
    assert metrics["faithfulness"] > 0.0
    assert metrics["answer_relevance"] > 0.0
