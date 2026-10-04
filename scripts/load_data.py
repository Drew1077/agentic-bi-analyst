import os
import time
from pathlib import Path

import pandas as pd
import mysql.connector
from dotenv import load_dotenv


# ============================================================
# Agentic BI Analyst
# CSV -> MySQL Data Loader
# Dataset Version: v1.0
# ============================================================

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "generated"


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

load_dotenv(PROJECT_ROOT / ".env")

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "database": os.getenv("MYSQL_DATABASE", "agentic_bi"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
}


# ------------------------------------------------------------
# Frozen dataset row counts
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# Table configuration
# ------------------------------------------------------------

TABLE_CONFIG = {
    "calendar": {
        "file": "calendar.csv",
        "columns": [
            "date",
            "day",
            "month",
            "month_name",
            "quarter",
            "year",
            "week",
            "day_name",
            "is_weekend",
            "holiday_name",
            "is_holiday",
            "fiscal_year",
            "fiscal_quarter",
            "season",
        ],
        "chunksize": None,
    },

    "stores": {
        "file": "stores.csv",
        "columns": [
            "store_id",
            "store_name",
            "store_type",
            "city",
            "state",
            "region",
            "opening_date",
            "store_size_sqft",
            "status",
        ],
        "chunksize": None,
    },

    "products": {
        "file": "products.csv",
        "columns": [
            "product_id",
            "product_name",
            "category",
            "subcategory",
            "brand",
            "unit_cost",
            "base_price",
            "launch_date",
            "product_status",
            "supplier_region",
            "weight_kg",
            "rating",
            "rating_count",
        ],
        "chunksize": None,
    },

    "customers": {
        "file": "customers.csv",
        "columns": [
            "customer_id",
            "first_name",
            "last_name",
            "email",
            "gender",
            "birth_year",
            "signup_date",
            "customer_segment",
            "city",
            "state",
            "region",
            "postal_code",
            "acquisition_channel",
            "preferred_device",
            "customer_status",
        ],
        "chunksize": 5000,
    },

    "orders": {
        "file": "orders.csv",
        "columns": [
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
        ],
        "chunksize": 10000,
    },

    "order_items": {
        "file": "order_items.csv",
        "columns": [
            "order_item_id",
            "order_id",
            "product_id",
            "quantity",
            "unit_price",
            "unit_cost",
            "discount_percent",
            "discount_amount",
            "gross_revenue",
            "net_revenue",
            "total_cost",
            "gross_profit",
        ],
        "chunksize": 10000,
    },

    "payments": {
        "file": "payments.csv",
        "columns": [
            "payment_id",
            "order_id",
            "payment_date",
            "payment_method",
            "payment_status",
            "amount",
            "transaction_reference",
            "refund_amount",
        ],
        "chunksize": 10000,
    },

    "returns": {
        "file": "returns.csv",
        "columns": [
            "return_id",
            "order_id",
            "order_item_id",
            "return_date",
            "return_quantity",
            "return_reason",
            "refund_amount",
            "return_status",
            "condition",
        ],
        "chunksize": 5000,
    },

    "marketing_spend": {
        "file": "marketing_spend.csv",
        "columns": [
            "marketing_id",
            "date",
            "channel",
            "campaign_name",
            "region",
            "spend",
            "impressions",
            "clicks",
            "conversions",
        ],
        "chunksize": 5000,
    },

    "inventory_snapshots": {
        "file": "inventory_snapshots.csv",
        "columns": [
            "snapshot_id",
            "snapshot_date",
            "store_id",
            "product_id",
            "opening_stock",
            "units_received",
            "units_sold",
            "units_returned",
            "closing_stock",
            "reorder_level",
            "stockout_flag",
        ],
        "chunksize": 10000,
    },
}


# ------------------------------------------------------------
# Dependency order
# ------------------------------------------------------------

LOAD_ORDER = [
    "calendar",
    "stores",
    "products",
    "customers",
    "orders",
    "order_items",
    "payments",
    "returns",
    "marketing_spend",
    "inventory_snapshots",
]


# ------------------------------------------------------------
# Database connection
# ------------------------------------------------------------

