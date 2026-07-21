"""
Query routes for VaultIQ FastAPI.

POST /api/v1/query        → Synchronous RAG query
POST /api/v1/query/stream → Server-Sent Events streaming RAG query
"""

import json
import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from loguru import logger

from src.retrieval import HybridRetriever
from src.retrieval.rag_chain import RAGChain
from ..dependencies import get_retriever, get_rag_chain
from ..schemas import QueryRequest, QueryResponse

router = APIRouter()


def _resolve_roles_from_header(
    x_user_roles: str | None,
    request_roles: list[str],
) -> list[str]:
    """
    Resolve ACL roles from:
    1. X-User-Roles HTTP header (set by Next.js after JWT validation) — TRUSTED
    2. Request body user_roles — used only in dev/testing

    In production, the Next.js middleware validates the JWT and sets
    X-User-Roles. The request body field is ignored when the header is present.
    """
    if x_user_roles:
        roles = [r.strip() for r in x_user_roles.split(",") if r.strip()]
        logger.debug(f"ACL roles from JWT header: {roles}")
        return roles

    # Fall back to request body (development only)
    logger.debug(f"ACL roles from request body (dev mode): {request_roles}")
    return request_roles


@router.post("/query", response_model=QueryResponse, summary="Synchronous RAG Query")
async def query_sync(
    body: QueryRequest,
    retriever: HybridRetriever = Depends(get_retriever),
    rag_chain: RAGChain | None = Depends(get_rag_chain),
    x_user_roles: str | None = Header(default=None),
):
    """
    Execute a full hybrid RAG retrieval and LLM generation cycle.

    **ACL enforcement:** Roles are resolved from the `X-User-Roles` header
    (injected by the Next.js middleware after JWT validation) or the request
    body `user_roles` field in development mode.

    Returns a complete answer with inline citations and token usage statistics.
    """
    user_roles = _resolve_roles_from_header(x_user_roles, body.user_roles)

    # Hybrid retrieval (dense Qdrant + sparse BM25 + RRF + ACL filter)
    try:
        results = retriever.retrieve(
            query=body.query,
            user_roles=user_roles,
            top_k=body.top_k,
            apply_temporal_decay=body.apply_temporal_decay,
            decay_half_life_days=body.decay_half_life_days,
        )
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=f"Retrieval error: {str(e)}")

    # LLM generation
    if not rag_chain:
        raise HTTPException(
            status_code=503,
            detail="LLM generation unavailable. GROQ_API_KEY not configured on the server.",
        )

    try:
        response = rag_chain.generate(
            query=body.query,
            retrieved_chunks=results,
            temperature=body.temperature,
        )
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Generation error: {str(e)}")

    return QueryResponse(
        answer=response["answer"],
        sources=response["sources"],
        model=response["model"],
        usage=response["usage"],
        retrieval_count=len(results),
    )


async def _stream_rag_response(
    query: str,
    results: list[dict],
    rag_chain: RAGChain,
    temperature: float,
) -> AsyncGenerator[str, None]:
    """
    Async generator that yields Server-Sent Events (SSE) for streaming
    LLM token output to the client.

    SSE Event format:
        data: {"token": "...", "done": false}
        data: {"sources": [...], "usage": {...}, "done": true}
    """
    try:
        # Format context (same as synchronous path)
        context = rag_chain._format_context(results)
        from src.retrieval.rag_chain import SYSTEM_PROMPT, QUERY_TEMPLATE
        user_message = QUERY_TEMPLATE.format(context=context, question=query)

        # Use Groq streaming API
        stream = rag_chain.client.chat.completions.create(
            model=rag_chain.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
            max_tokens=1024,
            stream=True,  # Enable streaming
        )

        total_tokens = 0
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                token_data = json.dumps({"token": delta.content, "done": False})
                yield f"data: {token_data}\n\n"
                await asyncio.sleep(0)  # Yield control to event loop

        # Final event with sources and debug pipeline breakdown
        sources = rag_chain._extract_sources(results)
        chunks_debug = [
            {
                "chunk_id": r.get("chunk_id", ""),
                "source_file": r.get("source_file", ""),
                "title": r.get("title", ""),
                "source_type": r.get("source_type", ""),
                "rrf_score": round(r.get("rrf_score", 0.0), 5),
                "decay_multiplier": round(r.get("decay_multiplier", 1.0), 3),
                "effective_date": r.get("effective_date", "2026-07-21"),
                "acl_roles": r.get("acl_roles", []),
            }
            for r in results
        ]
        final_data = json.dumps({
            "sources": sources,
            "chunks_debug": chunks_debug,
            "done": True,
        })
        yield f"data: {final_data}\n\n"

    except Exception as e:
        error_data = json.dumps({"error": str(e), "done": True})
        yield f"data: {error_data}\n\n"


@router.post("/query/stream", summary="Streaming RAG Query (SSE)")
async def query_stream(
    body: QueryRequest,
    retriever: HybridRetriever = Depends(get_retriever),
    rag_chain: RAGChain | None = Depends(get_rag_chain),
    x_user_roles: str | None = Header(default=None),
):
    """
    Execute a hybrid RAG retrieval and stream the LLM token output back
    to the client using Server-Sent Events (SSE).

    The Next.js frontend consumes this endpoint to render a real-time,
    token-by-token streaming chat experience.

    **SSE Events:**
    - `data: {"token": "...", "done": false}` — each generated token
    - `data: {"sources": [...], "done": true}` — final event with citations
    """
    user_roles = _resolve_roles_from_header(x_user_roles, body.user_roles)

    if not rag_chain:
        raise HTTPException(
            status_code=503,
            detail="LLM generation unavailable. GROQ_API_KEY not configured.",
        )

    # Retrieval (synchronous — must complete before streaming begins)
    try:
        results = retriever.retrieve(
            query=body.query,
            user_roles=user_roles,
            top_k=body.top_k,
            apply_temporal_decay=body.apply_temporal_decay,
            decay_half_life_days=body.decay_half_life_days,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval error: {str(e)}")

    return StreamingResponse(
        _stream_rag_response(body.query, results, rag_chain, body.temperature),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable nginx buffering for SSE
        },
    )
