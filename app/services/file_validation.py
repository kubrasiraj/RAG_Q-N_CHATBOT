
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile


import pymupdf
from docx import Document as WordDocument
from docx.opc.exceptions import PackageNotFoundError
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


CHUNK_SIZE = 1024 * 1024

DOCX_REQUIRED_FILES = {
    "[Content_Types].xml",
    "word/document.xml",
}


async def validate_document_upload(file: UploadFile) -> bytes:
    """
    Validate PDF, DOCX, or TXT uploads.

    Returns validated file content as bytes.
    """

    # 1. Validate filename and extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required.",
        )

    extension = Path(file.filename).suffix.lower()

    if extension not in settings.allowed_document_extensions:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Supported formats are PDF, DOCX, and TXT.",
        )

    # 2. Read file with size limit
    max_size = settings.max_document_size_mb * 1024 * 1024

    chunks = []
    total_size = 0

    try:
        while True:
            chunk = await file.read(CHUNK_SIZE)

            if not chunk:
                break

            total_size += len(chunk)

            if total_size > max_size:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail=(
                        f"File size cannot exceed "
                        f"{settings.max_document_size_mb} MB."
                    ),
                )

            chunks.append(chunk)

    finally:
        await file.seek(0)

    # 3. Reject empty files
    if total_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    content = b"".join(chunks)

    # 4. Validate according to actual file format
    if extension == ".pdf":
        _validate_pdf(content)

    elif extension == ".docx":
        _validate_docx(content)

    elif extension == ".txt":
        _validate_txt(content)

    return content


def _validate_pdf(content: bytes) -> None:
    try:
        with pymupdf.open(stream=content, filetype="pdf") as pdf:

            if pdf.needs_pass:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Password-protected PDFs are not supported.",
                )

            if pdf.page_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="PDF must contain at least one page.",
                )

    except HTTPException:
        raise

    except (pymupdf.FileDataError, RuntimeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or corrupted PDF file.",
        )


def _validate_docx(content: bytes) -> None:
    try:
        with ZipFile(BytesIO(content)) as archive:

            files = set(archive.namelist())

            if not DOCX_REQUIRED_FILES.issubset(files):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid DOCX document structure.",
                )

            # Basic protection against excessively large extracted content
            uncompressed_size = sum(
                item.file_size for item in archive.infolist()
            )

            if uncompressed_size > 100 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="DOCX document contains excessive compressed content.",
                )

        # Verify that python-docx can actually parse the document
        WordDocument(BytesIO(content))

    except HTTPException:
        raise

    except (
        BadZipFile,
        PackageNotFoundError,
        KeyError,
        ValueError,
        OSError,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or corrupted DOCX file.",
        )


def _validate_txt(content: bytes) -> None:
    try:
        content.decode("utf-8-sig")

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TXT files must use UTF-8 encoding.",
        )
