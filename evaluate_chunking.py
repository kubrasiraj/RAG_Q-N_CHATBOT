from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.document import Document
from app.services.document_extraction import extract_document
from app.services.text_processing import (
    chunk_document_pages,
    get_tokenizer,
)


SAMPLE_FILENAME = "sample_delivery_shipping_policy.txt"


def main():
    print("=" * 70)
    print("DOCUMENT Q&A RAG — CHUNKING EVALUATION")
    print("=" * 70)

    print("\nChunking configuration:")
    print("Target:", settings.chunk_size_tokens)
    print("Maximum:", settings.max_chunk_size_tokens)
    print("Overlap:", settings.chunk_overlap_tokens)

    with SessionLocal() as db:
        document = db.scalar(
            select(Document).where(
                Document.original_filename == SAMPLE_FILENAME,
                Document.status == "completed",
            )
        )

        if document is None:
            raise RuntimeError("Completed sample document not found.")

        print("\nDocument:", document.original_filename)
        print("Database ID:", document.id)
        print("Storage path:", document.storage_path)

        extraction = extract_document(
            document.storage_path,
            document.mime_type,
        )

        print("\nExtraction:")
        print("File type:", extraction.file_type)
        print("Page count:", extraction.page_count)
        print("Extracted characters:", len(extraction.full_text))

        chunks = chunk_document_pages(extraction.pages)

        tokenizer = get_tokenizer()

        print("\n" + "=" * 70)
        print("GENERATED CHUNKS")
        print("=" * 70)

        total_tokens = 0
        oversized_chunks = []

        for chunk in chunks:
            actual_tokens = len(
                tokenizer.backend_tokenizer.encode(
                    chunk.content
                ).ids
            )

            total_tokens += actual_tokens

            if actual_tokens > settings.max_chunk_size_tokens:
                oversized_chunks.append(chunk.chunk_index)

            print(f"\nChunk #{chunk.chunk_index}")
            print("Page:", chunk.page_number)
            print("Tokens:", actual_tokens)
            print("Characters:", len(chunk.content))
            print("Start:", repr(chunk.content[:180]))
            print("End:", repr(chunk.content[-180:]))

        print("\n" + "=" * 70)
        print("EVALUATION SUMMARY")
        print("=" * 70)

        print("Total chunks:", len(chunks))
        print("Total tokens:", total_tokens)

        if chunks:
            token_counts = [
                len(tokenizer.backend_tokenizer.encode(c.content).ids)
                for c in chunks
            ]

            print("Smallest chunk:", min(token_counts))
            print("Largest chunk:", max(token_counts))
            print(
                "Average chunk size:",
                round(sum(token_counts) / len(token_counts), 2),
            )

        print("Oversized chunks:", oversized_chunks)

        print("\nDatabase was NOT modified.")
        print("Evaluation completed.")


if __name__ == "__main__":
    main()