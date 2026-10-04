from dataclasses import dataclass
from typing import Any


SUPPORTED_FINDING_TYPES = {
    "observed",
    "evidence_backed",
    "hypothesis",
    "insufficient_evidence",
}


@dataclass
class CriticAgentRequest:
    """Input contract for the Validation/Critic Agent."""

    question: str
    result: Any


@dataclass
class CriticAgentResponse:
    """Output contract for the Validation/Critic Agent."""

    success: bool
    passed: bool
    issues: list[str]
    checks: list[dict[str, Any]]
    provenance: list[dict[str, Any]]
    errors: list[str]


class CriticAgent:
    """Deterministic validation agent for analytical results."""

    def validate_request(
        self,
        request: CriticAgentRequest,
    ) -> list[str]:
        """Validate the critic request."""

        errors = []

        if not isinstance(request, CriticAgentRequest):
            errors.append(
                "Request must be a CriticAgentRequest."
            )
            return errors

        if not isinstance(request.question, str):
            errors.append("Question must be a string.")
        elif not request.question.strip():
            errors.append("Question must not be empty.")

        if request.result is None:
            errors.append("Result must not be None.")

        return errors

    def _check_success(
        self,
        result: Any,
    ) -> tuple[bool, str | None]:
        """Check that the analytical result succeeded."""

        success = getattr(result, "success", None)

        if success is not True:
            return False, "Analytical result was not successful."

        return True, None

    def _check_answer(
        self,
        result: Any,
    ) -> tuple[bool, str | None]:
        """Check that a successful result contains an answer."""

        answer = getattr(result, "answer", None)

        if answer is None:
            return False, "Successful analytical result has no answer."

        if not isinstance(answer, str):
            return False, "Analytical answer must be a string."

        if not answer.strip():
            return False, "Successful analytical result has an empty answer."

        return True, None

    def _check_evidence(
        self,
        result: Any,
    ) -> tuple[bool, str | None]:
        """Check that analytical evidence has been preserved."""

        if not hasattr(result, "evidence"):
            return False, "Analytical result does not expose evidence."

        evidence = result.evidence

        if evidence is None:
            return False, "Analytical result contains no evidence."

        return True, None

    def _check_provenance(
        self,
        result: Any,
    ) -> tuple[bool, str | None]:
        """Check that provenance has been preserved."""

        if not hasattr(result, "provenance"):
            return False, "Analytical result does not expose provenance."

        provenance = result.provenance

        if provenance is None:
            return False, "Analytical result contains no provenance."

        return True, None

    def _check_findings(
        self,
        result: Any,
    ) -> tuple[bool, str | None]:
        """Validate structured findings when present."""

        if not hasattr(result, "findings"):
            return True, None

        findings = result.findings

        if not isinstance(findings, list):
            return False, "Findings must be a list."

        for index, finding in enumerate(findings):
            if not isinstance(finding, dict):
                return (
                    False,
                    f"Finding {index} must be a dictionary.",
                )

            finding_type = finding.get("type")

            if finding_type not in SUPPORTED_FINDING_TYPES:
                return (
                    False,
                    f"Finding {index} has an invalid type.",
                )

            statement = finding.get("statement")

            if not isinstance(statement, str) or not statement.strip():
                return (
                    False,
                    f"Finding {index} has no valid statement.",
                )

            if finding_type == "evidence_backed":
                supporting_evidence = finding.get(
                    "supporting_evidence"
                )

                if not supporting_evidence:
                    return (
                        False,
                        f"Evidence-backed finding {index} "
                        "has no supporting evidence.",
                    )

        return True, None

    def _check_numeric_evidence(
        self,
        result: Any,
    ) -> tuple[bool, str | None]:
        """Validate arithmetic consistency in comparison evidence."""

        if not hasattr(result, "evidence"):
            return True, None

        evidence = result.evidence

        if not isinstance(evidence, list):
            return True, None

        for index, item in enumerate(evidence):
            if not isinstance(item, dict):
                continue

            if item.get("type") != "comparison":
                continue

            current = item.get("current_value")
            previous = item.get("previous_value")
            absolute_change = item.get("absolute_change")

            if (
                isinstance(current, (int, float))
                and not isinstance(current, bool)
                and isinstance(previous, (int, float))
                and not isinstance(previous, bool)
                and isinstance(absolute_change, (int, float))
                and not isinstance(absolute_change, bool)
            ):
                expected_change = current - previous

                if abs(expected_change - absolute_change) > 1e-9:
                    return (
                        False,
                        f"Comparison evidence {index} has an "
                        "inconsistent absolute change.",
                    )

        return True, None

    def _run_checks(
        self,
        result: Any,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Run all deterministic validation checks."""

        checks = []
        issues = []

        check_functions = [
            ("result_success", self._check_success),
            ("answer_present", self._check_answer),
            ("evidence_preserved", self._check_evidence),
            ("provenance_preserved", self._check_provenance),
            ("findings_valid", self._check_findings),
            ("numeric_evidence_consistent", self._check_numeric_evidence),
        ]

        for name, check_function in check_functions:
            passed, issue = check_function(result)

            checks.append(
                {
                    "check": name,
                    "passed": passed,
                }
            )

            if not passed and issue is not None:
                issues.append(issue)

        return checks, issues

    def run(
        self,
        request: CriticAgentRequest,
    ) -> CriticAgentResponse:
        """Validate an analytical result."""

        validation_errors = self.validate_request(request)

        if validation_errors:
            return CriticAgentResponse(
                success=False,
                passed=False,
                issues=[],
                checks=[],
                provenance=[],
                errors=validation_errors,
            )

        checks, issues = self._run_checks(
            request.result
        )

        passed = not issues

        provenance = [
            {
                "agent": "critic_agent",
                "source": "deterministic_result_validation",
                "check_count": len(checks),
                "issue_count": len(issues),
                "passed": passed,
            }
        ]

        return CriticAgentResponse(
            success=True,
            passed=passed,
            issues=issues,
            checks=checks,
            provenance=provenance,
            errors=[],
        )