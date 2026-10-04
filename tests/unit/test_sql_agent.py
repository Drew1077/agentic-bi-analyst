import pytest
from app.agents.sql_agent import AnalysisSpec, SQLAnalystAgent, SQLAgentRequest




def test_extract_metric_text_from_natural_language_question():
    agent = SQLAnalystAgent()

    metric_text = agent.extract_metric_text(
        "What was the revenue in 2025?"
    )

    assert metric_text == "revenue"


def test_build_analysis_spec_for_aggregate_revenue():
    agent = SQLAnalystAgent()

    spec = agent.build_analysis_spec(
        SQLAgentRequest(
            question="revenue in 2025"
        )
    )

    assert spec.metric == "net_revenue"
    assert spec.dimensions == []
    assert spec.date_start == "2025-01-01"
    assert spec.date_end == "2025-12-31"


def test_build_analysis_spec_for_natural_language_aggregate_revenue():
    agent = SQLAnalystAgent()

    spec = agent.build_analysis_spec(
        SQLAgentRequest(
            question="What was the revenue in 2025?"
        )
    )

    assert spec.metric == "net_revenue"
    assert spec.dimensions == []
    assert spec.date_start == "2025-01-01"
    assert spec.date_end == "2025-12-31"


def test_generate_sql_for_aggregate_revenue():
    agent = SQLAnalystAgent()

    spec = agent.build_analysis_spec(
        SQLAgentRequest(
            question="revenue in 2025"
        )
    )

    sql = agent.generate_sql(spec)

    assert "SELECT\n     SUM(order_items.net_revenue) AS net_revenue" in sql
    assert "FROM orders" in sql
    assert "JOIN order_items" in sql
    assert "orders.order_date >= '2025-01-01'" in sql
    assert "orders.order_date <= '2025-12-31'" in sql
    assert "GROUP BY" not in sql
    assert "JOIN products" not in sql
    assert "JOIN customers" not in sql


def test_required_schema_for_aggregate_revenue():
    agent = SQLAnalystAgent()

    spec = AnalysisSpec(
        metric="net_revenue",
        dimensions=[],
        date_start="2025-01-01",
        date_end="2025-12-31",
        filters={},
    )

    required_schema = agent.required_schema_for_spec(spec)

    assert required_schema == {
        "orders": ["order_id", "order_date"],
        "order_items": ["order_id", "product_id", "net_revenue"],
    }


def test_run_aggregate_revenue(monkeypatch):
    agent = SQLAnalystAgent()

    class FakeResult:
        success = True
        columns = ["net_revenue"]
        rows = [{"net_revenue": 12345.67}]
        row_count = 1
        error = None
        execution_time_ms = 1.0

    monkeypatch.setattr(
        "app.agents.sql_agent.execute_sql",
        lambda sql: FakeResult(),
    )

    response = agent.run(
        SQLAgentRequest(
            question="revenue in 2025"
        )
    )

    assert response.success is True
    assert response.columns == ["net_revenue"]
    assert response.rows == [{"net_revenue": 12345.67}]
    assert response.evidence["metric"] == "net_revenue"
    assert response.evidence["dimensions"] == []
    assert response.provenance["dimensions"] == []
    assert "Net revenue" in response.answer

def test_resolve_metric_revenue():
    agent = SQLAnalystAgent()

    metric = agent.resolve_metric("revenue")

    assert metric == "net_revenue"

def test_resolve_metric_rejects_unknown_metric():
    agent = SQLAnalystAgent()

    try:
        agent.resolve_metric("customer lifetime value")
        assert False, "Expected unknown metric to raise an error"
    except KeyError as exc:
        assert "Could not resolve" in str(exc)

def test_validate_query_rejects_delete():
    agent = SQLAnalystAgent()

    result = agent.validate_query("DELETE FROM orders")

    assert result.valid is False
    assert any("DELETE" in error for error in result.errors)

def test_validate_query_rejects_unsafe_fact_combination():
    agent = SQLAnalystAgent()

    result = agent.validate_query(
        """
        SELECT SUM(order_items.net_revenue)
        FROM orders
        JOIN order_items
            ON orders.order_id = order_items.order_id
        JOIN payments
            ON payments.order_id = orders.order_id
        """
    )

    assert result.valid is False
    assert any(
        "order_items and payments" in error
        for error in result.errors
    )

