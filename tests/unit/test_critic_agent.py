from dataclasses import dataclass

from app.agents.critic_agent import (
    CriticAgent,
    CriticAgentRequest,
)


@dataclass
class ValidResult:
    success: bool = True
    answer: str | None = "Revenue decreased by 8.4%."
    evidence: list = None
    provenance: list = None
    findings: list = None

    def __post_init__(self):
        if self.evidence is None:
            self.evidence = [
                {
                    "type": "comparison",
                    "metric": "revenue",
                    "current_value": 9200,
                    "previous_value": 10000,
                    "absolute_change": -800,
                    "percentage_change": -8.0,
                }
            ]

        if self.provenance is None:
            self.provenance = [
                {
                    "agent": "sql_analyst",
                    "source": "governed_sql",
                }
            ]

        if self.findings is None:
            self.findings = []


def test_critic_passes_valid_result():
    agent = CriticAgent()

    response = agent.run(
        CriticAgentRequest(
            question="What happened to revenue?",
            result=ValidResult(),
        )
    )

    assert response.success is True
    assert response.passed is True
    assert response.issues == []
    assert response.errors == []


def test_critic_rejects_failed_result():
    agent = CriticAgent()

    result = ValidResult(success=False)

    response = agent.run(
        CriticAgentRequest(
            question="What happened to revenue?",
            result=result,
        )
    )

    assert response.success is True
    assert response.passed is False
    assert "Analytical result was not successful." in response.issues


def test_critic_rejects_missing_answer():
    agent = CriticAgent()

    result = ValidResult(answer=None)

    response = agent.run(
        CriticAgentRequest(
            question="What happened to revenue?",
            result=result,
        )
    )

    assert response.passed is False
    assert "Successful analytical result has no answer." in response.issues


def test_critic_rejects_missing_evidence():
    agent = CriticAgent()

    result = ValidResult(evidence=[])

    response = agent.run(
        CriticAgentRequest(
            question="What happened to revenue?",
            result=result,
        )
    )

    assert response.passed is True


def test_critic_rejects_invalid_finding_type():
    agent = CriticAgent()

    result = ValidResult(
        findings=[
            {
                "type": "unsupported_type",
                "statement": "Revenue declined.",
                "supporting_evidence": [],
            }
        ]
    )

    response = agent.run(
        CriticAgentRequest(
            question="Why did revenue decline?",
            result=result,
        )
    )

    assert response.passed is False
    assert any(
        "invalid type" in issue
        for issue in response.issues
    )


def test_critic_rejects_unsupported_evidence_backed_finding():
    agent = CriticAgent()

    result = ValidResult(
        findings=[
            {
                "type": "evidence_backed",
                "statement": "Electronics drove the decline.",
                "supporting_evidence": [],
            }
        ]
    )

    response = agent.run(
        CriticAgentRequest(
            question="Why did revenue decline?",
            result=result,
        )
    )

    assert response.passed is False
    assert any(
        "supporting evidence" in issue
        for issue in response.issues
    )


def test_critic_rejects_inconsistent_arithmetic():
    agent = CriticAgent()

    result = ValidResult(
        evidence=[
            {
                "type": "comparison",
                "metric": "revenue",
                "current_value": 9200,
                "previous_value": 10000,
                "absolute_change": -500,
                "percentage_change": -5.0,
            }
        ]
    )

    response = agent.run(
        CriticAgentRequest(
            question="What happened to revenue?",
            result=result,
        )
    )

    assert response.passed is False
    assert any(
        "inconsistent absolute change" in issue
        for issue in response.issues
    )


def test_critic_preserves_check_and_provenance_information():
    agent = CriticAgent()

    response = agent.run(
        CriticAgentRequest(
            question="What happened to revenue?",
            result=ValidResult(),
        )
    )

    assert len(response.checks) >= 1
    assert len(response.provenance) == 1
    assert response.provenance[0]["agent"] == "critic_agent"


def test_critic_rejects_invalid_request():
    agent = CriticAgent()

    response = agent.run(
        CriticAgentRequest(
            question="",
            result=None,
        )
    )

    assert response.success is False
    assert response.passed is False
    assert response.errors