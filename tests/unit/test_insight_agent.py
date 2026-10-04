from app.agents.insight_agent import (
    InsightAgent,
    InsightAgentRequest,
)


def test_insight_agent_interprets_decrease():
    agent = InsightAgent()

    response = agent.run(
        InsightAgentRequest(
            question="Why did revenue decline?",
            evidence=[
                {
                    "type": "comparison",
                    "metric": "revenue",
                    "direction": "decrease",
                    "percentage_change": -8.4,
                    "absolute_change": -1200,
                }
            ],
        )
    )

    assert response.success is True
    assert len(response.findings) == 1
    assert response.findings[0]["type"] == "observed"
    assert "revenue decreased by 8.4%" in response.findings[0]["statement"]
    assert response.errors == []


def test_insight_agent_interprets_increase():
    agent = InsightAgent()

    response = agent.run(
        InsightAgentRequest(
            question="What happened to revenue?",
            evidence=[
                {
                    "type": "comparison",
                    "metric": "revenue",
                    "direction": "increase",
                    "percentage_change": 12.5,
                    "absolute_change": 1500,
                }
            ],
        )
    )

    assert response.success is True
    assert response.findings[0]["type"] == "observed"
    assert "revenue increased by 12.5%" in response.findings[0]["statement"]


def test_insight_agent_interprets_contribution():
    agent = InsightAgent()

    response = agent.run(
        InsightAgentRequest(
            question="Why did revenue decline?",
            evidence=[
                {
                    "type": "contribution",
                    "dimension": "category",
                    "group": "Electronics",
                    "contribution_percentage": 62.5,
                    "absolute_change": -750,
                }
            ],
        )
    )

    assert response.success is True
    assert response.findings[0]["type"] == "evidence_backed"
    assert "Electronics" in response.findings[0]["statement"]
    assert "62.5%" in response.findings[0]["statement"]


def test_insight_agent_returns_insufficient_evidence_when_empty():
    agent = InsightAgent()

    response = agent.run(
        InsightAgentRequest(
            question="Why did revenue decline?",
            evidence=[],
        )
    )

    assert response.success is True
    assert len(response.findings) == 1
    assert response.findings[0]["type"] == "insufficient_evidence"
    assert response.errors == []


def test_insight_agent_rejects_invalid_question():
    agent = InsightAgent()

    response = agent.run(
        InsightAgentRequest(
            question="",
            evidence=[],
        )
    )

    assert response.success is False
    assert response.findings == []
    assert response.errors


def test_insight_agent_rejects_invalid_evidence():
    agent = InsightAgent()

    response = agent.run(
        InsightAgentRequest(
            question="Why did revenue decline?",
            evidence=["invalid"],
        )
    )

    assert response.success is False
    assert response.findings == []
    assert response.errors


def test_insight_agent_preserves_evidence_and_provenance():
    agent = InsightAgent()

    evidence = [
        {
            "type": "comparison",
            "metric": "revenue",
            "direction": "decrease",
            "percentage_change": -8.4,
            "absolute_change": -1200,
        }
    ]

    response = agent.run(
        InsightAgentRequest(
            question="Why did revenue decline?",
            evidence=evidence,
        )
    )

    assert response.evidence == evidence
    assert len(response.provenance) == 1
    assert response.provenance[0]["agent"] == "insight_agent"
    assert response.provenance[0]["source"] == "supplied_structured_evidence"
    assert response.provenance[0]["finding_count"] == 1