def test_build_analysis_spec_for_revenue_by_category():
    agent = SQLAnalystAgent()

    spec = agent.build_analysis_spec(
        SQLAgentRequest(
            question="revenue by category in 2025"
        )
    )

    assert spec.metric == "net_revenue"
    assert spec.dimensions == ["category"]
    assert spec.date_start == "2025-01-01"
    assert spec.date_end == "2025-12-31"
    assert spec.filters == {}

def test_generate_sql_for_revenue_by_category():
    agent = SQLAnalystAgent()

    spec = agent.build_analysis_spec(
        SQLAgentRequest(
            question="revenue by category in 2025"
        )
    )

    sql = agent.generate_sql(spec)

    assert "SUM(order_items.net_revenue) AS net_revenue" in sql
    assert "orders.order_id = order_items.order_id" in sql
    assert "products.product_id = order_items.product_id" in sql
    assert "orders.order_date >= '2025-01-01'" in sql
    assert "orders.order_date <= '2025-12-31'" in sql
    assert "GROUP BY products.category" in sql
    assert "ORDER BY products.category" in sql

def test_run_revenue_by_category_in_2025():
    agent = SQLAnalystAgent()

    response = agent.run(
        SQLAgentRequest(
            question="revenue by category in 2025"
        )
    )

    assert response.success is True
    assert response.answer is not None
    assert response.sql is not None
    assert response.rows
    assert response.errors == []

    assert response.columns == [
        "category",
        "net_revenue",
    ]

    assert "Net revenue by category" in response.answer
    assert response.evidence["metric"] == "net_revenue"
    assert response.provenance["sql_valid"] is True
    assert response.provenance["execution_success"] is True

def test_run_revenue_by_month_in_2025_formats_all_rows():
    agent = SQLAnalystAgent()

    response = agent.run(
        SQLAgentRequest(
            question="revenue by month in 2025"
        )
    )

    assert response.success is True
    assert response.answer is not None
    assert response.rows
    assert len(response.rows) == 12

    assert "Net revenue by month" in response.answer
    assert "1:" in response.answer
    assert "12:" in response.answer

def test_run_rejects_unsupported_metric_generation():
    agent = SQLAnalystAgent()

    response = agent.run(
        SQLAgentRequest(
            question="gross profit by category in 2025"
        )
    )

    assert response.success is False
    assert response.answer is None
    assert response.sql is None
    assert response.rows == []
    assert any(
        "Unsupported metric for SQL generation" in error
        for error in response.errors
    )

def test_run_includes_evidence_and_provenance():
    agent = SQLAnalystAgent()

    response = agent.run(
        SQLAgentRequest(
            question="revenue by category in 2025"
        )
    )

    assert response.success is True

    assert response.evidence["question"] == "revenue by category in 2025"
    assert response.evidence["metric"] == "net_revenue"
    assert response.evidence["dimensions"] == ["category"]
    assert response.evidence["date_start"] == "2025-01-01"
    assert response.evidence["date_end"] == "2025-12-31"
    assert response.evidence["row_count"] == 10

    assert response.provenance["metric"] == "net_revenue"
    assert response.provenance["dimensions"] == ["category"]
    assert response.provenance["sql_valid"] is True
    assert response.provenance["execution_success"] is True

def test_run_rejects_empty_question():
    agent = SQLAnalystAgent()

    response = agent.run(
        SQLAgentRequest(
            question=""
        )
    )

    assert response.success is False
    assert response.answer is None
    assert response.sql is None
    assert response.rows == []
    assert response.errors


def test_run_rejects_whitespace_only_question():
    agent = SQLAnalystAgent()

    response = agent.run(
        SQLAgentRequest(
            question="   "
        )
    )

    assert response.success is False
    assert response.answer is None
    assert response.sql is None
    assert response.rows == []
    assert response.errors


def test_run_rejects_non_string_question():
    agent = SQLAnalystAgent()

    response = agent.run(
        SQLAgentRequest(
            question=None
        )
    )

    assert response.success is False
    assert response.answer is None
    assert response.sql is None
    assert response.rows == []
    assert response.errors

def test_resolve_dimension_category():
    agent = SQLAnalystAgent()

    dimension = agent.resolve_dimension("revenue by category in 2025")

    assert dimension == "category"


def test_resolve_dimension_customer_city():
    agent = SQLAnalystAgent()

    dimension = agent.resolve_dimension("revenue by customer city in 2025")

    assert dimension == "customer.city"


def test_resolve_dimension_store_city():
    agent = SQLAnalystAgent()

    dimension = agent.resolve_dimension("revenue by store city in 2025")

    assert dimension == "store.city"

