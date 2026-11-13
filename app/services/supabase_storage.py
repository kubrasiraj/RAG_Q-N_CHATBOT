import logging
from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


logger = logging.getLogger(__name__)


class SupabaseStorageError(Exception):
    """Raised when a Supabase Storage operation fails."""


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """
    Create and cache the Supabase client.

    Credentials are read from environment-backed application settings.
    """

    if not settings.supabase_url:
        raise SupabaseStorageError(
            "Supabase URL is not configured."
        )

    if not settings.supabase_secret_key:
        raise SupabaseStorageError(
            "Supabase secret key is not configured."
        )

    try:
        return create_client(
            settings.supabase_url,
            settings.supabase_secret_key.get_secret_value(),
        )

    except Exception as exc:
        logger.exception("Could not initialize Supabase client.")
        raise SupabaseStorageError(
            "Could not initialize document storage."
        ) from exc


def upload_document(
    object_path: str,
    content: bytes,
    mime_type: str,
) -> str:
    """Upload document bytes to the configured private bucket."""

    if not content:
        raise ValueError("Cannot upload an empty document.")

    if not object_path or object_path.startswith("/"):
        raise ValueError("Invalid storage object path.")

    try:
        client = get_supabase_client()

        client.storage.from_(
            settings.supabase_storage_bucket
        ).upload(
            path=object_path,
            file=content,
            file_options={
                "content-type": mime_type,
                "upsert": "false",
            },
        )

        logger.info("Document uploaded to Supabase: %s", object_path)
        return object_path

    except ValueError:
        raise

    except Exception as exc:
        logger.exception(
            "Supabase document upload failed: %s",
            object_path,
        )
        raise SupabaseStorageError(
            "Unable to upload document to storage."
        ) from exc


def download_document(object_path: str) -> bytes:
    """Download a document from the configured private bucket."""

    if not object_path or object_path.startswith("/"):
        raise ValueError("Invalid storage object path.")

    try:
        client = get_supabase_client()

        content = client.storage.from_(
            settings.supabase_storage_bucket
        ).download(object_path)

        if not isinstance(content, bytes) or not content:
            raise SupabaseStorageError(
                "Downloaded document is empty or invalid."
            )

        return content

    except ValueError:
        raise

    except SupabaseStorageError:
        raise

    except Exception as exc:
        logger.exception(
            "Supabase document download failed: %s",
            object_path,
        )
        raise SupabaseStorageError(
            "Unable to download document from storage."
        ) from exc


def delete_document(object_path: str) -> bool:
    """Delete a document object from the configured private bucket."""

    if not object_path or object_path.startswith("/"):
        raise ValueError("Invalid storage object path.")

    try:
        client = get_supabase_client()

        client.storage.from_(
            settings.supabase_storage_bucket
        ).remove([object_path])

        logger.info("Document deleted from Supabase: %s", object_path)
        return True

    except ValueError:
        raise

    except Exception as exc:
        logger.exception(
            "Supabase document deletion failed: %s",
            object_path,
        )
        raise SupabaseStorageError(
            "Unable to delete document from storage."
        ) from exc