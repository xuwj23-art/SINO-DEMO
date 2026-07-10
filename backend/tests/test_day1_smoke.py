from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app
from app.routers import debug
from app.services import llm


def test_health_endpoint_uses_v1_prefix() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_debug_llm_reports_missing_key_without_prompt_leak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_missing_key(*args: object, **kwargs: object) -> str:
        raise llm.LlmConfigurationError("ANTHROPIC_API_KEY is required for /debug/llm.")

    monkeypatch.setattr(debug.llm, "generate", raise_missing_key)
    client = TestClient(app)

    response = client.get("/api/v1/debug/llm")

    assert response.status_code == 503
    assert "ANTHROPIC_API_KEY" in response.json()["detail"]
