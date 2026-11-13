
import logging
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.user import User
from app.services.supabase_storage import (
    SupabaseStorageError,
    delete_document as delete_storage_document,
    upload_document as upload_storage_document,
)


logger = logging.getLogger(__name__)


MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": (
        "application/vnd.openxmlformats-officedocument."
        "wordprocessingml.document"
    ),
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
    Upload the document to Supabase and create its database record.

    If the database transaction fails, attempt to remove the uploaded object.
    """

    safe_filename = Path(original_filename).name
    extension = Path(safe_filename).suffix.lower()
    mime_type = MIME_TYPES.get(extension)

    if mime_type is None:
        raise ValueError("Unsupported document extension.")

    if not content:
        raise ValueError("Document content cannot be empty.")

    # The object key is unique and scoped to the owning user.
    object_path = (
        f"users/{user.id}/documents/{uuid4().hex}{extension}"
    )

    # Upload first. Do not create a DB record if storage upload fails.
    upload_storage_document(
        object_path=object_path,
        content=content,
        mime_type=mime_type,
    )

    document = Document(
        user_id=user.id,
        original_filename=safe_filename,
        storage_path=object_path,
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
            delete_storage_document(object_path)
        except Exception:
            # Preserve the original database exception.
            logger.exception(
                "Failed to clean up Supabase object after DB failure: %s",
                object_path,
            )

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
    Delete a document's database record and Supabase object.

    If Supabase cleanup fails, attempt to restore the database record.
    """

    document = get_document_by_id(
        db=db,
        user_id=user_id,
        document_id=document_id,
    )

    object_path = document.storage_path

    try:
        db.delete(document)
        db.commit()

    except Exception:
        db.rollback()
        raise

    try:
        delete_storage_document(object_path)

    except Exception:
        # Restore the DB record so the user can retry deletion.
        db.rollback()

        try:
            db.add(document)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception(
                "Could not restore document DB record after "
                "Supabase deletion failure: %s",
                document_id,
            )

        raise
