import os
import sys
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv


# ============================================================
# Agentic BI Analyst
# MySQL Database Verification
# Dataset Version: v1.0
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")


DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "database": os.getenv("MYSQL_DATABASE", "agentic_bi"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
}


EXPECTED_COUNTS = {
    "calendar": 974,
    "stores": 63,
    "products": 2000,
    "customers": 20000,
    "orders": 150000,
    "order_items": 359066,
    "payments": 155412,
    "returns": 20963,
    "marketing_spend": 21392,
    "inventory_snapshots": 16800000,
}


TABLES = list(EXPECTED_COUNTS.keys())


def get_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)

        if not connection.is_connected():
            raise RuntimeError("MySQL connection failed.")

        return connection

    except mysql.connector.Error as exc:
        raise RuntimeError(
            f"MySQL connection error: {exc}"
        ) from exc


def print_result(check_name, passed, detail=""):
    status = "PASS" if passed else "FAIL"

    print(f"[{status}] {check_name}")

    if detail:
        print(f"       {detail}")


def check_tables(cursor):
    print("\n" + "=" * 70)
    print("1. TABLE EXISTENCE")
    print("=" * 70)

    cursor.execute("SHOW TABLES")
    actual_tables = {
        row[0]
        for row in cursor.fetchall()
    }

    all_passed = True

    for table in TABLES:
        exists = table in actual_tables

        print_result(
            f"Table: {table}",
            exists
        )

        if not exists:
            all_passed = False

    return all_passed


def check_row_counts(cursor):
    print("\n" + "=" * 70)
    print("2. ROW COUNTS")
    print("=" * 70)

    all_passed = True

    for table, expected in EXPECTED_COUNTS.items():

        cursor.execute(
            f"SELECT COUNT(*) FROM `{table}`"
        )

        actual = cursor.fetchone()[0]

        passed = actual == expected

        print_result(
            table,
            passed,
            f"actual={actual:,}, expected={expected:,}"
        )

        if not passed:
            all_passed = False

    return all_passed


def check_primary_key_uniqueness(cursor):
    print("\n" + "=" * 70)
    print("3. PRIMARY KEY UNIQUENESS")
    print("=" * 70)

    primary_keys = {
        "calendar": "date",
        "stores": "store_id",
        "products": "product_id",
        "customers": "customer_id",
        "orders": "order_id",
        "order_items": "order_item_id",
        "payments": "payment_id",
        "returns": "return_id",
        "marketing_spend": "marketing_id",
        "inventory_snapshots": "snapshot_id",
    }

    all_passed = True

    for table, pk in primary_keys.items():

        cursor.execute(
            f"""
            SELECT
                COUNT(*) AS total_rows,
                COUNT(DISTINCT `{pk}`) AS unique_keys
            FROM `{table}`
            """
        )

        total_rows, unique_keys = cursor.fetchone()

        passed = total_rows == unique_keys

        print_result(
            f"{table}.{pk}",
            passed,
            f"rows={total_rows:,}, unique_keys={unique_keys:,}"
        )

        if not passed:
            all_passed = False

    return all_passed


