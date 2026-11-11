
from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import settings


QUERY_INSTRUCTION = (
    "Represent this sentence for searching relevant passages: "
)


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """
    Load the embedding model once per application process.
    """

    return SentenceTransformer(settings.embedding_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate normalized embeddings for document chunks."""

    if not texts:
        return []

    model = get_embedding_model()

    embeddings = model.encode(
        texts,
        batch_size=settings.embedding_batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    if embeddings.shape[1] != settings.embedding_dimensions:
        raise ValueError(
            "Embedding dimensions do not match database configuration."
        )

    return embeddings.tolist()


def embed_query(query: str) -> list[float]:
    """Generate a query embedding for semantic retrieval."""

    cleaned_query = query.strip()

    if not cleaned_query:
        raise ValueError("Query cannot be empty.")

    query_text = QUERY_INSTRUCTION + cleaned_query

    embeddings = embed_texts([query_text])

    return embeddings[0]
