from __future__ import annotations



from dataclasses import dataclass
from pathlib import Path
from typing import Any
import pytest
import yaml
import pandas as pd
from dataclasses import dataclass
from typing import Any

import pandas as pd

SEMANTIC_FILES = (
    "metrics.yml",
    "dimensions.yml",
    "business_rules.yml",
    "joins.yml",
    "date_logic.yml",
    "synonyms.yml",
)


@dataclass(frozen=True)
class SemanticCatalog:
    """Runtime representation of the governed semantic layer."""

    metrics: dict[str, dict[str, Any]]
    dimensions: dict[str, Any]
    business_rules: dict[str, Any]
    joins: dict[str, Any]
    date_logic: dict[str, Any]
    synonyms: dict[str, Any]

    @classmethod
    def from_directory(cls, semantic_dir: str | Path) -> "SemanticCatalog":
        """
        Load the Chat 04 semantic layer from a semantic_layer directory.

        The YAML files remain the source of truth. This class only loads and
        validates them; it does not redefine KPI formulas or business rules.
        """
        directory = Path(semantic_dir)

        if not directory.exists():
            raise FileNotFoundError(
                f"Semantic layer directory does not exist: {directory}"
            )

        missing = [
            filename
            for filename in SEMANTIC_FILES
            if not (directory / filename).is_file()
        ]
        if missing:
            raise FileNotFoundError(
                "Missing required semantic files: " + ", ".join(missing)
            )

        documents = {
            filename: cls._load_yaml(directory / filename)
            for filename in SEMANTIC_FILES
        }

        metrics = documents["metrics.yml"].get("metrics", {})
        dimensions = documents["dimensions.yml"].get("dimension_catalog", {})
        business_rules = documents["business_rules.yml"]
        joins = documents["joins.yml"]
        date_logic = documents["date_logic.yml"]
        synonyms = documents["synonyms.yml"]

        if not isinstance(metrics, dict) or not metrics:
            raise ValueError("metrics.yml must contain a non-empty 'metrics' mapping.")

        if not isinstance(dimensions, dict) or not dimensions:
            raise ValueError(
                "dimensions.yml must contain a non-empty 'dimension_catalog' mapping."
            )

        return cls(
            metrics=metrics,
            dimensions=dimensions,
            business_rules=business_rules,
            joins=joins,
            date_logic=date_logic,
            synonyms=synonyms,
        )

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)

        if not isinstance(data, dict):
            raise ValueError(f"{path.name} must contain a YAML mapping.")

        return data

    def get_metric(self, metric_id: str) -> dict[str, Any]:
        """Return one governed metric definition by its canonical ID."""
        if metric_id not in self.metrics:
            raise KeyError(f"Unknown governed metric: {metric_id}")

        return self.metrics[metric_id]

    def resolve_metric(self, value: str) -> str:
        """
        Resolve a user/agent metric phrase to a canonical governed metric ID.

        Resolution order:
        1. Exact canonical metric ID
        2. Exact metric display name
        3. Governed synonym from synonyms.yml

        A synonym is valid only when its mapped metric ID exists in
        metrics.yml. This prevents ungoverned candidate metrics from
        becoming
        executable KPIs.
        """
        normalized = self._normalize(value)

        # 1. Canonical metric ID
        for metric_id in self.metrics:
            if self._normalize(metric_id) == normalized:
                return metric_id

        # 2. Metric display name
        for metric_id, definition in self.metrics.items():
            name = definition.get("name")

            if isinstance(name, str) and self._normalize(name) == normalized:
                return metric_id

        # 3. Governed synonyms from synonyms.yml
        synonym_map = self.synonyms.get("synonyms", {})

        if isinstance(synonym_map, dict):
            for metric_id, synonyms in synonym_map.items():
                # Never allow an ungoverned metric to resolve successfully.
                if metric_id not in self.metrics:
                    continue

                if not isinstance(synonyms, list):
                    continue

                for synonym in synonyms:
                    if (
                        isinstance(synonym, str)
                        and self._normalize(synonym) == normalized
                    ):
                        return metric_id

        raise KeyError(
            f"Could not resolve '{value}' to a governed metric."
        )

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.strip().lower().replace("_", " ").split())

    def list_metric_ids(self) -> list[str]:
        """Return canonical governed metric IDs in semantic-layer order."""
        return list(self.metrics.keys())

    def list_dimensions(self) -> dict[str, Any]:
        """Return the dimension catalog without modifying it."""
        return self.dimensions


