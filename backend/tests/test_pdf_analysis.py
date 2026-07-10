from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.pdf_analysis import (
    PdfDocumentKind,
    ProcessingDecision,
    analyze_pdf_upload,
)


def test_pdf_analysis_rejects_non_pdf_bytes_without_content() -> None:
    report = analyze_pdf_upload(b"not a pdf")

    data = report.to_dict()
    assert report.document_kind == PdfDocumentKind.INVALID
    assert report.processing_decision == ProcessingDecision.REJECT
    assert data["has_pdf_header"] is False
    assert "not a pdf" not in str(data)

