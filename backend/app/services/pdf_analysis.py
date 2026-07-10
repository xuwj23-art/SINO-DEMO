"""Framework-independent PDF upload analysis for the ingestion pipeline.

The analyzer intentionally returns only structural and quality metadata. It does
not call external services, run OCR, call an LLM, log document content, or return
extracted document text.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Any


ANALYZER_NAME = "pdf_analysis"
ANALYZER_VERSION = "0.1.0"
PDF_HEADER_SCAN_BYTES = 1024
HASH_CHUNK_BYTES = 1024 * 1024
ISSUE_PAGE_SAMPLE_LIMIT = 25


class PdfAnalysisError(RuntimeError):
    """Raised for caller/setup errors, not for malformed uploaded PDFs."""


class PdfDocumentKind(str, Enum):
    TEXT_BASED = "text_based"
    MIXED = "mixed"
    SCANNED = "scanned_or_image_based"
    ENCRYPTED = "encrypted"
    EMPTY = "empty"
    INVALID = "invalid_pdf"
    UNSUPPORTED = "unsupported"
    CORRUPT = "corrupt"


class RecommendedExtractionMethod(str, Enum):
    NATIVE_TEXT = "native_text"
    MIXED = "mixed"
    OCR = "ocr"
    UNAVAILABLE = "unavailable"


class ProcessingDecision(str, Enum):
    PROCESS_NATIVE_TEXT = "process_native_text"
    PROCESS_NATIVE_TEXT_WITH_REVIEW = "process_native_text_with_review"
    PROCESS_MIXED_WITH_REVIEW = "process_mixed_with_review"
    NEEDS_OCR_REVIEW = "needs_ocr_review"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    REJECT = "reject"


class PdfIssueCode(str, Enum):
    INVALID_PDF_HEADER = "invalid_pdf_header"
    EMPTY_FILE = "empty_file"
    EMPTY_PDF = "empty_pdf"
    FILE_TOO_LARGE = "file_too_large"
    PAGE_COUNT_LIMIT_EXCEEDED = "page_count_limit_exceeded"
    PARSER_UNAVAILABLE = "parser_unavailable"
    PARSER_FAILED = "parser_failed"
    ENCRYPTED_PDF = "encrypted_pdf"
    SCANNED_OR_IMAGE_PAGES = "scanned_or_image_pages_detected"
    MIXED_CONTENT = "mixed_native_text_and_image_content"
    PAGES_WITHOUT_TEXT = "pages_without_extractable_text"
    LOW_TEXT_CONFIDENCE = "low_text_confidence"
    ABNORMAL_TEXT_MARKERS = "abnormal_extracted_text_markers"
    TABLE_DENSE_PAGES = "table_dense_pages_detected"
    PAGE_ANALYSIS_FAILED = "page_analysis_failed"


class IssueSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class PdfAnalysisConfig:
    """Tunable thresholds for native PDF quality analysis."""

    max_file_size_bytes: int = 100 * 1024 * 1024
    max_pages: int = 1000
    allowed_base_dir: Path | None = None
    min_text_chars_for_text_page: int = 80
    min_words_for_text_page: int = 10
    low_text_chars_threshold: int = 40
    scanned_image_coverage_threshold: float = 0.65
    mixed_image_coverage_threshold: float = 0.30
    min_text_page_ratio_for_text_pdf: float = 0.90
    max_scanned_page_ratio_for_text_pdf: float = 0.05
    min_scanned_page_ratio_for_scanned_pdf: float = 0.75
    abnormal_char_ratio_threshold: float = 0.02
    table_dense_review_ratio: float = 0.25


@dataclass(frozen=True)
class PdfIssue:
    code: PdfIssueCode
    severity: IssueSeverity
    message: str
    count: int = 0
    page_numbers: tuple[int, ...] = ()


@dataclass(frozen=True)
class PdfPageQuality:
    page_number: int
    width_points: float
    height_points: float
    native_text_chars: int
    native_word_count: int
    text_block_count: int
    image_count: int
    image_coverage_ratio: float | None
    vector_drawing_count: int
    line_count: int
    has_native_text: bool
    appears_scanned: bool
    appears_mixed: bool
    appears_blank: bool
    is_low_confidence_text: bool
    has_abnormal_text_markers: bool
    is_table_dense: bool
    recommended_extraction_method: RecommendedExtractionMethod
    extraction_confidence: float


@dataclass(frozen=True)
class PdfAnalysisResult:
    analyzer_name: str
    analyzer_version: str
    file_size_bytes: int
    file_sha256: str | None
    has_pdf_header: bool
    is_encrypted: bool
    needs_password: bool
    page_count: int
    analyzed_page_count: int
    document_kind: PdfDocumentKind
    recommended_extraction_method: RecommendedExtractionMethod
    processing_decision: ProcessingDecision
    can_process_as_normal_text_pdf: bool
    can_extract_native_text: bool
    requires_ocr: bool
    requires_human_review: bool
    extraction_confidence: float
    native_text_pages: int
    mixed_pages: int
    scanned_or_image_pages: int
    blank_pages: int
    low_confidence_pages: int
    abnormal_text_pages: int
    table_dense_pages: int
    ocr_recommended_pages: int
    issues: tuple[PdfIssue, ...]
    pages: tuple[PdfPageQuality, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable metadata without document text."""

        return _to_plain_data(self)


