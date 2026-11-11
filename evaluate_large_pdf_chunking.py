
from collections import Counter
from pathlib import Path

from app.core.config import settings
from app.services.document_extraction import extract_document
from app.services.text_processing import chunk_document_pages


PDF_PATH = Path(
    "test_data/large_test_document_100_pages.pdf"
)


def main():
    if not PDF_PATH.exists():
        raise FileNotFoundError(PDF_PATH)

    extraction = extract_document(
        PDF_PATH,
        "application/pdf",
    )

    chunks = chunk_document_pages(extraction.pages)

    if not chunks:
        raise RuntimeError("No chunks were generated.")

    page_distribution = Counter(
        chunk.page_number for chunk in chunks
    )

    invalid_pages = [
        chunk.page_number
        for chunk in chunks
        if chunk.page_number is None
        or not 1 <= chunk.page_number <= extraction.page_count
    ]

    oversized_chunks = [
        chunk
        for chunk in chunks
        if chunk.token_count > settings.max_chunk_size_tokens
    ]

    pages_without_chunks = [
        page_number
        for page_number in range(1, extraction.page_count + 1)
        if page_distribution[page_number] == 0
    ]

    print("=" * 70)
    print("LARGE PDF — CHUNKING EVALUATION")
    print("=" * 70)

    print(f"PDF pages: {extraction.page_count}")
    print(f"Generated chunks: {len(chunks)}")
    print(f"Target tokens: {settings.chunk_size_tokens}")
    print(f"Maximum tokens: {settings.max_chunk_size_tokens}")
    print(f"Overlap tokens: {settings.chunk_overlap_tokens}")

    print("\nPAGE DISTRIBUTION")
    print("-" * 70)

    for page_number in range(1, extraction.page_count + 1):
        print(
            f"Page {page_number:02d}: "
            f"{page_distribution[page_number]} chunks"
        )

    print("\nCHUNK DETAILS")
    print("-" * 70)

    for chunk in chunks:
        print(
            f"Chunk #{chunk.chunk_index} | "
            f"Page: {chunk.page_number} | "
            f"Tokens: {chunk.token_count} | "
            f"Characters: {len(chunk.content)}"
        )

    token_counts = [chunk.token_count for chunk in chunks]

    print("\nEVALUATION SUMMARY")
    print("-" * 70)
    print(f"Smallest chunk: {min(token_counts)}")
    print(f"Largest chunk: {max(token_counts)}")
    print(
        f"Average chunk size: "
        f"{sum(token_counts) / len(token_counts):.1f}"
    )
    print(f"Invalid page references: {len(invalid_pages)}")
    print(f"Oversized chunks: {len(oversized_chunks)}")
    print(f"Pages without chunks: {pages_without_chunks}")

    assert not invalid_pages, "Invalid page numbers detected."
    assert not oversized_chunks, "Maximum token limit exceeded."
    assert not pages_without_chunks, "Some PDF pages were not chunked."

    print("\nRESULT: ALL CHUNKING CHECKS PASSED")
    print("Database was NOT modified.")


if __name__ == "__main__":
    main()
