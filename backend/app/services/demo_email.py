"""Demo-only compliance email drafting.

Throwaway demo path. Given a scene (intake / transaction) and the analysis
context, a single model call drafts a Traditional-Chinese compliance email in
Hong Kong financial style: account-opening result + reasons / missing materials,
or transaction restriction notice + how to follow up.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.services import llm

logger = logging.getLogger(__name__)

_VALID_SCENE = {"intake", "transaction"}


def _extract_json(raw: str) -> dict[str, Any] | None:
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


_INTAKE_SYSTEM = (
    "你是香港持牌券商的合規主任助理。根據客戶開戶初審結果，撰寫一封繁體中文的合規通知郵件，"
    "通知客戶開戶審核結果。\n"
    "要求：\n"
    "1. 香港金融行業規範、正式、禮貌的商務郵件語氣。\n"
    "2. 若不通過，清楚說明不通過的原因 / 需要補交的材料，並告知客戶下一步如何處理。\n"
    "3. 若為待覆核，說明需進一步核實的事項及客戶需配合的動作。\n"
    "4. 郵件須含稱謂、正文、下一步說明、結尾署名（盛富證券期貨有限公司 合規部）。\n"
    "5. 全文繁體中文，不使用英文標志名或字段名。\n\n"
    "只輸出嚴格 JSON，不要 markdown 代碼塊。格式："
    '{"subject": "郵件主旨", "body": "郵件正文（含稱謂與署名，可用\\n換行）"}'
)

_TXN_SYSTEM = (
    "你是香港持牌券商的合規主任助理。根據一筆被標記為可疑的交易及風險研判結果，"
    "撰寫一封繁體中文的客戶通知郵件，告知客戶其賬戶將被限制及原因。\n"
    "要求：\n"
    "1. 香港金融行業規範、正式、禮貌的商務郵件語氣。\n"
    "2. 說明被限制的原因（結合風險信號，但用客戶能理解的語言，不暴露內部偵測規則代碼）。\n"
    "3. 說明限制的範圍（如暫停交易）及客戶下一步如何處理（如聯絡客戶經理、提供資金來源證明、補充文件）。\n"
    "4. 郵件須含稱謂、正文、下一步說明、結尾署名（盛富證券期貨有限公司 合規部）。\n"
    "5. 全文繁體中文，不使用英文標志名或字段名。\n\n"
    "只輸出嚴格 JSON，不要 markdown 代碼塊。格式："
    '{"subject": "郵件主旨", "body": "郵件正文（含稱謂與署名，可用\\n換行）"}'
)


def _format_context(ctx: dict[str, Any]) -> str:
    if not isinstance(ctx, dict):
        return str(ctx)
    return "\n".join(f"  {k}: {v}" for k, v in ctx.items())


def generate_email(
    scene: str,
    client_name: str,
    client_id: str,
    context: dict[str, Any],
) -> dict[str, Any]:
    """Draft a Traditional-Chinese compliance email for intake or transaction."""

    scene = (scene or "").strip().lower()
    if scene not in _VALID_SCENE:
        scene = "intake"

    system = _INTAKE_SYSTEM if scene == "intake" else _TXN_SYSTEM
    ctx_block = _format_context(context) or "（無背景資訊）"
    user_content = (
        f"客戶姓名：{client_name}\n客戶編號：{client_id}\n\n背景資訊：\n{ctx_block}"
    )

    raw = llm.generate(
        system=system,
        messages=[{"role": "user", "content": user_content}],
        max_tokens=1536,
    )

    parsed = _extract_json(raw)
    if not parsed or not parsed.get("subject") or not parsed.get("body"):
        logger.warning("email: failed to parse structured result; raw reply was non-JSON")
        return {
            "subject": "開戶審核結果通知" if scene == "intake" else "賬戶限制通知",
            "body": (raw or "（模型無返回）")[:600],
            "scene": scene,
        }

    return {
        "subject": str(parsed["subject"]).strip(),
        "body": str(parsed["body"]).strip(),
        "scene": scene,
    }
