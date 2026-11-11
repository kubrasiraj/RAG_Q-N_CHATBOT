
import logging
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.document import (
    DocumentListResponse,
    DocumentResponse,
)
from app.services.document_service import (
    DocumentNotFoundError,
    create_document,
    delete_user_document,
    get_document_by_id,
    get_user_documents,
)
from app.services.file_validation import validate_document_upload


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a PDF, DOCX, or TXT document.

    The authenticated user automatically becomes the document owner.
    """

    content = await validate_document_upload(file)

    try:
        document = create_document(
            db=db,
            user=current_user,
            original_filename=file.filename,
            content=content,
        )

        return document

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except OSError as exc:
        logger.exception("Document storage operation failed.")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save the uploaded document.",
        ) from exc


@router.get(
    "/",
    response_model=DocumentListResponse,
)
def list_documents(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List documents belonging to the authenticated user."""

    documents, total = get_user_documents(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )

    return DocumentListResponse(
        items=documents,
        total=total,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
)
def retrieve_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve one document belonging to the authenticated user."""

    try:
        return get_document_by_id(
            db=db,
            user_id=current_user.id,
            document_id=document_id,
        )

    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        ) from exc


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document belonging to the authenticated user."""

    try:
        delete_user_document(
            db=db,
            user_id=current_user.id,
            document_id=document_id,
        )

    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found.",
        ) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
