
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk


def search_similar_chunks(
    db: Session,
    user_id: UUID,
    query_embedding: list[float],
    top_k: int = 5,
) -> list[dict]:
    """
    Search relevant document chunks using cosine distance.

    Results are restricted to completed documents belonging
    to the authenticated user.
    """

    if not query_embedding:
        raise ValueError("Query embedding cannot be empty.")

    if top_k < 1 or top_k > 50:
        raise ValueError("top_k must be between 1 and 50.")

    if len(query_embedding) != 384:
        raise ValueError(
            "Query embedding must contain 384 dimensions."
        )

    distance = DocumentChunk.embedding.cosine_distance(
        query_embedding
    ).label("distance")

    statement = (
        select(DocumentChunk, distance)
        .join(
            Document,
            DocumentChunk.document_id == Document.id,
        )
        .where(
            Document.user_id == user_id,
            Document.status == "completed",
        )
        .order_by(distance.asc())
        .limit(top_k)
    )

    results = db.execute(statement).all()

    return [
        {
            "chunk": chunk,
            "similarity": 1.0 - float(distance),
        }
        for chunk, distance in results
    ]