def test_resolve_year_2025():
    agent = SQLAnalystAgent()

    start, end = agent.resolve_year(
        "Show revenue by category in 2025"
    )

    assert start == "2025-01-01"
    assert end == "2025-12-31"


def test_resolve_year_2026_respects_dataset_boundary():
    agent = SQLAnalystAgent()

    start, end = agent.resolve_year(
        "Show revenue by category in 2026"
    )

    assert start == "2026-01-01"
    assert end == "2026-08-31"


def test_resolve_year_rejects_multiple_years():
    agent = SQLAnalystAgent()

    with pytest.raises(ValueError, match="Multiple years"):
        agent.resolve_year(
            "Compare revenue in 2025 and 2026"
        )


def test_resolve_year_rejects_year_outside_dataset():
    agent = SQLAnalystAgent()

    with pytest.raises(ValueError, match="outside the available dataset"):
        agent.resolve_year(
            "Show revenue by category in 2023"
        )

def test_generate_sql_for_revenue_by_brand():
    agent = SQLAnalystAgent()

    spec = agent.build_analysis_spec(
        SQLAgentRequest(
            question="revenue by brand in 2025"
        )
    )

    sql = agent.generate_sql(spec)

    assert "SUM(order_items.net_revenue) AS net_revenue" in sql
    assert "orders.order_id = order_items.order_id" in sql
    assert "products.product_id = order_items.product_id" in sql
    assert "orders.order_date >= '2025-01-01'" in sql
    assert "orders.order_date <= '2025-12-31'" in sql
    assert "GROUP BY products.brand" in sql
    assert "ORDER BY products.brand" in sql

def test_run_revenue_by_brand_in_2025():
    agent = SQLAnalystAgent()

    response = agent.run(
        SQLAgentRequest(
            question="revenue by brand in 2025"
        )
    )

    assert response.success is True
    assert response.answer is not None
    assert response.sql is not None
    assert response.rows
    assert response.errors == []

    assert response.columns == [
        "brand",
        "net_revenue",
    ]

    assert "net revenue" in response.answer.lower()
    assert response.evidence["metric"] == "net_revenue"
    assert response.evidence["dimensions"] == ["brand"]
    assert response.provenance["sql_valid"] is True
    assert response.provenance["execution_success"] is True

def test_generate_sql_for_revenue_by_subcategory():
    agent = SQLAnalystAgent()

    spec = agent.build_analysis_spec(
        SQLAgentRequest(
            question="revenue by subcategory in 2025"
        )
    )

    sql = agent.generate_sql(spec)

    assert "SUM(order_items.net_revenue) AS net_revenue" in sql
    assert "orders.order_id = order_items.order_id" in sql
    assert "products.product_id = order_items.product_id" in sql
    assert "orders.order_date >= '2025-01-01'" in sql
    assert "orders.order_date <= '2025-12-31'" in sql
    assert "GROUP BY products.subcategory" in sql
    assert "ORDER BY products.subcategory" in sql

def test_run_revenue_by_subcategory_in_2025():
    agent = SQLAnalystAgent()

    response = agent.run(
        SQLAgentRequest(
            question="revenue by subcategory in 2025"
        )
    )

    assert response.success is True
    assert response.answer is not None
    assert response.sql is not None
    assert response.rows
    assert response.errors == []

    assert response.columns == [
        "subcategory",
        "net_revenue",
    ]

    assert "net revenue" in response.answer.lower()
    assert response.evidence["metric"] == "net_revenue"
    assert response.evidence["dimensions"] == ["subcategory"]
    assert response.provenance["sql_valid"] is True
    assert response.provenance["execution_success"] is True

def test_generate_sql_for_revenue_by_product():
    agent = SQLAnalystAgent()

    spec = agent.build_analysis_spec(
        SQLAgentRequest(
            question="revenue by product in 2025"
        )
    )

    sql = agent.generate_sql(spec)

    assert "SUM(order_items.net_revenue) AS net_revenue" in sql
    assert "orders.order_id = order_items.order_id" in sql
    assert "products.product_id = order_items.product_id" in sql
    assert "orders.order_date >= '2025-01-01'" in sql
    assert "orders.order_date <= '2025-12-31'" in sql
    assert "GROUP BY products.product_name" in sql
    assert "ORDER BY products.product_name" in sql

