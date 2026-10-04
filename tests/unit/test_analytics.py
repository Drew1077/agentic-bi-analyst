from pathlib import Path

import pytest

from app.tools.analytics import SemanticCatalog
from app.tools.analytics import AnalyticsEngine
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEMANTIC_DIR = PROJECT_ROOT / "semantic_layer"


@pytest.fixture()
def catalog() -> SemanticCatalog:
    return SemanticCatalog.from_directory(SEMANTIC_DIR)


def test_semantic_catalog_loads(catalog: SemanticCatalog):
    assert len(catalog.metrics) == 15
    assert catalog.dimensions
    assert catalog.business_rules
    assert catalog.joins
    assert catalog.date_logic
    assert catalog.synonyms


def test_metric_resolution_by_id(catalog: SemanticCatalog):
    assert catalog.resolve_metric("net_revenue") == "net_revenue"


def test_metric_resolution_by_name(catalog: SemanticCatalog):
    assert catalog.resolve_metric("Net Revenue") == "net_revenue"


def test_metric_resolution_by_synonym(catalog: SemanticCatalog):
    assert catalog.resolve_metric("revenue") == "net_revenue"


def test_unknown_metric_is_rejected(catalog: SemanticCatalog):
    with pytest.raises(KeyError):
        catalog.resolve_metric("some invented metric")

def test_metric_resolution_from_synonyms_file(catalog: SemanticCatalog):
    assert catalog.resolve_metric("gross sales") == "gross_revenue"
    assert catalog.resolve_metric("AOV") == "average_order_value"
    assert catalog.resolve_metric("customers") == "customer_count"
    assert catalog.resolve_metric("ending inventory") == "closing_stock"


def test_ungoverned_synonym_is_rejected(catalog: SemanticCatalog):
    with pytest.raises(KeyError):
        catalog.resolve_metric("refunds")


def test_all_governed_metrics_have_resolvable_ids(
    catalog: SemanticCatalog,
):
    for metric_id in catalog.metrics:
        assert catalog.resolve_metric(metric_id) == metric_id


@pytest.fixture()
def analytics_engine(catalog: SemanticCatalog) -> AnalyticsEngine:
    return AnalyticsEngine(catalog)


@pytest.fixture()
def sales_data() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "order_id": [1, 1, 2],
            "customer_id": [101, 101, 102],
            "quantity": [2, 1, 3],
            "unit_price": [100.0, 50.0, 200.0],
            "unit_cost": [60.0, 30.0, 120.0],
            "discount_percent": [0.10, 0.00, 0.20],
        }
    )

def test_gross_revenue(
    analytics_engine: AnalyticsEngine,
    sales_data: pd.DataFrame,
):
    result = analytics_engine.calculate_kpi(
        "gross_revenue",
        sales_data,
    )

    assert result.metric_id == "gross_revenue"
    assert result.value == 850.0


def test_net_revenue(
    analytics_engine: AnalyticsEngine,
    sales_data: pd.DataFrame,
):
    result = analytics_engine.calculate_kpi(
        "net_revenue",
        sales_data,
    )

    assert result.metric_id == "net_revenue"
    assert result.value == 710.0


def test_gross_profit(
    analytics_engine: AnalyticsEngine,
    sales_data: pd.DataFrame,
):
    result = analytics_engine.calculate_kpi(
        "gross_profit",
        sales_data,
    )

    assert result.metric_id == "gross_profit"
    assert result.value == 200.0


def test_order_count_uses_distinct_orders(
    analytics_engine: AnalyticsEngine,
    sales_data: pd.DataFrame,
):
    result = analytics_engine.calculate_kpi(
        "orders",
        sales_data,
    )

    assert result.value == 2.0


def test_customer_count_excludes_null_customer_ids(
    analytics_engine: AnalyticsEngine,
):
    data = pd.DataFrame(
        {
            "customer_id": [101, 101, 102, None],
        }
    )

    result = analytics_engine.calculate_kpi(
        "customer_count",
        data,
    )

    assert result.value == 2.0




