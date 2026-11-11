
import logging
import uuid
from pathlib import Path

from app.core.config import settings


logger = logging.getLogger(__name__)


def save_document(content: bytes, original_filename: str) -> Path:
    """
    Save a validated document using a unique UUID filename.

    Returns the absolute storage path.
    """

    extension = Path(original_filename).suffix.lower()

    if extension not in settings.allowed_document_extensions:
        raise ValueError("Unsupported document extension.")

    if not content:
        raise ValueError("Cannot save an empty document.")

    storage_root = Path(settings.storage_dir).resolve()
    storage_root.mkdir(parents=True, exist_ok=True)

    # Never use the original filename as the disk filename.
    stored_filename = f"{uuid.uuid4()}{extension}"
    destination = storage_root / stored_filename

    try:
        # Exclusive creation prevents accidental overwriting.
        with destination.open("xb") as file:
            file.write(content)

        logger.info("Document saved successfully: %s", stored_filename)

        return destination

    except OSError:
        logger.exception("Failed to save uploaded document.")
        raise


def delete_document(storage_path: str | Path) -> bool:
    """
    Delete a document only if it belongs to our storage directory.

    Returns True if deleted, False if the file does not exist.
    """

    storage_root = Path(settings.storage_dir).resolve()
    target = Path(storage_path).resolve()

    # Prevent deletion outside the configured storage directory.
    if not target.is_relative_to(storage_root) or target == storage_root:
        raise ValueError("Invalid document storage path.")

    if not target.is_file():
        return False

    try:
        target.unlink()
        logger.info("Document deleted successfully: %s", target.name)
        return True

    except OSError:
        logger.exception("Failed to delete document: %s", target.name)
        raise