@dataclass(frozen=True)
class _PdfSource:
    data: bytes | None
    path: Path | None
    file_size_bytes: int
    file_sha256: str | None
    header: bytes


class PdfUploadAnalyzer:
    """Analyze uploaded PDFs before they enter the knowledge base."""

    def __init__(self, config: PdfAnalysisConfig | None = None) -> None:
        self.config = config or PdfAnalysisConfig()

    def analyze(self, source: bytes | bytearray | memoryview | str | Path) -> PdfAnalysisResult:
        """Analyze a PDF from bytes or a quarantined local path.

        Callers should pass a server-controlled temporary path or bytes from the
        upload layer. If ``allowed_base_dir`` is configured, path inputs are
        constrained to that directory after symlink resolution.
        """

        pdf_source = self._load_source(source)
        has_pdf_header = b"%PDF-" in pdf_source.header[:PDF_HEADER_SCAN_BYTES]

        if pdf_source.file_size_bytes == 0:
            return self._blocked_result(
                pdf_source,
                has_pdf_header=False,
                document_kind=PdfDocumentKind.INVALID,
                decision=ProcessingDecision.REJECT,
                issues=(
                    _issue(
                        PdfIssueCode.EMPTY_FILE,
                        IssueSeverity.ERROR,
                        "Uploaded file is empty.",
                    ),
                ),
            )

        if pdf_source.file_size_bytes > self.config.max_file_size_bytes:
            return self._blocked_result(
                pdf_source,
                has_pdf_header=has_pdf_header,
                document_kind=PdfDocumentKind.UNSUPPORTED,
                decision=ProcessingDecision.MANUAL_REVIEW_REQUIRED,
                requires_human_review=True,
                issues=(
                    _issue(
                        PdfIssueCode.FILE_TOO_LARGE,
                        IssueSeverity.ERROR,
                        "PDF exceeds the configured analysis size limit.",
                    ),
                ),
            )

        if not has_pdf_header:
            return self._blocked_result(
                pdf_source,
                has_pdf_header=False,
                document_kind=PdfDocumentKind.INVALID,
                decision=ProcessingDecision.REJECT,
                issues=(
                    _issue(
                        PdfIssueCode.INVALID_PDF_HEADER,
                        IssueSeverity.ERROR,
                        "Uploaded file does not have a recognizable PDF header.",
                    ),
                ),
            )

        try:
            fitz = _load_pymupdf()
        except PdfAnalysisError:
            return self._blocked_result(
                pdf_source,
                has_pdf_header=True,
                document_kind=PdfDocumentKind.UNSUPPORTED,
                decision=ProcessingDecision.MANUAL_REVIEW_REQUIRED,
                requires_human_review=True,
                issues=(
                    _issue(
                        PdfIssueCode.PARSER_UNAVAILABLE,
                        IssueSeverity.ERROR,
                        "PyMuPDF is required for local PDF analysis.",
                    ),
                ),
            )

        document = None
        try:
            if pdf_source.path is not None:
                document = fitz.open(str(pdf_source.path))
            else:
                document = fitz.open(stream=pdf_source.data, filetype="pdf")
        except Exception:
            return self._blocked_result(
                pdf_source,
                has_pdf_header=True,
                document_kind=PdfDocumentKind.CORRUPT,
                decision=ProcessingDecision.REJECT,
                requires_human_review=True,
                issues=(
                    _issue(
                        PdfIssueCode.PARSER_FAILED,
                        IssueSeverity.ERROR,
                        "PDF parser could not open the uploaded file.",
                    ),
                ),
            )

        try:
            is_encrypted = bool(getattr(document, "is_encrypted", False))
            needs_password = bool(getattr(document, "needs_pass", False))
            if is_encrypted or needs_password:
                return self._blocked_result(
                    pdf_source,
                    has_pdf_header=True,
                    document_kind=PdfDocumentKind.ENCRYPTED,
                    decision=ProcessingDecision.REJECT,
                    is_encrypted=is_encrypted,
                    needs_password=needs_password,
                    requires_human_review=True,
                    issues=(
                        _issue(
                            PdfIssueCode.ENCRYPTED_PDF,
                            IssueSeverity.ERROR,
                            "Encrypted PDFs are not processed automatically in the MVP pipeline.",
                        ),
                    ),
                )

            page_count = int(getattr(document, "page_count", 0))
            if page_count == 0:
                return self._blocked_result(
                    pdf_source,
                    has_pdf_header=True,
                    document_kind=PdfDocumentKind.EMPTY,
                    decision=ProcessingDecision.REJECT,
                    page_count=0,
                    issues=(
                        _issue(
                            PdfIssueCode.EMPTY_PDF,
                            IssueSeverity.ERROR,
                            "PDF contains no pages.",
                        ),
                    ),
                )

            if page_count > self.config.max_pages:
                return self._blocked_result(
                    pdf_source,
                    has_pdf_header=True,
                    document_kind=PdfDocumentKind.UNSUPPORTED,
                    decision=ProcessingDecision.MANUAL_REVIEW_REQUIRED,
                    page_count=page_count,
                    requires_human_review=True,
                    issues=(
                        _issue(
                            PdfIssueCode.PAGE_COUNT_LIMIT_EXCEEDED,
                            IssueSeverity.ERROR,
                            "PDF exceeds the configured page-count analysis limit.",
                        ),
                    ),
                )

            pages: list[PdfPageQuality] = []
            issues: list[PdfIssue] = []

            for page_index in range(page_count):
                try:
                    page = document.load_page(page_index)
                    pages.append(self._analyze_page(page, page_index + 1))
                except Exception:
                    issues.append(
                        _issue(
                            PdfIssueCode.PAGE_ANALYSIS_FAILED,
                            IssueSeverity.ERROR,
                            "A page could not be analyzed by the local PDF parser.",
                            page_numbers=(page_index + 1,),
                            count=1,
                        )
                    )

            return self._summarize_pages(
                pdf_source=pdf_source,
                has_pdf_header=True,
                page_count=page_count,
                pages=tuple(pages),
                base_issues=tuple(issues),
            )
        finally:
            if document is not None:
                document.close()

    def _load_source(self, source: bytes | bytearray | memoryview | str | Path) -> _PdfSource:
        if isinstance(source, (bytes, bytearray, memoryview)):
            data = bytes(source)
            return _PdfSource(
                data=data,
                path=None,
                file_size_bytes=len(data),
                file_sha256=sha256(data).hexdigest(),
                header=data[:PDF_HEADER_SCAN_BYTES],
            )

        path = Path(source)
        if not path.exists() or not path.is_file():
            raise PdfAnalysisError("PDF source path does not exist or is not a file.")

        resolved_path = path.resolve(strict=True)
        if self.config.allowed_base_dir is not None:
            allowed_base = self.config.allowed_base_dir.resolve(strict=True)
            if not _is_relative_to(resolved_path, allowed_base):
                raise PdfAnalysisError("PDF source path is outside the allowed base directory.")

        file_size = resolved_path.stat().st_size
        with resolved_path.open("rb") as pdf_file:
            header = pdf_file.read(PDF_HEADER_SCAN_BYTES)

        file_hash = None
        if file_size <= self.config.max_file_size_bytes:
            file_hash = _sha256_file(resolved_path)

        return _PdfSource(
            data=None,
            path=resolved_path,
            file_size_bytes=file_size,
            file_sha256=file_hash,
            header=header,
        )

    def _analyze_page(self, page: Any, page_number: int) -> PdfPageQuality:
        rect = page.rect
        width = _round_ratio(float(rect.width))
        height = _round_ratio(float(rect.height))
        page_area = max(float(rect.width) * float(rect.height), 1.0)

        # Extracted text is used only for aggregate quality signals and is not
        # returned or logged by this module.
        text = page.get_text("text", sort=True) or ""
        native_text_chars = sum(1 for char in text if not char.isspace())
        has_abnormal_text_markers = self._has_abnormal_text_markers(text)

        words = page.get_text("words", sort=True) or []
        native_word_count = len(words)
        line_counts = Counter((word[5], word[6]) for word in words if len(word) >= 7)
        line_count = len(line_counts)

        blocks = page.get_text("blocks") or []
        text_block_count = sum(1 for block in blocks if len(block) >= 7 and block[6] == 0)
        image_block_count = sum(1 for block in blocks if len(block) >= 7 and block[6] == 1)

        image_count = _safe_len(lambda: page.get_images(full=True), fallback=image_block_count)
        image_coverage_ratio = self._estimate_image_coverage_ratio(page, blocks, page_area)
        vector_drawing_count = _safe_len(page.get_drawings, fallback=0)

        has_native_text = (
            native_text_chars >= self.config.min_text_chars_for_text_page
            or native_word_count >= self.config.min_words_for_text_page
        )
        has_any_native_text = native_text_chars > 0 or native_word_count > 0
        image_heavy = (
            image_coverage_ratio is not None
            and image_coverage_ratio >= self.config.scanned_image_coverage_threshold
        ) or (
            image_coverage_ratio is None
            and image_count > 0
            and native_text_chars < self.config.low_text_chars_threshold
        )

        appears_blank = not has_any_native_text and image_count == 0 and vector_drawing_count < 3
        appears_scanned = not has_native_text and image_heavy
        appears_mixed = has_native_text and (
            image_coverage_ratio is not None
            and image_coverage_ratio >= self.config.mixed_image_coverage_threshold
        )
        is_low_confidence_text = (
            has_any_native_text
            and not has_native_text
            and not appears_blank
        ) or has_abnormal_text_markers
        is_table_dense = self._is_table_dense(
            native_word_count=native_word_count,
            line_counts=line_counts,
            vector_drawing_count=vector_drawing_count,
        )

        if appears_scanned:
            recommended_method = RecommendedExtractionMethod.OCR
            extraction_confidence = 0.0
        elif appears_mixed:
            recommended_method = RecommendedExtractionMethod.MIXED
            extraction_confidence = 0.72
        elif has_native_text:
            recommended_method = RecommendedExtractionMethod.NATIVE_TEXT
            extraction_confidence = 0.92
        elif appears_blank:
            recommended_method = RecommendedExtractionMethod.UNAVAILABLE
            extraction_confidence = 1.0
        else:
            recommended_method = RecommendedExtractionMethod.OCR
            extraction_confidence = 0.0

        if is_low_confidence_text:
            extraction_confidence = min(extraction_confidence, 0.45)

        return PdfPageQuality(
            page_number=page_number,
            width_points=width,
            height_points=height,
            native_text_chars=native_text_chars,
            native_word_count=native_word_count,
            text_block_count=text_block_count,
            image_count=image_count,
            image_coverage_ratio=image_coverage_ratio,
            vector_drawing_count=vector_drawing_count,
            line_count=line_count,
            has_native_text=has_native_text,
            appears_scanned=appears_scanned,
            appears_mixed=appears_mixed,
            appears_blank=appears_blank,
            is_low_confidence_text=is_low_confidence_text,
            has_abnormal_text_markers=has_abnormal_text_markers,
            is_table_dense=is_table_dense,
            recommended_extraction_method=recommended_method,
            extraction_confidence=_round_ratio(extraction_confidence),
        )

    def _summarize_pages(
        self,
        *,
        pdf_source: _PdfSource,
        has_pdf_header: bool,
        page_count: int,
        pages: tuple[PdfPageQuality, ...],
        base_issues: tuple[PdfIssue, ...],
    ) -> PdfAnalysisResult:
        native_text_pages = sum(1 for page in pages if page.has_native_text)
        mixed_pages = sum(1 for page in pages if page.appears_mixed)
        scanned_pages = sum(1 for page in pages if page.appears_scanned)
        blank_pages = sum(1 for page in pages if page.appears_blank)
        low_confidence_pages = sum(1 for page in pages if page.is_low_confidence_text)
        abnormal_text_pages = sum(1 for page in pages if page.has_abnormal_text_markers)
        table_dense_pages = sum(1 for page in pages if page.is_table_dense)
        ocr_recommended_pages = sum(
            1 for page in pages if page.recommended_extraction_method == RecommendedExtractionMethod.OCR
        )

        content_page_count = max(len(pages) - blank_pages, 0)
        text_page_ratio = _safe_ratio(native_text_pages, content_page_count)
        scanned_page_ratio = _safe_ratio(scanned_pages, content_page_count)

        if content_page_count == 0:
            document_kind = PdfDocumentKind.EMPTY
            recommended_method = RecommendedExtractionMethod.UNAVAILABLE
            decision = ProcessingDecision.REJECT
        elif (
            text_page_ratio >= self.config.min_text_page_ratio_for_text_pdf
            and scanned_page_ratio <= self.config.max_scanned_page_ratio_for_text_pdf
        ):
            document_kind = PdfDocumentKind.TEXT_BASED
            recommended_method = RecommendedExtractionMethod.NATIVE_TEXT
            decision = ProcessingDecision.PROCESS_NATIVE_TEXT
        elif (
            scanned_page_ratio >= self.config.min_scanned_page_ratio_for_scanned_pdf
            and text_page_ratio <= (1.0 - self.config.min_scanned_page_ratio_for_scanned_pdf)
        ):
            document_kind = PdfDocumentKind.SCANNED
            recommended_method = RecommendedExtractionMethod.OCR
            decision = ProcessingDecision.NEEDS_OCR_REVIEW
        else:
            document_kind = PdfDocumentKind.MIXED
            recommended_method = RecommendedExtractionMethod.MIXED
            decision = ProcessingDecision.PROCESS_MIXED_WITH_REVIEW

        table_review_required = (
            table_dense_pages > 0
            and _safe_ratio(table_dense_pages, max(page_count, 1)) >= self.config.table_dense_review_ratio
        )
        requires_ocr = ocr_recommended_pages > 0
        requires_human_review = (
            document_kind != PdfDocumentKind.TEXT_BASED
            or low_confidence_pages > 0
            or abnormal_text_pages > 0
            or table_review_required
            or bool(base_issues)
        )

        if document_kind == PdfDocumentKind.TEXT_BASED and requires_human_review:
            decision = ProcessingDecision.PROCESS_NATIVE_TEXT_WITH_REVIEW
        elif document_kind == PdfDocumentKind.EMPTY:
            decision = ProcessingDecision.REJECT

        extraction_confidence = self._document_confidence(
            pages=pages,
            document_kind=document_kind,
            requires_human_review=requires_human_review,
        )

        issues = list(base_issues)
        issues.extend(self._quality_issues(pages))
        if document_kind == PdfDocumentKind.EMPTY:
            issues.append(
                _issue(
                    PdfIssueCode.EMPTY_PDF,
                    IssueSeverity.ERROR,
                    "PDF has no pages with analyzable text or image content.",
                )
            )

        return PdfAnalysisResult(
            analyzer_name=ANALYZER_NAME,
            analyzer_version=ANALYZER_VERSION,
            file_size_bytes=pdf_source.file_size_bytes,
            file_sha256=pdf_source.file_sha256,
            has_pdf_header=has_pdf_header,
            is_encrypted=False,
            needs_password=False,
            page_count=page_count,
            analyzed_page_count=len(pages),
            document_kind=document_kind,
            recommended_extraction_method=recommended_method,
            processing_decision=decision,
            can_process_as_normal_text_pdf=(
                document_kind == PdfDocumentKind.TEXT_BASED and not requires_ocr
            ),
            can_extract_native_text=native_text_pages > 0,
            requires_ocr=requires_ocr,
            requires_human_review=requires_human_review,
            extraction_confidence=extraction_confidence,
            native_text_pages=native_text_pages,
            mixed_pages=mixed_pages,
            scanned_or_image_pages=scanned_pages,
            blank_pages=blank_pages,
            low_confidence_pages=low_confidence_pages,
            abnormal_text_pages=abnormal_text_pages,
            table_dense_pages=table_dense_pages,
            ocr_recommended_pages=ocr_recommended_pages,
            issues=tuple(issues),
            pages=pages,
        )

    def _blocked_result(
        self,
        pdf_source: _PdfSource,
        *,
        has_pdf_header: bool,
        document_kind: PdfDocumentKind,
        decision: ProcessingDecision,
        issues: tuple[PdfIssue, ...],
        page_count: int = 0,
        is_encrypted: bool = False,
        needs_password: bool = False,
        requires_human_review: bool = False,
    ) -> PdfAnalysisResult:
        return PdfAnalysisResult(
            analyzer_name=ANALYZER_NAME,
            analyzer_version=ANALYZER_VERSION,
            file_size_bytes=pdf_source.file_size_bytes,
            file_sha256=pdf_source.file_sha256,
            has_pdf_header=has_pdf_header,
            is_encrypted=is_encrypted,
            needs_password=needs_password,
            page_count=page_count,
            analyzed_page_count=0,
            document_kind=document_kind,
            recommended_extraction_method=RecommendedExtractionMethod.UNAVAILABLE,
            processing_decision=decision,
            can_process_as_normal_text_pdf=False,
            can_extract_native_text=False,
            requires_ocr=False,
            requires_human_review=requires_human_review,
            extraction_confidence=0.0,
            native_text_pages=0,
            mixed_pages=0,
            scanned_or_image_pages=0,
            blank_pages=0,
            low_confidence_pages=0,
            abnormal_text_pages=0,
            table_dense_pages=0,
            ocr_recommended_pages=0,
            issues=issues,
            pages=(),
        )

    def _estimate_image_coverage_ratio(
        self,
        page: Any,
        blocks: list[Any],
        page_area: float,
    ) -> float | None:
        areas: list[float] = []

        try:
            for image_info in page.get_image_info(hashes=False, xrefs=False):
                bbox = image_info.get("bbox")
                area = _bbox_area(bbox)
                if area > 0:
                    areas.append(area)
        except Exception:
            areas = []

        if not areas:
            for block in blocks:
                if len(block) >= 7 and block[6] == 1:
                    area = _bbox_area(block[:4])
                    if area > 0:
                        areas.append(area)

        if not areas:
            return None

        return _round_ratio(min(sum(areas) / page_area, 1.0))

    def _has_abnormal_text_markers(self, text: str) -> bool:
        if not text:
            return False

        abnormal_count = 0
        for char in text:
            codepoint = ord(char)
            if char == "\ufffd" or char == "\x00":
                abnormal_count += 1
            elif codepoint < 32 and char not in "\n\r\t":
                abnormal_count += 1
            elif 0xE000 <= codepoint <= 0xF8FF:
                abnormal_count += 1

        return _safe_ratio(abnormal_count, len(text)) >= self.config.abnormal_char_ratio_threshold

    def _is_table_dense(
        self,
        *,
        native_word_count: int,
        line_counts: Counter[Any],
        vector_drawing_count: int,
    ) -> bool:
        if native_word_count < 40:
            return False

        line_count = len(line_counts)
        if line_count == 0:
            return False

        short_lines = sum(1 for word_count in line_counts.values() if word_count <= 6)
        short_line_ratio = _safe_ratio(short_lines, line_count)
        drawing_grid_signal = vector_drawing_count >= 20 and native_word_count >= 20
        compact_text_grid_signal = (
            native_word_count >= 60 and line_count >= 20 and short_line_ratio >= 0.65
        )
        return drawing_grid_signal or compact_text_grid_signal

    def _document_confidence(
        self,
        *,
        pages: tuple[PdfPageQuality, ...],
        document_kind: PdfDocumentKind,
        requires_human_review: bool,
    ) -> float:
        content_pages = [page for page in pages if not page.appears_blank]
        if not content_pages:
            return 0.0

        confidence = sum(page.extraction_confidence for page in content_pages) / len(content_pages)
        if document_kind == PdfDocumentKind.MIXED:
            confidence = min(confidence, 0.72)
        elif document_kind == PdfDocumentKind.SCANNED:
            confidence = min(confidence, 0.20)

        if requires_human_review:
            confidence = min(confidence, 0.80)

        return _round_ratio(confidence)

    def _quality_issues(self, pages: tuple[PdfPageQuality, ...]) -> tuple[PdfIssue, ...]:
        issues: list[PdfIssue] = []

        scanned_pages = tuple(page.page_number for page in pages if page.appears_scanned)
        mixed_pages = tuple(page.page_number for page in pages if page.appears_mixed)
        no_text_pages = tuple(
            page.page_number
            for page in pages
            if not page.has_native_text and not page.appears_blank
        )
        low_confidence_pages = tuple(
            page.page_number for page in pages if page.is_low_confidence_text
        )
        abnormal_pages = tuple(
            page.page_number for page in pages if page.has_abnormal_text_markers
        )
        table_dense_pages = tuple(page.page_number for page in pages if page.is_table_dense)

        if scanned_pages:
            issues.append(
                _issue(
                    PdfIssueCode.SCANNED_OR_IMAGE_PAGES,
                    IssueSeverity.WARNING,
                    "One or more pages appear scanned or image-based and need OCR or review.",
                    page_numbers=scanned_pages,
                    count=len(scanned_pages),
                )
            )
        if mixed_pages:
            issues.append(
                _issue(
                    PdfIssueCode.MIXED_CONTENT,
                    IssueSeverity.WARNING,
                    "One or more pages combine native text with substantial image content.",
                    page_numbers=mixed_pages,
                    count=len(mixed_pages),
                )
            )
        if no_text_pages:
            issues.append(
                _issue(
                    PdfIssueCode.PAGES_WITHOUT_TEXT,
                    IssueSeverity.WARNING,
                    "One or more non-blank pages do not have enough extractable native text.",
                    page_numbers=no_text_pages,
                    count=len(no_text_pages),
                )
            )
        if low_confidence_pages:
            issues.append(
                _issue(
                    PdfIssueCode.LOW_TEXT_CONFIDENCE,
                    IssueSeverity.WARNING,
                    "One or more pages have low native text extraction confidence.",
                    page_numbers=low_confidence_pages,
                    count=len(low_confidence_pages),
                )
            )
        if abnormal_pages:
            issues.append(
                _issue(
                    PdfIssueCode.ABNORMAL_TEXT_MARKERS,
                    IssueSeverity.WARNING,
                    "Extracted text contains abnormal character markers on one or more pages.",
                    page_numbers=abnormal_pages,
                    count=len(abnormal_pages),
                )
            )
        if table_dense_pages:
            issues.append(
                _issue(
                    PdfIssueCode.TABLE_DENSE_PAGES,
                    IssueSeverity.INFO,
                    "One or more pages appear table-dense and may need citation-quality review.",
                    page_numbers=table_dense_pages,
                    count=len(table_dense_pages),
                )
            )

        return tuple(issues)


