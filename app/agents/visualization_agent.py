from dataclasses import dataclass
from io import BytesIO
from typing import Any
from decimal import Decimal
from datetime import date, datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


SUPPORTED_CHART_TYPES = {
    "none",
    "line",
    "bar",
    "scatter",
    "heatmap",
    "waterfall",
}


@dataclass
class VisualizationAgentRequest:
    """Input contract for the Visualization Agent."""

    question: str
    result: Any


@dataclass
class VisualizationAgentResponse:
    """Output contract for the Visualization Agent."""

    success: bool
    chart_spec: dict[str, Any] | None
    rendered_chart: bytes | None
    chart_format: str | None
    validation: dict[str, Any]
    evidence: Any
    provenance: Any
    errors: list[str]


class VisualizationAgent:
    """Deterministic visualization agent for validated analytical results."""

    def validate_request(
        self,
        request: VisualizationAgentRequest,
    ) -> list[str]:
        errors: list[str] = []

        if not isinstance(request, VisualizationAgentRequest):
            return ["Request must be a VisualizationAgentRequest."]

        if not isinstance(request.question, str):
            errors.append("Question must be a string.")
        elif not request.question.strip():
            errors.append("Question must not be empty.")

        if request.result is None:
            errors.append("Result must not be None.")
        elif getattr(request.result, "success", None) is not True:
            errors.append("Analytical result must be successful.")

        return errors

    @staticmethod
    def _is_numeric(value: Any) -> bool:
        return (
            isinstance(value, (int, float, Decimal))
            and not isinstance(value, bool)
        )

    @staticmethod
    def _is_date_field(name: str) -> bool:
        normalized = name.lower()
        return any(
            token in normalized
            for token in (
                "date",
                "month",
                "year",
                "week",
                "quarter",
                "period",
            )
        )

    def _extract_rows(
        self,
        result: Any,
    ) -> tuple[list[str], list[dict[str, Any]], list[str]]:
        columns = getattr(result, "columns", None)
        rows = getattr(result, "rows", None)

        if not isinstance(columns, list):
            return [], [], ["Analytical result does not expose tabular columns."]

        if not isinstance(rows, list):
            return [], [], ["Analytical result does not expose tabular rows."]

        normalized_columns = [str(column) for column in columns]
        normalized_rows: list[dict[str, Any]] = []

        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                return [], [], [f"Result row {index} must be a dictionary."]
            normalized_rows.append(dict(row))

        return normalized_columns, normalized_rows, []

    def _root_cause_data(
        self,
        result: Any,
    ) -> list[dict[str, Any]]:
        evidence = getattr(result, "evidence", None)

        if not isinstance(evidence, list):
            return []

        contributions = [
            item
            for item in evidence
            if isinstance(item, dict)
            and item.get("type") == "contribution"
            and isinstance(item.get("group"), str)
            and self._is_numeric(item.get("absolute_change"))
        ]

        return contributions

    def select_chart(
        self,
        question: str,
        result: Any,
    ) -> str:
        """Select a chart type from the validated result structure."""

        root_cause = self._root_cause_data(result)
        if len(root_cause) >= 2:
            return "waterfall"

        columns, rows, _ = self._extract_rows(result)
        if not rows or not columns:
            return "none"

        numeric_columns = [
            column
            for column in columns
            if any(
                self._is_numeric(row.get(column))
                for row in rows
            )
        ]

        date_columns = [
            column
            for column in columns
            if self._is_date_field(column)
        ]

        categorical_columns = [
            column
            for column in columns
            if column not in numeric_columns
            and column not in date_columns
        ]

        if date_columns and numeric_columns:
            return "line"

        if len(categorical_columns) >= 2 and numeric_columns:
            return "heatmap"

        if len(categorical_columns) == 1 and numeric_columns:
            return "bar"

        if len(numeric_columns) >= 2:
            return "scatter"

        return "none"

    def _build_chart_spec(
        self,
        question: str,
        result: Any,
        chart_type: str,
    ) -> dict[str, Any]:
        root_cause = self._root_cause_data(result)

        if chart_type == "waterfall":
            return {
                "chart_type": "waterfall",
                "title": "Root-Cause Contribution",
                "x_axis": {
                    "field": "group",
                    "label": "Group",
                },
                "y_axis": {
                    "field": "absolute_change",
                    "label": "Absolute Change",
                    "unit": "source_value",
                },
                "series": [
                    {
                        "field": "absolute_change",
                        "label": "Absolute Change",
                    }
                ],
                "data": root_cause,
                "source": {
                    "type": "root_cause_evidence",
                    "row_count": len(root_cause),
                },
            }

        columns, rows, errors = self._extract_rows(result)
        if errors:
            raise ValueError(errors[0])

        numeric_columns = [
            column
            for column in columns
            if any(
                self._is_numeric(row.get(column))
                for row in rows
            )
        ]
        date_columns = [
            column
            for column in columns
            if self._is_date_field(column)
        ]
        categorical_columns = [
            column
            for column in columns
            if column not in numeric_columns
            and column not in date_columns
        ]

        if chart_type == "line":
            x_field = date_columns[0]
            y_field = numeric_columns[0]
        elif chart_type == "bar":
            x_field = categorical_columns[0]
            y_field = numeric_columns[0]
        elif chart_type == "scatter":
            x_field = numeric_columns[0]
            y_field = numeric_columns[1]
        elif chart_type == "heatmap":
            x_field = categorical_columns[0]
            y_field = categorical_columns[1]
            value_field = numeric_columns[0]
        else:
            x_field = None
            y_field = None

        spec: dict[str, Any] = {
            "chart_type": chart_type,
            "title": question.strip(),
            "x_axis": (
                {"field": x_field, "label": x_field}
                if x_field is not None
                else None
            ),
            "y_axis": (
                {"field": y_field, "label": y_field}
                if y_field is not None
                else None
            ),
            "series": (
                [{"field": y_field, "label": y_field}]
                if y_field is not None
                else []
            ),
            "data": rows,
            "source": {
                "type": "analytical_result",
                "columns": columns,
                "row_count": len(rows),
            },
        }

        if chart_type == "heatmap":
            spec["value_field"] = value_field

        return spec

    def validate_chart_spec(
        self,
        chart_spec: dict[str, Any],
        result: Any,
    ) -> tuple[bool, list[str]]:
        errors: list[str] = []

        if not isinstance(chart_spec, dict):
            return False, ["Chart specification must be a dictionary."]

        chart_type = chart_spec.get("chart_type")
        if chart_type not in SUPPORTED_CHART_TYPES:
            errors.append("Chart specification has an unsupported chart type.")
            return False, errors

        if chart_type == "none":
            return True, []

        data = chart_spec.get("data")
        if not isinstance(data, list) or not data:
            errors.append("Chart specification must contain non-empty data.")

        x_axis = chart_spec.get("x_axis")
        y_axis = chart_spec.get("y_axis")

        if not isinstance(x_axis, dict) or not x_axis.get("field"):
            errors.append("Chart specification requires an x-axis field.")

        if not isinstance(y_axis, dict) or not y_axis.get("field"):
            errors.append("Chart specification requires a y-axis field.")

        if chart_type != "waterfall":
            columns, rows, row_errors = self._extract_rows(result)
            errors.extend(row_errors)

            if not row_errors:
                source_fields = set(columns)
                for axis in (x_axis, y_axis):
                    field = axis["field"]
                    if field not in source_fields:
                        errors.append(
                            f"Chart field is not present in source result: {field}"
                        )

                if data != rows:
                    errors.append(
                        "Chart data does not exactly match source result rows."
                    )
        else:
            source_evidence = self._root_cause_data(result)
            if data != source_evidence:
                errors.append(
                    "Waterfall data does not exactly match root-cause evidence."
                )

        return not errors, errors

    @staticmethod
    def _to_plot_value(value: Any) -> Any:
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return value

    def _render(
        self,
        chart_spec: dict[str, Any],
    ) -> bytes | None:
        chart_type = chart_spec["chart_type"]
        if chart_type == "none":
            return None

        data = chart_spec["data"]
        x_field = chart_spec["x_axis"]["field"]
        y_field = chart_spec["y_axis"]["field"]

        figure, axis = plt.subplots(figsize=(9, 5))

        try:
            if chart_type == "line":
                x = [self._to_plot_value(row[x_field]) for row in data]
                y = [float(row[y_field]) for row in data]
                axis.plot(x, y, marker="o")
                axis.tick_params(axis="x", rotation=45)

            elif chart_type == "bar":
                x = [str(row[x_field]) for row in data]
                y = [float(row[y_field]) for row in data]
                axis.bar(x, y)
                axis.tick_params(axis="x", rotation=45)

            elif chart_type == "scatter":
                x = [float(row[x_field]) for row in data]
                y = [float(row[y_field]) for row in data]
                axis.scatter(x, y)

            elif chart_type == "heatmap":
                x_field = chart_spec["x_axis"]["field"]
                y_field = chart_spec["y_axis"]["field"]
                value_field = chart_spec["value_field"]
                x_values = list(dict.fromkeys(str(row[x_field]) for row in data))
                y_values = list(dict.fromkeys(str(row[y_field]) for row in data))
                matrix = [
                    [
                        next(
                            (
                                float(row[value_field])
                                for row in data
                                if str(row[x_field]) == x_value
                                and str(row[y_field]) == y_value
                            ),
                            0.0,
                        )
                        for x_value in x_values
                    ]
                    for y_value in y_values
                ]
                image = axis.imshow(matrix, aspect="auto")
                figure.colorbar(image, ax=axis)
                axis.set_xticks(range(len(x_values)), x_values, rotation=45)
                axis.set_yticks(range(len(y_values)), y_values)

            elif chart_type == "waterfall":
                labels = [str(row["group"]) for row in data]
                changes = [float(row["absolute_change"]) for row in data]
                cumulative = []
                running = 0.0
                for change in changes:
                    cumulative.append(running + change)
                    running += change
                starts = [0.0] + cumulative[:-1]
                bottoms = [
                    min(start, end)
                    for start, end in zip(starts, cumulative)
                ]
                heights = [abs(end - start) for start, end in zip(starts, cumulative)]
                axis.bar(labels, heights, bottom=bottoms)
                axis.axhline(0, linewidth=0.8)
                axis.tick_params(axis="x", rotation=45)

            axis.set_title(chart_spec["title"])
            axis.set_xlabel(chart_spec["x_axis"]["label"])
            axis.set_ylabel(chart_spec["y_axis"]["label"])
            figure.tight_layout()

            buffer = BytesIO()
            figure.savefig(buffer, format="png", dpi=120)
            return buffer.getvalue()
        finally:
            plt.close(figure)

    def run(
        self,
        request: VisualizationAgentRequest,
    ) -> VisualizationAgentResponse:
        request_errors = self.validate_request(request)

        if request_errors:
            return VisualizationAgentResponse(
                success=False,
                chart_spec=None,
                rendered_chart=None,
                chart_format=None,
                validation={"passed": False, "errors": request_errors},
                evidence=getattr(request.result, "evidence", None),
                provenance=getattr(request.result, "provenance", None),
                errors=request_errors,
            )

        result = request.result
        chart_type = self.select_chart(request.question, result)

        try:
            chart_spec = self._build_chart_spec(
                request.question,
                result,
                chart_type,
            )
        except ValueError as exc:
            errors = [str(exc)]
            return VisualizationAgentResponse(
                success=False,
                chart_spec=None,
                rendered_chart=None,
                chart_format=None,
                validation={"passed": False, "errors": errors},
                evidence=getattr(result, "evidence", None),
                provenance=getattr(result, "provenance", None),
                errors=errors,
            )

        passed, validation_errors = self.validate_chart_spec(
            chart_spec,
            result,
        )

        if not passed:
            return VisualizationAgentResponse(
                success=False,
                chart_spec=chart_spec,
                rendered_chart=None,
                chart_format=None,
                validation={
                    "passed": False,
                    "errors": validation_errors,
                },
                evidence=getattr(result, "evidence", None),
                provenance=getattr(result, "provenance", None),
                errors=validation_errors,
            )

        try:
            rendered_chart = self._render(chart_spec)
        except (KeyError, TypeError, ValueError) as exc:
            errors = [f"Chart rendering failed: {exc}"]
            return VisualizationAgentResponse(
                success=False,
                chart_spec=chart_spec,
                rendered_chart=None,
                chart_format=None,
                validation={"passed": False, "errors": errors},
                evidence=getattr(result, "evidence", None),
                provenance=getattr(result, "provenance", None),
                errors=errors,
            )

        if rendered_chart is not None and not rendered_chart.startswith(b"\x89PNG"):
            errors = ["Rendered chart is not a valid PNG artifact."]
            return VisualizationAgentResponse(
                success=False,
                chart_spec=chart_spec,
                rendered_chart=None,
                chart_format=None,
                validation={"passed": False, "errors": errors},
                evidence=getattr(result, "evidence", None),
                provenance=getattr(result, "provenance", None),
                errors=errors,
            )

        return VisualizationAgentResponse(
            success=True,
            chart_spec=chart_spec,
            rendered_chart=rendered_chart,
            chart_format="png" if rendered_chart is not None else None,
            validation={
                "passed": True,
                "errors": [],
            },
            evidence=getattr(result, "evidence", None),
            provenance=getattr(result, "provenance", None),
            errors=[],
        )
