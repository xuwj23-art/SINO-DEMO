"""Native-text PDF extraction and chunking for the demo RAG pipeline.

This module intentionally handles only text-based PDFs. It does not run OCR,
call external services, or attempt table/form understanding.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict


MAX_CHUNK_CHARS = 500
MIN_SPLIT_CHARS = 300

BBox = list[float]


class PdfExtractionError(RuntimeError):
    """Raised when a PDF cannot be safely opened or extracted."""


class Chunk(TypedDict):
    """JSON-friendly chunk shape consumed by the Day3 vector store."""

    chunk_id: str
    document_id: str
    page: int
    paragraph: int
    text: str
    bbox: BBox


class _Paragraph(TypedDict):
    page: int
    paragraph: int
    text: str
    bbox: BBox


def extract_chunks(pdf_path: str | Path, document_id: str) -> list[Chunk]:
    """Extract native PDF text into page-local chunks with bbox metadata."""

    document_id = document_id.strip()
    if not document_id:
        raise PdfExtractionError("document_id is required for PDF extraction.")

    path = _resolve_pdf_path(pdf_path)
    fitz = _load_pymupdf()
    document: Any | None = None

    try:
        document = fitz.open(str(path))
        if getattr(document, "needs_pass", False):
            raise PdfExtractionError("Encrypted PDFs are not supported for extraction.")

        chunks: list[Chunk] = []
        pending_text = ""
        pending_bbox: BBox | None = None
        pending_page: int | None = None
        pending_paragraph: int | None = None
        sequence = 1
        paragraph_counter = 0

        def flush_pending() -> None:
            nonlocal pending_text
            nonlocal pending_bbox
            nonlocal pending_page
            nonlocal pending_paragraph
            nonlocal sequence

            text = pending_text.strip()
            if not text or pending_bbox is None or pending_page is None or pending_paragraph is None:
                pending_text = ""
                pending_bbox = None
                pending_page = None
                pending_paragraph = None
                return

            chunks.append(
                {
                    "chunk_id": f"{document_id}:chunk:{sequence:04d}",
                    "document_id": document_id,
                    "page": pending_page,
                    "paragraph": pending_paragraph,
                    "text": text,
                    "bbox": _round_bbox(pending_bbox),
                }
            )
            sequence += 1
            pending_text = ""
            pending_bbox = None
            pending_page = None
            pending_paragraph = None

        for page_index in range(int(getattr(document, "page_count", 0))):
            page_number = page_index + 1
            page = document.load_page(page_index)
            page_dict = page.get_text("dict", sort=True)

            for paragraph in _iter_page_paragraphs(page_dict, page_number):
                paragraph_counter += 1
                for text_part in _split_text(paragraph["text"]):
                    part: _Paragraph = {
                        "page": page_number,
                        "paragraph": paragraph_counter,
                        "text": text_part,
                        "bbox": paragraph["bbox"],
                    }

                    would_cross_page = pending_page is not None and pending_page != part["page"]
                    would_exceed_limit = (
                        bool(pending_text)
                        and len(pending_text) + len(part["text"]) + 2 > MAX_CHUNK_CHARS
                    )
                    if would_cross_page or would_exceed_limit:
                        flush_pending()

                    if not pending_text:
                        pending_text = part["text"]
                        pending_bbox = part["bbox"]
                        pending_page = part["page"]
                        pending_paragraph = part["paragraph"]
                    else:
                        pending_text = f"{pending_text}\n\n{part['text']}"
                        pending_bbox = _union_bbox(pending_bbox, part["bbox"])

            flush_pending()

        return chunks
    except PdfExtractionError:
        raise
    except Exception as exc:
        raise PdfExtractionError("Failed to extract native text from PDF.") from exc
    finally:
        if document is not None:
            document.close()


def _resolve_pdf_path(pdf_path: str | Path) -> Path:
    try:
        path = Path(pdf_path).resolve(strict=True)
    except OSError as exc:
        raise PdfExtractionError("PDF source path does not exist or is not accessible.") from exc

    if not path.is_file():
        raise PdfExtractionError("PDF source path is not a file.")

    return path


def _load_pymupdf() -> Any:
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:
        raise PdfExtractionError("PyMuPDF is required for native PDF extraction.") from exc

    return fitz


def _iter_page_paragraphs(page_dict: dict[str, Any], page_number: int) -> list[_Paragraph]:
    paragraphs: list[_Paragraph] = []

    for block in page_dict.get("blocks", []):
        if block.get("type", 0) != 0:
            continue

        lines: list[str] = []
        bbox: BBox | None = None
        for line in block.get("lines", []):
            line_text_parts: list[str] = []
            for span in line.get("spans", []):
                span_text = str(span.get("text", ""))
                if not span_text.strip():
                    continue

                span_bbox = _normalize_bbox(span.get("bbox"))
                if span_bbox is None:
                    continue

                line_text_parts.append(span_text)
                bbox = span_bbox if bbox is None else _union_bbox(bbox, span_bbox)

            line_text = "".join(line_text_parts).strip()
            if line_text:
                lines.append(line_text)

        text = _normalize_text("\n".join(lines))
        if text and bbox is not None:
            paragraphs.append(
                {
                    "page": page_number,
                    "paragraph": 0,
                    "text": text,
                    "bbox": bbox,
                }
            )

    return paragraphs


def _split_text(text: str) -> list[str]:
    remaining = text.strip()
    parts: list[str] = []

    while len(remaining) > MAX_CHUNK_CHARS:
        split_at = remaining.rfind("\n", 0, MAX_CHUNK_CHARS + 1)
        if split_at < MIN_SPLIT_CHARS:
            split_at = remaining.rfind(" ", 0, MAX_CHUNK_CHARS + 1)
        if split_at < MIN_SPLIT_CHARS:
            split_at = MAX_CHUNK_CHARS

        part = remaining[:split_at].strip()
        if not part:
            part = remaining[:MAX_CHUNK_CHARS].strip()
            split_at = MAX_CHUNK_CHARS

        parts.append(part)
        remaining = remaining[split_at:].strip()

    if remaining:
        parts.append(remaining)

    return parts


def _normalize_text(text: str) -> str:
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _normalize_bbox(raw_bbox: Any) -> BBox | None:
    if raw_bbox is None or len(raw_bbox) != 4:
        return None

    x0, y0, x1, y1 = (float(value) for value in raw_bbox)
    return [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]


def _union_bbox(first: BBox | None, second: BBox) -> BBox:
    if first is None:
        return list(second)

    return [
        min(first[0], second[0]),
        min(first[1], second[1]),
        max(first[2], second[2]),
        max(first[3], second[3]),
    ]


def _round_bbox(bbox: BBox) -> BBox:
    return [round(float(value), 2) for value in bbox]
