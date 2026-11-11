
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


DocumentStatus = Literal[
    "pending",
    "processing",
    "completed",
    "failed",
]


class DocumentResponse(BaseModel):
    """Response schema for a single document."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: str
    mime_type: str
    file_size_bytes: int
    status: DocumentStatus
    page_count: int | None = None
    created_at: datetime
    updated_at: datetime
    processed_at: datetime | None = None


class DocumentListResponse(BaseModel):
    """Response schema for a collection of documents."""

    items: list[DocumentResponse]
    total: int
