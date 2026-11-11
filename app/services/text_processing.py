
import re
import unicodedata
from dataclasses import dataclass

from transformers import AutoTokenizer

from app.core.config import settings
from app.services.document_extraction import ExtractedPage


def normalize_text(text: str) -> str:
    """Normalize extracted text while preserving meaningful structure."""

    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)

    text = "".join(
        char
        for char in text
        if char in "\n\t" or not unicodedata.category(char).startswith("C")
    )

    # Join words split by hyphenation at line endings.
    text = re.sub(r"(?<=\w)-[ \t]*\n[ \t]*(?=\w)", "", text)

    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Normalize spaces while preserving newlines.
    text = re.sub(r"[^\S\n]+", " ", text)

    # Collapse excessive blank lines.
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    content: str
    page_number: int | None
    token_count: int


def get_tokenizer():
    """Load the tokenizer for the configured embedding model."""

    return AutoTokenizer.from_pretrained(settings.embedding_model)


def _encode(text: str, tokenizer) -> list[int]:
    """Encode text without adding special tokens."""

    return tokenizer.backend_tokenizer.encode(
        text,
        add_special_tokens=False,
    ).ids


def _token_count(text: str, tokenizer) -> int:
    return len(_encode(text, tokenizer))


def _is_section_heading(line: str) -> bool:
    """Identify explicit Markdown or short numbered heading lines."""

    line = line.strip()

    if not line:
        return False

    if re.match(r"^#{1,6}\s+\S", line):
        return True

    numbered_heading = re.match(
        r"^\d+(?:\.\d+)*[.)]?\s+[A-Za-z].{0,100}$",
        line,
    )

    if numbered_heading and len(line) <= 120:
        if not re.search(r"[.!?]$", line):
            return True

    return False


def _split_sections(text: str) -> list[str]:
    """
    Split text at explicit heading lines.

    If no headings are detected, the entire text is handled as
    one section and paragraph/sentence splitting acts as fallback.
    """

    sections = []
    current_lines = []

    for line in text.splitlines():
        if _is_section_heading(line) and current_lines:
            section = "\n".join(current_lines).strip()

            if section:
                sections.append(section)

            current_lines = [line]
        else:
            current_lines.append(line)

    final_section = "\n".join(current_lines).strip()

    if final_section:
        sections.append(final_section)

    return sections


def _split_paragraphs(section: str) -> list[str]:
    """Split a section into non-empty paragraphs."""

    return [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", section)
        if paragraph.strip()
    ]


def _split_sentences(paragraph: str) -> list[str]:
    """
    Split paragraphs at sentence boundaries.

    The negative digit lookbehind avoids splitting numbered headings
    immediately after their section number, such as '1. Introduction'.
    """

    sentences = re.split(
        r"(?<!\d)(?<=[.!?])\s+",
        paragraph.strip(),
    )

    return [
        sentence.strip()
        for sentence in sentences
        if sentence.strip()
    ]


def _split_long_sentence(
    sentence: str,
    tokenizer,
    max_tokens: int,
) -> list[str]:
    """
    Split an oversized sentence into token-limited fragments.

    This is a fallback for sentences that cannot fit within the
    maximum chunk size.
    """

    token_ids = _encode(sentence, tokenizer)

    if len(token_ids) <= max_tokens:
        return [sentence]

    fragments = []

    for start in range(0, len(token_ids), max_tokens):
        fragment_ids = token_ids[start:start + max_tokens]

        fragment = tokenizer.decode(
            fragment_ids,
            skip_special_tokens=True,
        ).strip()

        if fragment:
            fragments.append(fragment)

    return fragments


def _get_overlap_units(
    previous_units: list[str],
    tokenizer,
    overlap_tokens: int,
) -> list[str]:
    """
    Select complete trailing sentence units.

    The configured overlap is a target, not a strict limit.
    If the final sentence is slightly larger than the target,
    preserve that complete sentence instead of returning zero overlap.
    """

    if not previous_units or overlap_tokens <= 0:
        return []

    selected = []

    for unit in reversed(previous_units):
        candidate = [unit] + selected
        candidate_text = " ".join(candidate)
        candidate_count = _token_count(candidate_text, tokenizer)

        if candidate_count <= overlap_tokens:
            selected = candidate
            continue

        # Allow one complete trailing sentence when it is
        # slightly larger than the configured overlap target.
        if not selected and candidate_count <= overlap_tokens + 40:
            selected = candidate

        break

    return selected


