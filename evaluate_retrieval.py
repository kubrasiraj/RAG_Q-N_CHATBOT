
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.embedding_service import embed_query


DOCUMENT_FILENAME = "sample_delivery_shipping_policy.txt"
TOP_K = 3
EMBEDDING_DIMENSIONS = 384


EVALUATION_CASES = [
    # Positive evaluation cases
    {
        "question": "How long does delivery take in Karachi?",
        "relevant_chunks": {0},
        "answerable": True,
    },
    {
        "question": "How much time does order processing require?",
        "relevant_chunks": {0},
        "answerable": True,
    },
    {
        "question": "What can cause delivery delays?",
        "relevant_chunks": {0, 1},
        "answerable": True,
    },
    {
        "question": "Does the store provide free shipping?",
        "relevant_chunks": {1, 2},
        "answerable": True,
    },
    {
        "question": "How many delivery attempts are allowed?",
        "relevant_chunks": {1, 2},
        "answerable": True,
    },
    {
        "question": "How can customers track their orders?",
        "relevant_chunks": {0},
        "answerable": True,
    },
    {
        "question": "What privacy precautions should customers follow?",
        "relevant_chunks": {1, 2},
        "answerable": True,
    },
    {
        "question": "Which information is not covered by this policy?",
        "relevant_chunks": {2},
        "answerable": True,
    },
    {
        "question": "What happens when an address is incomplete?",
        "relevant_chunks": {1},
        "answerable": True,
    },
    {
        "question": "Does the policy guarantee a delivery date?",
        "relevant_chunks": {0, 2},
        "answerable": True,
    },

    # Negative evaluation cases
    {
        "question": "What is the product warranty period?",
        "relevant_chunks": set(),
        "answerable": False,
    },
    {
        "question": "Which payment methods does the store accept?",
        "relevant_chunks": set(),
        "answerable": False,
    },
    {
        "question": "Where is the store's physical branch located?",
        "relevant_chunks": set(),
        "answerable": False,
    },
    {
        "question": "What are the customer support working hours?",
        "relevant_chunks": set(),
        "answerable": False,
    },
    {
        "question": "Which courier company delivers the orders?",
        "relevant_chunks": set(),
        "answerable": False,
    },
]


def get_document(db) -> Document:
    statement = (
        select(Document)
        .where(
            Document.original_filename == DOCUMENT_FILENAME,
            Document.status == "completed",
        )
        .order_by(Document.created_at.desc())
    )

    document = db.execute(statement).scalars().first()

    if document is None:
        raise RuntimeError(
            f"Completed document not found: {DOCUMENT_FILENAME}"
        )

    return document


def retrieve_chunks(
    db,
    document_id,
    query_embedding: list[float],
    top_k: int = TOP_K,
) -> list[dict]:
    if len(query_embedding) != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Query embedding must contain "
            f"{EMBEDDING_DIMENSIONS} dimensions."
        )

    distance = DocumentChunk.embedding.cosine_distance(
        query_embedding
    ).label("distance")

    statement = (
        select(DocumentChunk, distance)
        .where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.embedding.is_not(None),
        )
        .order_by(distance.asc())
        .limit(top_k)
    )

    rows = db.execute(statement).all()

    return [
        {
            "chunk": chunk,
            "similarity": 1.0 - float(distance_value),
        }
        for chunk, distance_value in rows
    ]


def evaluate_case(db, document, case: dict) -> dict:
    question = case["question"]
    relevant_chunks = case["relevant_chunks"]
    answerable = case["answerable"]

    query_embedding = embed_query(question)

    results = retrieve_chunks(
        db=db,
        document_id=document.id,
        query_embedding=query_embedding,
        top_k=TOP_K,
    )

    retrieved_indexes = [
        result["chunk"].chunk_index
        for result in results
    ]

    relevant_ranks = [
        rank
        for rank, result in enumerate(results, start=1)
        if result["chunk"].chunk_index in relevant_chunks
    ]

    max_similarity = (
        max(result["similarity"] for result in results)
        if results
        else None
    )

    if answerable:
        hit_at_1 = int(
            bool(relevant_ranks) and relevant_ranks[0] == 1
        )

        hit_at_k = int(bool(relevant_ranks))

        retrieved_relevant = {
            result["chunk"].chunk_index
            for result in results
            if result["chunk"].chunk_index in relevant_chunks
        }

        recall_at_k = (
            len(retrieved_relevant) / len(relevant_chunks)
        )

        reciprocal_rank = (
            1.0 / relevant_ranks[0]
            if relevant_ranks
            else 0.0
        )

        negative_retrieval = None

    else:
        hit_at_1 = None
        hit_at_k = None
        recall_at_k = None
        reciprocal_rank = None

        # Vector search returns candidates even for
        # questions whose answers are absent from the document.
        negative_retrieval = bool(results)

    return {
        "question": question,
        "answerable": answerable,
        "expected": sorted(relevant_chunks),
        "retrieved": retrieved_indexes,
        "max_similarity": max_similarity,
        "hit_at_1": hit_at_1,
        "hit_at_k": hit_at_k,
        "recall_at_k": recall_at_k,
        "mrr": reciprocal_rank,
        "negative_retrieval": negative_retrieval,
        "results": results,
    }


