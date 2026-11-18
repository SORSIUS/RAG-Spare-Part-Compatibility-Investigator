from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SupportingCitation(StrictModel):
    source_id: str
    quote: str


class AnswerClaim(StrictModel):
    text: str
    citations: list[SupportingCitation]


class GeneratedAnswer(StrictModel):
    insufficient_evidence: bool
    claims: list[AnswerClaim]
    unknowns: list[str]
    follow_up_questions: list[str]


class ChatRequest(StrictModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    mode: str = Field(default="answer", pattern=r"^(answer|evidence)$")

    @field_validator("question")
    @classmethod
    def strip_question(cls, value):
        if not value.strip():
            raise ValueError("Ask a question first.")
        return value.strip()