def test_generate_sql_revenue_by_customer_city():
    agent = SQLAnalystAgent()
    spec = agent.build_analysis_spec(
        SQLAgentRequest("revenue by customer city in 2025")
    )

    sql = agent.generate_sql(spec)

    assert "customers.city AS city" in sql
    assert "JOIN customers" in sql
    assert "customers.customer_id = orders.customer_id" in sql
    assert "SUM(order_items.net_revenue) AS net_revenue" in sql
    assert "2025-01-01" in sql
    assert "2025-12-31" in sql
    assert "GROUP BY customers.city" in sql

def test_run_revenue_by_customer_city_in_2025():
    agent = SQLAnalystAgent()

    response = agent.run(
        SQLAgentRequest("revenue by customer city in 2025")
    )

    assert response.success is True
    assert response.errors == []
    assert response.rows
    assert response.provenance["metric"] == "net_revenue"
    assert response.provenance["dimensions"] == ["customer.city"]
    assert response.provenance["date_start"] == "2025-01-01"
    assert response.provenance["date_end"] == "2025-12-31"
    assert response.provenance["sql_valid"] is True
    assert response.provenance["execution_success"] is True

def test_run_revenue_by_product_in_2025():
    agent = SQLAnalystAgent()

    response = agent.run(
        SQLAgentRequest(
            question="revenue by product in 2025"
        )
    )

    assert response.success is True
    assert response.answer is not None
    assert response.sql is not None
    assert response.rows
    assert response.errors == []

    assert response.columns == [
        "product",
        "net_revenue",
    ]

    assert "net revenue" in response.answer.lower()
    assert response.evidence["metric"] == "net_revenue"
    assert response.evidence["dimensions"] == ["product"]
    assert response.provenance["sql_valid"] is True
    assert response.provenance["execution_success"] is True

def test_resolve_gross_revenue_metric():
    agent = SQLAnalystAgent()

    metric = agent.resolve_metric("gross revenue")

    assert metric == "gross_revenue"

def test_generate_sql_for_gross_revenue_by_category():
    agent = SQLAnalystAgent()

    spec = agent.build_analysis_spec(
        SQLAgentRequest(
            question="gross revenue by category in 2025"
        )
    )

    sql = agent.generate_sql(spec)

    assert "SUM(order_items.quantity * order_items.unit_price) AS gross_revenue" in sql
    assert "orders.order_id = order_items.order_id" in sql
    assert "products.product_id = order_items.product_id" in sql
    assert "orders.order_date >= '2025-01-01'" in sql
    assert "orders.order_date <= '2025-12-31'" in sql
    assert "GROUP BY products.category" in sql
    assert "ORDER BY products.category" in sql

def test_run_gross_revenue_by_category_in_2025():
    agent = SQLAnalystAgent()

    response = agent.run(
        SQLAgentRequest(
            question="gross revenue by category in 2025"
        )
    )

    assert response.success is True
    assert response.answer is not None
    assert response.sql is not None
    assert response.rows
    assert response.errors == []

    assert response.columns == [
        "category",
        "gross_revenue",
    ]

    assert "gross revenue" in response.answer.lower()
    assert response.evidence["metric"] == "gross_revenue"
    assert response.evidence["dimensions"] == ["category"]
    assert response.provenance["sql_valid"] is True
    assert response.provenance["execution_success"] is True

def test_revise_sql_removes_internal_semicolon():
    agent = SQLAnalystAgent()

    sql = "SELECT * FROM orders; SELECT * FROM customers"
    revised = agent.revise_sql(
        sql,
        ["Only one SQL statement is allowed."],
    )

    assert revised == "SELECT * FROM orders SELECT * FROM customers"


def test_revise_sql_removes_trailing_semicolon():
    agent = SQLAnalystAgent()

    sql = "SELECT * FROM orders;"
    revised = agent.revise_sql(
        sql,
        ["SQL candidate requires revision."],
    )

    assert revised == "SELECT * FROM orders"


def test_revise_sql_returns_none_for_empty_sql():
    agent = SQLAnalystAgent()

    revised = agent.revise_sql(
        "   ",
        ["SQL candidate is empty."],
    )

    assert revised is None


def test_revise_sql_returns_sql_when_no_validation_errors():
    agent = SQLAnalystAgent()

    sql = "SELECT * FROM orders"

    revised = agent.revise_sql(
        sql,
        [],
    )

    assert revised == sql

