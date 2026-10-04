from dataclasses import dataclass

from app.agents.report_composer import (
    ReportComposer,
    ReportComposerRequest,
)


@dataclass
class FakeAnalyticalResult:
    success: bool = True
    answer: str = "Revenue decreased by 8.4%."
    columns: list = None
    rows: list = None
    evidence: list = None
    provenance: list = None

    def __post_init__(self):
        self.columns = self.columns or ["month", "revenue"]
        self.rows = self.rows or [
            {"month": "2025-01", "revenue": 100000}
        ]
        self.evidence = self.evidence or [
            {
                "type": "comparison",
                "metric": "net_revenue",
                "direction": "decrease",
                "percentage_change": -8.4,
            }
        ]
        self.provenance = self.provenance or [
            {"agent": "critic_agent", "source": "validated"}
        ]


@dataclass
class FakeVisualization:
    success: bool = True
    chart_spec: dict = None
    rendered_chart: bytes = b"\x89PNG\r\n"
    chart_format: str = "png"
    validation: dict = None

    def __post_init__(self):
        self.chart_spec = self.chart_spec or {
            "chart_type": "line",
            "title": "Revenue trend",
        }
        self.validation = self.validation or {
            "passed": True,
            "errors": [],
        }


def _recommendation():
    return {
        "recommendation": "Review the validated decline.",
        "supporting_evidence": [
            {
                "type": "comparison",
                "direction": "decrease",
            }
        ],
        "owner": "Relevant business function",
        "potential_impact": {
            "type": "not_available",
            "value": None,
            "assumptions": [],
        },
        "priority": "medium",
        "priority_basis": ["validated decrease in the measured metric"],
        "assumptions": [],
        "evidence_strength": "moderate",
    }


def test_report_composer_builds_required_sections():
    composer = ReportComposer()

    response = composer.run(
        ReportComposerRequest(
            question="What happened to revenue?",
            analytical_result=FakeAnalyticalResult(),
            findings=[
                {
                    "type": "observed",
                    "statement": "Revenue decreased by 8.4%.",
                    "supporting_evidence": [
                        {
                            "type": "comparison",
                            "direction": "decrease",
                        }
                    ],
                }
            ],
            recommendations=[_recommendation()],
            visualization=FakeVisualization(),
        )
    )

    assert response.success is True

    report = response.report
    assert report["title"] == "Business Analysis Report"
    assert report["question"] == "What happened to revenue?"
    assert report["executive_summary"] == "Revenue decreased by 8.4%."
    assert report["findings"]
    assert report["recommendations"]
    assert report["visualization"]["chart_format"] == "png"
    assert report["methodology"]["new_analysis_performed"] is False
    assert report["evidence"] == FakeAnalyticalResult().evidence


def test_report_composer_rejects_failed_analytical_result():
    composer = ReportComposer()
    result = FakeAnalyticalResult(success=False)

    response = composer.run(
        ReportComposerRequest(
            question="What happened?",
            analytical_result=result,
            findings=[],
            recommendations=[],
        )
    )

    assert response.success is False
    assert "successful" in " ".join(response.errors)


def test_report_composer_rejects_recommendation_without_evidence():
    composer = ReportComposer()

    response = composer.run(
        ReportComposerRequest(
            question="What should we do?",
            analytical_result=FakeAnalyticalResult(),
            findings=[],
            recommendations=[
                {
                    "recommendation": "Do something.",
                    "supporting_evidence": [],
                }
            ],
        )
    )

    assert response.success is False
    assert any("supporting evidence" in error for error in response.errors)


def test_report_composer_rejects_failed_visualization():
    composer = ReportComposer()
    visualization = FakeVisualization(success=False)

    response = composer.run(
        ReportComposerRequest(
            question="Show the trend.",
            analytical_result=FakeAnalyticalResult(),
            findings=[],
            recommendations=[],
            visualization=visualization,
        )
    )

    assert response.success is False
    assert any("Visualization" in error for error in response.errors)


def test_report_composer_preserves_findings_and_recommendations_exactly():
    composer = ReportComposer()
    findings = [
        {
            "type": "evidence_backed",
            "statement": "Accessories contributed 62%.",
            "supporting_evidence": [
                {"type": "contribution", "group": "Accessories"}
            ],
        }
    ]
    recommendations = [_recommendation()]

    response = composer.run(
        ReportComposerRequest(
            question="Why did revenue decline?",
            analytical_result=FakeAnalyticalResult(),
            findings=findings,
            recommendations=recommendations,
        )
    )

    assert response.success is True
    assert response.report["findings"][0] == findings[0]
    assert response.report["recommendations"] == recommendations


def test_report_composer_preserves_provenance():
    composer = ReportComposer()
    result = FakeAnalyticalResult()

    response = composer.run(
        ReportComposerRequest(
            question="What happened?",
            analytical_result=result,
            findings=[],
            recommendations=[],
        )
    )

    assert response.success is True
    assert response.evidence == result.evidence
    assert response.provenance["analytical_result"] == result.provenance
