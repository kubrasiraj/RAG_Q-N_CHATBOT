
import pytest

from app.core.config import settings
from app.services.document_extraction import ExtractedPage
from app.services.text_processing import (
    _split_sections,
    chunk_document_pages,
    normalize_text,
)

class FakeEncoding:
    def __init__(self, ids):
        self.ids = ids

class FakeBackendTokenizer:
    def encode(self, text, add_special_tokens=False):
        return FakeEncoding([ord(char) for char in text])

class FakeTokenizer:
    def __init__(self):
        self.backend_tokenizer = FakeBackendTokenizer()

    def decode(self, token_ids, skip_special_tokens=True):
        return "".join(chr(token_id) for token_id in token_ids)

@pytest.fixture
def tokenizer():
    return FakeTokenizer()

def test_normalize_text():
    text = "Hello\r\n\r\nWorld"

    result = normalize_text(text)

    assert result == "Hello\n\nWorld"

def test_split_sections():
    text = (
        "1. Delivery\n"
        "Delivery takes two days.\n\n"
        "2. Refunds\n"
        "Refunds take five days."
    )

    sections = _split_sections(text)

    assert len(sections) == 2
    assert "1. Delivery" in sections[0]
    assert "2. Refunds" in sections[1]

def test_chunk_document_preserves_page_number(
    tokenizer,
    monkeypatch,
):
    monkeypatch.setattr(settings, "chunk_size_tokens", 40)
    monkeypatch.setattr(settings, "max_chunk_size_tokens", 50)
    monkeypatch.setattr(settings, "chunk_overlap_tokens", 10)

    pages = [
        ExtractedPage(
            page_number=3,
            content="Delivery takes two business days. "
                    "Orders are processed before dispatch.",
        )
    ]

    chunks = chunk_document_pages(
        pages=pages,
        tokenizer=tokenizer,
    )

    assert chunks
    assert all(chunk.page_number == 3 for chunk in chunks)

def test_chunk_size_never_exceeds_maximum(
    tokenizer,
    monkeypatch,
):
    monkeypatch.setattr(settings, "chunk_size_tokens", 40)
    monkeypatch.setattr(settings, "max_chunk_size_tokens", 50)
    monkeypatch.setattr(settings, "chunk_overlap_tokens", 10)

    pages = [
        ExtractedPage(
            page_number=1,
            content=(
                "This is a long sentence with many words. "
                "Another sentence follows with additional information. "
                "A final sentence contains more details."
            ),
        )
    ]

    chunks = chunk_document_pages(
        pages=pages,
        tokenizer=tokenizer,
    )

    assert chunks

    for chunk in chunks:
        assert chunk.token_count <= 50

def test_chunk_indexes_are_sequential(tokenizer):
    pages = [
        ExtractedPage(
            page_number=1,
            content="First page has some useful information.",
        ),
        ExtractedPage(
            page_number=2,
            content="Second page contains additional information.",
        ),
    ]

    chunks = chunk_document_pages(
        pages=pages,
        tokenizer=tokenizer,
    )

    indexes = [chunk.chunk_index for chunk in chunks]

    assert indexes == list(range(len(chunks)))

def test_empty_pages_return_no_chunks(tokenizer):
    pages = [
        ExtractedPage(
            page_number=1,
            content="   ",
        )
    ]

    chunks = chunk_document_pages(
        pages=pages,
        tokenizer=tokenizer,
    )

    assert chunks == []

def test_invalid_overlap_raises_error(
    tokenizer,
    monkeypatch,
):
    monkeypatch.setattr(settings, "chunk_size_tokens", 40)
    monkeypatch.setattr(settings, "max_chunk_size_tokens", 50)
    monkeypatch.setattr(settings, "chunk_overlap_tokens", 40)

    pages = [
        ExtractedPage(
            page_number=1,
            content="Some document content.",
        )
    ]

    with pytest.raises(ValueError, match="Overlap"):
        chunk_document_pages(
            pages=pages,
            tokenizer=tokenizer,
        )