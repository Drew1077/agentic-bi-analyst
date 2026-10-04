from pathlib import Path
import os
import sys

import mysql.connector
import pandas as pd
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.tools.analytics import AnalyticsEngine, load_semantic_catalog


ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "database": os.getenv("MYSQL_DATABASE", "agentic_bi"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
}


def get_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)

        if not connection.is_connected():
            raise RuntimeError("MySQL connection was not established.")

        return connection

    except mysql.connector.Error as exc:
        raise RuntimeError(f"Could not connect to MySQL: {exc}") from exc


def load_sales_data(connection) -> pd.DataFrame:
    query = """
        SELECT
            oi.order_id,
            o.customer_id,
            oi.quantity,
            oi.unit_price,
            oi.unit_cost,
            oi.discount_percent
        FROM order_items AS oi
        INNER JOIN orders AS o
            ON oi.order_id = o.order_id
    """

    return pd.read_sql(query, connection)


def calculate_mysql_kpis(connection) -> dict[str, float | None]:
    query = """
        SELECT
            SUM(oi.quantity * oi.unit_price) AS gross_revenue,

            SUM(
                (oi.quantity * oi.unit_price)
                - (
                    oi.quantity
                    * oi.unit_price
                    * oi.discount_percent
                )
            ) AS net_revenue,

            SUM(
                (
                    oi.quantity * oi.unit_price
                    - (
                        oi.quantity
                        * oi.unit_price
                        * oi.discount_percent
                    )
                )
                - (oi.quantity * oi.unit_cost)
            ) AS gross_profit,

            COUNT(DISTINCT oi.order_id) AS orders,

            SUM(oi.quantity) AS units_sold,

            COUNT(DISTINCT o.customer_id) AS customer_count

        FROM order_items AS oi
        INNER JOIN orders AS o
            ON oi.order_id = o.order_id
    """

    cursor = connection.cursor(dictionary=True)
    cursor.execute(query)

    row = cursor.fetchone()
    cursor.close()

    gross_revenue = float(row["gross_revenue"])
    net_revenue = float(row["net_revenue"])
    gross_profit = float(row["gross_profit"])
    orders = int(row["orders"])
    units_sold = int(row["units_sold"])
    customer_count = int(row["customer_count"])

    discount_amount = gross_revenue - net_revenue

    return {
        "gross_revenue": gross_revenue,
        "net_revenue": net_revenue,
        "gross_profit": gross_profit,
        "profit_margin": (
            gross_profit / net_revenue
            if net_revenue != 0
            else None
        ),
        "discount_rate": (
            discount_amount / gross_revenue
            if gross_revenue != 0
            else None
        ),
        "orders": float(orders),
        "units_sold": float(units_sold),
        "average_order_value": (
            net_revenue / orders
            if orders != 0
            else None
        ),
        "average_selling_price": (
            net_revenue / units_sold
            if units_sold != 0
            else None
        ),
        "customer_count": float(customer_count),
        "customer_revenue": net_revenue,
        "revenue_per_customer": (
            net_revenue / customer_count
            if customer_count != 0
            else None
        ),
    }


def load_inventory_snapshot(
    connection,
    snapshot_date,
) -> pd.DataFrame:
    query = """
        SELECT
            snapshot_date,
            store_id,
            product_id,
            opening_stock,
            units_received,
            units_sold,
            units_returned,
            closing_stock,
            stockout_flag
        FROM inventory_snapshots
        WHERE snapshot_date = %s
    """

    return pd.read_sql(
        query,
        connection,
        params=(snapshot_date,),
    )


