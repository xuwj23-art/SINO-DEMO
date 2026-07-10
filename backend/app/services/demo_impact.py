"""Demo-only regulatory impact analysis on existing clients.

Throwaway demo path. Given the uploaded AML policy, a regulatory push, and a
list of synthetic existing clients' KYC profiles, a single model call assesses
which clients are affected by the push and how. All client data is synthetic.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.services import llm

logger = logging.getLogger(__name__)

MAX_DOC_CHARS = 120_000
_VALID_LEVEL = {"high", "medium", "low"}


def _truncate_doc(doc_text: str) -> str:
    doc_text = (doc_text or "").strip()
    if len(doc_text) <= MAX_DOC_CHARS:
        return doc_text
    return doc_text[:MAX_DOC_CHARS] + "\n\n[文档过长，已截断以适配演示上下文]"


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


def _format_client(c: dict[str, Any]) -> str:
    """Render one synthetic client's KYC as readable text for the model."""
    if not isinstance(c, dict):
        return str(c)
    parts: list[str] = []
    cid = c.get("id") or c.get("client_id") or ""
    cname = c.get("name") or c.get("client_name") or ""
    data = c.get("data") if isinstance(c.get("data"), dict) else c
    parts.append(f"客户 {cname}（编号 {cid}）")
    for layer in ("account", "kyc"):
        sub = data.get(layer) if isinstance(data, dict) else None
        if isinstance(sub, dict) and sub:
            for k, v in sub.items():
                parts.append(f"  {layer}.{k}: {v}")
    return "\n".join(parts)


_IMPACT_SYSTEM = (
    "你是金融机构的合规分析员。用户会给你三份材料：\n"
    "1. 《政策》：本公司内部反洗钱政策，每一页以 `===== Page N =====` 标记页码。\n"
    "2. 《监管推送》：一条外部监管更新（标题+正文）。\n"
    "3. 《存量客户清单》：若干客户的 KYC 资料（合成虚构数据）。\n\n"
    "请逐个客户判断这条监管推送对其的影响，输出：\n"
    "1. impact_level：该客户受影响程度，取值 high / medium / low。\n"
    "   - high：推送直接改变该客户的合规处置（如 PEP 客户遇 PEP 新规、资金来源可疑客户遇电汇新规）；\n"
    "   - medium：推送要求复查该客户某项资料或加强监控；\n"
    "   - low：推送与该客户基本无关，常规即可。\n"
    "2. impact_points：具体影响点（逐条，结合推送要求与该客户 KYC 的具体字段/数值）。\n"
    "3. recommended_action：对该客户的建议动作（如复核 PEP 身份、重新核验资金来源、更新地址证明、复查电汇信息完整性等）。\n"
    "4. cited_page + quote：若影响点对应《政策》某条款，填页码并逐字抄录 10-40 字原文；无则 cited_page 为 null、quote 为空。\n\n"
    "规则：\n"
    "- 只依据《政策》《监管推送》《存量客户清单》判断，不得引入外部知识或臆测。\n"
    "- impact_points / recommended_action 用简体中文，面向合规人员，禁止出现英文标志名/字段名/代码。\n"
    "- 必须为清单中每个客户都给出一条 impact 结果。\n\n"
    "只输出一个严格的 JSON 对象，不要 markdown 代码块或额外文字。格式：\n"
    '{"impacts": [{"client_id": "...", "client_name": "...", "impact_level": "high|medium|low", '
    '"impact_points": ["..."], "recommended_action": "...", "cited_page": 页码或null, "quote": "..."}], '
    '"summary": "一句话总结影响面"}'
)


def analyze_impact(
    doc_text: str,
    push_title: str,
    push_body: str,
    clients: list[dict[str, Any]],
) -> dict[str, Any]:
    """Assess a regulatory push's impact across the synthetic client book."""

    doc = _truncate_doc(doc_text)
    push_title = (push_title or "").strip()
    push_body = (push_body or "").strip()

    if not clients:
        return {"impacts": [], "summary": "未提供存量客户清单，无法分析影响面。"}

    push_block = f"标题：{push_title}\n正文：{push_body}"
    doc_block = doc if doc else "（用户尚未上传政策）"
    clients_block = "\n\n".join(_format_client(c) for c in clients) or "（无客户）"

    user_content = (
        f"《政策》：\n{doc_block}\n\n"
        f"《监管推送》：\n{push_block}\n\n"
        f"《存量客户清单》：\n{clients_block}"
    )

    raw = llm.generate(
        system=_IMPACT_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
        max_tokens=3072,
    )

    parsed = _extract_json(raw)
    if not parsed or not isinstance(parsed.get("impacts"), list):
        logger.warning("impact: failed to parse structured result; raw reply was non-JSON")
        return {"impacts": [], "summary": (raw or "（模型无返回）")[:200]}

    impacts: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for item in parsed["impacts"]:
        if not isinstance(item, dict):
            continue
        cid = str(item.get("client_id") or "").strip()
        cname = str(item.get("client_name") or "").strip()
        if not cid and not cname:
            continue
        if cid in seen_ids:
            continue
        seen_ids.add(cid)
        level = str(item.get("impact_level") or "").strip().lower()
        if level not in _VALID_LEVEL:
            level = "medium"
        page = item.get("cited_page")
        if isinstance(page, bool) or page in (None, ""):
            page = None
        else:
            try:
                page = int(page)
            except (TypeError, ValueError):
                page = None

        def _str_list(key: str) -> list[str]:
            vals = item.get(key)
            if isinstance(vals, list):
                return [str(v).strip() for v in vals if str(v).strip()]
            if isinstance(vals, str) and vals.strip():
                return [vals.strip()]
            return []

        impacts.append({
            "client_id": cid,
            "client_name": cname,
            "impact_level": level,
            "impact_points": _str_list("impact_points"),
            "recommended_action": str(item.get("recommended_action") or "").strip(),
            "cited_page": page,
            "quote": str(item.get("quote") or "").strip(),
        })

    return {
        "impacts": impacts,
        "summary": str(parsed.get("summary") or "").strip(),
    }