def load_semantic_catalog(
    project_root: str | Path | None = None,
) -> SemanticCatalog:
    """
    Convenience loader for the repository's standard semantic_layer directory.

    If project_root is omitted, resolve it relative to this file:
        app/tools/analytics.py -> project root
    """
    if project_root is None:
        project_root = Path(__file__).resolve().parents[2]

    semantic_dir = Path(project_root) / "semantic_layer"
    return SemanticCatalog.from_directory(semantic_dir)





@dataclass(frozen=True)
class KPIResult:
    """Structured result of a deterministic KPI calculation."""

    metric_id: str
    value: float | None
    unit: str | None
    row_count: int
    filters_applied: tuple[str, ...] = ()


@dataclass(frozen=True)
class ComparisonResult:
    metric_id: str
    current_value: float | None
    previous_value: float | None
    absolute_change: float | None
    percentage_change: float | None
    direction: str


@dataclass(frozen=True)
class ContributionResult:
    metric_id: str
    dimension: str
    group: Any
    current_value: float | None
    previous_value: float | None
    absolute_change: float | None
    contribution_percentage: float | None


@dataclass(frozen=True)
class TrendPoint:
    metric_id: str
    period: Any
    value: float | None
    previous_value: float | None
    absolute_change: float | None
    percentage_change: float | None
    direction: str


@dataclass(frozen=True)
class AnomalyResult:
    metric_id: str
    period: Any
    value: float | None
    baseline_mean: float | None
    baseline_std: float | None
    z_score: float | None
    is_anomaly: bool


