
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.user import User
from app.services.file_storage import delete_document, save_document


MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}


class DocumentNotFoundError(Exception):
    """Raised when a document does not exist or is not accessible."""


def create_document(
    db: Session,
    user: User,
    original_filename: str,
    content: bytes,
) -> Document:
    """
    Save the uploaded file and create its database record.

    If the database transaction fails, remove the saved file.
    """

    extension = Path(original_filename).suffix.lower()
    mime_type = MIME_TYPES.get(extension)

    if mime_type is None:
        raise ValueError("Unsupported document extension.")

    storage_path = save_document(
        content=content,
        original_filename=original_filename,
    )

    document = Document(
        user_id=user.id,
        original_filename=Path(original_filename).name,
        storage_path=str(storage_path),
        mime_type=mime_type,
        file_size_bytes=len(content),
        status="pending",
    )

    try:
        db.add(document)
        db.commit()
        db.refresh(document)

    except Exception:
        db.rollback()

        try:
            delete_document(storage_path)
        except OSError:
            # Preserve the original database exception.
            pass

        raise

    return document


def get_document_by_id(
    db: Session,
    user_id: UUID,
    document_id: UUID,
) -> Document:
    """Retrieve a document belonging to the authenticated user."""

    statement = select(Document).where(
        Document.id == document_id,
        Document.user_id == user_id,
    )

    document = db.scalar(statement)

    if document is None:
        raise DocumentNotFoundError("Document not found.")

    return document


def get_user_documents(
    db: Session,
    user_id: UUID,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Document], int]:
    """Return paginated documents belonging to one user."""

    count_statement = (
        select(func.count())
        .select_from(Document)
        .where(Document.user_id == user_id)
    )

    total = db.scalar(count_statement) or 0

    documents_statement = (
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    documents = list(db.scalars(documents_statement).all())

    return documents, total


def delete_user_document(
    db: Session,
    user_id: UUID,
    document_id: UUID,
) -> None:
    """
    Delete a document's database record and physical file.

    The physical file is removed only after the database transaction
    succeeds. If file deletion fails, the record is restored where
    possible so the document can be retried.
    """

    document = get_document_by_id(
        db=db,
        user_id=user_id,
        document_id=document_id,
    )

    storage_path = document.storage_path

    try:
        db.delete(document)
        db.commit()

    except Exception:
        db.rollback()
        raise

    try:
        delete_document(storage_path)

    except Exception:
        # Restore the database record if physical cleanup fails.
        db.rollback()

        try:
            db.add(document)
            db.commit()
        except Exception:
            db.rollback()

        raise
