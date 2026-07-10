from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services import demo_rag


DOC_TEXT = (
    "===== Page 1 =====\n"
    "客户开户前必须提供有效身份证明和三个月内住址证明。\n"
    "===== Page 2 =====\n"
    "客户服务人员应将无法由现有材料支持的问题转交人工处理。"
)


def test_customer_answer_returns_cited_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_generate(*args: object, **kwargs: object) -> str:
        return json.dumps(
            {
                "answer": "开户前需要提供有效身份证明和住址证明。",
                "citations": [
                    {"page": 1, "quote": "有效身份证明和三个月内住址证明"}
                ],
                "mode": "answered",
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(demo_rag.llm, "generate", fake_generate)

    result = demo_rag.customer_answer(DOC_TEXT, "开户需要什么资料？")

    assert result["mode"] == "answered"
    assert result["handoff_required"] is False
    assert result["citations"] == [
        {"page": 1, "quote": "有效身份证明和三个月内住址证明"}
    ]
    assert "[1]" in result["answer"]


def test_customer_answer_hands_off_out_of_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_generate(*args: object, **kwargs: object) -> str:
        return json.dumps(
            {
                "answer": demo_rag.CUSTOMER_HANDOFF_ANSWER,
                "citations": [],
                "mode": "handoff",
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(demo_rag.llm, "generate", fake_generate)

    result = demo_rag.customer_answer(DOC_TEXT, "明天恒生指数会涨吗？")

    assert result["mode"] == "handoff"
    assert result["handoff_required"] is True
    assert result["answer"] == demo_rag.CUSTOMER_HANDOFF_ANSWER
    assert result["citations"] == []


def test_customer_answer_forces_handoff_when_citation_is_not_in_material(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_generate(*args: object, **kwargs: object) -> str:
        return json.dumps(
            {
                "answer": "开户只需要口头说明即可。[1]",
                "citations": [{"page": 1, "quote": "口头说明即可"}],
                "mode": "answered",
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(demo_rag.llm, "generate", fake_generate)

    result = demo_rag.customer_answer(DOC_TEXT, "开户材料可以口头说明吗？")

    assert result["mode"] == "handoff"
    assert result["answer"] == demo_rag.CUSTOMER_HANDOFF_ANSWER
    assert result["citations"] == []