def _chunk_section(
    section: str,
    tokenizer,
    target_tokens: int,
    max_tokens: int,
    overlap_tokens: int,
) -> list[tuple[str, int]]:
    """
    Create overlapping and balanced chunks without unnecessarily
    breaking sentences.
    """

    units = []

    for paragraph in _split_paragraphs(section):
        for sentence in _split_sentences(paragraph):
            units.extend(
                _split_long_sentence(
                    sentence=sentence,
                    tokenizer=tokenizer,
                    max_tokens=max_tokens,
                )
            )

    if not units:
        return []

    chunks = []
    cursor = 0
    previous_chunk_units = []

    # A final chunk smaller than half the target is considered small.
    minimum_chunk_tokens = target_tokens // 2

    while cursor < len(units):
        overlap = _get_overlap_units(
            previous_units=previous_chunk_units,
            tokenizer=tokenizer,
            overlap_tokens=overlap_tokens,
        )

        fresh_units = []

        while cursor < len(units):
            candidate_units = overlap + fresh_units + [units[cursor]]
            candidate_text = " ".join(candidate_units)
            candidate_count = _token_count(candidate_text, tokenizer)

            allowed_tokens = max_tokens if overlap else target_tokens

            if candidate_count <= allowed_tokens:
                fresh_units.append(units[cursor])
                cursor += 1
                continue

            # If overlap prevents the next sentence from fitting,
            # remove overlap and retry without advancing the cursor.
            if not fresh_units and overlap:
                overlap = []
                continue

            # A sentence can exceed the target, but must never
            # exceed the hard maximum.
            if not fresh_units and not overlap:
                if candidate_count > max_tokens:
                    raise ValueError(
                        "Sentence fragment exceeds maximum chunk size."
                    )

                fresh_units.append(units[cursor])
                cursor += 1

            break

        if not fresh_units:
            raise ValueError("Unable to make progress while chunking.")

        # Calculate the size of the remaining unprocessed content.
        remaining_token_count = _token_count(
            " ".join(units[cursor:]),
            tokenizer,
        )

        # Rebalance a small final chunk by moving complete sentence
        # units from the current chunk into the remaining content.
        while (
            0 < remaining_token_count < minimum_chunk_tokens
            and fresh_units
        ):
            candidate_fresh_units = fresh_units[:-1]

            candidate_current_units = (
                overlap + candidate_fresh_units
            )

            candidate_current_count = _token_count(
                " ".join(candidate_current_units),
                tokenizer,
            )

            # Do not make the current chunk too small.
            if candidate_current_count < minimum_chunk_tokens:
                break

            # Recalculate overlap for the next chunk.
            candidate_next_overlap = _get_overlap_units(
                previous_units=candidate_current_units,
                tokenizer=tokenizer,
                overlap_tokens=overlap_tokens,
            )

            candidate_next_units = (
                candidate_next_overlap + units[cursor - 1:]
            )

            candidate_next_count = _token_count(
                " ".join(candidate_next_units),
                tokenizer,
            )

            # Never allow the next chunk to exceed the hard limit.
            if candidate_next_count > max_tokens:
                break

            # Move the last complete sentence into the remaining content.
            fresh_units.pop()
            cursor -= 1

            remaining_token_count = _token_count(
                " ".join(units[cursor:]),
                tokenizer,
            )

        chunk_units = overlap + fresh_units
        chunk_content = " ".join(chunk_units).strip()
        token_count = _token_count(chunk_content, tokenizer)

        if token_count > max_tokens:
            raise ValueError("Generated chunk exceeds maximum token limit.")

        chunks.append((chunk_content, token_count))
        previous_chunk_units = chunk_units

    return chunks


def chunk_document_pages(
    pages: list[ExtractedPage],
    tokenizer=None,
) -> list[TextChunk]:
    """
    Structure-aware, page-preserving document chunking.

    Splitting priority:
    section -> paragraph -> sentence -> token fragments.
    """

    target_tokens = settings.chunk_size_tokens
    max_tokens = settings.max_chunk_size_tokens
    overlap_tokens = settings.chunk_overlap_tokens

    if target_tokens <= 0:
        raise ValueError("Target chunk size must be greater than zero.")

    if max_tokens < target_tokens:
        raise ValueError(
            "Maximum chunk size must be greater than or equal to target size."
        )

    if overlap_tokens < 0 or overlap_tokens >= target_tokens:
        raise ValueError(
            "Overlap must be non-negative and smaller than target chunk size."
        )

    if tokenizer is None:
        tokenizer = get_tokenizer()

    chunks = []
    chunk_index = 0

    for page in pages:
        cleaned_text = normalize_text(page.content)

        if not cleaned_text:
            continue

        sections = _split_sections(cleaned_text)

        for section in sections:
            section_chunks = _chunk_section(
                section=section,
                tokenizer=tokenizer,
                target_tokens=target_tokens,
                max_tokens=max_tokens,
                overlap_tokens=overlap_tokens,
            )

            for content, token_count in section_chunks:
                chunks.append(
                    TextChunk(
                        chunk_index=chunk_index,
                        content=content,
                        page_number=page.page_number,
                        token_count=token_count,
                    )
                )

                chunk_index += 1

    return chunks