def test_profit_margin(
    analytics_engine: AnalyticsEngine,
    sales_data: pd.DataFrame,
):
    result = analytics_engine.calculate_kpi(
        "profit_margin",
        sales_data,
    )

    assert result.value == pytest.approx(200 / 710)

def test_discount_rate(
    analytics_engine: AnalyticsEngine,
    sales_data: pd.DataFrame,
):
    result = analytics_engine.calculate_kpi(
        "discount_rate",
        sales_data,
    )

    assert result.value == pytest.approx(140 / 850)

def test_average_order_value(
    analytics_engine: AnalyticsEngine,
    sales_data: pd.DataFrame,
):
    result = analytics_engine.calculate_kpi(
        "average_order_value",
        sales_data,
    )

    assert result.value == pytest.approx(710 / 2)

def test_average_selling_price(
    analytics_engine: AnalyticsEngine,
    sales_data: pd.DataFrame,
):
    result = analytics_engine.calculate_kpi(
        "average_selling_price",
        sales_data,
    )

    assert result.value == pytest.approx(710 / 6)

def test_revenue_per_customer(
    analytics_engine: AnalyticsEngine,
    sales_data: pd.DataFrame,
):
    result = analytics_engine.calculate_kpi(
        "revenue_per_customer",
        sales_data,
    )

    assert result.value == pytest.approx(710 / 2)

def test_profit_margin_returns_none_when_revenue_is_zero(
    analytics_engine: AnalyticsEngine,
):
    data = pd.DataFrame(
        {
            "quantity": [1],
            "unit_price": [0.0],
            "unit_cost": [0.0],
            "discount_percent": [0.0],
        }
    )

    result = analytics_engine.calculate_kpi(
        "profit_margin",
        data,
    )

    assert result.value is None

def test_revenue_per_customer_returns_none_without_customers(
    analytics_engine: AnalyticsEngine,
):
    data = pd.DataFrame(
        {
            "quantity": [1],
            "unit_price": [100.0],
            "unit_cost": [50.0],
            "discount_percent": [0.0],
            "customer_id": [None],
        }
    )

    result = analytics_engine.calculate_kpi(
        "revenue_per_customer",
        data,
    )

    assert result.value is None


def test_closing_stock(
    analytics_engine: AnalyticsEngine,
):
    data = pd.DataFrame(
        {
            "closing_stock": [100, 50, 25],
        }
    )

    result = analytics_engine.calculate_kpi(
        "closing_stock",
        data,
    )

    assert result.value == 175.0

def test_stockout_rate(
    analytics_engine: AnalyticsEngine,
):
    data = pd.DataFrame(
        {
            "stockout_flag": [1, 0, 1, 0],
        }
    )

    result = analytics_engine.calculate_kpi(
        "stockout_rate",
        data,
    )

    assert result.value == pytest.approx(0.5)


def test_stockout_rate_ignores_null_flags(
    analytics_engine: AnalyticsEngine,
):
    data = pd.DataFrame(
        {
            "stockout_flag": [1, 0, None],
        }
    )

    result = analytics_engine.calculate_kpi(
        "stockout_rate",
        data,
    )

    assert result.value == pytest.approx(0.5)


def test_inventory_turnover_requires_grain_safe_inputs(
    analytics_engine: AnalyticsEngine,
    sales_data: pd.DataFrame,
):
    with pytest.raises(NotImplementedError):
        analytics_engine.calculate_kpi(
            "inventory_turnover",
            sales_data,
        )

def test_all_governed_metrics_have_calculation_behavior(
    analytics_engine: AnalyticsEngine,
    sales_data: pd.DataFrame,
):
    implemented_metrics = {
        "gross_revenue",
        "net_revenue",
        "gross_profit",
        "profit_margin",
        "discount_rate",
        "orders",
        "units_sold",
        "average_order_value",
        "average_selling_price",
        "customer_count",
        "customer_revenue",
        "revenue_per_customer",
        "closing_stock",
        "stockout_rate",
    }

    intentionally_deferred_metrics = {
        "inventory_turnover",
    }

    governed_metrics = set(
        analytics_engine.catalog.list_metric_ids()
    )

    assert governed_metrics == (
        implemented_metrics
        | intentionally_deferred_metrics
    )


