
import json
from pathlib import Path

from groq import RateLimitError
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.document import Document
from app.services.qa_service import ask_question


DOCUMENT_FILENAME = "sample_delivery_shipping_policy.txt"
TOP_K = 5

RESULTS_DIR = Path("evaluation_results")
RESULTS_FILE = RESULTS_DIR / "citation_evaluation.jsonl"


# Each answer check is a group of acceptable phrases.
# At least one phrase from every group must appear in the answer.
EVALUATION_CASES = [
    {
        "id": "Q01",
        "question": "How long does delivery take in other major cities?",
        "answerable": True,
        "expected_chunks": {0},
        "answer_checks": [
            ["3 to 6 business days", "3-6 business days"],
        ],
    },
    {
        "id": "Q02",
        "question": "What is the estimated delivery time for remote areas?",
        "answerable": True,
        "expected_chunks": {0},
        "answer_checks": [
            ["5 to 8 business days", "5-8 business days"],
        ],
    },
    {
        "id": "Q03",
        "question": "Are the delivery estimates guaranteed?",
        "answerable": True,
        "expected_chunks": {0},
        "answer_checks": [
            ["not guaranteed", "estimate only", "not a guaranteed"],
        ],
    },
    {
        "id": "Q04",
        "question": "What are the common reasons for delivery delays?",
        "answerable": True,
        "expected_chunks": {1},
        "answer_checks": [
            ["delay", "delays"],
        ],
    },
    {
        "id": "Q05",
        "question": "Who is responsible for providing correct delivery details?",
        "answerable": True,
        "expected_chunks": {1},
        "answer_checks": [
            ["customer"],
        ],
    },
    {
        "id": "Q06",
        "question": "How can customers track their orders?",
        "answerable": True,
        "expected_chunks": {0},
        "answer_checks": [
            ["track", "tracking"],
        ],
    },
    {
        "id": "Q07",
        "question": "Does the document specify a minimum order value for free shipping?",
        "answerable": True,
        "expected_chunks": {2},
        "answer_checks": [
            ["not specified", "not provided", "does not specify"],
        ],
    },
    {
        "id": "Q08",
        "question": "What privacy precautions should customers follow?",
        "answerable": True,
        "expected_chunks": {1},
        "answer_checks": [
            ["privacy", "personal information", "personal details"],
        ],
    },
    {
        "id": "Q09",
        "question": "Does the store offer cash on delivery?",
        "answerable": False,
        "expected_chunks": set(),
        "answer_checks": [],
    },
    {
        "id": "Q10",
        "question": "What is the order cancellation process?",
        "answerable": False,
        "expected_chunks": set(),
        "answer_checks": [],
    },
    {
        "id": "Q11",
        "question": "What is the customer support phone number?",
        "answerable": False,
        "expected_chunks": set(),
        "answer_checks": [],
    },
    {
        "id": "Q12",
        "question": "How many days does the product return period last?",
        "answerable": False,
        "expected_chunks": set(),
        "answer_checks": [],
    },
]


def load_completed_results(document_id):
    """Load previously completed PASS/FAIL evaluations."""
    completed = set()

    if not RESULTS_FILE.exists():
        return completed

    latest_results = {}

    with RESULTS_FILE.open("r", encoding="utf-8") as file:
        for line in file:
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            if record.get("document_id") == str(document_id):
                latest_results[record["case_id"]] = record["status"]

    for case_id, status in latest_results.items():
        if status in {"PASS", "FAIL"}:
            completed.add(case_id)

    return completed


