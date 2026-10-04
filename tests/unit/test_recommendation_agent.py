from dataclasses import dataclass

from app.agents.recommendation_agent import (
    RecommendationAgent,
    RecommendationAgentRequest,
)


@dataclass
class FakeAnalyticalResult:
    success: bool = True
    answer: str = "Revenue decreased by 8.4%."
    evidence: list = None
    provenance: list = None

    def __post_init__(self):
        self.evidence = self.evidence or [
            {"type": "comparison", "direction": "decrease"}
        ]
        self.provenance = self.provenance or [
            {"agent": "critic_agent", "source": "validated"}
        ]


def test_recommendation_agent_generates_from_evidence_backed_finding():
    agent = RecommendationAgent()

    request = RecommendationAgentRequest(
        question="Why did revenue decline?",
        analytical_result=FakeAnalyticalResult(),
        findings=[
            {
                "type": "evidence_backed",
                "statement": "Accessories contributed 62% of the decline.",
                "supporting_evidence": [
                    {
                        "type": "contribution",
                        "dimension": "category",
                        "group": "Accessories",
                        "contribution_percentage": 62.0,
                    }
                ],
            }
        ],
    )

    response = agent.run(request)

    assert response.success is True
    assert len(response.recommendations) == 1

    recommendation = response.recommendations[0]
    assert "Accessories" in recommendation["recommendation"]
    assert recommendation["priority"] == "high"
    assert recommendation["potential_impact"]["type"] == "not_available"
    assert recommendation["supporting_evidence"][0]["group"] == "Accessories"


def test_recommendation_agent_handles_observed_decrease():
    agent = RecommendationAgent()

    request = RecommendationAgentRequest(
        question="What happened to revenue?",
        analytical_result=FakeAnalyticalResult(),
        findings=[
            {
                "type": "observed",
                "statement": "Revenue decreased by 8.4%.",
                "supporting_evidence": [
                    {
                        "type": "comparison",
                        "metric": "net_revenue",
                        "direction": "decrease",
                        "percentage_change": -8.4,
                    }
                ],
            }
        ],
    )

    response = agent.run(request)

    assert response.success is True
    assert len(response.recommendations) == 1
    assert "decline" in response.recommendations[0]["recommendation"].lower()
    assert response.recommendations[0]["priority"] == "medium"


def test_recommendation_agent_does_not_action_hypothesis():
    agent = RecommendationAgent()

    request = RecommendationAgentRequest(
        question="Why did revenue decline?",
        analytical_result=FakeAnalyticalResult(),
        findings=[
            {
                "type": "hypothesis",
                "statement": "Pricing may have contributed.",
                "supporting_evidence": [
                    {"type": "hypothesis", "statement": "Pricing may have contributed."}
                ],
            }
        ],
    )

    response = agent.run(request)

    assert response.success is True
    assert response.recommendations == []


def test_recommendation_agent_rejects_missing_supporting_evidence():
    agent = RecommendationAgent()

    request = RecommendationAgentRequest(
        question="Why did revenue decline?",
        analytical_result=FakeAnalyticalResult(),
        findings=[
            {
                "type": "evidence_backed",
                "statement": "Revenue declined.",
                "supporting_evidence": [],
            }
        ],
    )

    response = agent.run(request)

    assert response.success is False
    assert any("supporting evidence" in error for error in response.errors)


def test_recommendation_agent_preserves_explicit_impact_estimate():
    agent = RecommendationAgent()

    request = RecommendationAgentRequest(
        question="What should we review?",
        analytical_result=FakeAnalyticalResult(),
        findings=[
            {
                "type": "evidence_backed",
                "statement": "Accessories contributed materially.",
                "supporting_evidence": [
                    {
                        "type": "contribution",
                        "dimension": "category",
                        "group": "Accessories",
                        "contribution_percentage": 62.0,
                        "impact_estimate": 12000,
                        "impact_assumptions": ["10% recovery scenario"],
                    }
                ],
            }
        ],
    )

    response = agent.run(request)

    assert response.success is True
    impact = response.recommendations[0]["potential_impact"]
    assert impact["type"] == "estimated"
    assert impact["value"] == 12000
    assert impact["assumptions"] == ["10% recovery scenario"]


def test_recommendation_agent_preserves_analytical_provenance():
    agent = RecommendationAgent()
    result = FakeAnalyticalResult()

    response = agent.run(
        RecommendationAgentRequest(
            question="What happened?",
            analytical_result=result,
            findings=[
                {
                    "type": "observed",
                    "statement": "Revenue decreased.",
                    "supporting_evidence": [
                        {
                            "type": "comparison",
                            "direction": "decrease",
                        }
                    ],
                }
            ],
        )
    )

    assert response.success is True
    assert response.provenance["analytical_result"] == result.provenance
    assert response.evidence == result.evidence
