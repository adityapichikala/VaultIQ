"""
Pydantic schemas for VaultIQ API request and response models.
"""

from pydantic import BaseModel, Field
from typing import Optional


# ─── Request Models ───────────────────────────────────────────────

class QueryRequest(BaseModel):
    """Request body for POST /api/v1/query and /api/v1/query/stream."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user's question to answer.",
        examples=["What is our remote work policy?"],
    )
    user_roles: list[str] = Field(
        default=["all-employees"],
        description=(
            "ACL roles of the requesting user. In production, these are "
            "extracted from the JWT token claims, not supplied by the client."
        ),
        examples=[["engineering", "all-employees"]],
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of document chunks to retrieve before generation.",
    )
    temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="LLM sampling temperature. Lower = more factual.",
    )
    apply_temporal_decay: bool = Field(
        default=True,
        description="If True, applies exponential decay to boost newer documents.",
    )
    decay_half_life_days: float = Field(
        default=180.0,
        ge=1.0,
        le=3650.0,
        description="Half-life in days for recency temporal decay.",
    )
    enable_reranker: bool = Field(
        default=True,
        description="If True, applies 2nd-stage neural Cross-Encoder reranking.",
    )
    sanitize_pii: bool = Field(
        default=True,
        description="If True, applies PII redaction to prompt input.",
    )


class IngestRequest(BaseModel):
    """Request body for POST /api/v1/ingest."""

    data_dir: Optional[str] = Field(
        default=None,
        description=(
            "Path to the data directory to ingest. "
            "Defaults to ./data/synthetic if not specified."
        ),
    )
    force_rebuild: bool = Field(
        default=False,
        description="If True, deletes and rebuilds the existing index.",
    )
    dataset_name: str = Field(
        default="default",
        description="Identifier name for the dataset collection.",
    )
    version: str = Field(
        default="1.0",
        description="Version string for the ingested dataset.",
    )
    effective_date: Optional[str] = Field(
        default=None,
        description="ISO date string (YYYY-MM-DD) for temporal decay indexing.",
    )


class DatasetInfo(BaseModel):
    """Summary of an active dataset."""
    name: str
    version: str
    document_count: int
    chunk_count: int
    created_at: str


class DatasetListResponse(BaseModel):
    """Response body for GET /api/v1/datasets."""
    datasets: list[DatasetInfo]
    total_datasets: int


# ─── Response Models ──────────────────────────────────────────────

class SourceDoc(BaseModel):
    """A source document citation."""
    file: str
    title: str
    type: str


class RAGTriadMetrics(BaseModel):
    """RAG Triad evaluation metrics."""
    context_precision: float
    faithfulness: float
    answer_relevance: float
    overall_score: float


class QueryResponse(BaseModel):
    """Response body for POST /api/v1/query."""

    answer: str = Field(description="The LLM-generated answer.")
    sources: list[SourceDoc] = Field(description="Cited source documents.")
    model: str = Field(description="The LLM model used for generation.")
    usage: dict = Field(description="Token usage statistics from the LLM API.")
    retrieval_count: int = Field(
        description="Number of document chunks retrieved before ACL filtering."
    )
    triad_metrics: Optional[RAGTriadMetrics] = Field(
        default=None,
        description="Inline RAG Triad quality metrics.",
    )


class HealthResponse(BaseModel):
    """Response body for GET /api/v1/health."""

    status: str
    qdrant_vectors: int
    bm25_documents: int
    llm_available: bool
    qdrant_mode: str  # "local" or "remote"


class IngestResponse(BaseModel):
    """Response body for POST /api/v1/ingest."""

    status: str
    documents_ingested: int
    chunks_created: int
    vectors_indexed: int