def test_run_revises_invalid_sql_before_execution(monkeypatch):
    agent = SQLAnalystAgent()

    original_sql = "SELECT * FROM orders; SELECT * FROM customers"
    revised_sql = "SELECT * FROM orders SELECT * FROM customers"

    validation_calls = []

    class FakeValidation:
        def __init__(self, valid, errors=None):
            self.valid = valid
            self.errors = errors or []

    def fake_validate(sql):
        validation_calls.append(sql)

        if sql == original_sql:
            return FakeValidation(
                False,
                ["Only one SQL statement is allowed."],
            )

        return FakeValidation(True)

    class FakeResult:
        success = True
        columns = ["category", "net_revenue"]
        rows = [
            {
                "category": "Furniture",
                "net_revenue": 1000,
            }
        ]
        row_count = 1
        error = None
        execution_time_ms = 1.0

    executed_sql = []

    def fake_execute(sql):
        executed_sql.append(sql)
        return FakeResult()

    monkeypatch.setattr(
        agent,
        "validate_query",
        fake_validate,
    )

    monkeypatch.setattr(
        agent,
        "generate_sql",
        lambda spec: original_sql,
    )

    monkeypatch.setattr(
        "app.agents.sql_agent.execute_sql",
        fake_execute,
    )

    monkeypatch.setattr(
        agent,
        "revise_sql",
        lambda sql, errors: revised_sql,
    )

    request = SQLAgentRequest(
        "revenue by category in 2025"
    )

    response = agent.run(request)

    assert response.success is True
    assert executed_sql == [revised_sql]
    assert validation_calls == [
        original_sql,
        revised_sql,
        revised_sql,
    ]

def test_run_fails_if_revised_sql_is_still_invalid(monkeypatch):
    agent = SQLAnalystAgent()

    original_sql = "SELECT * FROM orders; SELECT * FROM customers"
    revised_sql = "SELECT * FROM orders; SELECT * FROM payments"

    validation_calls = []

    class FakeValidation:
        def __init__(self, valid, errors=None):
            self.valid = valid
            self.errors = errors or []

    def fake_validate(sql):
        validation_calls.append(sql)

        return FakeValidation(
            False,
            ["Only one SQL statement is allowed."],
        )

    execute_called = []

    def fake_execute(sql):
        execute_called.append(sql)
        raise AssertionError(
            "execute_sql must not be called when SQL remains invalid."
        )

    monkeypatch.setattr(
        agent,
        "validate_query",
        fake_validate,
    )

    monkeypatch.setattr(
        agent,
        "generate_sql",
        lambda spec: original_sql,
    )

    monkeypatch.setattr(
        "app.agents.sql_agent.execute_sql",
        fake_execute,
    )

    monkeypatch.setattr(
        agent,
        "revise_sql",
        lambda sql, errors: revised_sql,
    )

    request = SQLAgentRequest(
        "revenue by category in 2025"
    )

    response = agent.run(request)

    assert response.success is False
    assert execute_called == []
    assert validation_calls == [
        original_sql,
        revised_sql,
    ]
    assert response.provenance["sql_valid"] is False

def test_run_fails_when_required_schema_is_missing(monkeypatch):
    agent = SQLAnalystAgent()

    original_schema_has_column = agent.schema_has_column

    def fake_schema_has_column(table, column):
        if table == "products" and column == "category":
            return False
        return original_schema_has_column(table, column)

    monkeypatch.setattr(
        agent,
        "schema_has_column",
        fake_schema_has_column,
    )

    response = agent.run(
        SQLAgentRequest("revenue by category in 2025")
    )

    assert response.success is False
    assert "products.category" in response.errors[0]
    assert response.provenance["schema_valid"] is False

def test_schema_has_existing_column():
    agent = SQLAnalystAgent()

    assert agent.schema_has_column(
        "products",
        "category",
    )


def test_schema_has_nonexistent_column():
    agent = SQLAnalystAgent()

    assert not agent.schema_has_column(
        "products",
        "does_not_exist",
    )


def test_schema_has_column_for_nonexistent_table():
    agent = SQLAnalystAgent()

    assert not agent.schema_has_column(
        "does_not_exist",
        "category",
    )

def test_validate_required_schema_accepts_existing_schema():
    agent = SQLAnalystAgent()

    errors = agent.validate_required_schema(
        {
            "orders": ["order_id", "order_date"],
            "order_items": ["order_id", "product_id", "net_revenue"],
            "products": ["product_id", "category"],
        }
    )

    assert errors == []


