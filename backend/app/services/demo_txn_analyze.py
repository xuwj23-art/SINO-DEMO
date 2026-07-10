"""Demo-only suspicious-transaction risk analysis.

Throwaway demo path (see docs/demo/DEMO-NOTES.zh-CN.md). Given the uploaded AML
policy, a synthetic client's KYC profile, and a flagged transaction, a single
model call produces a risk assessment that ties the transaction signals to the
client's background and the firm's policy — with a policy-page citation.

No embeddings, no vector store, no real trading-system calls. All client and
transaction data is fully synthetic.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.services import llm

logger = logging.getLogger(__name__)

MAX_DOC_CHARS = 120_000

_VALID_RISK = {"high", "medium", "low"}

# Map the frontend's internal suspect_flag codes to plain Chinese so the model
# (and in turn the audience-facing output) never sees raw English identifiers.
_FLAG_CN = {
    "large_frequency": "短时间多笔大额",
    "third_party": "第三方账户转入",
    "income_mismatch": "金额与收入不符",
    "rapid_movement": "快进快出",
}


def _flag_cn(flag: str) -> str:
    return _FLAG_CN.get(str(flag), str(flag))


def _truncate_doc(doc_text: str) -> str:
    doc_text = (doc_text or "").strip()
    if len(doc_text) <= MAX_DOC_CHARS:
        return doc_text
    return doc_text[:MAX_DOC_CHARS] + "\n\n[文档过长，已截断以适配演示上下文]"


def _extract_json(raw: str) -> dict[str, Any] | None:
    """Best-effort parse of a JSON object embedded in an LLM reply."""

    if not raw:
        return None
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


def _format_client(client: dict[str, Any]) -> str:
    """Render the synthetic client dict as readable text for the model."""

    if not isinstance(client, dict):
        return str(client)
    parts: list[str] = []
    for layer in ("account", "kyc"):
        sub = client.get(layer)
        if isinstance(sub, dict) and sub:
            parts.append(f"【{layer}】")
            for k, v in sub.items():
                parts.append(f"  {k}: {v}")
    return "\n".join(parts) if parts else "(無客戶資料)"


_TXN_SYSTEM = (
    "你是金融機構的反洗錢（AML）交易監控分析員。用戶會給你三份材料：\n"
    "1. 《政策》：本公司內部反洗錢政策，每一頁以 `===== Page N =====` 標記頁碼。\n"
    "2. 《客戶背景》：該客戶開戶時的 KYC 資料（職業、年收入、淨資產、資金來源、"
    "PEP 身份、風險評級、開戶初審結論等）。\n"
    "3. 《可疑交易》：一筆被系統標記為可疑的交易，附帶已觸發的可疑信號"
    "（已用中文標註，如「短时间多笔大额」「第三方账户转入」「金额与收入不符」）。\n\n"
    "請基於上述材料完成風險研判，輸出：\n"
    "1. risk_level：綜合風險等級，取值 high / medium / low。\n"
    "2. signals：風險信號逐條說明（結合交易的具體金額/次數/對手方與可疑信號類型）。\n"
    "3. client_context：將本筆可疑交易與《客戶背景》關聯——例如該客戶開戶初審時"
    "是否已標記待覆核、年收入與本筆金額是否相符、是否為 PEP 等。\n"
    "4. actions：處置建議（例如限制該客戶交易、向聯合財富情報組提交可疑交易報告、"
    "人工覆核資金來源、要求客戶提供第三者關係證明等）。\n"
    "5. cited_page + quote：從《政策》中找到與「可疑交易識別/持續監察/上報」最相關的"
    "條款頁碼，並逐字抄錄 10-40 字原文（用於 PDF 定位高亮）。\n"
    "6. summary：簡體中文一句話總結。\n\n"
    "規則：\n"
    "- 只依據《政策》《客戶背景》《可疑交易》判斷，不得引入外部知識或臆測。\n"
    "- signals / actions 用簡體中文，每條簡潔一句。\n"
    "- 【重要】面向合規人員輸出，全部使用通俗中文，嚴禁出現任何英文標志名、"
    "字段名或代碼（如 large_frequency、third_party、ctrlLevel 等）；"
    "需要表達時用中文（如「短时间多笔大额」「第三方账户转入」「限制交易」）。\n\n"
    "只輸出一個嚴格的 JSON 對象，不要 markdown 代碼塊或額外文字。格式：\n"
    '{"risk_level": "high|medium|low", "signals": ["..."], '
    '"client_context": "...", "actions": ["..."], '
    '"cited_page": 頁碼數字, "quote": "政策原文", "summary": "一句話總結"}'
)


def analyze(doc_text: str, client: dict[str, Any], transaction: dict[str, Any]) -> dict[str, Any]:
    """Assess a flagged transaction against the client's KYC profile and policy."""

    doc = _truncate_doc(doc_text)
    if not doc:
        return {
            "risk_level": "medium",
            "signals": [],
            "client_context": "",
            "actions": [],
            "cited_page": None,
            "quote": "",
            "summary": "尚未提供政策文件，无法完成交易风险研判。",
        }

    txn_lines: list[str] = []
    for k, v in (transaction or {}).items():
        if k == "suspect_flags" and isinstance(v, list):
            flags = "、".join(_flag_cn(f) for f in v) if v else "（无）"
            txn_lines.append(f"  已触发可疑信号: {flags}")
        else:
            txn_lines.append(f"  {k}: {v}")
    txn_block = "\n".join(txn_lines) if txn_lines else "(無交易資料)"

    user_content = (
        f"《政策》：\n{doc}\n\n"
        f"《客戶背景》：\n{_format_client(client)}\n\n"
        f"《可疑交易》：\n{txn_block}"
    )

    raw = llm.generate(
        system=_TXN_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
        max_tokens=2048,
    )

    parsed = _extract_json(raw)
    if not parsed:
        logger.warning("txn_analyze: failed to parse structured result; raw reply was non-JSON")
        return {
            "risk_level": "medium",
            "signals": [],
            "client_context": "",
            "actions": [],
            "cited_page": None,
            "quote": "",
            "summary": (raw or "（模型无返回）")[:200],
        }

    risk = str(parsed.get("risk_level") or "").strip().lower()
    if risk not in _VALID_RISK:
        risk = "medium"

    def _str_list(key: str) -> list[str]:
        vals = parsed.get(key)
        if isinstance(vals, list):
            return [str(v).strip() for v in vals if str(v).strip()]
        if isinstance(vals, str) and vals.strip():
            return [vals.strip()]
        return []

    page = parsed.get("cited_page")
    if isinstance(page, bool) or page in (None, ""):
        page = None
    else:
        try:
            page = int(page)
        except (TypeError, ValueError):
            page = None

    return {
        "risk_level": risk,
        "signals": _str_list("signals"),
        "client_context": str(parsed.get("client_context") or "").strip(),
        "actions": _str_list("actions"),
        "cited_page": page,
        "quote": str(parsed.get("quote") or "").strip(),
        "summary": str(parsed.get("summary") or "").strip(),
    }
