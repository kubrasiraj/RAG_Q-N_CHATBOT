
import asyncio
from io import BytesIO

import pymupdf
import pytest
from docx import Document as WordDocument
from fastapi import HTTPException
from starlette.datastructures import UploadFile

from app.core.config import settings
from app.services.file_validation import validate_document_upload


def create_pdf() -> bytes:
    pdf =pymupdf.open()
    pdf.new_page()
    content = pdf.tobytes()
    pdf.close()
    return content


def create_docx() -> bytes:
    document = WordDocument()
    document.add_paragraph("Document Q&A RAG test document")

    buffer = BytesIO()
    document.save(buffer)

    return buffer.getvalue()


def upload_file(filename: str, content: bytes) -> UploadFile:
    return UploadFile(
        filename=filename,
        file=BytesIO(content),
    )


@pytest.mark.parametrize(
    "filename,content",
    [
        ("sample.pdf", create_pdf()),
        ("sample.docx", create_docx()),
        ("sample.txt", b"Hello, this is a test document."),
    ],
)
def test_valid_document_upload(filename, content):
    file = upload_file(filename, content)

    result = asyncio.run(validate_document_upload(file))

    assert result == content


def test_reject_unsupported_extension():
    file = upload_file("sample.exe", b"some content")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(validate_document_upload(file))

    assert exc.value.status_code == 415


def test_reject_invalid_pdf():
    file = upload_file("sample.pdf", b"This is not a PDF")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(validate_document_upload(file))

    assert exc.value.status_code == 400


def test_reject_invalid_docx():
    file = upload_file("sample.docx", b"This is not a DOCX")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(validate_document_upload(file))

    assert exc.value.status_code == 400


def test_reject_invalid_txt_encoding():
    file = upload_file("sample.txt", b"\xff\xfe\xfa")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(validate_document_upload(file))

    assert exc.value.status_code == 400


def test_reject_empty_file():
    file = upload_file("empty.txt", b"")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(validate_document_upload(file))

    assert exc.value.status_code == 400


def test_reject_oversized_file(monkeypatch):
    monkeypatch.setattr(settings, "max_document_size_mb", 1)

    content = b"a" * (1024 * 1024 + 1)
    file = upload_file("large.txt", content)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(validate_document_upload(file))

    assert exc.value.status_code == 413