def print_report(index: int, report: dict) -> None:
    print("\n" + "-" * 80)
    print(f"Q{index:02d}: {report['question']}")
    print(f"Answerable: {report['answerable']}")
    print(f"Expected chunks: {report['expected']}")
    print(f"Retrieved chunks: {report['retrieved']}")

    if report["max_similarity"] is not None:
        print(
            f"Maximum similarity: "
            f"{report['max_similarity']:.4f}"
        )
    else:
        print("Maximum similarity: No results")

    for rank, result in enumerate(
        report["results"],
        start=1,
    ):
        chunk = result["chunk"]

        print(
            f"Rank {rank}: "
            f"Chunk {chunk.chunk_index} | "
            f"Similarity: {result['similarity']:.4f}"
        )

    if report["answerable"]:
        print(f"Hit@1: {report['hit_at_1']}")
        print(f"Hit@{TOP_K}: {report['hit_at_k']}")
        print(f"Recall@{TOP_K}: {report['recall_at_k']:.4f}")
        print(f"MRR: {report['mrr']:.4f}")

    else:
        print(
            "Negative retrieval:",
            "CHUNKS RETRIEVED"
            if report["negative_retrieval"]
            else "NO RESULTS",
        )


def print_metrics(reports: list[dict]) -> None:
    positive_reports = [
        report
        for report in reports
        if report["answerable"]
    ]

    negative_reports = [
        report
        for report in reports
        if not report["answerable"]
    ]

    total_positive = len(positive_reports)
    total_negative = len(negative_reports)

    print("\n" + "=" * 80)
    print("FINAL RETRIEVAL EVALUATION")
    print("=" * 80)

    if total_positive:
        hit_rate_at_1 = (
            sum(r["hit_at_1"] for r in positive_reports)
            / total_positive
        )

        hit_rate_at_k = (
            sum(r["hit_at_k"] for r in positive_reports)
            / total_positive
        )

        mean_recall_at_k = (
            sum(r["recall_at_k"] for r in positive_reports)
            / total_positive
        )

        mrr = (
            sum(r["mrr"] for r in positive_reports)
            / total_positive
        )

        print(f"Positive cases: {total_positive}")
        print(f"Hit Rate@1: {hit_rate_at_1:.2%}")
        print(f"Hit Rate@{TOP_K}: {hit_rate_at_k:.2%}")
        print(f"Mean Recall@{TOP_K}: {mean_recall_at_k:.2%}")
        print(f"MRR: {mrr:.4f}")

    if total_negative:
        negative_retrieval_rate = (
            sum(
                int(r["negative_retrieval"])
                for r in negative_reports
            )
            / total_negative
        )

        print(f"\nNegative cases: {total_negative}")
        print(
            "Cases with retrieved chunks: "
            f"{negative_retrieval_rate:.2%}"
        )

        print("\nNegative question similarity scores:")

        for report in negative_reports:
            score = report["max_similarity"]

            print(
                f"- {report['question']}: "
                f"{score:.4f}" if score is not None
                else f"- {report['question']}: No results"
            )

    print("=" * 80)


def main() -> None:
    db = SessionLocal()

    try:
        document = get_document(db)

        chunk_statement = (
            select(DocumentChunk)
            .where(
                DocumentChunk.document_id == document.id,
                DocumentChunk.embedding.is_not(None),
            )
            .order_by(DocumentChunk.chunk_index.asc())
        )

        stored_chunks = (
            db.execute(chunk_statement).scalars().all()
        )

        if not stored_chunks:
            raise RuntimeError(
                "Document has no stored chunks with embeddings."
            )

        available_indexes = {
            chunk.chunk_index
            for chunk in stored_chunks
        }

        for case in EVALUATION_CASES:
            missing = (
                case["relevant_chunks"] - available_indexes
            )

            if missing:
                raise RuntimeError(
                    f"Expected chunks {missing} do not exist "
                    "in the selected document."
                )

        print("=" * 80)
        print("DOCUMENT Q&A RAG - RETRIEVAL EVALUATION")
        print("=" * 80)
        print(f"Document: {document.original_filename}")
        print(f"Document ID: {document.id}")
        print(f"Stored chunks: {len(stored_chunks)}")
        print(f"Positive cases: {sum(c['answerable'] for c in EVALUATION_CASES)}")
        print(f"Negative cases: {sum(not c['answerable'] for c in EVALUATION_CASES)}")
        print(f"Top K: {TOP_K}")

        reports = []

        for index, case in enumerate(
            EVALUATION_CASES,
            start=1,
        ):
            report = evaluate_case(
                db=db,
                document=document,
                case=case,
            )

            reports.append(report)

            print_report(index, report)

        print_metrics(reports)

        print("\nEvaluation completed.")
        print("Database was NOT modified.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
