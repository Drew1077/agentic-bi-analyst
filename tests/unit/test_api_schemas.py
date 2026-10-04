import pytest
from pydantic import ValidationError

from app.api.schemas import AnalyzeRequest


def test_analyze_request_accepts_non_empty_question():
    request = AnalyzeRequest(question=" revenue by category in 2025 ")

    assert request.question == " revenue by category in 2025 "


def test_analyze_request_rejects_whitespace_question():
    with pytest.raises(ValidationError, match="Question must not be empty"):
        AnalyzeRequest(question="   ")


def test_analyze_request_rejects_extra_fields():
    with pytest.raises(ValidationError):
        AnalyzeRequest(
            question="revenue in 2025",
            extra="not allowed",
        )
