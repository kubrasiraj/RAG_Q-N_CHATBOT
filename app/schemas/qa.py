from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class QARequest(BaseModel):
    question: str = Field(
        min_length=3,
        max_length=2000,
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
    )

    @model_validator(mode="after")
    def validate_question(self):
        if not self.question.strip():
            raise ValueError("Question cannot be empty.")

        self.question = self.question.strip()
        return self


class LLMAnswer(BaseModel):
    """Internal validation schema for the LLM JSON response."""

    answer: str = Field(min_length=1, max_length=10000)
    citation_ids: list[str] = Field(default_factory=list)
    insufficient_context: bool = False

    @model_validator(mode="after")
    def validate_answer(self):
        self.answer = self.answer.strip()

        if not self.answer:
            raise ValueError("LLM answer cannot be empty.")

        if self.insufficient_context and self.citation_ids:
            raise ValueError(
                "An insufficient-context answer cannot contain citations."
            )

        if not self.insufficient_context and not self.citation_ids:
            raise ValueError(
                "A supported answer must contain at least one citation."
            )

        return self


class QASource(BaseModel):
    source_id: str
    document_id: UUID
    filename: str
    page_number: int | None
    chunk_index: int
    similarity: float
    excerpt: str


class QAResponse(BaseModel):
    answer: str
    sources: list[QASource]
    insufficient_context: bool