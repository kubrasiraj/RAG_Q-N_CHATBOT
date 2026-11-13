import logging
from uuid import UUID

from sqlalchemy import update

from app.db.session import SessionLocal
from app.models.document import Document
from app.services.document_processing import (
    DocumentProcessingError,
    process_document,
)


logger = logging.getLogger(__name__)

PROCESSING_FAILED_MESSAGE = "Document processing failed."


def run_document_processing(document_id: UUID, user_id: UUID) -> None:
    """
    Process one uploaded document inside a FastAPI background task.

    The request-scoped database session is closed as soon as the upload
    response is sent, so this function opens and closes its own session.
    Only plain identifiers cross the boundary, never ORM objects.

    The heavy lifting (extraction, chunking, embeddings, persistence and
    the pending -> processing -> completed/failed status updates) stays in
    process_document(), which is reused unchanged. Errors are logged and
    never raised, because nobody is waiting on a background task.
    """

    db = SessionLocal()

    try:
        document = db.get(Document, document_id)

        if document is None:
            logger.warning(
                "Background processing skipped, document not found: %s",
                document_id,
            )
            return

        # The id comes from the record created in the authenticated upload
        # request. This check guarantees it is never processed on behalf of
        # a different owner.
        if document.user_id != user_id:
            logger.error(
                "Background processing refused, owner mismatch: %s",
                document_id,
            )
            return

        # Prevents accidental duplicate processing.
        if document.status != "pending":
            logger.info(
                "Background processing skipped, status is %r: %s",
                document.status,
                document_id,
            )
            return

        process_document(db=db, document_id=document_id)

    except DocumentProcessingError:
        # process_document() already recorded the failure and logged the
        # details. Nothing is exposed to API clients.
        logger.warning(
            "Background processing did not complete: %s",
            document_id,
        )

    except Exception:
        logger.exception(
            "Unexpected error during background processing: %s",
            document_id,
        )
        _mark_failed_if_still_processing(document_id)

    finally:
        db.close()


def _mark_failed_if_still_processing(document_id: UUID) -> None:
    """
    Safety net: if an unexpected error escaped process_document() while the
    document was marked as processing, do not leave it stuck there.

    Uses a fresh session and a conditional UPDATE, so a document that has
    already reached completed or failed is never touched.
    """

    db = SessionLocal()

    try:
        db.execute(
            update(Document)
            .where(
                Document.id == document_id,
                Document.status == "processing",
            )
            .values(
                status="failed",
                error_message=PROCESSING_FAILED_MESSAGE,
            )
        )
        db.commit()

    except Exception:
        db.rollback()
        logger.exception(
            "Could not mark document as failed: %s",
            document_id,
        )

    finally:
        db.close()