def get_latest_snapshot_date(connection):
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT MAX(snapshot_date)
        FROM inventory_snapshots
        """
    )

    result = cursor.fetchone()[0]
    cursor.close()

    if result is None:
        raise RuntimeError(
            "No inventory snapshot date exists in the database."
        )

    return result


def calculate_mysql_inventory_kpis(
    connection,
    snapshot_date,
) -> dict[str, float | None]:

    query = """
        SELECT
            SUM(closing_stock) AS closing_stock,

            CASE
                WHEN COUNT(stockout_flag) = 0 THEN NULL
                ELSE SUM(stockout_flag) / COUNT(stockout_flag)
            END AS stockout_rate

        FROM inventory_snapshots

        WHERE snapshot_date = %s
    """

    cursor = connection.cursor(dictionary=True)
    cursor.execute(query, (snapshot_date,))

    row = cursor.fetchone()
    cursor.close()

    return {
        "closing_stock": (
            float(row["closing_stock"])
            if row["closing_stock"] is not None
            else None
        ),
        "stockout_rate": (
            float(row["stockout_rate"])
            if row["stockout_rate"] is not None
            else None
        ),
    }


def compare_results(
    engine_results: dict[str, float | None],
    mysql_results: dict[str, float | None],
) -> bool:

    print("\n[INFO] Comparing AnalyticsEngine vs MySQL:")

    all_passed = True
    tolerance = 1e-6

    for metric in engine_results:
        engine_value = engine_results[metric]
        mysql_value = mysql_results[metric]

        if engine_value is None and mysql_value is None:
            print(f"[PASS] {metric}")
            continue

        if engine_value is None or mysql_value is None:
            print(
                f"[FAIL] {metric}: "
                f"Engine={engine_value}, MySQL={mysql_value}"
            )
            all_passed = False
            continue

        difference = abs(engine_value - mysql_value)

        if difference <= tolerance:
            print(
                f"[PASS] {metric}: "
                f"Engine={engine_value:.10f}, "
                f"MySQL={mysql_value:.10f}, "
                f"Difference={difference:.10f}"
            )
        else:
            print(
                f"[FAIL] {metric}: "
                f"Engine={engine_value:.10f}, "
                f"MySQL={mysql_value:.10f}, "
                f"Difference={difference:.10f}"
            )
            all_passed = False

    return all_passed


def verify_fact_isolation(connection) -> bool:
    """
    Verify that joining independent fact tables at raw grain
    can change the result, while the governed sales calculation
    remains based on order_items only.
    """

    correct_query = """
        SELECT
            SUM(oi.quantity * oi.unit_price) AS gross_revenue
        FROM order_items AS oi
    """

    unsafe_query = """
        SELECT
            SUM(oi.quantity * oi.unit_price) AS gross_revenue
        FROM order_items AS oi
        INNER JOIN payments AS p
            ON oi.order_id = p.order_id
    """

    cursor = connection.cursor(dictionary=True)

    cursor.execute(correct_query)
    correct_result = cursor.fetchone()["gross_revenue"]

    cursor.execute(unsafe_query)
    unsafe_result = cursor.fetchone()["gross_revenue"]

    cursor.close()

    correct_value = float(correct_result)
    unsafe_value = float(unsafe_result)

    print("\n[INFO] Fact-isolation verification:")
    print(f"[INFO] Correct order-item revenue: {correct_value:.2f}")
    print(f"[INFO] Raw order_items → payments revenue: {unsafe_value:.2f}")

    if abs(correct_value - unsafe_value) > 1e-6:
        print(
            "[PASS] Raw fact-table join produces a different result, "
            "confirming the double-counting risk."
        )
        print(
            "[PASS] Governed sales calculations must isolate "
            "order_items before aggregation."
        )
        return True

    print(
        "[FAIL] Unsafe fact-table join produced the same result. "
        "The expected double-counting risk was not demonstrated."
    )

    return False


def main():
    connection = None

    try:
        connection = get_connection()

        print("[PASS] MySQL connection established.")

        sales_data = load_sales_data(connection)

        print(f"[PASS] Sales data loaded: {len(sales_data):,} rows")

        semantic_directory = PROJECT_ROOT
        catalog = load_semantic_catalog(semantic_directory)
        engine = AnalyticsEngine(catalog)

        print("[PASS] Semantic catalog loaded.")
        print("[PASS] Analytics engine initialized.")

        # ---------------------------------------------------------
        # Sales KPI verification
        # ---------------------------------------------------------

        metrics_to_verify = [
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
        ]

        engine_sales_results = {}

        for metric in metrics_to_verify:
            result = engine.calculate_kpi(metric, sales_data)
            engine_sales_results[metric] = result.value

        mysql_sales_results = calculate_mysql_kpis(connection)

        sales_passed = compare_results(
            engine_sales_results,
            mysql_sales_results,
        )

        if not sales_passed:
            raise AssertionError(
                "Sales KPI verification failed."
            )

        print(
            "\n[PASS] All sales KPI results match "
            "independent MySQL calculations."
        )

        

    

        # ---------------------------------------------------------
        # Inventory verification
        # ---------------------------------------------------------

        snapshot_date = get_latest_snapshot_date(connection)

        print(
            f"\n[INFO] Inventory snapshot selected: "
            f"{snapshot_date}"
        )

        inventory_data = load_inventory_snapshot(
            connection,
            snapshot_date,
        )

        print(
            "[PASS] Inventory snapshot loaded: "
            f"{len(inventory_data):,} rows"
        )

        engine_inventory_results = {}

        for metric in [
            "closing_stock",
            "stockout_rate",
        ]:
            result = engine.calculate_kpi(
                metric,
                inventory_data,
            )

            engine_inventory_results[metric] = result.value

        mysql_inventory_results = calculate_mysql_inventory_kpis(
            connection,
            snapshot_date,
        )

        inventory_passed = compare_results(
            engine_inventory_results,
            mysql_inventory_results,
        )

        if not inventory_passed:
            raise AssertionError(
                "Inventory KPI verification failed."
            )

        print(
            "\n[PASS] All inventory KPI results match "
            "independent MySQL calculations."
        )


        fact_isolation_passed = verify_fact_isolation(connection)
        
        if not fact_isolation_passed:
            raise AssertionError(
                "Fact-isolation verification failed."
            )

    finally:
        if connection is not None and connection.is_connected():
            connection.close()
            print("\n[INFO] MySQL connection closed.")


if __name__ == "__main__":
    main()