"""Evidence-backed Recommendation Agent.

The Recommendation Agent converts validated findings into deterministic,
traceable business actions. It does not access the database or create new
analytical evidence.
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
class RecommendationAgentRequest:
    """Input contract for the Recommendation Agent."""

    question: str
    analytical_result: Any
    findings: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Recommendation:
    """One evidence-traceable business recommendation."""

    recommendation: str
    supporting_evidence: list[dict[str, Any]] = field(default_factory=list)
    owner: str = "Relevant business function"
    potential_impact: dict[str, Any] = field(
        default_factory=lambda: {
            "type": "not_available",
            "value": None,
            "assumptions": [],
        }
    )
    priority: str = "low"
    priority_basis: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    evidence_strength: str = "limited"


@dataclass
class RecommendationAgentResponse:
    """Output contract for the Recommendation Agent."""

    success: bool
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    evidence: Any = None
    provenance: Any = None
    errors: list[str] = field(default_factory=list)


class RecommendationAgent:
    """Convert validated findings into traceable business recommendations."""

    def validate_request(
        self,
        request: RecommendationAgentRequest,
    ) -> list[str]:
        errors: list[str] = []

        if not isinstance(request, RecommendationAgentRequest):
            return ["Request must be a RecommendationAgentRequest."]

        if not isinstance(request.question, str):
            errors.append("Question must be a string.")
        elif not request.question.strip():
            errors.append("Question must not be empty.")

        result = request.analytical_result
        if result is None:
            errors.append("Analytical result must not be None.")
        elif getattr(result, "success", None) is not True:
            errors.append("Analytical result must be successful.")

        if not isinstance(request.findings, list):
            errors.append("Findings must be a list.")
        else:
            for index, finding in enumerate(request.findings):
                if not isinstance(finding, dict):
                    errors.append(
                        f"Finding {index} must be a dictionary."
                    )
                    continue

                finding_type = finding.get("type")
                if finding_type not in SUPPORTED_FINDING_TYPES:
                    errors.append(
                        f"Finding {index} has unsupported type: "
                        f"{finding_type}"
                    )

                statement = finding.get("statement")
                if not isinstance(statement, str) or not statement.strip():
                    errors.append(
                        f"Finding {index} must contain a non-empty statement."
                    )

                supporting = finding.get("supporting_evidence", [])
                if not isinstance(supporting, list):
                    errors.append(
                        f"Finding {index} supporting_evidence must be a list."
                    )
                elif not supporting:
                    errors.append(
                        f"Finding {index} must have supporting evidence."
                    )

        return errors

    @staticmethod
    def _direction(finding: dict[str, Any]) -> str | None:
        for evidence in finding.get("supporting_evidence", []):
            direction = evidence.get("direction")
            if direction in {"increase", "decrease", "no_change"}:
                return direction
        return None

    @staticmethod
    def _contribution_context(
        finding: dict[str, Any],
    ) -> tuple[str | None, str | None]:
        for evidence in finding.get("supporting_evidence", []):
            if evidence.get("type") == "contribution":
                return (
                    str(evidence["group"])
                    if evidence.get("group") is not None
                    else None,
                    str(evidence["dimension"])
                    if evidence.get("dimension") is not None
                    else None,
                )
        return None, None

    @staticmethod
    def _impact_from_evidence(
        finding: dict[str, Any],
    ) -> dict[str, Any]:
        for evidence in finding.get("supporting_evidence", []):
            if "potential_impact" in evidence:
                return {
                    "type": "estimated",
                    "value": evidence.get("potential_impact"),
                    "assumptions": list(
                        evidence.get("impact_assumptions", [])
                    ),
                }

            if "impact_estimate" in evidence:
                return {
                    "type": "estimated",
                    "value": evidence.get("impact_estimate"),
                    "assumptions": list(
                        evidence.get("impact_assumptions", [])
                    ),
                }

        return {
            "type": "not_available",
            "value": None,
            "assumptions": [],
        }

    def _build_recommendation(
        self,
        finding: dict[str, Any],
    ) -> Recommendation | None:
        finding_type = finding["type"]

        # Hypotheses and insufficient evidence are not converted into
        # operational actions because doing so would turn uncertainty into
        # unsupported business advice.
        if finding_type in {"hypothesis", "insufficient_evidence"}:
            return None

        statement = finding["statement"]
        evidence = finding["supporting_evidence"]
        direction = self._direction(finding)
        group, dimension = self._contribution_context(finding)

        if group and dimension:
            recommendation = (
                f"Review the drivers affecting {group} in {dimension} "
                "and identify a targeted corrective or growth action "
                "supported by the observed contribution."
            )
            owner = f"{dimension.title()} / Commercial function"
            priority = "high" if finding_type == "evidence_backed" else "medium"
            priority_basis = [
                "validated contribution evidence",
                "finding is directly supported by supplied evidence",
            ]
            assumptions = [
                "The measured contribution identifies an area for review; "
                "it does not by itself establish causation."
            ]
        elif direction == "decrease":
            recommendation = (
                "Investigate the validated decline and review the relevant "
                "business drivers before selecting a corrective action."
            )
            owner = "Relevant business function"
            priority = "medium"
            priority_basis = [
                "validated decrease in the measured metric",
            ]
            assumptions = [
                "The observed change is a signal for investigation and does "
                "not by itself establish the underlying cause."
            ]
        elif direction == "increase":
            recommendation = (
                "Review the validated increase to identify repeatable "
                "drivers and assess whether the favorable pattern can be "
                "sustained or expanded."
            )
            owner = "Relevant business function"
            priority = "medium"
            priority_basis = [
                "validated increase in the measured metric",
            ]
            assumptions = [
                "The observed increase is descriptive and does not by itself "
                "establish which business action caused it."
            ]
        elif direction == "no_change":
            recommendation = (
                "Continue monitoring the metric and investigate only if "
                "future evidence shows a material change."
            )
            owner = "Relevant business function"
            priority = "low"
            priority_basis = [
                "validated no-change result",
            ]
            assumptions = []
        else:
            recommendation = (
                "Review the finding with the relevant business function "
                "and determine an action using the supplied evidence."
            )
            owner = "Relevant business function"
            priority = "medium"
            priority_basis = [
                "finding is supported by supplied analytical evidence",
            ]
            assumptions = [
                "The supplied finding is sufficient for review but not for "
                "claiming causation."
            ]

        evidence_strength = (
            "strong"
            if finding_type == "evidence_backed"
            else "moderate"
        )

        return Recommendation(
            recommendation=recommendation,
            supporting_evidence=evidence,
            owner=owner,
            potential_impact=self._impact_from_evidence(finding),
            priority=priority,
            priority_basis=priority_basis,
            assumptions=assumptions,
            evidence_strength=evidence_strength,
        )

    def run(
        self,
        request: RecommendationAgentRequest,
    ) -> RecommendationAgentResponse:
        errors = self.validate_request(request)

        if errors:
            return RecommendationAgentResponse(
                success=False,
                evidence=getattr(
                    request.analytical_result,
                    "evidence",
                    None,
                ),
                provenance=getattr(
                    request.analytical_result,
                    "provenance",
                    None,
                ),
                errors=errors,
            )

        recommendations: list[Recommendation] = []

        for finding in request.findings:
            recommendation = self._build_recommendation(finding)
            if recommendation is not None:
                recommendations.append(recommendation)

        serialized = [
            {
                "recommendation": item.recommendation,
                "supporting_evidence": item.supporting_evidence,
                "owner": item.owner,
                "potential_impact": item.potential_impact,
                "priority": item.priority,
                "priority_basis": item.priority_basis,
                "assumptions": item.assumptions,
                "evidence_strength": item.evidence_strength,
            }
            for item in recommendations
        ]

        analytical_result = request.analytical_result
        provenance = {
            "agent": "recommendation_agent",
            "source": "validated_findings",
            "recommendation_count": len(serialized),
        }

        return RecommendationAgentResponse(
            success=True,
            recommendations=serialized,
            evidence=getattr(analytical_result, "evidence", None),
            provenance={
                "analytical_result": getattr(
                    analytical_result,
                    "provenance",
                    None,
                ),
                "recommendation": provenance,
            },
            errors=[],
        )
