#!/usr/bin/env python
"""
OPTIONAL development fallback: process documents by hand.

The backend now processes uploads automatically in a FastAPI background task, so normally you do
not need this. Use it only for documents that are stuck in "pending" or "failed", for example files
uploaded before automatic processing existed, or uploads whose background task was lost because the
server restarted before it ran.

What it does
------------
It reuses the backend's own `process_document()` (extraction, chunking, embeddings, chunk storage,
status updates). Nothing is duplicated here. It authenticates with the backend's own
`authenticate_user()`, then processes only that user's eligible documents, one at a time.

What it is NOT
--------------
It is not an API, not part of the frontend bundle, and it does not run automatically. You run it
yourself from the repository root, using the backend's Poetry environment and .env:

    poetry run python .\\frontend\\scripts\\process_pending.py --email you@example.com

Options: --dry-run (list only), --retry-failed (include documents with status "failed"),
--document-id <uuid> (repeatable), --limit N, --yes (skip the confirmation prompt), --verbose.
"""

from __future__ import annotations

import argparse
import getpass
import logging
import os
import sys
import time
from pathlib import Path
from uuid import UUID

REPO_ROOT = Path(__file__).resolve().parents[2]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="DEV ONLY: process this user's pending documents with the backend's process_document().",
    )
    parser.add_argument("--email", required=True, help="Email of the account whose documents to process.")
    parser.add_argument("--document-id", action="append", type=UUID, default=[], metavar="UUID",
                        help="Only process this document (repeatable).")
    parser.add_argument("--retry-failed", action="store_true", help='Also re-process documents with status "failed".')
    parser.add_argument("--limit", type=int, default=0, metavar="N", help="Process at most N documents (0 = no limit).")
    parser.add_argument("--dry-run", action="store_true", help="List eligible documents and exit without processing.")
    parser.add_argument("--yes", action="store_true", help="Do not ask for confirmation.")
    parser.add_argument("--verbose", action="store_true", help="Show the backend's log output, including tracebacks.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    # The backend reads .env relative to the working directory and imports `app.*` from the repo root.
    os.chdir(REPO_ROOT)
    sys.path.insert(0, str(REPO_ROOT))

    logging.basicConfig(level=logging.INFO if args.verbose else logging.CRITICAL)
    if not args.verbose:
        logging.disable(logging.CRITICAL)  # the backend logs full tracebacks on failure; hide them unless asked

    try:
        from sqlalchemy import func, select

        from app.db.session import SessionLocal, engine
        from app.models.document import Document
        from app.models.document_chunk import DocumentChunk
        from app.services.auth_service import authenticate_user
        from app.services.document_processing import DocumentProcessingError, process_document
    except Exception as exc:  # missing .env values, missing dependencies, wrong environment
        print(f"Could not load the backend ({type(exc).__name__}). Run this from the backend's Poetry "
              "environment with a valid .env in the repository root:")
        print("  poetry run python .\\frontend\\scripts\\process_pending.py --email you@example.com")
        return 1

    password = getpass.getpass(f"Password for {args.email}: ")

    try:
        with SessionLocal() as db:
            user = authenticate_user(db=db, email=args.email, password=password)
            if user is None:
                print("Authentication failed: invalid email or password, or the account is inactive.")
                return 1
            user_id = user.id

            wanted = ["pending"] + (["failed"] if args.retry_failed else [])
            statement = select(Document).where(Document.user_id == user_id, Document.status.in_(wanted))
            if args.document_id:
                statement = statement.where(Document.id.in_(args.document_id))
            statement = statement.order_by(Document.created_at.asc())
            if args.limit > 0:
                statement = statement.limit(args.limit)
            eligible = [(d.id, d.original_filename, d.status) for d in db.scalars(statement).all()]

            stuck = db.scalar(
                select(func.count()).select_from(Document).where(Document.user_id == user_id, Document.status == "processing")
            ) or 0
    except Exception as exc:
        print(f"Could not reach the database ({type(exc).__name__}). Is Docker Compose running and DATABASE_URL correct?")
        return 1

    if stuck:
        print(f"Skipping {stuck} document(s) already marked 'processing' (process_document refuses those).")

    if not eligible:
        print("No eligible documents. Nothing to do.")
        engine.dispose()
        return 0

    print(f"{len(eligible)} document(s) eligible for {args.email}:")
    for doc_id, name, status in eligible:
        print(f"  - {name}  [{status}]  {doc_id}")

    if args.dry_run:
        print("Dry run: nothing was processed.")
        engine.dispose()
        return 0

    if not args.yes and input("Process them now? The first run may download the embedding model. [y/N] ").strip().lower() != "y":
        print("Cancelled. Nothing was processed.")
        engine.dispose()
        return 0

    results: list[tuple[str, str, str]] = []
    for doc_id, name, _ in eligible:
        started = time.perf_counter()
        error: str | None = None
        try:
            with SessionLocal() as db:  # a fresh session per document keeps failures isolated
                process_document(db=db, document_id=doc_id)
        except DocumentProcessingError as exc:
            error = str(exc)
        except Exception as exc:
            error = f"Unexpected {type(exc).__name__}"

        # Report what the database says now, not what we assume happened.
        with SessionLocal() as db:
            doc = db.get(Document, doc_id)
            final = doc.status if doc else "missing"
            pages = doc.page_count if doc else None
            chunks = db.scalar(select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == doc_id)) or 0

        elapsed = time.perf_counter() - started
        detail = f"pages={pages if pages is not None else 'n/a'}, chunks={chunks}, {elapsed:.1f}s"
        print(f"  {final.upper():<10} {name}  ({detail})" + (f"\n             reason: {error}" if error else ""))
        results.append((name, final, detail))

    completed = sum(1 for _, s, _ in results if s == "completed")
    failed = sum(1 for _, s, _ in results if s != "completed")
    print(f"\nDone: {completed} completed, {failed} not completed. Refresh the Documents page; it shows the status from the API.")
    if failed and not args.verbose:
        print("Re-run with --verbose to see the backend's error output for failed documents.")

    engine.dispose()
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
