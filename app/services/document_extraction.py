
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile

import pymupdf
from docx import Document as WordDocument
from docx.opc.exceptions import PackageNotFoundError
from docx.table import Table
from docx.text.paragraph import Paragraph


MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": (
        "application/vnd.openxmlformats-officedocument."
        "wordprocessingml.document"
    ),
    ".txt": "text/plain",
}

MIME_TO_EXTENSION = {
    mime_type: extension
    for extension, mime_type in MIME_TYPES.items()
}


class DocumentExtractionError(Exception):
    """Raised when document text extraction fails."""


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int | None
    content: str


@dataclass(frozen=True)
class ExtractionResult:
    file_type: str
    pages: list[ExtractedPage]
    page_count: int | None
    ocr_page_numbers: list[int]

    @property
    def full_text(self) -> str:
        return "\n\n".join(
            page.content
            for page in self.pages
            if page.content.strip()
        )

    @property
    def requires_ocr(self) -> bool:
        return bool(self.ocr_page_numbers)


def extract_document(
    file_path: str | Path | bytes,
    mime_type: str,
) -> ExtractionResult:
    """
    Extract text from a supported document.

    Accepts either:
    - A local filesystem path (backward compatibility).
    - Document bytes downloaded from Supabase Storage.
    """

    if mime_type not in MIME_TO_EXTENSION:
        raise DocumentExtractionError(
            "Unsupported document format."
        )

    if isinstance(file_path, bytes):
        if not file_path:
            raise DocumentExtractionError(
                "Document content is empty."
            )

        extension = MIME_TO_EXTENSION[mime_type]
        source: Path | bytes = file_path

    else:
        path = Path(file_path)

        if not path.exists() or not path.is_file():
            raise DocumentExtractionError(
                "Document file does not exist."
            )

        extension = path.suffix.lower()

        if MIME_TYPES.get(extension) != mime_type:
            raise DocumentExtractionError(
                "Document extension and MIME type do not match."
            )

        source = path

    if MIME_TYPES.get(extension) != mime_type:
        raise DocumentExtractionError(
            "Document extension and MIME type do not match."
        )

    if mime_type == "application/pdf":
        return _extract_pdf(source)

    if mime_type == (
        "application/vnd.openxmlformats-officedocument."
        "wordprocessingml.document"
    ):
        return _extract_docx(source)

    if mime_type == "text/plain":
        return _extract_txt(source)

    raise DocumentExtractionError(
        "Unsupported document format."
    )


def _extract_pdf(source: Path | bytes) -> ExtractionResult:
    """Extract text from a text-based PDF."""

    pages = []

    try:
        if isinstance(source, bytes):
            pdf = pymupdf.open(
                stream=source,
                filetype="pdf",
            )
        else:
            pdf = pymupdf.open(source)

        with pdf:
            if pdf.needs_pass:
                raise DocumentExtractionError(
                    "Password-protected PDFs are not supported."
                )

            if pdf.page_count == 0:
                raise DocumentExtractionError(
                    "PDF contains no pages."
                )

            page_count = pdf.page_count

            for index, page in enumerate(pdf):
                text = page.get_text("text").strip()

                pages.append(
                    ExtractedPage(
                        page_number=index + 1,
                        content=text,
                    )
                )

    except DocumentExtractionError:
        raise

    except (
        pymupdf.FileDataError,
        RuntimeError,
        ValueError,
        OSError,
    ) as exc:
        raise DocumentExtractionError(
            "Unable to extract text from PDF."
        ) from exc

    if not any(page.content for page in pages):
        raise DocumentExtractionError(
            "PDF contains no extractable text. Scanned PDFs are not supported."
        )

    return ExtractionResult(
        file_type="pdf",
        pages=pages,
        page_count=page_count,
        ocr_page_numbers=[],
    )


def _extract_docx(source: Path | bytes) -> ExtractionResult:
    """Extract paragraphs and tables from DOCX documents."""

    content_blocks = []

    try:
        if isinstance(source, bytes):
            document = WordDocument(BytesIO(source))
        else:
            document = WordDocument(str(source))

        # Preserve paragraph and table order.
        for block in document.iter_inner_content():

            if isinstance(block, Paragraph):
                text = block.text.strip()

                if text:
                    content_blocks.append(text)

            elif isinstance(block, Table):
                for row in block.rows:
                    cells = [
                        cell.text.strip()
                        for cell in row.cells
                    ]

                    row_text = " | ".join(
                        cell for cell in cells if cell
                    )

                    if row_text:
                        content_blocks.append(row_text)

    except (
        BadZipFile,
        PackageNotFoundError,
        KeyError,
        ValueError,
        OSError,
    ) as exc:
        raise DocumentExtractionError(
            "Unable to extract text from DOCX."
        ) from exc

    full_text = "\n\n".join(content_blocks).strip()

    if not full_text:
        raise DocumentExtractionError(
            "DOCX contains no extractable text."
        )

    return ExtractionResult(
        file_type="docx",
        pages=[
            ExtractedPage(
                page_number=None,
                content=full_text,
            )
        ],
        page_count=None,
        ocr_page_numbers=[],
    )


def _extract_txt(source: Path | bytes) -> ExtractionResult:
    """Extract UTF-8 text from TXT documents."""

    try:
        if isinstance(source, bytes):
            content = source.decode("utf-8-sig").strip()
        else:
            content = source.read_text(
                encoding="utf-8-sig"
            ).strip()

    except (UnicodeDecodeError, OSError) as exc:
        raise DocumentExtractionError(
            "Unable to read TXT document as UTF-8."
        ) from exc

    if not content:
        raise DocumentExtractionError(
            "TXT document contains no extractable text."
        )

    return ExtractionResult(
        file_type="txt",
        pages=[
            ExtractedPage(
                page_number=None,
                content=content,
            )
        ],
        page_count=None,
        ocr_page_numbers=[],
    )
