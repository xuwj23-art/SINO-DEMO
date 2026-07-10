from __future__ import annotations

import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import Settings


def test_anthropic_base_url_accepts_https() -> None:
    settings = Settings(anthropic_base_url="https://www.packyapi.com/")

    assert settings.anthropic_base_url == "https://www.packyapi.com"


def test_anthropic_base_url_rejects_http() -> None:
    with pytest.raises(ValidationError):
        Settings(anthropic_base_url="http://www.packyapi.com")

