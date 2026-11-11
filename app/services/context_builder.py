from typing import Any


def build_retrieval_context(
    search_results: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    """
    Build LLM context and source metadata from retrieved chunks.

    Source IDs are generated for this request only.
    """

    context_parts: list[str] = []
    sources: list[dict[str, Any]] = []

    for index, result in enumerate(search_results, start=1):
        chunk = result["chunk"]
        document = chunk.document

        source_id = f"S{index}"

        source = {
            "source_id": source_id,
            "document_id": document.id,
            "filename": document.original_filename,
            "page_number": chunk.page_number,
            "chunk_index": chunk.chunk_index,
            "similarity": round(
                float(result["similarity"]),
                4,
            ),
            "excerpt": chunk.content[:500],
        }

        sources.append(source)

        context_parts.append(
            f"""
[SOURCE {source_id}]
Document: {document.original_filename}
Page: {chunk.page_number if chunk.page_number is not None else "Not available"}
Chunk: {chunk.chunk_index}

Content:
{chunk.content}
[/SOURCE {source_id}]
""".strip()
        )

    return "\n\n".join(context_parts), sources