def get_connection():
    """Create and return a MySQL connection."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)

        if not connection.is_connected():
            raise RuntimeError("MySQL connection was not established.")

        return connection

    except mysql.connector.Error as exc:
        raise RuntimeError(
            f"Could not connect to MySQL: {exc}"
        ) from exc


# ------------------------------------------------------------
# File validation
# ------------------------------------------------------------

def validate_files():
    """Make sure all expected CSV files exist."""

    print("\nChecking source CSV files...")

    missing_files = []

    for table_name, config in TABLE_CONFIG.items():
        file_path = DATA_DIR / config["file"]

        if not file_path.exists():
            missing_files.append(str(file_path))
        else:
            print(f"[OK] {config['file']}")

    if missing_files:
        print("\nMissing files:")

        for file_path in missing_files:
            print(f"  - {file_path}")

        raise FileNotFoundError(
            "One or more required CSV files are missing."
        )

    print("[OK] All source files found.")


# ------------------------------------------------------------
# SQL helpers
# ------------------------------------------------------------

def create_insert_sql(table_name, columns):
    """Create a parameterized INSERT statement."""

    column_list = ", ".join(f"`{column}`" for column in columns)
    placeholders = ", ".join(["%s"] * len(columns))

    return (
        f"INSERT INTO `{table_name}` "
        f"({column_list}) "
        f"VALUES ({placeholders})"
    )


# ------------------------------------------------------------
# Data preparation
# ------------------------------------------------------------

def prepare_dataframe(df, table_name):
    """
    Perform only database-loading-safe conversions.

    This function does NOT modify business values or regenerate data.
    """

    # Convert pandas NaN/NaT to Python None so MySQL receives SQL NULL.
    df = df.astype(object).where(pd.notna(df), None)

    # MySQL BOOLEAN columns accept 0/1 values.
    boolean_columns = {
        "calendar": ["is_weekend", "is_holiday"],
        "inventory_snapshots": ["stockout_flag"],
    }

    for column in boolean_columns.get(table_name, []):
        if column in df.columns:
            df[column] = df[column].apply(
                lambda value: None if value is None else int(bool(value))
            )

    return df


# ------------------------------------------------------------
# Single-table loader
# ------------------------------------------------------------

def load_table(connection, table_name):
    """Load one CSV file into its corresponding MySQL table."""

    config = TABLE_CONFIG[table_name]

    file_path = DATA_DIR / config["file"]
    columns = config["columns"]
    chunksize = config["chunksize"]

    print("\n" + "=" * 70)
    print(f"Loading table: {table_name}")
    print(f"Source: {file_path.name}")
    print(f"Expected rows: {EXPECTED_COUNTS[table_name]:,}")
    print("=" * 70)

    insert_sql = create_insert_sql(table_name, columns)

    cursor = connection.cursor()

    total_loaded = 0
    start_time = time.time()

    try:
        if chunksize is None:
            # Used only for small tables.
            df = pd.read_csv(file_path)

            df = prepare_dataframe(df, table_name)

            rows = list(
                df[columns].itertuples(index=False, name=None)
            )

            cursor.executemany(insert_sql, rows)
            connection.commit()

            total_loaded = len(rows)

            print(
                f"[OK] {table_name}: "
                f"{total_loaded:,} rows loaded"
            )

        else:
            # Large files are processed incrementally.
            for chunk_number, df in enumerate(
                pd.read_csv(
                    file_path,
                    chunksize=chunksize
                ),
                start=1,
            ):
                df = prepare_dataframe(df, table_name)

                rows = list(
                    df[columns].itertuples(
                        index=False,
                        name=None
                    )
                )

                cursor.executemany(insert_sql, rows)

                connection.commit()

                rows_in_chunk = len(df)
                total_loaded += rows_in_chunk

                elapsed = time.time() - start_time

                print(
                    f"[{table_name}] "
                    f"chunk={chunk_number:,} "
                    f"loaded={total_loaded:,} "
                    f"elapsed={elapsed:.1f}s"
                )

        elapsed = time.time() - start_time

        expected = EXPECTED_COUNTS[table_name]

        if total_loaded != expected:
            raise RuntimeError(
                f"{table_name}: loaded {total_loaded:,} rows "
                f"but expected {expected:,}."
            )

        print(
            f"[SUCCESS] {table_name}: "
            f"{total_loaded:,}/{expected:,} rows "
            f"loaded in {elapsed:.1f}s"
        )

    except Exception:
        connection.rollback()

        print(
            f"[FAILED] Loading table '{table_name}'. "
            "Transaction rolled back."
        )

        raise

    finally:
        cursor.close()


# ------------------------------------------------------------
# Existing-row protection
# ------------------------------------------------------------

def check_existing_rows(connection):
    """
    Prevent accidental duplicate loading.

    The loader expects an empty project database before the first load.
    """

    cursor = connection.cursor()

    try:
        existing_tables = []

        for table_name in LOAD_ORDER:
            cursor.execute(
                f"SELECT COUNT(*) FROM `{table_name}`"
            )

            count = cursor.fetchone()[0]

            if count > 0:
                existing_tables.append(
                    f"{table_name}={count:,}"
                )

        if existing_tables:
            print("\nExisting data detected:")

            for item in existing_tables:
                print(f"  - {item}")

            raise RuntimeError(
                "\nDatabase already contains data. "
                "Loader stopped to prevent duplicate inserts."
            )

    finally:
        cursor.close()


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    print("\n" + "=" * 70)
    print("AGENTIC BI ANALYST - DATA LOADER")
    print("Dataset Version: v1.0")
    print("=" * 70)

    print(f"\nProject root: {PROJECT_ROOT}")
    print(f"Data directory: {DATA_DIR}")
    print(f"Database: {DB_CONFIG['database']}")

    validate_files()

    print("\nConnecting to MySQL...")

    connection = get_connection()

    print("[OK] MySQL connection established.")

    try:
        check_existing_rows(connection)

        print("\nStarting data load...")
        print(
            "Load order: "
            + " -> ".join(LOAD_ORDER)
        )

        overall_start = time.time()

        for table_name in LOAD_ORDER:
            load_table(
                connection,
                table_name
            )

        overall_elapsed = time.time() - overall_start

        print("\n" + "=" * 70)
        print("DATA LOAD COMPLETED SUCCESSFULLY")
        print("=" * 70)

        print(
            f"Total loading time: "
            f"{overall_elapsed / 60:.2f} minutes"
        )

    except Exception as exc:
        print("\n" + "=" * 70)
        print("DATA LOAD FAILED")
        print("=" * 70)
        print(f"Error: {exc}")

        raise

    finally:
        connection.close()
        print("\nMySQL connection closed.")


if __name__ == "__main__":
    main()