
import pymupdf
import pytest

from docx import Document as WordDocument

from app.services.document_extraction import (
    DocumentExtractionError,
    extract_document,
)


PDF_MIME = "application/pdf"

DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument."
    "wordprocessingml.document"
)

TXT_MIME = "text/plain"


def create_pdf(path, text="Delivery policy document"):
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), text)
    pdf.save(path)
    pdf.close()


def create_docx(path):
    document = WordDocument()

    document.add_paragraph("Delivery policy")

    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Shipping"
    table.rows[0].cells[1].text = "Free"

    document.save(path)


def test_extract_pdf_success(tmp_path):
    path = tmp_path / "sample.pdf"
    create_pdf(path)

    result = extract_document(path, PDF_MIME)

    assert result.file_type == "pdf"
    assert result.page_count == 1
    assert result.pages[0].page_number == 1
    assert "Delivery policy document" in result.full_text
    assert result.requires_ocr is False


def test_extract_docx_success(tmp_path):
    path = tmp_path / "sample.docx"
    create_docx(path)

    result = extract_document(path, DOCX_MIME)

    assert result.file_type == "docx"
    assert result.pages[0].page_number is None
    assert "Delivery policy" in result.full_text
    assert "Shipping | Free" in result.full_text


def test_extract_txt_success(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_text(
        "Delivery policy\nShipping takes 3 days.",
        encoding="utf-8",
    )

    result = extract_document(path, TXT_MIME)

    assert result.file_type == "txt"
    assert "Delivery policy" in result.full_text
    assert "Shipping takes 3 days." in result.full_text


def test_extract_pdf_preserves_page_numbers(tmp_path):
    path = tmp_path / "multi_page.pdf"

    pdf = pymupdf.open()

    for number in range(1, 4):
        page = pdf.new_page()
        page.insert_text((72, 72), f"Page content {number}")

    pdf.save(path)
    pdf.close()

    result = extract_document(path, PDF_MIME)

    assert result.page_count == 3
    assert [
        page.page_number for page in result.pages
    ] == [1, 2, 3]


def test_extract_scanned_pdf_is_rejected(tmp_path):
    path = tmp_path / "scanned.pdf"

    # Create a PDF page containing an image but no selectable text.
    image = pymupdf.Pixmap(
        pymupdf.csRGB,
        pymupdf.IRect(0, 0, 100, 100),
        0,
    )
    image.clear_with(255)

    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_image(
        pymupdf.Rect(50, 50, 150, 150),
        pixmap=image,
    )
    pdf.save(path)
    pdf.close()

    with pytest.raises(
        DocumentExtractionError,
        match="Scanned PDFs are not supported",
    ):
        extract_document(path, PDF_MIME)

def test_extract_empty_txt_fails(tmp_path):
    path = tmp_path / "empty.txt"
    path.write_text("", encoding="utf-8")

    with pytest.raises(DocumentExtractionError):
        extract_document(path, TXT_MIME)


def test_extract_missing_file_fails(tmp_path):
    path = tmp_path / "missing.pdf"

    with pytest.raises(DocumentExtractionError):
        extract_document(path, PDF_MIME)


def test_extract_mismatched_mime_type_fails(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_text("Some text", encoding="utf-8")

    with pytest.raises(DocumentExtractionError):
        extract_document(path, PDF_MIME)


def test_extract_unsupported_extension_fails(tmp_path):
    path = tmp_path / "sample.exe"
    path.write_bytes(b"some content")

    with pytest.raises(DocumentExtractionError):
        extract_document(path, "application/octet-stream")
