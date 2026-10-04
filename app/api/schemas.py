from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AnalyzeRequest(BaseModel):
    """Validated HTTP request for an analytical question."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=4000)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question must not be empty.")
        return value


class AnalyzeResponse(BaseModel):
    """JSON-safe adapter contract for an Orchestrator response."""

    model_config = ConfigDict(extra="forbid")

    success: bool
    answer: str | None
    intent: str | None
    plan: dict[str, Any] | None
    results: dict[str, Any]
    evidence: dict[str, Any]
    provenance: dict[str, Any]
    errors: list[str]


class HealthResponse(BaseModel):
    """Service health response."""

    status: str


class ErrorResponse(BaseModel):
    """Controlled unexpected-error response."""

    detail: str
