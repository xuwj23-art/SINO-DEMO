"""Demo-only compliance intake: pre-account-opening AML/KYC screening.

Throwaway demo path (see docs/demo/DEMO-NOTES.zh-CN.md), deliberately separate
from the 0006 formal direction. Given the uploaded internal AML policy text and
a synthetic client application, a single model call extracts the account-
opening checks required by the policy and evaluates the client against each,
returning a checklist with policy-page citations.

No embeddings, no vector store, no real trading-system calls. Client data is
fully synthetic (see docs/reference/trader-admin-system-usage-scenarios.zh-CN.md).
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date
from typing import Any

from app.services import llm

logger = logging.getLogger(__name__)

# Bound the policy context the same way demo_rag does, so a pathological upload
# cannot blow past the model window.
MAX_DOC_CHARS = 120_000

# Per-item status values, mirrored in the frontend animation logic.
STATUS_PASS = "pass"
STATUS_FAIL = "fail"
STATUS_REVIEW = "review"
_VALID_STATUS = {STATUS_PASS, STATUS_FAIL, STATUS_REVIEW}


def _truncate_doc(doc_text: str) -> str:
    doc_text = (doc_text or "").strip()
    if len(doc_text) <= MAX_DOC_CHARS:
        return doc_text
    return doc_text[:MAX_DOC_CHARS] + "\n\n[文档过长，已截断以适配演示上下文]"


def _extract_json(raw: str) -> dict[str, Any] | None:
    """Best-effort parse of a JSON object embedded in an LLM reply.

    Models occasionally wrap the JSON in a markdown code fence or prepend
    chatty text; we strip fences first, then fall back to brace-matching.
    """

    if not raw:
        return None
    # Strip a ```json ... ``` (or ``` ... ```) fence if present.
    fenced = re.search(r"```(?:json)?\s*(.*?)```", raw, re.S | re.I)
    candidate = fenced.group(1).strip() if fenced else raw
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(candidate[start : end + 1])
    except json.JSONDecodeError:
        return None
        return None
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None


_INTAKE_SYSTEM = (
    "你是金融機構的 AML/KYC 合規審核助手。用戶會給你兩份材料：\n"
    "1. 《政策》：本公司內部反洗錢政策，每一頁以 `===== Page N =====` 標記頁碼。\n"
    "2. 《客戶申請》：一份合成（虛構）的客戶開戶申請，含個人身份、KYC、財務與申請業務資訊。\n\n"
    "請完成兩步：\n"
    "第一步 —— 從《政策》中識別所有「開立賬戶前須完成」的審核項，"
    "例如：身分核實、住址證明時效、政治人物(PEP)核查、受益所有人識別、"
    "資金來源與財富來源核實、客戶風險評級等。只取政策確實提及的審核項，不要臆造政策沒有的要求。\n"
    "第二步 —— 針對每個審核項，依據《客戶申請》的內容逐項判斷，status 取值：\n"
    "  - pass：客戶資料符合政策要求；\n"
    "  - fail：明確不符合政策要求（例如住址證明超期、為 PEP 但未做強化盡查、資金來源與收入明顯不符等）；\n"
    "  - review：存在疑點或資料不完整，需合規人員人工覆核（例如缺少佐證文件、聲明與財務狀況略有出入）。\n\n"
    "規則：\n"
    "1. 只依據《政策》與《客戶申請》判斷，不得引入外部知識或臆測。\n"
    "2. 【重要】每一個審核項（無論 pass / fail / review）都必須填寫 cited_page 與 quote，"
    "讓工作人員能溯源到《政策》原文。cited_page 填《政策》中該審核項所依據條款的頁碼，"
    "quote 從該頁逐字抄錄 10-40 字原文（用於 PDF 定位高亮）。"
    "例如 pass 項也要引用其「符合」的政策條款原文。\n"
    "3. detail 用簡體中文一句話說明判斷理由（結合客戶資料的具體數值或事實）。\n"
    "4. outcome 取值：任一項 fail 則為 failed；無 fail 但有 review 則為 needs_review；全為 pass 則為 passed。\n"
    "5. summary 用簡體中文一句話總結（例如「發現 2 項不通過、1 項待覆核，未通過開戶初審」）。\n\n"
    "只輸出一個嚴格的 JSON 對象，不要 markdown 代碼塊或額外文字。格式：\n"
    '{"checklist": [{"key": "英文短標識", "title": "審核項中文名", '
    '"status": "pass|fail|review", "detail": "判斷理由", '
    '"cited_page": 頁碼數字, "quote": "政策原文"}], '
    '"outcome": "passed|failed|needs_review", "summary": "一句話總結"}'
)


def _format_client(client: dict[str, Any]) -> str:
    """Render the synthetic client dict as readable text for the model.

    Flattens the account/kyc/application layers so the model sees all fields
    without us having to know the exact key set ahead of time.
    """

    if not isinstance(client, dict):
        return str(client)

    parts: list[str] = []
    for layer in ("account", "kyc", "application"):
        sub = client.get(layer)
        if isinstance(sub, dict) and sub:
            parts.append(f"【{layer}】")
            for k, v in sub.items():
                parts.append(f"  {k}: {v}")
        elif sub is not None:
            parts.append(f"【{layer}】 {sub}")
    # Also surface any top-level scalar fields (defensive).
    extras = {k: v for k, v in client.items() if k not in ("account", "kyc", "application")}
    if extras:
        parts.append("【其他】")
        for k, v in extras.items():
            parts.append(f"  {k}: {v}")
    return "\n".join(parts) if parts else "(無客戶資料)"


def _coerce_item(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    title = str(raw.get("title") or "").strip()
    if not title:
        return None
    status = str(raw.get("status") or "").strip().lower()
    if status not in _VALID_STATUS:
        status = STATUS_REVIEW
    page = raw.get("cited_page")
    if isinstance(page, bool) or page in (None, ""):
        page = None
    else:
        try:
            page = int(page)
        except (TypeError, ValueError):
            page = None
    return {
        "key": str(raw.get("key") or title)[:64],
        "title": title,
        "status": status,
        "detail": str(raw.get("detail") or "").strip(),
        "cited_page": page,
        "quote": str(raw.get("quote") or "").strip(),
    }


def intake(doc_text: str, client: dict[str, Any]) -> dict[str, Any]:
    """Run a single-pass AML/KYC intake screening against the policy."""

    doc = _truncate_doc(doc_text)
    if not doc:
        return {
            "checklist": [],
            "outcome": "failed",
            "issues": [],
            "summary": "尚未提供政策文件，无法进行开户初审。",
        }
    if not isinstance(client, dict) or not client:
        return {
            "checklist": [],
            "outcome": "failed",
            "issues": [],
            "summary": "尚未提供客户申请资料，无法进行开户初审。",
        }

    user_content = (
        f"《政策》：\n{doc}\n\n《客戶申請》：\n{_format_client(client)}\n\n"
        f"（審核基準日：{date.today().isoformat()}。"
        f"判斷住址證明等時效性要求時，以此日為準。）"
    )
    raw = llm.generate(
        system=_INTAKE_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
        max_tokens=3072,
    )

    parsed = _extract_json(raw)
    if not parsed or not isinstance(parsed.get("checklist"), list):
        # Degrade gracefully: surface the raw reply so the demo isn't a dead end.
        logger.warning("intake: failed to parse structured checklist; raw reply was non-JSON")
        return {
            "checklist": [],
            "outcome": "needs_review",
            "issues": [],
            "summary": (raw or "（模型无返回）")[:200],
        }

    checklist: list[dict[str, Any]] = []
    for raw_item in parsed["checklist"]:
        item = _coerce_item(raw_item)
        if item:
            checklist.append(item)

    outcome = str(parsed.get("outcome") or "").strip().lower()
    if outcome not in ("passed", "failed", "needs_review"):
        # Re-derive outcome from statuses if the model got it wrong.
        statuses = {it["status"] for it in checklist}
        outcome = (
            "failed" if STATUS_FAIL in statuses
            else "needs_review" if STATUS_REVIEW in statuses
            else "passed"
        )

    issues = [it for it in checklist if it["status"] in (STATUS_FAIL, STATUS_REVIEW)]
    summary = str(parsed.get("summary") or "").strip()

    return {
        "checklist": checklist,
        "outcome": outcome,
        "issues": issues,
        "summary": summary,
    }