def check_foreign_keys(cursor):
    print("\n" + "=" * 70)
    print("4. FOREIGN KEY INTEGRITY")
    print("=" * 70)

    checks = [
        (
            "orders -> customers",
            """
            SELECT COUNT(*)
            FROM orders o
            LEFT JOIN customers c
                ON o.customer_id = c.customer_id
            WHERE c.customer_id IS NULL
            """
        ),
        (
            "orders -> stores",
            """
            SELECT COUNT(*)
            FROM orders o
            LEFT JOIN stores s
                ON o.store_id = s.store_id
            WHERE s.store_id IS NULL
            """
        ),
        (
            "order_items -> orders",
            """
            SELECT COUNT(*)
            FROM order_items oi
            LEFT JOIN orders o
                ON oi.order_id = o.order_id
            WHERE o.order_id IS NULL
            """
        ),
        (
            "order_items -> products",
            """
            SELECT COUNT(*)
            FROM order_items oi
            LEFT JOIN products p
                ON oi.product_id = p.product_id
            WHERE p.product_id IS NULL
            """
        ),
        (
            "payments -> orders",
            """
            SELECT COUNT(*)
            FROM payments p
            LEFT JOIN orders o
                ON p.order_id = o.order_id
            WHERE o.order_id IS NULL
            """
        ),
        (
            "returns -> orders",
            """
            SELECT COUNT(*)
            FROM returns r
            LEFT JOIN orders o
                ON r.order_id = o.order_id
            WHERE o.order_id IS NULL
            """
        ),
        (
            "returns -> order_items",
            """
            SELECT COUNT(*)
            FROM returns r
            LEFT JOIN order_items oi
                ON r.order_item_id = oi.order_item_id
            WHERE oi.order_item_id IS NULL
            """
        ),
        (
            "marketing_spend -> calendar",
            """
            SELECT COUNT(*)
            FROM marketing_spend m
            LEFT JOIN calendar c
                ON m.date = c.date
            WHERE c.date IS NULL
            """
        ),
        (
            "inventory -> calendar",
            """
            SELECT COUNT(*)
            FROM inventory_snapshots i
            LEFT JOIN calendar c
                ON i.snapshot_date = c.date
            WHERE c.date IS NULL
            """
        ),
        (
            "inventory -> stores",
            """
            SELECT COUNT(*)
            FROM inventory_snapshots i
            LEFT JOIN stores s
                ON i.store_id = s.store_id
            WHERE s.store_id IS NULL
            """
        ),
        (
            "inventory -> products",
            """
            SELECT COUNT(*)
            FROM inventory_snapshots i
            LEFT JOIN products p
                ON i.product_id = p.product_id
            WHERE p.product_id IS NULL
            """
        ),
    ]

    all_passed = True

    for name, query in checks:

        cursor.execute(query)

        orphan_count = cursor.fetchone()[0]

        passed = orphan_count == 0

        print_result(
            name,
            passed,
            f"orphan_rows={orphan_count:,}"
        )

        if not passed:
            all_passed = False

    return all_passed


def check_financial_formulas(cursor):
    print("\n" + "=" * 70)
    print("5. FINANCIAL FORMULA VALIDATION")
    print("=" * 70)

    checks = [
        (
            "gross_revenue = quantity × unit_price",
            """
            SELECT COUNT(*)
            FROM order_items
            WHERE ABS(
                gross_revenue -
                (quantity * unit_price)
            ) > 0.01
            """
        ),
        (
            "discount_amount = gross_revenue × discount_percent",
            """
            SELECT COUNT(*)
            FROM order_items
            WHERE ABS(
                discount_amount -
                (gross_revenue * discount_percent)
            ) > 0.01
            """
        ),
        (
            "net_revenue = gross_revenue - discount_amount",
            """
            SELECT COUNT(*)
            FROM order_items
            WHERE ABS(
                net_revenue -
                (gross_revenue - discount_amount)
            ) > 0.01
            """
        ),
        (
            "total_cost = quantity × unit_cost",
            """
            SELECT COUNT(*)
            FROM order_items
            WHERE ABS(
                total_cost -
                (quantity * unit_cost)
            ) > 0.01
            """
        ),
        (
            "gross_profit = net_revenue - total_cost",
            """
            SELECT COUNT(*)
            FROM order_items
            WHERE ABS(
                gross_profit -
                (net_revenue - total_cost)
            ) > 0.01
            """
        ),
    ]

    all_passed = True

    for name, query in checks:

        cursor.execute(query)

        invalid_rows = cursor.fetchone()[0]

        passed = invalid_rows == 0

        print_result(
            name,
            passed,
            f"invalid_rows={invalid_rows:,}"
        )

        if not passed:
            all_passed = False

    return all_passed


def check_inventory_equation(cursor):
    print("\n" + "=" * 70)
    print("6. INVENTORY EQUATION VALIDATION")
    print("=" * 70)

    query = """
        SELECT COUNT(*)
        FROM inventory_snapshots
        WHERE closing_stock != (
            opening_stock
            + units_received
            - units_sold
            + units_returned
        )
    """

    cursor.execute(query)

    invalid_rows = cursor.fetchone()[0]

    passed = invalid_rows == 0

    print_result(
        "closing_stock equation",
        passed,
        f"invalid_rows={invalid_rows:,}"
    )

    return passed


