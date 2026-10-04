from decimal import Decimal

from app.agents.root_cause_agent import (
    RootCauseAgent,
    RootCauseAgentRequest,
)
from app.agents.sql_agent import SQLAgentResponse


def make_sql_response(rows):
    return SQLAgentResponse(
        success=True,
        answer="Revenue analysis completed.",
        sql="SELECT ...",
        columns=["category", "net_revenue"],
        rows=rows,
        evidence={
            "metric": "net_revenue",
            "dimensions": ["category"],
        },
        provenance={
            "agent": "sql_analyst",
        },
        errors=[],
    )


def test_root_cause_success(monkeypatch):
    agent = RootCauseAgent.__new__(RootCauseAgent)

    class FakeSQLAgent:
        def build_analysis_spec(self, request):
            class Spec:
                metric = "net_revenue"
                dimensions = ["category"]

            return Spec()

        def run(self, request):
            if "2025" in request.question:
                return make_sql_response(
                    [
                        {
                            "category": "A",
                            "net_revenue": Decimal("120"),
                        },
                        {
                            "category": "B",
                            "net_revenue": Decimal("80"),
                        },
                    ]
                )

            return make_sql_response(
                [
                    {
                        "category": "A",
                        "net_revenue": Decimal("100"),
                    },
                    {
                        "category": "B",
                        "net_revenue": Decimal("100"),
                    },
                ]
            )

    agent.sql_agent = FakeSQLAgent()

    from app.agents.insight_agent import InsightAgent

    agent.insight_agent = InsightAgent()

    response = agent.run(
        RootCauseAgentRequest(
            question="Why did revenue by category change in 2025?"
        )
    )

    assert response.success is True
    assert response.answer is not None
    assert response.errors == []

    comparison = next(
        item
        for item in response.evidence
        if item["type"] == "comparison"
    )

    assert comparison["current_value"] == 200.0
    assert comparison["previous_value"] == 200.0
    assert comparison["absolute_change"] == 0.0

    contributions = [
        item
        for item in response.evidence
        if item["type"] == "contribution"
    ]

    assert len(contributions) == 2


def test_root_cause_detects_decrease():
    agent = RootCauseAgent.__new__(RootCauseAgent)

    class FakeSQLAgent:
        def build_analysis_spec(self, request):
            class Spec:
                metric = "net_revenue"
                dimensions = ["category"]

            return Spec()

        def run(self, request):
            if "2025" in request.question:
                return make_sql_response(
                    [
                        {
                            "category": "A",
                            "net_revenue": Decimal("90"),
                        },
                    ]
                )

            return make_sql_response(
                [
                    {
                        "category": "A",
                        "net_revenue": Decimal("100"),
                    },
                ]
            )

    agent.sql_agent = FakeSQLAgent()

    from app.agents.insight_agent import InsightAgent

    agent.insight_agent = InsightAgent()

    response = agent.run(
        RootCauseAgentRequest(
            question="Why did revenue by category change in 2025?"
        )
    )

    comparison = next(
        item
        for item in response.evidence
        if item["type"] == "comparison"
    )

    assert comparison["direction"] == "decreased"
    assert comparison["percentage_change"] == -10.0


def test_root_cause_contribution_is_calculated():
    agent = RootCauseAgent.__new__(RootCauseAgent)

    class FakeSQLAgent:
        def build_analysis_spec(self, request):
            class Spec:
                metric = "net_revenue"
                dimensions = ["category"]

            return Spec()

        def run(self, request):
            if "2025" in request.question:
                return make_sql_response(
                    [
                        {
                            "category": "A",
                            "net_revenue": Decimal("150"),
                        },
                        {
                            "category": "B",
                            "net_revenue": Decimal("100"),
                        },
                    ]
                )

            return make_sql_response(
                [
                    {
                        "category": "A",
                        "net_revenue": Decimal("100"),
                    },
                    {
                        "category": "B",
                        "net_revenue": Decimal("100"),
                    },
                ]
            )

    agent.sql_agent = FakeSQLAgent()

    from app.agents.insight_agent import InsightAgent

    agent.insight_agent = InsightAgent()

    response = agent.run(
        RootCauseAgentRequest(
            question="Why did revenue by category change in 2025?"
        )
    )

    contributions = {
        item["group"]: item
        for item in response.evidence
        if item["type"] == "contribution"
    }

    assert contributions["A"]["absolute_change"] == 50.0
    assert contributions["B"]["absolute_change"] == 0.0
    assert contributions["A"]["contribution_percentage"] == 100.0
    assert contributions["B"]["contribution_percentage"] == 0.0


def test_root_cause_requires_year():
    agent = RootCauseAgent.__new__(RootCauseAgent)

    response = agent.run(
        RootCauseAgentRequest(
            question="Why did revenue change?"
        )
    )

    assert response.success is False
    assert response.answer is None
    assert any(
        "explicit four-digit year" in error
        for error in response.errors
    )


def test_root_cause_propagates_sql_failure():
    agent = RootCauseAgent.__new__(RootCauseAgent)

    class FakeSQLAgent:
        def build_analysis_spec(self, request):
            class Spec:
                metric = "net_revenue"
                dimensions = ["category"]

            return Spec()

        def run(self, request):
            return SQLAgentResponse(
                success=False,
                answer=None,
                sql=None,
                columns=[],
                rows=[],
                evidence={},
                provenance={},
                errors=["SQL execution failed."],
            )

    agent.sql_agent = FakeSQLAgent()

    response = agent.run(
        RootCauseAgentRequest(
            question="Why did revenue by category change in 2025?"
        )
    )

    assert response.success is False
    assert response.answer is None
    assert any(
        "SQL analysis failed" in error
        for error in response.errors
    )