from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.pdf_extract import PdfExtractionError, extract_chunks


def test_extract_chunks_returns_text_page_and_bbox_metadata(tmp_path: Path) -> None:
    pdf_path = tmp_path / "sample.pdf"
    _write_sample_pdf(pdf_path)

    chunks = extract_chunks(pdf_path, "doc-001")

    assert chunks
    assert chunks[0]["chunk_id"] == "doc-001:chunk:0001"
    assert all(chunk["document_id"] == "doc-001" for chunk in chunks)
    assert all(chunk["page"] >= 1 for chunk in chunks)
    assert all(chunk["paragraph"] >= 1 for chunk in chunks)
    assert all(chunk["text"].strip() for chunk in chunks)

    combined_text = "\n".join(chunk["text"] for chunk in chunks)
    assert "Client onboarding checklist" in combined_text
    assert "Risk review notes" in combined_text

    for chunk in chunks:
        bbox = chunk["bbox"]
        assert len(bbox) == 4
        assert bbox[0] <= bbox[2]
        assert bbox[1] <= bbox[3]


def test_extract_chunks_preserves_one_based_page_numbers(tmp_path: Path) -> None:
    pdf_path = tmp_path / "multi-page.pdf"
    _write_sample_pdf(pdf_path)

    chunks = extract_chunks(pdf_path, "doc-pages")

    assert {chunk["page"] for chunk in chunks} == {1, 2}


def test_extract_chunks_rejects_missing_path(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.pdf"

    with pytest.raises(PdfExtractionError):
        extract_chunks(missing_path, "doc-missing")


def _write_sample_pdf(pdf_path: Path) -> None:
    import fitz

    document = fitz.open()
    try:
        page_one = document.new_page()
        page_one.insert_text(
            (72, 72),
            "Client onboarding checklist requires identity proof, address proof, "
            "and account opening approval before activation.",
        )
        page_one.insert_text(
            (72, 120),
            "The operations team should confirm whether enhanced due diligence "
            "is needed before submitting the application.",
        )

        page_two = document.new_page()
        page_two.insert_text(
            (72, 72),
            "Risk review notes must cite the supporting policy section and keep "
            "the final decision traceable to source documents.",
        )

        document.save(pdf_path)
    finally:
        document.close()
