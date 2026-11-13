
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.document_extraction import extract_document
from app.services.embedding_service import embed_texts
from app.services.supabase_storage import download_document
from app.services.text_processing import chunk_document_pages


logger = logging.getLogger(__name__)


class DocumentProcessingError(Exception):
    """Raised when document processing fails."""


def process_document(
    db: Session,
    document_id: UUID,
) -> Document:
    """
    Complete document processing pipeline:

    1. Load document metadata from Neon PostgreSQL.
    2. Mark it as processing.
    3. Download document bytes from Supabase Storage.
    4. Extract text from PDF, DOCX, or TXT.
    5. Generate normalized token-aware chunks.
    6. Generate embeddings.
    7. Save chunks and embeddings in PostgreSQL.
    8. Mark document as completed.
    """

    document = db.get(Document, document_id)

    if document is None:
        raise DocumentProcessingError("Document not found.")

    if document.status == "processing":
        raise DocumentProcessingError(
            "Document is already being processed."
        )

    document.status = "processing"
    document.error_message = None

    try:
        db.commit()

        # Stage 1: Download original file from persistent storage.
        file_content = download_document(
            document.storage_path
        )

        # Stage 2: Extract text directly from downloaded bytes.
        extraction = extract_document(
            file_path=file_content,
            mime_type=document.mime_type,
        )

        # Stage 3: Cleaning and token-aware chunking.
        chunks = chunk_document_pages(extraction.pages)

        if not chunks:
            raise DocumentProcessingError(
                "No usable text chunks were generated."
            )

        # Stage 4: Embedding generation.
        embeddings = embed_texts(
            [chunk.content for chunk in chunks]
        )

        if len(embeddings) != len(chunks):
            raise DocumentProcessingError(
                "Embedding count does not match chunk count."
            )

        # Stage 5: Replace previous chunks in the same transaction.
        db.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == document.id
            )
        )

        chunk_records = [
            DocumentChunk(
                document_id=document.id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                page_number=chunk.page_number,
                embedding=embedding,
            )
            for chunk, embedding in zip(chunks, embeddings)
        ]

        db.add_all(chunk_records)

        # Stage 6: Update document processing information.
        document.page_count = extraction.page_count
        document.status = "completed"
        document.processed_at = datetime.now(timezone.utc)
        document.error_message = None

        db.commit()
        db.refresh(document)

        logger.info(
            "Document processed successfully: %s, chunks=%s",
            document.id,
            len(chunks),
        )

        return document

    except Exception as exc:
        db.rollback()

        # Mark processing as failed without exposing internal errors.
        failed_document = db.get(Document, document_id)

        if failed_document is not None:
            failed_document.status = "failed"
            failed_document.error_message = (
                "Document processing failed."
            )

            try:
                db.commit()
            except Exception:
                db.rollback()
                logger.exception(
                    "Could not update failed document status: %s",
                    document_id,
                )

        logger.exception(
            "Document processing failed: %s",
            document_id,
        )

        if isinstance(exc, DocumentProcessingError):
            raise

        raise DocumentProcessingError(
            "Unable to process document."
        ) from exc
