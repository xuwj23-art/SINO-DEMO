"""In-memory demo state.

The 0006 demo deliberately avoids a database and vector service. Later days add
documents, chunks, embeddings, regulatory updates, and notifications here.
"""

from __future__ import annotations

from typing import Any

import numpy as np

DOCUMENTS: dict[str, dict[str, Any]] = {}
CHUNKS: list[dict[str, Any]] = []
EMBEDDINGS: np.ndarray | None = None
REGULATORY: dict[str, dict[str, Any]] = {}
NOTIFICATIONS: list[dict[str, Any]] = []