class AnalyticsEngine:
    """
    Deterministic analytics engine backed by the governed semantic catalog.

    The engine does not redefine business metrics. It resolves metric IDs
    through the semantic catalog and calculates them using governed
    semantic definitions.
    """

    def __init__(self, catalog: SemanticCatalog):
        self.catalog = catalog

    def calculate_kpi(
        self,
        metric: str,
        data: pd.DataFrame,
    ) -> KPIResult:
        """
        Calculate one governed KPI over the supplied analytical dataset.

        Parameters
        ----------
        metric:
            Canonical metric ID, display name, or governed synonym.

        data:
            DataFrame containing the columns required by the metric.

        Returns
        -------
        KPIResult
            Structured deterministic KPI result.
        """
        metric_id = self.catalog.resolve_metric(metric)
        definition = self.catalog.get_metric(metric_id)

        value = self._calculate_metric(metric_id, definition, data)

        unit = definition.get("unit")

        return KPIResult(
            metric_id=metric_id,
            value=value,
            unit=unit,
            row_count=len(data),
        )


    def _gross_revenue(self, data: pd.DataFrame) -> float:
        return float(
            (
                data["quantity"]
                * data["unit_price"]
            ).sum()
        )


    def _net_revenue(self, data: pd.DataFrame) -> float:
        gross_revenue = (
            data["quantity"]
            * data["unit_price"]
        )

        discount_amount = (
            gross_revenue
            * data["discount_percent"]
        )

        return float(
            (gross_revenue - discount_amount).sum()
        )


    def _gross_profit(self, data: pd.DataFrame) -> float:
        net_revenue = self._net_revenue(data)

        total_cost = (
            data["quantity"]
            * data["unit_cost"]
        ).sum()

        return float(net_revenue - total_cost)

    def _calculate_metric(
        self,
        metric_id: str,
        definition: dict[str, Any],
        data: pd.DataFrame,
    ) -> float | None:
        """
        Execute the deterministic calculation for a governed metric.
        """

        if data.empty:
            return None

        if metric_id == "gross_revenue":
            return float(
                (data["quantity"] * data["unit_price"]).sum()
            )

        if metric_id == "net_revenue":
            gross_revenue = (
                data["quantity"] * data["unit_price"]
            )

            discount_amount = (
                gross_revenue * data["discount_percent"]
            )

            return float(
                (gross_revenue - discount_amount).sum()
            )

        if metric_id == "gross_profit":
            gross_revenue = (
                data["quantity"] * data["unit_price"]
            )

            discount_amount = (
                gross_revenue * data["discount_percent"]
            )

            net_revenue = (
                gross_revenue - discount_amount
            )

            total_cost = (
                data["quantity"] * data["unit_cost"]
            )

            return float(
                (net_revenue - total_cost).sum()
            )

        if metric_id == "profit_margin":
            net_revenue = self._net_revenue(data)

            if net_revenue == 0:
                return None

            gross_profit = self._gross_profit(data)

            return float(gross_profit / net_revenue)

        if metric_id == "discount_rate":
            gross_revenue = self._gross_revenue(data)

            if gross_revenue == 0:
                return None

            discount_amount = (
                data["quantity"]
                * data["unit_price"]
                * data["discount_percent"]
            ).sum()

            return float(discount_amount / gross_revenue)

        if metric_id == "orders":
            return float(data["order_id"].nunique())

        if metric_id == "units_sold":
            return float(data["quantity"].sum())

        if metric_id == "average_order_value":
            orders = data["order_id"].nunique()

            if orders == 0:
                return None

            return float(self._net_revenue(data) / orders)

        if metric_id == "average_selling_price":
            units_sold = data["quantity"].sum()

            if units_sold == 0:
                return None

            return float(self._net_revenue(data) / units_sold)

        if metric_id == "customer_count":
            return float(
                data["customer_id"].dropna().nunique()
            )

        if metric_id == "customer_revenue":
            return float(self._net_revenue(data))

        if metric_id == "revenue_per_customer":
            customer_count = data["customer_id"].dropna().nunique()

            if customer_count == 0:
                return None

            return float(
                self._net_revenue(data) / customer_count
            )

        if metric_id == "closing_stock":
            return float(data["closing_stock"].sum())

        if metric_id == "stockout_rate":
            if "stockout_flag" not in data.columns:
                raise ValueError(
                    "stockout_rate requires 'stockout_flag'."
                )

            observations = data["stockout_flag"].notna().sum()

            if observations == 0:
                return None

            return float(
                data["stockout_flag"].sum() / observations
            )

        if metric_id == "inventory_turnover":
            raise NotImplementedError(
                "inventory_turnover requires independently aggregated "
                "sales and inventory data at a compatible analytical grain."
            )

        raise NotImplementedError(
            f"KPI '{metric_id}' is not implemented yet."
        )


    def compare_periods(
        self,
        metric: str,
        current_data: pd.DataFrame,
        previous_data: pd.DataFrame,
    ) -> ComparisonResult:
        current_result = self.calculate_kpi(metric, current_data)
        previous_result = self.calculate_kpi(metric, previous_data)

        current_value = current_result.value
        previous_value = previous_result.value

        if current_value is None or previous_value is None:
            return ComparisonResult(
                metric_id=current_result.metric_id,
                current_value=current_value,
                previous_value=previous_value,
                absolute_change=None,
                percentage_change=None,
                direction="unknown",
            )

        absolute_change = current_value - previous_value

        if previous_value == 0:
            percentage_change = None
        else:
            percentage_change = (
                absolute_change / previous_value
            ) * 100

        if absolute_change > 0:
            direction = "increase"
        elif absolute_change < 0:
            direction = "decrease"
        else:
            direction = "no_change"

        return ComparisonResult(
            metric_id=current_result.metric_id,
            current_value=current_value,
            previous_value=previous_value,
            absolute_change=absolute_change,
            percentage_change=percentage_change,
            direction=direction,
        )


    def analyze_contribution(
        self,
        metric: str,
        current_data: pd.DataFrame,
        previous_data: pd.DataFrame,
        dimension: str,
    ) -> list[ContributionResult]:
        metric_id = self.catalog.resolve_metric(metric)

        if dimension not in current_data.columns:
            raise ValueError(
                f"Dimension '{dimension}' is not present in current_data."
            )

        if dimension not in previous_data.columns:
            raise ValueError(
                f"Dimension '{dimension}' is not present in previous_data."
            )

        groups = sorted(
            set(current_data[dimension].dropna().unique())
            | set(previous_data[dimension].dropna().unique()),
            key=str,
        )

        group_changes: list[tuple[Any, float | None, float | None, float | None]] = []

        for group in groups:
            current_group = current_data[
                current_data[dimension] == group
            ]

            previous_group = previous_data[
                previous_data[dimension] == group
            ]

            current_result = self.calculate_kpi(
                metric_id,
                current_group,
            )

            previous_result = self.calculate_kpi(
                metric_id,
                previous_group,
            )

            current_value = current_result.value
            previous_value = previous_result.value

            if current_value is None or previous_value is None:
                absolute_change = None
            else:
                absolute_change = current_value - previous_value

            group_changes.append(
                (
                    group,
                    current_value,
                    previous_value,
                    absolute_change,
                )
            )

        total_change = sum(
            change
            for _, _, _, change in group_changes
            if change is not None
        )

        results: list[ContributionResult] = []

        for (
            group,
            current_value,
            previous_value,
            absolute_change,
        ) in group_changes:

            if absolute_change is None or total_change == 0:
                contribution_percentage = None
            else:
                contribution_percentage = (
                    absolute_change / total_change
                ) * 100

            results.append(
                ContributionResult(
                    metric_id=metric_id,
                    dimension=dimension,
                    group=group,
                    current_value=current_value,
                    previous_value=previous_value,
                    absolute_change=absolute_change,
                    contribution_percentage=contribution_percentage,
                )
            )

        return results


    def analyze_trend(
        self,
        metric: str,
        periods: list[tuple[Any, pd.DataFrame]],
    ) -> list[TrendPoint]:
        metric_id = self.catalog.resolve_metric(metric)

        if not periods:
            return []

        results: list[TrendPoint] = []

        previous_value: float | None = None

        for period, data in periods:
            kpi_result = self.calculate_kpi(
                metric_id,
                data,
            )

            current_value = kpi_result.value

            if current_value is None or previous_value is None:
                absolute_change = None
                percentage_change = None
                direction = "unknown"
            else:
                absolute_change = current_value - previous_value

                if previous_value == 0:
                    percentage_change = None
                else:
                    percentage_change = (
                        absolute_change / previous_value
                    ) * 100

                if absolute_change > 0:
                    direction = "increase"
                elif absolute_change < 0:
                    direction = "decrease"
                else:
                    direction = "no_change"

            results.append(
                TrendPoint(
                    metric_id=metric_id,
                    period=period,
                    value=current_value,
                    previous_value=previous_value,
                    absolute_change=absolute_change,
                    percentage_change=percentage_change,
                    direction=direction,
                )
            )

            previous_value = current_value

        return results


    def detect_anomalies(
        self,
        metric: str,
        periods: list[tuple[Any, pd.DataFrame]],
        window: int = 3,
        threshold: float = 3.0,
    ) -> list[AnomalyResult]:
        metric_id = self.catalog.resolve_metric(metric)

        if window < 2:
            raise ValueError("window must be at least 2.")

        if threshold <= 0:
            raise ValueError("threshold must be greater than 0.")

        if not periods:
            return []

        trend = self.analyze_trend(
            metric_id,
            periods,
        )

        values = [
            point.value
            for point in trend
        ]

        results: list[AnomalyResult] = []

        for index, point in enumerate(trend):
            if point.value is None:
                results.append(
                    AnomalyResult(
                        metric_id=metric_id,
                        period=point.period,
                        value=None,
                        baseline_mean=None,
                        baseline_std=None,
                        z_score=None,
                        is_anomaly=False,
                    )
                )
                continue

            start_index = max(0, index - window)

            baseline_values = [
                value
                for value in values[start_index:index]
                if value is not None
            ]

            if len(baseline_values) < 2:
                results.append(
                    AnomalyResult(
                        metric_id=metric_id,
                        period=point.period,
                        value=point.value,
                        baseline_mean=None,
                        baseline_std=None,
                        z_score=None,
                        is_anomaly=False,
                    )
                )
                continue

            baseline = pd.Series(
                baseline_values,
                dtype=float,
            )

            baseline_mean = float(baseline.mean())
            baseline_std = float(baseline.std(ddof=0))

            if baseline_std == 0:
                z_score = None
                is_anomaly = False
            else:
                z_score = (
                    point.value - baseline_mean
                ) / baseline_std

                is_anomaly = abs(z_score) >= threshold

            results.append(
                AnomalyResult(
                    metric_id=metric_id,
                    period=point.period,
                    value=point.value,
                    baseline_mean=baseline_mean,
                    baseline_std=baseline_std,
                    z_score=z_score,
                    is_anomaly=is_anomaly,
                )
            )

        return results