from app.tools.sql import (
    SQLResult,
    SchemaInfo,
    ValidationResult,
    execute_sql,
    inspect_schema,
    validate_sql,
)


def test_validate_select_query():
    result = validate_sql("SELECT * FROM orders")

    assert result.valid is True
    assert result.errors == []


def test_validate_cte_query():
    result = validate_sql(
        "WITH recent_orders AS ("
        "SELECT * FROM orders "
        "WHERE order_date >= '2026-01-01'"
        ") "
        "SELECT * FROM recent_orders"
    )

    assert result.valid is True
    assert result.errors == []


def test_validate_rejects_insert():
    result = validate_sql(
        "INSERT INTO orders (order_id) VALUES (999999)"
    )

    assert result.valid is False
    assert any("INSERT" in error for error in result.errors)


def test_validate_rejects_update():
    result = validate_sql(
        "UPDATE orders SET order_status = 'Cancelled'"
    )

    assert result.valid is False
    assert any("UPDATE" in error for error in result.errors)


def test_validate_rejects_delete():
    result = validate_sql("DELETE FROM orders")

    assert result.valid is False
    assert any("DELETE" in error for error in result.errors)


def test_validate_rejects_drop():
    result = validate_sql("DROP TABLE orders")

    assert result.valid is False
    assert any("DROP" in error for error in result.errors)

def test_validate_rejects_order_items_payments_join():
    result = validate_sql(
        """
        SELECT SUM(oi.quantity * oi.unit_price) AS gross_revenue
        FROM order_items oi
        JOIN payments p
            ON oi.order_id = p.order_id
        """
    )

    assert result.valid is False
    assert any(
        "order_items and payments" in error
        for error in result.errors
    )


def test_validate_allows_orders_order_items_join():
    result = validate_sql(
        """
        SELECT
            COUNT(DISTINCT o.order_id) AS orders,
            SUM(oi.quantity * oi.unit_price) AS gross_revenue
        FROM orders o
        JOIN order_items oi
            ON o.order_id = oi.order_id
        """
    )

    assert result.valid is True
    assert result.errors == []


def test_validate_rejects_orders_order_items_payments():
    result = validate_sql(
        """
        SELECT SUM(oi.quantity * oi.unit_price) AS gross_revenue
        FROM orders o
        JOIN order_items oi
            ON o.order_id = oi.order_id
        JOIN payments p
            ON o.order_id = p.order_id
        """
    )

    assert result.valid is False
    assert any(
        "orders, order_items, and payments" in error
        for error in result.errors
    )


def test_validate_rejects_orders_order_items_returns():
    result = validate_sql(
        """
        SELECT SUM(oi.quantity * oi.unit_price) AS gross_revenue
        FROM orders o
        JOIN order_items oi
            ON o.order_id = oi.order_id
        JOIN returns r
            ON o.order_id = r.order_id
        """
    )

    assert result.valid is False
    assert any(
        "orders, order_items, and returns" in error
        for error in result.errors
    )


def test_validate_rejects_order_items_inventory():
    result = validate_sql(
        """
        SELECT SUM(oi.quantity) AS units_sold
        FROM order_items oi
        JOIN inventory_snapshots i
            ON oi.product_id = i.product_id
        """
    )

    assert result.valid is False
    assert any(
        "order_items and inventory_snapshots" in error
        for error in result.errors
    )


def test_validate_rejects_payments_returns_order_items():
    result = validate_sql(
        """
        SELECT SUM(oi.quantity * oi.unit_price) AS gross_revenue
        FROM order_items oi
        JOIN payments p
            ON oi.order_id = p.order_id
        JOIN returns r
            ON oi.order_item_id = r.order_item_id
        """
    )

    assert result.valid is False
    assert any(
        "raw payments, returns, and order_items" in error
        for error in result.errors
    )


def test_validate_rejects_multiple_statements():
    result = validate_sql(
        "SELECT * FROM orders; DELETE FROM orders"
    )

    assert result.valid is False
    assert any(
        "Multiple SQL statements" in error
        for error in result.errors
    )


def test_validate_rejects_empty_sql():
    result = validate_sql("")

    assert result.valid is False
    assert any("empty" in error.lower() for error in result.errors)


def test_validate_accepts_line_comment():
    result = validate_sql(
        "-- This is a comment\n"
        "SELECT * FROM orders"
    )

    assert result.valid is True
    assert result.errors == []


def test_validate_accepts_inline_line_comment():
    result = validate_sql(
        "SELECT 1 -- DROP TABLE orders"
    )

    assert result.valid is True
    assert result.errors == []


def test_validate_accepts_block_comment():
    result = validate_sql(
        "/* This is a comment */ "
        "SELECT * FROM orders"
    )

    assert result.valid is True
    assert result.errors == []


def test_execute_select_returns_structured_result():
    result = execute_sql(
        "SELECT COUNT(*) AS order_count FROM orders"
    )

    assert result.success is True
    assert result.columns == ["order_count"]
    assert result.rows == [{"order_count": 150000}]
    assert result.row_count == 1
    assert result.error is None