def save_result(record):
    """Append one result without overwriting previous evaluations."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    with RESULTS_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def check_answer(answer, answer_checks):
    """Basic deterministic answer-content checks."""
    normalized = answer.casefold()

    return all(
        any(phrase.casefold() in normalized for phrase in phrase_group)
        for phrase_group in answer_checks
    )


def evaluate_case(db, user_id, case):
    response = ask_question(
        db=db,
        user_id=user_id,
        question=case["question"],
        top_k=TOP_K,
    )

    actual_chunks = {
        source.chunk_index
        for source in response.sources
    }

    expected_chunks = case["expected_chunks"]

    if case["answerable"]:
        abstention_correct = not response.insufficient_context

        citations_relevant = (
            bool(actual_chunks)
            and actual_chunks.issubset(expected_chunks)
        )

        answer_content_correct = check_answer(
            response.answer,
            case["answer_checks"],
        )

        passed = (
            abstention_correct
            and citations_relevant
            and answer_content_correct
        )

    else:
        abstention_correct = (
            response.insufficient_context
            and not response.sources
        )

        citations_relevant = not response.sources
        answer_content_correct = abstention_correct
        passed = abstention_correct

    return {
        "passed": passed,
        "answer": response.answer,
        "insufficient_context": response.insufficient_context,
        "actual_chunks": sorted(actual_chunks),
        "expected_chunks": sorted(expected_chunks),
        "citation_count": len(response.sources),
        "abstention_correct": abstention_correct,
        "citations_relevant": citations_relevant,
        "answer_content_correct": answer_content_correct,
    }


def main():
    with SessionLocal() as db:
        document = db.scalar(
            select(Document)
            .where(
                Document.original_filename == DOCUMENT_FILENAME,
                Document.status == "completed",
            )
            .order_by(Document.created_at.desc())
        )

        if document is None:
            print("Evaluation document not found or not completed.")
            return

        completed = load_completed_results(document.id)

        print("=" * 75)
        print("ADVANCED RAG EVALUATION")
        print("=" * 75)
        print(f"Document: {document.original_filename}")
        print(f"Total cases: {len(EVALUATION_CASES)}")
        print(f"Previously completed: {len(completed)}")
        print(f"Remaining: {len(EVALUATION_CASES) - len(completed)}")

        counts = {
            "PASS": 0,
            "FAIL": 0,
            "ERROR": 0,
            "SKIPPED": 0,
        }

        all_citations = 0
        relevant_citations = 0
        unsupported_citations = 0

        for index, case in enumerate(EVALUATION_CASES, start=1):
            if case["id"] in completed:
                counts["SKIPPED"] += 1
                print(f"\n{case['id']}: SKIPPED (already evaluated)")
                continue

            print("\n" + "=" * 75)
            print(f"TEST {index}/{len(EVALUATION_CASES)} - {case['id']}")
            print("=" * 75)
            print("Question:", case["question"])

            try:
                result = evaluate_case(
                    db=db,
                    user_id=document.user_id,
                    case=case,
                )

            except RateLimitError as exc:
                counts["ERROR"] += 1

                save_result({
                    "document_id": str(document.id),
                    "case_id": case["id"],
                    "question": case["question"],
                    "status": "ERROR",
                    "error_type": "RateLimitError",
                    "error": str(exc),
                })

                print("\nGROQ RATE LIMIT REACHED.")
                print("Evaluation stopped to protect remaining quota.")
                break

            except Exception as exc:
                counts["ERROR"] += 1

                save_result({
                    "document_id": str(document.id),
                    "case_id": case["id"],
                    "question": case["question"],
                    "status": "ERROR",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                })

                print(f"\nERROR: {type(exc).__name__}: {exc}")
                continue

            status = "PASS" if result["passed"] else "FAIL"
            counts[status] += 1

            if case["answerable"]:
                all_citations += result["citation_count"]

                relevant_citations += sum(
                    1
                    for chunk in result["actual_chunks"]
                    if chunk in case["expected_chunks"]
                )
            else:
                unsupported_citations += result["citation_count"]

            save_result({
                "document_id": str(document.id),
                "case_id": case["id"],
                "question": case["question"],
                "status": status,
                **result,
            })

            print("\nAnswer:", result["answer"])
            print("Insufficient context:", result["insufficient_context"])
            print("Expected chunks:", result["expected_chunks"])
            print("Returned chunks:", result["actual_chunks"])
            print("Citations:", result["citation_count"])
            print("Answer content check:", result["answer_content_correct"])
            print("Citation relevance check:", result["citations_relevant"])
            print("Abstention check:", result["abstention_correct"])
            print("RESULT:", status)

    print("\n" + "=" * 75)
    print("EVALUATION REPORT")
    print("=" * 75)

    for status, count in counts.items():
        print(f"{status}: {count}")

    if all_citations:
        precision = (relevant_citations / all_citations) * 100
    else:
        precision = 0.0

    print(f"\nCitation precision: {precision:.2f}%")
    print("Citations returned for unsupported questions:", unsupported_citations)
    print("Results file:", RESULTS_FILE)
    print("=" * 75)


if __name__ == "__main__":
    main()