def test_governed_synonym_calculates_correct_metric(
    analytics_engine: AnalyticsEngine,
    sales_data: pd.DataFrame,
):
    result = analytics_engine.calculate_kpi(
        "revenue",
        sales_data,
    )

    assert result.metric_id == "net_revenue"
    assert result.value == pytest.approx(710.0)


def test_inventory_turnover_requires_grain_safe_inputs(
    analytics_engine: AnalyticsEngine,
    sales_data: pd.DataFrame,
):
    with pytest.raises(NotImplementedError):
        analytics_engine.calculate_kpi(
            "inventory_turnover",
            sales_data,
        )


def test_period_comparison_increase(
    analytics_engine: AnalyticsEngine,
    sales_data: pd.DataFrame,
):
    previous_data = sales_data.copy()
    current_data = sales_data.copy()

    current_data["unit_price"] = current_data["unit_price"] * 1.10

    result = analytics_engine.compare_periods(
        "net_revenue",
        current_data,
        previous_data,
    )

    assert result.metric_id == "net_revenue"
    assert result.current_value == pytest.approx(781.0)
    assert result.previous_value == pytest.approx(710.0)
    assert result.absolute_change == pytest.approx(71.0)
    assert result.percentage_change == pytest.approx(10.0)
    assert result.direction == "increase"


def test_period_comparison_decrease(
    analytics_engine: AnalyticsEngine,
    sales_data: pd.DataFrame,
):
    previous_data = sales_data.copy()
    current_data = sales_data.copy()

    current_data["unit_price"] = current_data["unit_price"] * 0.90

    result = analytics_engine.compare_periods(
        "net_revenue",
        current_data,
        previous_data,
    )

    assert result.metric_id == "net_revenue"
    assert result.current_value == pytest.approx(639.0)
    assert result.previous_value == pytest.approx(710.0)
    assert result.absolute_change == pytest.approx(-71.0)
    assert result.percentage_change == pytest.approx(-10.0)
    assert result.direction == "decrease"


def test_period_comparison_no_change(
    analytics_engine: AnalyticsEngine,
    sales_data: pd.DataFrame,
):
    result = analytics_engine.compare_periods(
        "net_revenue",
        sales_data,
        sales_data.copy(),
    )

    assert result.current_value == pytest.approx(710.0)
    assert result.previous_value == pytest.approx(710.0)
    assert result.absolute_change == pytest.approx(0.0)
    assert result.percentage_change == pytest.approx(0.0)
    assert result.direction == "no_change"


def test_period_comparison_handles_zero_previous_value(
    analytics_engine: AnalyticsEngine,
    sales_data: pd.DataFrame,
):
    previous_data = sales_data.copy()
    previous_data["quantity"] = 0

    result = analytics_engine.compare_periods(
        "net_revenue",
        sales_data,
        previous_data,
    )

    assert result.current_value == pytest.approx(710.0)
    assert result.previous_value == pytest.approx(0.0)
    assert result.absolute_change == pytest.approx(710.0)
    assert result.percentage_change is None
    assert result.direction == "increase"


@pytest.fixture()
def contribution_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    previous_data = pd.DataFrame(
        {
            "order_id": [1, 2, 3],
            "customer_id": [101, 102, 103],
            "category": [
                "Electronics",
                "Clothing",
                "Furniture",
            ],
            "quantity": [1, 1, 1],
            "unit_price": [100.0, 100.0, 100.0],
            "unit_cost": [60.0, 60.0, 60.0],
            "discount_percent": [0.0, 0.0, 0.0],
        }
    )

    current_data = pd.DataFrame(
        {
            "order_id": [4, 5, 6],
            "customer_id": [104, 105, 106],
            "category": [
                "Electronics",
                "Clothing",
                "Furniture",
            ],
            "quantity": [1, 1, 1],
            "unit_price": [150.0, 120.0, 90.0],
            "unit_cost": [60.0, 60.0, 60.0],
            "discount_percent": [0.0, 0.0, 0.0],
        }
    )

    return current_data, previous_data


