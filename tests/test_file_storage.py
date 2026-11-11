
from pathlib import Path

import pytest

from app.core.config import settings
from app.services.file_storage import save_document, delete_document


def test_save_pdf(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))

    content = b"sample pdf content"

    saved_path = save_document(content, "research.pdf")

    assert saved_path.exists()
    assert saved_path.read_bytes() == content
    assert saved_path.suffix == ".pdf"
    assert saved_path.parent == tmp_path.resolve()
    assert saved_path.name != "research.pdf"


def test_save_docx(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))

    saved_path = save_document(b"docx content", "report.docx")

    assert saved_path.exists()
    assert saved_path.suffix == ".docx"


def test_save_txt(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))

    saved_path = save_document(b"hello", "notes.txt")

    assert saved_path.exists()
    assert saved_path.suffix == ".txt"


def test_reject_unsupported_extension(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))

    with pytest.raises(ValueError):
        save_document(b"content", "malware.exe")


def test_reject_empty_content(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))

    with pytest.raises(ValueError):
        save_document(b"", "empty.pdf")


def test_delete_document(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))

    saved_path = save_document(b"content", "report.pdf")

    result = delete_document(saved_path)

    assert result is True
    assert not saved_path.exists()


def test_delete_missing_document(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "storage_dir", str(tmp_path))

    missing_path = tmp_path / "missing.pdf"

    assert delete_document(missing_path) is False


def test_prevent_deleting_outside_storage(tmp_path, monkeypatch):
    storage = tmp_path / "storage"
    storage.mkdir()

    outside_file = tmp_path / "important.txt"
    outside_file.write_text("keep this file")

    monkeypatch.setattr(settings, "storage_dir", str(storage))

    with pytest.raises(ValueError):
        delete_document(outside_file)

    assert outside_file.exists()