def analyze_pdf_upload(
    source: bytes | bytearray | memoryview | str | Path,
    config: PdfAnalysisConfig | None = None,
) -> PdfAnalysisResult:
    """Convenience function for analyzing a PDF upload."""

    return PdfUploadAnalyzer(config=config).analyze(source)


def _issue(
    code: PdfIssueCode,
    severity: IssueSeverity,
    message: str,
    *,
    page_numbers: tuple[int, ...] = (),
    count: int | None = None,
) -> PdfIssue:
    return PdfIssue(
        code=code,
        severity=severity,
        message=message,
        count=len(page_numbers) if count is None else count,
        page_numbers=page_numbers[:ISSUE_PAGE_SAMPLE_LIMIT],
    )


def _load_pymupdf() -> Any:
    try:
        import fitz  # type: ignore[import-not-found]
    except ImportError as exc:
        raise PdfAnalysisError("PyMuPDF is not installed.") from exc
    return fitz


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as pdf_file:
        while True:
            chunk = pdf_file.read(HASH_CHUNK_BYTES)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _bbox_area(bbox: Any) -> float:
    if bbox is None:
        return 0.0

    try:
        x0, y0, x1, y1 = bbox
    except (TypeError, ValueError):
        try:
            x0, y0, x1, y1 = bbox.x0, bbox.y0, bbox.x1, bbox.y1
        except AttributeError:
            return 0.0

    width = max(float(x1) - float(x0), 0.0)
    height = max(float(y1) - float(y0), 0.0)
    return width * height


def _safe_len(callable_value: Any, *, fallback: int) -> int:
    try:
        return len(callable_value() or [])
    except Exception:
        return fallback


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def _round_ratio(value: float) -> float:
    return round(float(value), 4)


def _is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False


def _to_plain_data(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _to_plain_data(item) for key, item in asdict(value).items()}
    if isinstance(value, tuple):
        return [_to_plain_data(item) for item in value]
    if isinstance(value, list):
        return [_to_plain_data(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_plain_data(item) for key, item in value.items()}
    return value
