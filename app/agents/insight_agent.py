"""Evidence-grounded Insight Agent.

The Insight Agent interprets structured analytical evidence produced by
governed project components. It does not access the database or perform
independent analytical calculations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


SUPPORTED_FINDING_TYPES = {
    "observed",
    "evidence_backed",
    "hypothesis",
    "insufficient_evidence",
}


@dataclass
class InsightAgentRequest:
    """Request supplied to the Insight Agent."""

    question: str
    evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class InsightFinding:
    """A structured finding derived from supplied evidence."""

    type: str
    statement: str
    supporting_evidence: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class InsightAgentResponse:
    """Structured response returned by the Insight Agent."""

    success: bool
    answer: str | None = None
    findings: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    provenance: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class InsightAgent:
    """Interpret governed analytical evidence into business findings."""

    def __init__(self) -> None:
        """Initialize the Insight Agent.

        The agent intentionally has no database connection and no external
        data dependencies.
        """

    def validate_request(self, request: InsightAgentRequest) -> list[str]:
        """Validate an Insight Agent request."""

        errors: list[str] = []

        if not isinstance(request, InsightAgentRequest):
            return ["Request must be an InsightAgentRequest."]

        if not isinstance(request.question, str):
            errors.append("Question must be a string.")
        elif not request.question.strip():
            errors.append("Question must not be empty.")

        if not isinstance(request.evidence, list):
            errors.append("Evidence must be a list.")
        else:
            for index, item in enumerate(request.evidence):
                if not isinstance(item, dict):
                    errors.append(
                        f"Evidence item {index} must be a dictionary."
                    )

        return errors

    def build_finding(
        self,
        finding_type: str,
        statement: str,
        supporting_evidence: list[dict[str, Any]] | None = None,
    ) -> InsightFinding:
        """Build a validated structured finding."""

        if finding_type not in SUPPORTED_FINDING_TYPES:
            raise ValueError(
                f"Unsupported finding type: {finding_type}"
            )

        if not isinstance(statement, str) or not statement.strip():
            raise ValueError("Finding statement must not be empty.")

        evidence = supporting_evidence or []

        return InsightFinding(
            type=finding_type,
            statement=statement.strip(),
            supporting_evidence=evidence,
        )

    def interpret_evidence(
        self,
        question: str,
        evidence: list[dict[str, Any]],
    ) -> list[InsightFinding]:
        """Convert supplied evidence into structured findings.

        This method only interprets explicitly supplied evidence. It does not
        perform new numerical calculations.
        """

        findings: list[InsightFinding] = []

        for item in evidence:
            evidence_type = item.get("type")

            if evidence_type == "comparison":
                finding = self._interpret_comparison(item)
                if finding is not None:
                    findings.append(finding)

            elif evidence_type == "contribution":
                finding = self._interpret_contribution(item)
                if finding is not None:
                    findings.append(finding)

            elif evidence_type in SUPPORTED_FINDING_TYPES:
                statement = item.get("statement")

                if isinstance(statement, str) and statement.strip():
                    findings.append(
                        self.build_finding(
                            evidence_type,
                            statement,
                            [item],
                        )
                    )

        if not findings:
            findings.append(
                self.build_finding(
                    "insufficient_evidence",
                    (
                        "The available evidence is insufficient to produce "
                        "a supported business finding."
                    ),
                    evidence,
                )
            )

        return findings

    def _interpret_comparison(
        self,
        evidence: dict[str, Any],
    ) -> InsightFinding | None:
        """Interpret a period comparison result."""

        direction = evidence.get("direction")
        percentage_change = evidence.get("percentage_change")
        absolute_change = evidence.get("absolute_change")
        metric = evidence.get("metric") or evidence.get("metric_id")

        if direction not in {
            "increase",
            "decrease",
            "no_change",
        }:
            return None

        metric_text = str(metric or "The metric")

        if direction == "no_change":
            statement = f"{metric_text} showed no change between the analyzed periods."

        elif percentage_change is not None:
            statement = (
                f"{metric_text} {direction}d by "
                f"{self._format_number(abs(percentage_change))}% "
                f"between the analyzed periods."
            )

        elif absolute_change is not None:
            statement = (
                f"{metric_text} showed an absolute {direction} "
                f"of {self._format_number(absolute_change)} "
                f"between the analyzed periods."
            )

        else:
            statement = (
                f"{metric_text} showed a {direction} between "
                "the analyzed periods."
            )

        return self.build_finding(
            "observed",
            statement,
            [evidence],
        )

    def _interpret_contribution(
        self,
        evidence: dict[str, Any],
    ) -> InsightFinding | None:
        """Interpret a contribution result without claiming causation."""

        dimension = evidence.get("dimension")
        group = evidence.get("group")
        contribution = evidence.get("contribution_percentage")
        absolute_change = evidence.get("absolute_change")

        if group is None:
            return None

        group_text = str(group)
        dimension_text = str(dimension or "dimension")

        if contribution is not None:
            statement = (
                f"{group_text} in {dimension_text} had a "
                f"{self._format_number(contribution)}% contribution "
                "to the measured metric change."
            )
        elif absolute_change is not None:
            statement = (
                f"{group_text} in {dimension_text} had an absolute "
                f"change of {self._format_number(absolute_change)} "
                "in the measured metric."
            )
        else:
            statement = (
                f"{group_text} in {dimension_text} was identified in "
                "the supplied contribution evidence."
            )

        return self.build_finding(
            "evidence_backed",
            statement,
            [evidence],
        )

    @staticmethod
    def _format_number(value: Any) -> str:
        """Format numeric values without changing their meaning."""

        if isinstance(value, bool):
            return str(value)

        if isinstance(value, int):
            return f"{value:,}"

        if isinstance(value, float):
            return f"{value:,.2f}".rstrip("0").rstrip(".")

        return str(value)

    def format_answer(
        self,
        findings: list[InsightFinding],
    ) -> str | None:
        """Build a deterministic answer from structured findings."""

        if not findings:
            return None

        statements = [
            finding.statement
            for finding in findings
            if finding.statement.strip()
        ]

        if not statements:
            return None

        return " ".join(statements)

    def run(
        self,
        request: InsightAgentRequest,
    ) -> InsightAgentResponse:
        """Run the Insight Agent."""

        validation_errors = self.validate_request(request)

        if validation_errors:
            return InsightAgentResponse(
                success=False,
                errors=validation_errors,
            )

        findings = self.interpret_evidence(
            request.question,
            request.evidence,
        )

        answer = self.format_answer(findings)

        provenance = [
            {
                "agent": "insight_agent",
                "source": "supplied_structured_evidence",
                "finding_count": len(findings),
            }
        ]

        return InsightAgentResponse(
            success=True,
            answer=answer,
            findings=[
                {
                    "type": finding.type,
                    "statement": finding.statement,
                    "supporting_evidence": finding.supporting_evidence,
                }
                for finding in findings
            ],
            evidence=request.evidence,
            provenance=provenance,
            errors=[],
        )