import re
from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.agents.insight_agent import (
    InsightAgent,
    InsightAgentRequest,
)
from app.agents.sql_agent import (
    SQLAgentRequest,
    SQLAnalystAgent,
)
from app.tools.analytics import (
    AnalyticsEngine,
    load_semantic_catalog,
)


@dataclass
class RootCauseAgentRequest:
    """Input contract for the Root-Cause Agent."""

    question: str


@dataclass
class RootCauseAgentResponse:
    """Output contract for the Root-Cause Agent."""

    success: bool
    answer: str | None
    findings: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    provenance: list[dict[str, Any]]
    errors: list[str]


class RootCauseAgent:
    """Evidence-grounded Root-Cause Agent."""

    def __init__(self):
        self.sql_agent = SQLAnalystAgent()
        self.analytics_engine = AnalyticsEngine(
            load_semantic_catalog()
        )
        self.insight_agent = InsightAgent()

    def validate_request(
        self,
        request: RootCauseAgentRequest,
    ) -> list[str]:
        """Validate the root-cause request."""

        errors = []

        if not isinstance(request, RootCauseAgentRequest):
            errors.append(
                "Request must be a RootCauseAgentRequest."
            )
            return errors

        if not isinstance(request.question, str):
            errors.append("Question must be a string.")
            return errors

        if not request.question.strip():
            errors.append("Question must not be empty.")

        return errors

    def _replace_year(
        self,
        question: str,
        year: int,
    ) -> str:
        """Replace the explicit four-digit year in a question."""

        return re.sub(
            r"\b20\d{2}\b",
            str(year),
            question,
            count=1,
        )

    def _build_period_questions(
        self,
        question: str,
        current_year: int,
    ) -> tuple[str, str]:
        """Build current and previous-period SQL Analyst questions."""

        previous_year = current_year - 1

        current_question = self._replace_year(
            question,
            current_year,
        )

        previous_question = self._replace_year(
            question,
            previous_year,
        )

        return current_question, previous_question

    def _rows_to_dataframe(
        self,
        rows: list[dict[str, Any]],
    ) -> pd.DataFrame:
        """Convert SQL Analyst rows into an analytics DataFrame."""

        return pd.DataFrame(rows)

    def _build_comparison_evidence(
        self,
        comparison,
        metric: str,
        current_year: int,
        previous_year: int,
    ) -> dict[str, Any]:
        """Convert Analytics Engine comparison into structured evidence."""

        return {
            "type": "comparison",
            "metric": metric,
            "current_period": str(current_year),
            "previous_period": str(previous_year),
            "direction": comparison.direction,
            "current_value": comparison.current_value,
            "previous_value": comparison.previous_value,
            "absolute_change": comparison.absolute_change,
            "percentage_change": comparison.percentage_change,
        }

    def _build_contribution_evidence(
        self,
        contributions,
        current_year: int,
        previous_year: int,
    ) -> list[dict[str, Any]]:
        """Convert contribution results into structured evidence."""

        evidence = []

        for contribution in contributions:
            evidence.append(
                {
                    "type": "contribution",
                    "dimension": contribution.dimension,
                    "group": contribution.group,
                    "current_period": str(current_year),
                    "previous_period": str(previous_year),
                    "current_value": contribution.current_value,
                    "previous_value": contribution.previous_value,
                    "absolute_change": contribution.absolute_change,
                    "contribution_percentage": (
                        contribution.contribution_percentage
                    ),
                }
            )

        return evidence

    def run(
        self,
        request: RootCauseAgentRequest,
    ) -> RootCauseAgentResponse:
        """Run the complete Root-Cause Agent workflow."""

        request_errors = self.validate_request(request)

        if request_errors:
            return RootCauseAgentResponse(
                success=False,
                answer=None,
                findings=[],
                evidence=[],
                provenance=[],
                errors=request_errors,
            )

        question = request.question.strip()

        year_matches = re.findall(
            r"\b20\d{2}\b",
            question,
        )

        if not year_matches:
            return RootCauseAgentResponse(
                success=False,
                answer=None,
                findings=[],
                evidence=[],
                provenance=[],
                errors=[
                    "An explicit four-digit year is required "
                    "for root-cause analysis."
                ],
            )

        current_year = int(year_matches[0])
        previous_year = current_year - 1

        current_question, previous_question = (
            self._build_period_questions(
                question,
                current_year,
            )
        )

        current_response = self.sql_agent.run(
            SQLAgentRequest(
                question=current_question,
            )
        )

        if not current_response.success:
            return RootCauseAgentResponse(
                success=False,
                answer=None,
                findings=[],
                evidence=[],
                provenance=[],
                errors=[
                    "Current-period SQL analysis failed: "
                    + "; ".join(current_response.errors)
                ],
            )

        previous_response = self.sql_agent.run(
            SQLAgentRequest(
                question=previous_question,
            )
        )

        if not previous_response.success:
            return RootCauseAgentResponse(
                success=False,
                answer=None,
                findings=[],
                evidence=[],
                provenance=[],
                errors=[
                    "Previous-period SQL analysis failed: "
                    + "; ".join(previous_response.errors)
                ],
            )

        current_data = self._rows_to_dataframe(
            current_response.rows
        )

        previous_data = self._rows_to_dataframe(
            previous_response.rows
        )

        try:
            current_spec = self.sql_agent.build_analysis_spec(
                SQLAgentRequest(
                    question=current_question,
                )
            )

            metric = current_spec.metric

            if not current_spec.dimensions:
                return RootCauseAgentResponse(
                    success=False,
                    answer=None,
                    findings=[],
                    evidence=[],
                    provenance=[],
                    errors=[
                        "Root-cause analysis requires a comparison dimension, "
                        "such as category, product, or brand."
                    ],
                )

            dimension = current_spec.dimensions[0]

            current_total = float(
                current_data["net_revenue"].sum()
            )

            previous_total = float(
                previous_data["net_revenue"].sum()
            )

            absolute_change = current_total - previous_total

            if previous_total == 0:
                percentage_change = None
            else:
                percentage_change = (
                    absolute_change / previous_total
                ) * 100

            if absolute_change > 0:
                direction = "increased"
            elif absolute_change < 0:
                direction = "decreased"
            else:
                direction = "unchanged"

            evidence = [
                {
                    "type": "comparison",
                    "metric": metric,
                    "current_period": str(current_year),
                    "previous_period": str(previous_year),
                    "direction": direction,
                    "current_value": current_total,
                    "previous_value": previous_total,
                    "absolute_change": absolute_change,
                    "percentage_change": percentage_change,
                }
            ]

            groups = sorted(
                set(current_data[dimension].dropna().unique())
                | set(previous_data[dimension].dropna().unique()),
                key=str,
            )

            group_changes = []

            for group in groups:
                current_group = current_data[
                    current_data[dimension] == group
                ]

                previous_group = previous_data[
                    previous_data[dimension] == group
                ]

                current_value = float(
                    current_group["net_revenue"].sum()
                )

                previous_value = float(
                    previous_group["net_revenue"].sum()
                )

                group_change = (
                    current_value - previous_value
                )

                group_changes.append(
                    (
                        group,
                        current_value,
                        previous_value,
                        group_change,
                    )
                )

            for (
                group,
                current_value,
                previous_value,
                group_change,
            ) in group_changes:

                if absolute_change == 0:
                    contribution_percentage = None
                else:
                    contribution_percentage = (
                        group_change / absolute_change
                    ) * 100

                evidence.append(
                    {
                        "type": "contribution",
                        "dimension": dimension,
                        "group": group,
                        "current_period": str(current_year),
                        "previous_period": str(previous_year),
                        "current_value": current_value,
                        "previous_value": previous_value,
                        "absolute_change": group_change,
                        "contribution_percentage": (
                            contribution_percentage
                        ),
                    }
                )
        except Exception as exc:
            return RootCauseAgentResponse(
                success=False,
                answer=None,
                findings=[],
                evidence=[],
                provenance=[],
                errors=[
                    f"Root-cause analysis failed: {exc}"
                ],
            )

        insight_response = self.insight_agent.run(
            InsightAgentRequest(
                question=question,
                evidence=evidence,
            )
        )

        if not insight_response.success:
            return RootCauseAgentResponse(
                success=False,
                answer=None,
                findings=[],
                evidence=evidence,
                provenance=[],
                errors=insight_response.errors,
            )

        provenance = [
            {
                "agent": "root_cause_agent",
                "source": "sql_analyst_and_analytics_engine",
                "current_period": str(current_year),
                "previous_period": str(previous_year),
                "metric": metric,
                "dimension": dimension,
            }
        ]

        provenance.extend(insight_response.provenance)

        return RootCauseAgentResponse(
            success=True,
            answer=insight_response.answer,
            findings=insight_response.findings,
            evidence=evidence,
            provenance=provenance,
            errors=[],
        )