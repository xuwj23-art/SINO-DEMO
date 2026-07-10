"""Debug smoke-test endpoints for Day 1."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.schemas import DebugEmbeddingResponse, DebugLlmResponse
from app.services import embeddings, llm

router = APIRouter(prefix="/api/v1/debug", tags=["debug"])


@router.get("/llm")
def debug_llm() -> DebugLlmResponse:
    """Call the configured generation model with a tiny prompt."""

    try:
        message = llm.generate(
            system="You are a concise API smoke-test assistant.",
            messages=[
                {
                    "role": "user",
                    "content": "Return one short Chinese greeting for a knowledge-base demo.",
                }
            ],
            max_tokens=64,
        )
    except llm.LlmConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except llm.LlmServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Generation model smoke test failed.",
        ) from exc

    return DebugLlmResponse(model=settings.gen_model, message=message)


@router.get("/embed")
def debug_embed() -> DebugEmbeddingResponse:
    """Load the local embedding model and return the vector dimension."""

    try:
        vectors = embeddings.embed(["知识库演示 embedding smoke test"])
    except embeddings.EmbeddingServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return DebugEmbeddingResponse(
        model=settings.embed_model,
        dim=int(vectors.shape[1]),
        count=int(vectors.shape[0]),
    )

