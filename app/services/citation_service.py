from typing import Any


class InvalidCitationError(Exception):
    """Raised when the LLM returns an unknown source ID."""


def validate_citations(
    citation_ids: list[str],
    available_sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Validate LLM citation IDs against actual retrieved sources.
    """

    source_map = {
        source["source_id"]: source
        for source in available_sources
    }

    if len(citation_ids) != len(set(citation_ids)):
        raise InvalidCitationError(
            "The LLM returned duplicate citation IDs."
        )

    validated_sources = []

    for citation_id in citation_ids:
        source = source_map.get(citation_id)

        if source is None:
            raise InvalidCitationError(
                "The LLM returned an unknown citation ID."
            )

        validated_sources.append(source)

    return validated_sources