def test_execute_select_returns_dictionary_rows():
    result = execute_sql(
        "SELECT store_id, store_name "
        "FROM stores "
        "ORDER BY store_id "
        "LIMIT 3"
    )

    assert result.success is True
    assert result.row_count == 3
    assert len(result.rows) == 3
    assert all(isinstance(row, dict) for row in result.rows)

    assert result.columns == [
        "store_id",
        "store_name",
    ]


def test_execute_empty_result():
    result = execute_sql(
        "SELECT store_id, store_name "
        "FROM stores "
        "WHERE store_id = %s",
        ("DOES_NOT_EXIST",),
    )

    assert result.success is True
    assert result.columns == [
        "store_id",
        "store_name",
    ]
    assert result.rows == []
    assert result.row_count == 0
    assert result.error is None


def test_execute_rejects_destructive_sql():
    result = execute_sql("DELETE FROM orders")

    assert result.success is False
    assert result.rows == []
    assert result.row_count == 0
    assert result.error is not None
    assert "SQL validation failed" in result.error
    assert "DELETE" in result.error


def test_execute_malformed_sql_returns_error():
    result = execute_sql("SELECT FROM orders")

    assert result.success is False
    assert result.rows == []
    assert result.row_count == 0
    assert result.error is not None


def test_execute_parameterized_query():
    result = execute_sql(
        "SELECT COUNT(*) AS order_count "
        "FROM orders "
        "WHERE order_date >= %s",
        ("2026-01-01",),
    )

    assert result.success is True
    assert result.columns == ["order_count"]
    assert result.rows == [{"order_count": 35280}]
    assert result.row_count == 1


def test_execute_records_execution_time():
    result = execute_sql(
        "SELECT COUNT(*) AS order_count FROM orders"
    )

    assert result.success is True
    assert result.execution_time_ms is not None
    assert isinstance(result.execution_time_ms, float)
    assert result.execution_time_ms >= 0


def test_execute_rejects_result_above_max_rows():
    result = execute_sql(
        "SELECT order_id, customer_id, order_date FROM orders"
    )

    assert result.success is False
    assert result.rows == []
    assert result.row_count == 0
    assert "exceeds the maximum allowed result size" in result.error


def test_execute_allows_result_within_max_rows():
    result = execute_sql(
        "SELECT order_id, customer_id, order_date FROM orders LIMIT 100"
    )

    assert result.success is True
    assert result.row_count == 100
    assert result.error is None


def test_inspect_schema_returns_expected_tables():
    schema = inspect_schema()

    expected_tables = {
        "calendar",
        "customers",
        "inventory_snapshots",
        "marketing_spend",
        "order_items",
        "orders",
        "payments",
        "products",
        "returns",
        "stores",
    }

    assert isinstance(schema, SchemaInfo)
    assert set(schema.tables.keys()) == expected_tables


def test_inspect_schema_orders_columns():
    schema = inspect_schema()

    orders = schema.tables["orders"]

    expected_columns = {
        "order_id",
        "customer_id",
        "store_id",
        "order_date",
        "order_timestamp",
        "order_status",
        "payment_status",
        "shipping_method",
        "delivery_date",
        "shipping_fee",
        "discount_amount",
        "tax_amount",
        "order_total",
    }

    actual_columns = {
        column["name"]
        for column in orders["columns"]
    }

    assert actual_columns == expected_columns


def test_inspect_schema_primary_keys():
    schema = inspect_schema()

    assert schema.tables["orders"]["primary_key"] == ["order_id"]
    assert schema.tables["order_items"]["primary_key"] == [
        "order_item_id"
    ]
    assert schema.tables["products"]["primary_key"] == ["product_id"]
    assert schema.tables["customers"]["primary_key"] == [
        "customer_id"
    ]


def test_inspect_schema_relationships():
    schema = inspect_schema()

    relationships = {
        (
            relationship["table"],
            relationship["column"],
            relationship["referenced_table"],
            relationship["referenced_column"],
        )
        for relationship in schema.relationships
    }

    expected_relationships = {
        (
            "orders",
            "customer_id",
            "customers",
            "customer_id",
        ),
        (
            "orders",
            "store_id",
            "stores",
            "store_id",
        ),
        (
            "order_items",
            "order_id",
            "orders",
            "order_id",
        ),
        (
            "order_items",
            "product_id",
            "products",
            "product_id",
        ),
        (
            "payments",
            "order_id",
            "orders",
            "order_id",
        ),
        (
            "returns",
            "order_id",
            "orders",
            "order_id",
        ),
        (
            "returns",
            "order_item_id",
            "order_items",
            "order_item_id",
        ),
    }

    assert expected_relationships.issubset(relationships)


def test_execute_connection_failure_returns_structured_result(
    monkeypatch,
):
    def failing_connection():
        raise RuntimeError("Simulated database connection failure")

    monkeypatch.setattr(
        "app.tools.sql._get_connection",
        failing_connection,
    )

    result = execute_sql(
        "SELECT COUNT(*) AS order_count FROM orders"
    )

    assert result.success is False
    assert result.columns == []
    assert result.rows == []
    assert result.row_count == 0
    assert result.error is not None
    assert "connection" in result.error.lower()