def test_contribution_analysis(
    analytics_engine: AnalyticsEngine,
    contribution_data: tuple[pd.DataFrame, pd.DataFrame],
):
    current_data, previous_data = contribution_data

    results = analytics_engine.analyze_contribution(
        "net_revenue",
        current_data,
        previous_data,
        "category",
    )

    assert len(results) == 3

    electronics = next(
        result
        for result in results
        if result.group == "Electronics"
    )

    clothing = next(
        result
        for result in results
        if result.group == "Clothing"
    )

    furniture = next(
        result
        for result in results
        if result.group == "Furniture"
    )

    assert electronics.absolute_change == pytest.approx(50.0)
    assert clothing.absolute_change == pytest.approx(20.0)
    assert furniture.absolute_change == pytest.approx(-10.0)

    assert electronics.contribution_percentage == pytest.approx(83.3333, abs=0.001,)
    assert clothing.contribution_percentage == pytest.approx(33.3333, abs=0.001,)
    assert furniture.contribution_percentage == pytest.approx(-16.6667, abs=0.001,)


def test_contribution_analysis_handles_zero_total_change(
    analytics_engine: AnalyticsEngine,
    contribution_data: tuple[pd.DataFrame, pd.DataFrame],
):
    current_data, previous_data = contribution_data

    results = analytics_engine.analyze_contribution(
        "net_revenue",
        previous_data,
        previous_data.copy(),
        "category",
    )

    assert len(results) == 3

    for result in results:
        assert result.absolute_change == pytest.approx(0.0)
        assert result.contribution_percentage is None


def test_contribution_analysis_rejects_missing_dimension(
    analytics_engine: AnalyticsEngine,
    contribution_data: tuple[pd.DataFrame, pd.DataFrame],
):
    current_data, previous_data = contribution_data

    with pytest.raises(ValueError, match="Dimension 'region'"):
        analytics_engine.analyze_contribution(
            "net_revenue",
            current_data,
            previous_data,
            "region",
        )


def test_trend_analysis(
    analytics_engine: AnalyticsEngine,
):
    january = pd.DataFrame(
        {
            "order_id": [1],
            "customer_id": [101],
            "quantity": [1],
            "unit_price": [100.0],
            "unit_cost": [60.0],
            "discount_percent": [0.0],
        }
    )

    february = pd.DataFrame(
        {
            "order_id": [2],
            "customer_id": [102],
            "quantity": [1],
            "unit_price": [120.0],
            "unit_cost": [60.0],
            "discount_percent": [0.0],
        }
    )

    march = pd.DataFrame(
        {
            "order_id": [3],
            "customer_id": [103],
            "quantity": [1],
            "unit_price": [90.0],
            "unit_cost": [60.0],
            "discount_percent": [0.0],
        }
    )

    results = analytics_engine.analyze_trend(
        "net_revenue",
        [
            ("2026-01", january),
            ("2026-02", february),
            ("2026-03", march),
        ],
    )

    assert len(results) == 3

    assert results[0].period == "2026-01"
    assert results[0].value == pytest.approx(100.0)
    assert results[0].previous_value is None
    assert results[0].direction == "unknown"

    assert results[1].period == "2026-02"
    assert results[1].value == pytest.approx(120.0)
    assert results[1].previous_value == pytest.approx(100.0)
    assert results[1].absolute_change == pytest.approx(20.0)
    assert results[1].percentage_change == pytest.approx(20.0)
    assert results[1].direction == "increase"

    assert results[2].period == "2026-03"
    assert results[2].value == pytest.approx(90.0)
    assert results[2].previous_value == pytest.approx(120.0)
    assert results[2].absolute_change == pytest.approx(-30.0)
    assert results[2].percentage_change == pytest.approx(-25.0)
    assert results[2].direction == "decrease"