def check_nulls(cursor):
    print("\n" + "=" * 70)
    print("7. REQUIRED NULL VALIDATION")
    print("=" * 70)

    checks = [
        ("calendar.date", "calendar", "date"),
        ("stores.store_id", "stores", "store_id"),
        ("products.product_id", "products", "product_id"),
        ("customers.customer_id", "customers", "customer_id"),
        ("orders.order_id", "orders", "order_id"),
        ("order_items.order_item_id", "order_items", "order_item_id"),
        ("payments.payment_id", "payments", "payment_id"),
        ("returns.return_id", "returns", "return_id"),
        ("marketing_spend.marketing_id", "marketing_spend", "marketing_id"),
        (
            "inventory_snapshots.snapshot_id",
            "inventory_snapshots",
            "snapshot_id",
        ),
    ]

    all_passed = True

    for label, table, column in checks:

        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM `{table}`
            WHERE `{column}` IS NULL
            """
        )

        null_count = cursor.fetchone()[0]

        passed = null_count == 0

        print_result(
            label,
            passed,
            f"null_rows={null_count:,}"
        )

        if not passed:
            all_passed = False

    return all_passed


def check_indexes(cursor):
    print("\n" + "=" * 70)
    print("8. INDEX VERIFICATION")
    print("=" * 70)

    required_indexes = {
        "orders": [
            "idx_orders_customer",
            "idx_orders_store",
            "idx_orders_date",
        ],
        "order_items": [
            "idx_order_items_order",
            "idx_order_items_product",
        ],
        "payments": [
            "idx_payments_order",
            "idx_payments_date",
        ],
        "returns": [
            "idx_returns_order",
            "idx_returns_order_item",
        ],
        "marketing_spend": [
            "idx_marketing_date",
            "idx_marketing_date_channel",
        ],
        "inventory_snapshots": [
            "idx_inventory_date_store_product",
            "idx_inventory_product_date",
        ],
    }

    all_passed = True

    for table, expected_indexes in required_indexes.items():

        cursor.execute(
            f"SHOW INDEX FROM `{table}`"
        )

        actual_indexes = {
            row[2]
            for row in cursor.fetchall()
        }

        for index_name in expected_indexes:

            passed = index_name in actual_indexes

            print_result(
                f"{table}.{index_name}",
                passed
            )

            if not passed:
                all_passed = False

    return all_passed


def main():

    print("\n" + "=" * 70)
    print("AGENTIC BI ANALYST - DATABASE VERIFICATION")
    print("Dataset Version: v1.0")
    print("=" * 70)

    print(f"\nDatabase: {DB_CONFIG['database']}")

    connection = None

    results = {}

    try:

        connection = get_connection()

        print("[OK] MySQL connection established.")

        cursor = connection.cursor()

        results["tables"] = check_tables(cursor)
        results["row_counts"] = check_row_counts(cursor)
        results["primary_keys"] = check_primary_key_uniqueness(cursor)
        results["foreign_keys"] = check_foreign_keys(cursor)
        results["financial_formulas"] = check_financial_formulas(cursor)
        results["inventory_equation"] = check_inventory_equation(cursor)
        results["required_nulls"] = check_nulls(cursor)
        results["indexes"] = check_indexes(cursor)

        cursor.close()

    except Exception as exc:

        print("\n" + "=" * 70)
        print("VERIFICATION ERROR")
        print("=" * 70)
        print(exc)

        sys.exit(1)

    finally:

        if connection is not None:
            connection.close()

    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)

    all_passed = True

    for check_name, passed in results.items():

        print_result(
            check_name,
            passed
        )

        if not passed:
            all_passed = False

    print("\n" + "=" * 70)

    if all_passed:
        print("DATABASE VERIFICATION PASSED")
        print("=" * 70)
        print(
            "All Chat 03 database integrity checks passed."
        )
        sys.exit(0)

    else:
        print("DATABASE VERIFICATION FAILED")
        print("=" * 70)
        print(
            "One or more database integrity checks failed."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()