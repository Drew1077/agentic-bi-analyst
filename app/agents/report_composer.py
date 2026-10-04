"""Structured Report Composer.

The Report Composer combines already-validated analytical content into a
deterministic report structure. It does not query the database or create new
analytical evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ReportComposerRequest:
    """Input contract for the Report Composer."""

    question: str
    analytical_result: Any
    findings: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[dict[str, Any]] = field(default_factory=list)
    visualization: Any = None


@dataclass
class ReportComposerResponse:
    """Output contract for the Report Composer."""

    success: bool
    report: dict[str, Any] | None
    evidence: Any
    provenance: Any
    validation: dict[str, Any]
    errors: list[str] = field(default_factory=list)


class ReportComposer:
    """Compose validated findings into a structured business report."""

    def validate_request(
        self,
        request: ReportComposerRequest,
    ) -> list[str]:
        errors: list[str] = []

        if not isinstance(request, ReportComposerRequest):
            return ["Request must be a ReportComposerRequest."]

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

        if not isinstance(request.recommendations, list):
            errors.append("Recommendations must be a list.")
        else:
            for index, recommendation in enumerate(request.recommendations):
                if not isinstance(recommendation, dict):
                    errors.append(
                        f"Recommendation {index} must be a dictionary."
                    )
                    continue

                if not recommendation.get("recommendation"):
                    errors.append(
                        f"Recommendation {index} must contain text."
                    )

                supporting = recommendation.get(
                    "supporting_evidence",
                    [],
                )
                if not isinstance(supporting, list) or not supporting:
                    errors.append(
                        f"Recommendation {index} must contain supporting evidence."
                    )

        visualization = request.visualization
        if visualization is not None:
            if getattr(visualization, "success", None) is not True:
                errors.append(
                    "Visualization must be successful when supplied."
                )

        return errors

    @staticmethod
    def _build_findings(
        findings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {
                "type": finding.get("type"),
                "statement": finding.get("statement"),
                "supporting_evidence": finding.get(
                    "supporting_evidence",
                    [],
                ),
            }
            for finding in findings
        ]

    @staticmethod
    def _build_visualization(
        visualization: Any,
    ) -> dict[str, Any] | None:
        if visualization is None:
            return None

        return {
            "chart_spec": getattr(
                visualization,
                "chart_spec",
                None,
            ),
            "chart_format": getattr(
                visualization,
                "chart_format",
                None,
            ),
            "rendered_chart": getattr(
                visualization,
                "rendered_chart",
                None,
            ),
            "validation": getattr(
                visualization,
                "validation",
                {},
            ),
        }

    @staticmethod
    def _build_limitations(
        findings: list[dict[str, Any]],
        recommendations: list[dict[str, Any]],
    ) -> list[str]:
        limitations: list[str] = []

        if any(
            finding.get("type") == "hypothesis"
            for finding in findings
        ):
            limitations.append(
                "Some supplied findings are hypotheses and require "
                "additional validation."
            )

        if any(
            finding.get("type") == "insufficient_evidence"
            for finding in findings
        ):
            limitations.append(
                "The supplied evidence is insufficient for some findings."
            )

        if any(
            recommendation.get("potential_impact", {}).get("type")
            == "not_available"
            for recommendation in recommendations
        ):
            limitations.append(
                "Potential impact was not available from the supplied evidence."
            )

        limitations.append(
            "Recommendations are evidence-backed actions for review; they "
            "do not establish causation unless explicitly supported by evidence."
        )

        return limitations

    def compose(
        self,
        request: ReportComposerRequest,
    ) -> dict[str, Any]:
        result = request.analytical_result

        answer = getattr(result, "answer", None)
        evidence = getattr(result, "evidence", None)
        provenance = getattr(result, "provenance", None)

        return {
            "title": "Business Analysis Report",
            "question": request.question.strip(),
            "executive_summary": answer,
            "key_results": {
                "answer": answer,
                "columns": getattr(result, "columns", []),
                "rows": getattr(result, "rows", []),
            },
            "findings": self._build_findings(request.findings),
            "visualization": self._build_visualization(
                request.visualization
            ),
            "recommendations": request.recommendations,
            "methodology": {
                "source": "validated analytical result and supplied findings",
                "database_access": False,
                "new_analysis_performed": False,
            },
            "evidence": evidence,
            "provenance": provenance,
            "limitations": self._build_limitations(
                request.findings,
                request.recommendations,
            ),
        }

    def validate_report(
        self,
        report: dict[str, Any],
        request: ReportComposerRequest,
    ) -> tuple[bool, list[str]]:
        errors: list[str] = []

        if not isinstance(report, dict):
            return False, ["Report must be a dictionary."]

        required_sections = {
            "title",
            "question",
            "executive_summary",
            "key_results",
            "findings",
            "visualization",
            "recommendations",
            "methodology",
            "evidence",
            "provenance",
            "limitations",
        }

        missing = required_sections - set(report)
        if missing:
            errors.append(
                "Report is missing sections: "
                + ", ".join(sorted(missing))
            )

        if report.get("question") != request.question.strip():
            errors.append("Report question does not match the request.")

        if report.get("findings") != self._build_findings(
            request.findings
        ):
            errors.append("Report findings do not match supplied findings.")

        if report.get("recommendations") != request.recommendations:
            errors.append(
                "Report recommendations do not match supplied recommendations."
            )

        return not errors, errors

    def run(
        self,
        request: ReportComposerRequest,
    ) -> ReportComposerResponse:
        errors = self.validate_request(request)

        if errors:
            result = request.analytical_result
            return ReportComposerResponse(
                success=False,
                report=None,
                evidence=getattr(result, "evidence", None),
                provenance=getattr(result, "provenance", None),
                validation={"passed": False, "errors": errors},
                errors=errors,
            )

        report = self.compose(request)
        passed, validation_errors = self.validate_report(
            report,
            request,
        )

        if not passed:
            return ReportComposerResponse(
                success=False,
                report=report,
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
                validation={
                    "passed": False,
                    "errors": validation_errors,
                },
                errors=validation_errors,
            )

        return ReportComposerResponse(
            success=True,
            report=report,
            evidence=getattr(
                request.analytical_result,
                "evidence",
                None,
            ),
            provenance={
                "analytical_result": getattr(
                    request.analytical_result,
                    "provenance",
                    None,
                ),
                "report_composer": {
                    "source": "validated_inputs",
                    "section_order": [
                        "title",
                        "question",
                        "executive_summary",
                        "key_results",
                        "findings",
                        "visualization",
                        "recommendations",
                        "methodology",
                        "evidence",
                        "provenance",
                        "limitations",
                    ],
                },
            },
            validation={"passed": True, "errors": []},
            errors=[],
        )