def test_trend_analysis_handles_empty_periods(
    analytics_engine: AnalyticsEngine,
):
    results = analytics_engine.analyze_trend(
        "net_revenue",
        [],
    )

    assert results == []


def test_trend_analysis_handles_zero_previous_value(
    analytics_engine: AnalyticsEngine,
):
    zero_period = pd.DataFrame(
        {
            "order_id": [1],
            "customer_id": [101],
            "quantity": [0],
            "unit_price": [100.0],
            "unit_cost": [60.0],
            "discount_percent": [0.0],
        }
    )

    current_period = pd.DataFrame(
        {
            "order_id": [2],
            "customer_id": [102],
            "quantity": [1],
            "unit_price": [100.0],
            "unit_cost": [60.0],
            "discount_percent": [0.0],
        }
    )

    results = analytics_engine.analyze_trend(
        "net_revenue",
        [
            ("2026-01", zero_period),
            ("2026-02", current_period),
        ],
    )

    assert results[0].value == pytest.approx(0.0)
    assert results[0].direction == "unknown"

    assert results[1].value == pytest.approx(100.0)
    assert results[1].absolute_change == pytest.approx(100.0)
    assert results[1].percentage_change is None
    assert results[1].direction == "increase"


@pytest.fixture()
def anomaly_periods() -> list[tuple[str, pd.DataFrame]]:
    values = [100.0, 102.0, 101.0, 99.0, 1000.0]

    periods = []

    for index, value in enumerate(values, start=1):
        data = pd.DataFrame(
            {
                "order_id": [index],
                "customer_id": [100 + index],
                "quantity": [1],
                "unit_price": [value],
                "unit_cost": [50.0],
                "discount_percent": [0.0],
            }
        )

        periods.append(
            (f"2026-0{index}", data)
        )

    return periods


def test_anomaly_detection(
    analytics_engine: AnalyticsEngine,
    anomaly_periods: list[tuple[str, pd.DataFrame]],
):
    results = analytics_engine.detect_anomalies(
        "net_revenue",
        anomaly_periods,
        window=3,
        threshold=3.0,
    )

    assert len(results) == 5

    assert results[0].is_anomaly is False
    assert results[0].z_score is None

    assert results[1].is_anomaly is False
    assert results[1].z_score is None

    assert results[2].is_anomaly is False
    assert results[2].z_score is not None

    assert results[3].is_anomaly is False

    assert results[4].period == "2026-05"
    assert results[4].value == pytest.approx(1000.0)
    assert results[4].is_anomaly is True
    assert results[4].z_score is not None
    assert results[4].z_score > 3.0


def test_anomaly_detection_handles_zero_standard_deviation(
    analytics_engine: AnalyticsEngine,
):
    periods = []

    for index in range(1, 6):
        data = pd.DataFrame(
            {
                "order_id": [index],
                "customer_id": [100 + index],
                "quantity": [1],
                "unit_price": [100.0],
                "unit_cost": [50.0],
                "discount_percent": [0.0],
            }
        )

        periods.append(
            (f"2026-0{index}", data)
        )

    results = analytics_engine.detect_anomalies(
        "net_revenue",
        periods,
        window=3,
        threshold=3.0,
    )

    for result in results:
        assert result.is_anomaly is False

    assert results[-1].z_score is None


def test_anomaly_detection_rejects_invalid_window(
    analytics_engine: AnalyticsEngine,
    anomaly_periods: list[tuple[str, pd.DataFrame]],
):
    with pytest.raises(
        ValueError,
        match="window must be at least 2",
    ):
        analytics_engine.detect_anomalies(
            "net_revenue",
            anomaly_periods,
            window=1,
        )


def test_anomaly_detection_rejects_invalid_threshold(
    analytics_engine: AnalyticsEngine,
    anomaly_periods: list[tuple[str, pd.DataFrame]],
):
    with pytest.raises(
        ValueError,
        match="threshold must be greater than 0",
    ):
        analytics_engine.detect_anomalies(
            "net_revenue",
            anomaly_periods,
            threshold=0,
        )