def test_validate_required_schema_rejects_missing_column():
    agent = SQLAnalystAgent()

    errors = agent.validate_required_schema(
        {
            "products": ["category", "does_not_exist"],
        }
    )

    assert errors == [
        "Required column does not exist: products.does_not_exist"
    ]


def test_validate_required_schema_rejects_missing_table():
    agent = SQLAnalystAgent()

    errors = agent.validate_required_schema(
        {
            "does_not_exist": ["category"],
        }
    )

    assert errors == [
        "Required table does not exist: does_not_exist"
    ]

def test_extract_metric_text_with_customer_city():
    agent = SQLAnalystAgent()

    metric_text = agent.extract_metric_text(
        "revenue by customer city in 2025"
    )

    assert metric_text == "revenue"

def test_run_fails_when_required_schema_is_missing(monkeypatch):
    agent = SQLAnalystAgent()

    original_schema_has_column = agent.schema_has_column

    def fake_schema_has_column(table, column):
        if table == "products" and column == "category":
            return False

        return original_schema_has_column(table, column)

    monkeypatch.setattr(
        agent,
        "schema_has_column",
        fake_schema_has_column,
    )

    response = agent.run(
        SQLAgentRequest(
            "revenue by category in 2025"
        )
    )

    assert response.success is False
    assert "products.category" in response.errors[0]
    assert response.provenance["schema_valid"] is False

def test_resolve_time_grain_aliases():
    agent = SQLAnalystAgent()

    assert agent.resolve_time_grain("revenue by day in 2025") == "day"
    assert agent.resolve_time_grain("revenue by weekly trend in 2025") == "week"
    assert agent.resolve_time_grain("revenue by month in 2025") == "month"
    assert agent.resolve_time_grain("revenue by quarterly trend in 2025") == "quarter"
    assert agent.resolve_time_grain("revenue by yearly trend in 2025") == "year"


def test_build_analysis_spec_for_revenue_by_month():
    agent = SQLAnalystAgent()

    spec = agent.build_analysis_spec(
        SQLAgentRequest(
            question="revenue by month in 2025"
        )
    )

    assert spec.metric == "net_revenue"
    assert spec.dimensions == []
    assert spec.time_grain == "month"
    assert spec.date_start == "2025-01-01"
    assert spec.date_end == "2025-12-31"


def test_generate_sql_for_revenue_by_month():
    agent = SQLAnalystAgent()

    spec = agent.build_analysis_spec(
        SQLAgentRequest(
            question="revenue by month in 2025"
        )
    )

    sql = agent.generate_sql(spec)

    assert "calendar.date = orders.order_date" in sql
    assert "calendar.month AS month" in sql
    assert "GROUP BY calendar.month" in sql
    assert "ORDER BY calendar.month" in sql
    assert "SUM(order_items.net_revenue) AS net_revenue" in sql


def test_generate_sql_for_revenue_by_quarter():
    agent = SQLAnalystAgent()

    spec = agent.build_analysis_spec(
        SQLAgentRequest(
            question="revenue by quarter in 2025"
        )
    )

    sql = agent.generate_sql(spec)

    assert "calendar.quarter AS quarter" in sql
    assert "GROUP BY calendar.quarter" in sql
    assert "ORDER BY calendar.quarter" in sql


def test_generate_sql_for_revenue_by_year():
    agent = SQLAnalystAgent()

    spec = agent.build_analysis_spec(
        SQLAgentRequest(
            question="revenue by year in 2025"
        )
    )

    sql = agent.generate_sql(spec)

    assert "calendar.year AS year" in sql
    assert "GROUP BY calendar.year" in sql
    assert "ORDER BY calendar.year" in sql


def test_generate_sql_for_revenue_by_day():
    agent = SQLAnalystAgent()

    spec = agent.build_analysis_spec(
        SQLAgentRequest(
            question="revenue by day in 2025"
        )
    )

    sql = agent.generate_sql(spec)

    assert "calendar.date AS day" in sql
    assert "GROUP BY calendar.date" in sql
    assert "ORDER BY calendar.date" in sql


def test_generate_sql_for_revenue_by_week():
    agent = SQLAnalystAgent()

    spec = agent.build_analysis_spec(
        SQLAgentRequest(
            question="revenue by week in 2025"
        )
    )

    sql = agent.generate_sql(spec)

    assert "calendar.week AS week" in sql
    assert "GROUP BY calendar.week" in sql
    assert "ORDER BY calendar.week" in sql