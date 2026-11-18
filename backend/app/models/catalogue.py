from pydantic import Field, field_validator

from app.models.chat import StrictModel


class ComparisonRequest(StrictModel):
    original: str = Field(min_length=1, max_length=80)
    candidate: str = Field(min_length=1, max_length=80)
    brand: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("original", "candidate", "brand")
    @classmethod
    def trim_value(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Provide a nonempty part identifier or brand.")
        return value.strip() if value is not None else None


class EvidenceRequest(StrictModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=8, ge=1, le=12)

    @field_validator("query")
    @classmethod
    def trim_query(cls, value):
        if not value.strip():
            raise ValueError("Provide a nonempty query.")
        return value.strip()


class LookupRequest(StrictModel):
    part: str = Field(min_length=1, max_length=80)
    brand: str | None = Field(default=None, min_length=1, max_length=100)
    limit: int = Field(default=8, ge=1, le=12, strict=True)

    @field_validator("part", "brand")
    @classmethod
    def trim_value(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Provide a nonempty identifier or brand.")
        return value.strip() if value is not None else None