def test_kpi_returns_none_for_empty_data(
    analytics_engine: AnalyticsEngine,
):
    empty_data = pd.DataFrame(
        columns=[
            "order_id",
            "customer_id",
            "quantity",
            "unit_price",
            "unit_cost",
            "discount_percent",
        ]
    )

    result = analytics_engine.calculate_kpi(
        "net_revenue",
        empty_data,
    )

    assert result.value is None
    assert result.metric_id == "net_revenue"
    assert result.row_count == 0


def test_invalid_metric_is_rejected(
    analytics_engine: AnalyticsEngine,
    sales_data: pd.DataFrame,
):
    with pytest.raises(
        KeyError,
        match="Could not resolve",
    ):
        analytics_engine.calculate_kpi(
            "totally_unknown_metric",
            sales_data,
        )



def test_inventory_turnover_remains_deferred(
    analytics_engine: AnalyticsEngine,
    sales_data: pd.DataFrame,
):
    with pytest.raises(
        NotImplementedError,
        match="independently aggregated",
    ):
        analytics_engine.calculate_kpi(
            "inventory_turnover",
            sales_data,
        )


def test_missing_required_columns_raise_error(
    analytics_engine: AnalyticsEngine,
):
    incomplete_data = pd.DataFrame(
        {
            "order_id": [1],
            "customer_id": [101],
        }
    )

    with pytest.raises(KeyError):
        analytics_engine.calculate_kpi(
            "net_revenue",
            incomplete_data,
        )


def test_revenue_per_customer_excludes_null_customers(
    analytics_engine: AnalyticsEngine,
):
    data = pd.DataFrame(
        {
            "order_id": [1, 2],
            "customer_id": [101, None],
            "quantity": [1, 1],
            "unit_price": [100.0, 200.0],
            "unit_cost": [60.0, 120.0],
            "discount_percent": [0.0, 0.0],
        }
    )

    result = analytics_engine.calculate_kpi(
        "revenue_per_customer",
        data,
    )

    assert result.value == pytest.approx(300.0)


def test_average_selling_price_returns_none_for_zero_units(
    analytics_engine: AnalyticsEngine,
):
    data = pd.DataFrame(
        {
            "order_id": [1],
            "customer_id": [101],
            "quantity": [0],
            "unit_price": [100.0],
            "unit_cost": [60.0],
            "discount_percent": [0.0],
        }
    )

    result = analytics_engine.calculate_kpi(
        "average_selling_price",
        data,
    )

    assert result.value is None


def test_average_order_value_returns_none_for_zero_orders(
    analytics_engine: AnalyticsEngine,
):
    data = pd.DataFrame(
        {
            "order_id": [],
            "customer_id": [],
            "quantity": [],
            "unit_price": [],
            "unit_cost": [],
            "discount_percent": [],
        }
    )

    result = analytics_engine.calculate_kpi(
        "average_order_value",
        data,
    )

    assert result.value is None


def test_stockout_rate_returns_none_when_all_flags_are_null(
    analytics_engine: AnalyticsEngine,
):
    data = pd.DataFrame(
        {
            "stockout_flag": [None, None, None],
        }
    )

    result = analytics_engine.calculate_kpi(
        "stockout_rate",
        data,
    )

    assert result.value is None


def test_contribution_analysis_handles_empty_inputs(
    analytics_engine: AnalyticsEngine,
):
    current_data = pd.DataFrame(
        columns=[
            "category",
            "order_id",
            "customer_id",
            "quantity",
            "unit_price",
            "unit_cost",
            "discount_percent",
        ]
    )

    previous_data = current_data.copy()

    results = analytics_engine.analyze_contribution(
        "net_revenue",
        current_data,
        previous_data,
        "category",
    )

    assert results == []


def test_anomaly_detection_handles_empty_periods(
    analytics_engine: AnalyticsEngine,
):
    results = analytics_engine.detect_anomalies(
        "net_revenue",
        [],
    )

    assert results == []


