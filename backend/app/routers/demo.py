"""Demo-only endpoints for tomorrow's presentation.

Throwaway path, isolated from the 0006 formal direction. See
docs/demo/DEMO-NOTES.zh-CN.md. Provides single-document full-context Q&A and
regulatory-push linkage against the currently uploaded document.
"""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, HTTPException, status

from app.config import settings
from app.schemas import (
    DemoAnalyzeRequest,
    DemoAnalyzeResponse,
    DemoAskRequest,
    DemoAskResponse,
    DemoCustomerAskRequest,
    DemoCustomerAskResponse,
    DemoEmailRequest,
    DemoEmailResponse,
    DemoImpactRequest,
    DemoImpactResponse,
    DemoIntakeRequest,
    DemoIntakeResponse,
    DemoRegulatoryUpdate,
    DemoTxnAnalyzeRequest,
    DemoTxnAnalyzeResponse,
    DemoUpdatesResponse,
)
from app.services import demo_email, demo_impact, demo_intake, demo_rag, demo_txn_analyze, llm

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])


@router.post("/ask", response_model=DemoAskResponse)
def demo_ask(payload: DemoAskRequest) -> DemoAskResponse:
    """Answer a question grounded in the full uploaded document text."""

    try:
        result = demo_rag.answer(payload.doc_text, payload.question)
    except llm.LlmConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except llm.LlmServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="生成模型调用失败。",
        ) from exc

    return DemoAskResponse(**result)


@router.post("/customer-service/ask", response_model=DemoCustomerAskResponse)
def demo_customer_service_ask(payload: DemoCustomerAskRequest) -> DemoCustomerAskResponse:
    """Customer-facing Q&A that falls back to human service out of scope."""

    try:
        result = demo_rag.customer_answer(payload.doc_text, payload.question)
    except llm.LlmConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except llm.LlmServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="生成模型调用失败。",
        ) from exc

    return DemoCustomerAskResponse(**result)


@router.post("/regulatory/analyze", response_model=DemoAnalyzeResponse)
def demo_analyze(payload: DemoAnalyzeRequest) -> DemoAnalyzeResponse:
    """Summarize a regulatory push and link it to the current document."""

    try:
        result = demo_rag.analyze_update(
            payload.doc_text, payload.push_title, payload.push_body
        )
    except llm.LlmConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except llm.LlmServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="生成模型调用失败。",
        ) from exc

    return DemoAnalyzeResponse(**result)


@router.get("/regulatory/updates", response_model=DemoUpdatesResponse)
def demo_updates() -> DemoUpdatesResponse:
    """Proxy the external regulatory test site's updates list.

    Never 500s: on any fetch/parse failure it returns an empty list with an
    error flag so the frontend polling loop stays healthy.
    """

    base = (settings.regulatory_test_site_url or "").rstrip("/")
    if not base:
        return DemoUpdatesResponse(updates=[], source_ok=False, error="未配置测试站地址")

    url = f"{base}/api/updates"
    try:
        resp = httpx.get(url, timeout=8.0)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # network / json / http errors all handled the same
        logger.warning("Failed to fetch regulatory updates from %s: %s", url, exc)
        return DemoUpdatesResponse(updates=[], source_ok=False, error="测试站不可达")

    # Accept either a bare list or {"updates": [...]}.
    raw_items = data.get("updates") if isinstance(data, dict) else data
    if not isinstance(raw_items, list):
        raw_items = []

    updates: list[DemoRegulatoryUpdate] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        updates.append(
            DemoRegulatoryUpdate(
                id=str(item.get("id", "")),
                title=str(item.get("title", "")),
                published_at=str(item.get("published_at", "")),
                body=str(item.get("body", "")),
            )
        )

    return DemoUpdatesResponse(updates=updates, source_ok=True)


@router.post("/intake", response_model=DemoIntakeResponse)
def demo_intake_endpoint(payload: DemoIntakeRequest) -> DemoIntakeResponse:
    """Pre-account-opening AML/KYC screening against the uploaded policy.

    Single model pass: extracts the policy's account-opening checks and
    evaluates the (synthetic) client against each, returning a cited checklist.
    """

    try:
        result = demo_intake.intake(payload.doc_text, payload.client)
    except llm.LlmConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except llm.LlmServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="生成模型调用失败。",
        ) from exc

    return DemoIntakeResponse(**result)


@router.post("/transaction/analyze", response_model=DemoTxnAnalyzeResponse)
def demo_txn_analyze_endpoint(payload: DemoTxnAnalyzeRequest) -> DemoTxnAnalyzeResponse:
    """Risk analysis for a flagged transaction, tied to the client's KYC profile.

    Single model pass: assesses the (synthetic) flagged transaction against the
    client background and the uploaded policy, returning a cited risk assessment.
    """

    try:
        result = demo_txn_analyze.analyze(payload.doc_text, payload.client, payload.transaction)
    except llm.LlmConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except llm.LlmServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="生成模型调用失败。",
        ) from exc

    return DemoTxnAnalyzeResponse(**result)


@router.post("/regulatory/impact", response_model=DemoImpactResponse)
def demo_impact_endpoint(payload: DemoImpactRequest) -> DemoImpactResponse:
    """Assess a regulatory push's impact across the synthetic client book.

    Single model pass: ties the regulatory change to each existing client's
    KYC profile, returning per-client impact level + points + action + citation.
    """

    try:
        result = demo_impact.analyze_impact(
            payload.doc_text, payload.push_title, payload.push_body, payload.clients
        )
    except llm.LlmConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except llm.LlmServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="生成模型调用失败。",
        ) from exc

    return DemoImpactResponse(**result)


@router.post("/email/generate", response_model=DemoEmailResponse)
def demo_email_endpoint(payload: DemoEmailRequest) -> DemoEmailResponse:
    """Draft a Traditional-Chinese compliance email (intake / transaction)."""

    try:
        result = demo_email.generate_email(
            payload.scene, payload.client_name, payload.client_id, payload.context
        )
    except llm.LlmConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except llm.LlmServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="生成模型调用失败。",
        ) from exc

    return DemoEmailResponse(**result)
