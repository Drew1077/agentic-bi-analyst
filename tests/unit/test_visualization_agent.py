from dataclasses import dataclass

from app.agents.visualization_agent import (
    VisualizationAgent,
    VisualizationAgentRequest,
)


@dataclass
class FakeSQLResult:
    success: bool = True
    answer: str = "Revenue by category."
    columns: list[str] = None
    rows: list[dict] = None
    evidence: dict = None
    provenance: dict = None

    def __post_init__(self):
        self.columns = self.columns or ["category", "net_revenue"]
        self.rows = self.rows or [
            {"category": "A", "net_revenue": 100},
            {"category": "B", "net_revenue": 150},
        ]
        self.evidence = self.evidence if self.evidence is not None else {"row_count": 2}
        self.provenance = self.provenance if self.provenance is not None else {"source": "test"}


def request(result=None, question="revenue by category"):
    return VisualizationAgentRequest(
        question=question,
        result=result or FakeSQLResult(),
    )


def test_validate_request_accepts_valid_request():
    agent = VisualizationAgent()
    assert agent.validate_request(request()) == []


def test_validate_request_rejects_empty_question():
    agent = VisualizationAgent()
    errors = agent.validate_request(request(question=" "))
    assert errors == ["Question must not be empty."]


def test_validate_request_rejects_failed_result():
    agent = VisualizationAgent()

    result = FakeSQLResult(success=False)
    errors = agent.validate_request(request(result=result))

    assert errors == ["Analytical result must be successful."]


def test_selects_bar_for_category_metric_result():
    agent = VisualizationAgent()
    assert agent.select_chart("revenue by category", FakeSQLResult()) == "bar"


def test_selects_line_for_date_metric_result():
    agent = VisualizationAgent()
    result = FakeSQLResult(
        columns=["month", "net_revenue"],
        rows=[
            {"month": "2025-01", "net_revenue": 100},
            {"month": "2025-02", "net_revenue": 120},
        ],
    )

    assert agent.select_chart("revenue trend", result) == "line"


def test_selects_scatter_for_two_numeric_fields():
    agent = VisualizationAgent()
    result = FakeSQLResult(
        columns=["orders", "net_revenue"],
        rows=[
            {"orders": 10, "net_revenue": 100},
            {"orders": 20, "net_revenue": 250},
        ],
    )

    assert agent.select_chart("orders and revenue", result) == "scatter"


def test_selects_heatmap_for_two_dimensions_and_metric():
    agent = VisualizationAgent()
    result = FakeSQLResult(
        columns=["region", "category", "net_revenue"],
        rows=[
            {"region": "North", "category": "A", "net_revenue": 100},
            {"region": "North", "category": "B", "net_revenue": 120},
            {"region": "South", "category": "A", "net_revenue": 90},
            {"region": "South", "category": "B", "net_revenue": 110},
        ],
    )

    assert agent.select_chart("revenue by region and category", result) == "heatmap"


def test_selects_waterfall_for_root_cause_contributions():
    agent = VisualizationAgent()
    result = FakeSQLResult(
        columns=[],
        rows=[],
        evidence=[
            {
                "type": "contribution",
                "group": "Accessories",
                "absolute_change": -100,
                "contribution_percentage": 60,
            },
            {
                "type": "contribution",
                "group": "Furniture",
                "absolute_change": -50,
                "contribution_percentage": 30,
            },
        ],
    )

    assert agent.select_chart("why did revenue decline?", result) == "waterfall"


def test_single_kpi_returns_no_chart():
    agent = VisualizationAgent()
    result = FakeSQLResult(
        columns=["net_revenue"],
        rows=[{"net_revenue": 1000}],
    )

    assert agent.select_chart("revenue in 2025", result) == "none"


def test_run_returns_valid_bar_chart():
    agent = VisualizationAgent()

    response = agent.run(request())

    assert response.success is True
    assert response.chart_spec["chart_type"] == "bar"
    assert response.validation["passed"] is True
    assert response.chart_format == "png"
    assert response.rendered_chart is not None
    assert response.rendered_chart.startswith(b"\x89PNG")


def test_run_preserves_source_rows_in_chart_spec():
    agent = VisualizationAgent()
    result = FakeSQLResult()

    response = agent.run(request(result=result))

    assert response.success is True
    assert response.chart_spec["data"] == result.rows
    assert response.chart_spec["source"]["columns"] == result.columns


def test_chart_validation_rejects_fabricated_data():
    agent = VisualizationAgent()
    result = FakeSQLResult()
    spec = agent._build_chart_spec(
        "revenue by category",
        result,
        "bar",
    )
    spec["data"][0]["net_revenue"] = 999999

    passed, errors = agent.validate_chart_spec(spec, result)

    assert passed is False
    assert "exactly match source result rows" in errors[0]


def test_chart_validation_rejects_unknown_field():
    agent = VisualizationAgent()
    result = FakeSQLResult()
    spec = agent._build_chart_spec(
        "revenue by category",
        result,
        "bar",
    )
    spec["y_axis"]["field"] = "profit"

    passed, errors = agent.validate_chart_spec(spec, result)

    assert passed is False
    assert "not present in source result" in errors[0]


def test_run_single_kpi_succeeds_without_rendered_chart():
    agent = VisualizationAgent()
    result = FakeSQLResult(
        columns=["net_revenue"],
        rows=[{"net_revenue": 1000}],
    )

    response = agent.run(request(result=result))

    assert response.success is True
    assert response.chart_spec["chart_type"] == "none"
    assert response.rendered_chart is None
    assert response.chart_format is None
    assert response.validation["passed"] is True


def test_run_preserves_evidence_and_provenance():
    agent = VisualizationAgent()
    result = FakeSQLResult()

    response = agent.run(request(result=result))

    assert response.evidence == result.evidence
    assert response.provenance == result.provenance


def test_validate_request_rejects_wrong_request_type():
    agent = VisualizationAgent()
    errors = agent.validate_request(None)
    assert errors == ["Request must be a VisualizationAgentRequest."]


def test_validate_request_rejects_missing_result():
    agent = VisualizationAgent()
    errors = agent.validate_request(
        VisualizationAgentRequest(
            question="revenue",
            result=None,
        )
    )
    assert errors == ["Result must not be None."]


def test_supported_chart_types_are_deterministic():
    agent = VisualizationAgent()
    assert agent.select_chart("revenue", FakeSQLResult()) == "bar"
    assert agent.select_chart("revenue", FakeSQLResult()) == "bar"


def test_rendered_chart_is_valid_png_artifact():
    agent = VisualizationAgent()
    response = agent.run(request())

    assert response.success is True
    assert response.chart_format == "png"
    assert response.rendered_chart[:8] == b"\x89PNG\r\n\x1a\n"
