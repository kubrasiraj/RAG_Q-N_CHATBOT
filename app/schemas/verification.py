
from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvidenceVerification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_supported: bool
    supporting_source_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_verification(self):
        if self.is_supported and not self.supporting_source_ids:
            raise ValueError(
                "A supported answer must have supporting sources."
            )

        if not self.is_supported and self.supporting_source_ids:
            raise ValueError(
                "An unsupported answer cannot have supporting sources."
            )

        if len(self.supporting_source_ids) != len(
            set(self.supporting_source_ids)
        ):
            raise ValueError("Duplicate supporting source IDs.")

        return self
