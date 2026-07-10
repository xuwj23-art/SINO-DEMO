"""Shared Pydantic schemas for the demo API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str
    version: str


class DebugLlmResponse(BaseModel):
    model: str
    message: str


class DebugEmbeddingResponse(BaseModel):
    model: str
    dim: int = Field(ge=1)
    count: int = Field(ge=1)


# --- Demo (throwaway) schemas: see docs/demo/DEMO-NOTES.zh-CN.md ---


class DemoAskRequest(BaseModel):
    doc_text: str = ""
    question: str


class DemoCitation(BaseModel):
    page: int
    quote: str


class DemoAskResponse(BaseModel):
    answer: str
    citations: list[DemoCitation] = Field(default_factory=list)
    mode: str = "answered"


class DemoCustomerAskRequest(BaseModel):
    doc_text: str = ""
    question: str = Field(min_length=1, max_length=800)


class DemoCustomerAskResponse(BaseModel):
    answer: str
    citations: list[DemoCitation] = Field(default_factory=list)
    mode: str = "handoff"
    handoff_required: bool = False
    handoff_label: str = "转人工客服"


class DemoAnalyzeRequest(BaseModel):
    doc_text: str = ""
    push_title: str = ""
    push_body: str = ""


class DemoSuggestion(BaseModel):
    point: str
    rationale: str = ""
    cited_pages: list[int] = Field(default_factory=list)
    quote: str = ""


class DemoAnalyzeResponse(BaseModel):
    summary: str = ""
    relevance: str = ""
    suggestions: list[DemoSuggestion] = Field(default_factory=list)


class DemoRegulatoryUpdate(BaseModel):
    id: str
    title: str = ""
    published_at: str = ""
    body: str = ""


class DemoUpdatesResponse(BaseModel):
    updates: list[DemoRegulatoryUpdate] = Field(default_factory=list)
    source_ok: bool = True
    error: str | None = None


# --- Demo compliance intake (throwaway demo; see docs/demo/DEMO-NOTES.zh-CN.md) ---


class DemoIntakeRequest(BaseModel):
    doc_text: str = ""
    client: dict


class DemoChecklistItem(BaseModel):
    key: str
    title: str
    status: str  # "pass" | "fail" | "review"
    detail: str = ""
    cited_page: int | None = None
    quote: str = ""


class DemoIntakeResponse(BaseModel):
    checklist: list[DemoChecklistItem] = Field(default_factory=list)
    outcome: str  # "passed" | "failed" | "needs_review"
    issues: list[DemoChecklistItem] = Field(default_factory=list)
    summary: str = ""


# --- Demo transaction monitoring (throwaway demo; extends the AML lifecycle) ---


class DemoTransaction(BaseModel):
    id: str
    time: str
    client_id: str
    client_name: str
    type: str  # buy | sell | deposit | withdraw | transfer
    amount: float
    currency: str = "HKD"
    counterparty: str = ""  # 第三方账户名（第三方入金时填）
    suspect_flags: list[str] = Field(default_factory=list)


class DemoTxnAnalyzeRequest(BaseModel):
    doc_text: str = ""
    client: dict
    transaction: dict


class DemoTxnAnalyzeResponse(BaseModel):
    risk_level: str  # high | medium | low
    signals: list[str] = Field(default_factory=list)
    client_context: str = ""
    actions: list[str] = Field(default_factory=list)
    cited_page: int | None = None
    quote: str = ""
    summary: str = ""


# --- Demo regulatory impact on existing clients (throwaway demo) ---


class DemoImpactRequest(BaseModel):
    doc_text: str = ""
    push_title: str = ""
    push_body: str = ""
    clients: list[dict] = Field(default_factory=list)


class DemoClientImpact(BaseModel):
    client_id: str
    client_name: str
    impact_level: str  # high | medium | low
    impact_points: list[str] = Field(default_factory=list)
    recommended_action: str = ""
    cited_page: int | None = None
    quote: str = ""


class DemoImpactResponse(BaseModel):
    impacts: list[DemoClientImpact] = Field(default_factory=list)
    summary: str = ""


# --- Demo email generation (intake / transaction notifications) ---


class DemoEmailRequest(BaseModel):
    scene: str  # "intake" | "transaction"
    client_name: str = ""
    client_id: str = ""
    context: dict = {}  # intake: {outcome, issues} / transaction: {risk_level, signals, actions}


class DemoEmailResponse(BaseModel):
    subject: str
    body: str  # 繁體中文郵件正文
    scene: str

