from pathlib import Path

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

DATA_DIR = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "generated"
)

EXPECTED_ROWS = {
    "calendar.csv": 974,
    "stores.csv": 63,
    "products.csv": 2_000,
    "customers.csv": 20_000,
    "orders.csv": 150_000,
    "order_items.csv": 359_066,
    "payments.csv": 155_412,
    "returns.csv": 20_963,
    "marketing_spend.csv": 21_392,
    "inventory_snapshots.csv": 16_800_000,
}


# ============================================================
# HELPERS
# ============================================================

def load_csv(filename):
    path = DATA_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Missing file: {path}"
        )

    return pd.read_csv(path)


def check(condition, passed_message, failed_message):
    if condition:
        print(f"  [PASS] {passed_message}")
        return True

    print(f"  [FAIL] {failed_message}")
    return False


# ============================================================
# BASIC ROW COUNT VALIDATION
# ============================================================

def validate_row_counts():
    print("\n" + "=" * 60)
    print("1. ROW COUNT VALIDATION")
    print("=" * 60)

    all_passed = True

    for filename, expected in EXPECTED_ROWS.items():

        print(f"\nChecking {filename}...")

        # Inventory is large, so use chunked reading.
        if filename == "inventory_snapshots.csv":

            actual = 0

            for chunk in pd.read_csv(
                DATA_DIR / filename,
                usecols=["snapshot_id"],
                chunksize=500_000,
            ):
                actual += len(chunk)

        else:

            df = pd.read_csv(
                DATA_DIR / filename
            )

            actual = len(df)

        passed = check(
            actual == expected,
            f"{actual:,} rows",
            f"Expected {expected:,}, found {actual:,}",
        )

        all_passed &= passed

    return all_passed


# ============================================================
# PRIMARY KEY VALIDATION
# ============================================================

def validate_primary_keys():
    print("\n" + "=" * 60)
    print("2. PRIMARY KEY VALIDATION")
    print("=" * 60)

    all_passed = True

    primary_keys = {
        "calendar.csv": "date",
        "stores.csv": "store_id",
        "products.csv": "product_id",
        "customers.csv": "customer_id",
        "orders.csv": "order_id",
        "order_items.csv": "order_item_id",
        "payments.csv": "payment_id",
        "returns.csv": "return_id",
        "marketing_spend.csv": "marketing_id",
        "inventory_snapshots.csv": "snapshot_id",
    }

    for filename, key in primary_keys.items():

        print(f"\nChecking {filename} → {key}")

        duplicate_count = 0

        for chunk in pd.read_csv(
            DATA_DIR / filename,
            usecols=[key],
            chunksize=500_000,
        ):

            duplicate_count += (
                chunk[key].duplicated().sum()
            )

        passed = check(
            duplicate_count == 0,
            "No duplicate primary keys",
            f"{duplicate_count:,} duplicate keys found",
        )

        all_passed &= passed

    return all_passed


# ============================================================
# FOREIGN KEY VALIDATION
# ============================================================

def validate_foreign_keys():
    print("\n" + "=" * 60)
    print("3. FOREIGN KEY VALIDATION")
    print("=" * 60)

    all_passed = True

    customers = load_csv(
        "customers.csv"
    )

    products = load_csv(
        "products.csv"
    )

    stores = load_csv(
        "stores.csv"
    )

    orders = load_csv(
        "orders.csv"
    )

    order_items = load_csv(
        "order_items.csv"
    )

    # --------------------------------------------------------
    # Orders → Customers
    # --------------------------------------------------------

    invalid = (
        ~orders["customer_id"].isin(
            customers["customer_id"]
        )
    ).sum()

    all_passed &= check(
        invalid == 0,
        "orders.customer_id → customers.customer_id valid",
        f"{invalid:,} invalid customer references",
    )

    # --------------------------------------------------------
    # Orders → Stores
    # --------------------------------------------------------

    invalid = (
        ~orders["store_id"].isin(
            stores["store_id"]
        )
    ).sum()

    all_passed &= check(
        invalid == 0,
        "orders.store_id → stores.store_id valid",
        f"{invalid:,} invalid store references",
    )

    # --------------------------------------------------------
    # Order Items → Orders
    # --------------------------------------------------------

    invalid = (
        ~order_items["order_id"].isin(
            orders["order_id"]
        )
    ).sum()

    all_passed &= check(
        invalid == 0,
        "order_items.order_id → orders.order_id valid",
        f"{invalid:,} invalid order references",
    )

    # --------------------------------------------------------
    # Order Items → Products
    # --------------------------------------------------------

    invalid = (
        ~order_items["product_id"].isin(
            products["product_id"]
        )
    ).sum()

    all_passed &= check(
        invalid == 0,
        "order_items.product_id → products.product_id valid",
        f"{invalid:,} invalid product references",
    )

    return all_passed


# ============================================================
# ORDER ITEM FINANCIAL VALIDATION
# ============================================================

def validate_order_items():
    print("\n" + "=" * 60)
    print("4. ORDER ITEM FINANCIAL VALIDATION")
    print("=" * 60)

    items = load_csv(
        "order_items.csv"
    )

    all_passed = True

    # --------------------------------------------------------
    # Quantity
    # --------------------------------------------------------

    invalid = (
        items["quantity"] <= 0
    ).sum()

    all_passed &= check(
        invalid == 0,
        "All quantities > 0",
        f"{invalid:,} invalid quantities",
    )

    # --------------------------------------------------------
    # Prices and costs
    # --------------------------------------------------------

    invalid = (
        (items["unit_price"] <= 0)
        | (items["unit_cost"] <= 0)
    ).sum()

    all_passed &= check(
        invalid == 0,
        "All prices and costs > 0",
        f"{invalid:,} invalid price/cost rows",
    )

    # --------------------------------------------------------
    # Discount range
    # --------------------------------------------------------

    invalid = (
        (items["discount_percent"] < 0)
        | (items["discount_percent"] > 0.50)
    ).sum()

    all_passed &= check(
        invalid == 0,
        "Discount percentages within 0–50%",
        f"{invalid:,} invalid discount values",
    )

    # --------------------------------------------------------
    # Gross revenue formula
    # --------------------------------------------------------

    expected = (
        items["quantity"]
        * items["unit_price"]
    )

    invalid = (
        (items["gross_revenue"] - expected)
        .abs()
        > 0.02
    ).sum()

    all_passed &= check(
        invalid == 0,
        "gross_revenue formula reconciles",
        f"{invalid:,} reconciliation failures",
    )

    # --------------------------------------------------------
    # Discount amount
    # --------------------------------------------------------

    expected = (
        items["gross_revenue"]
        * items["discount_percent"]
    )

    invalid = (
        (items["discount_amount"] - expected)
        .abs()
        > 0.02
    ).sum()

    all_passed &= check(
        invalid == 0,
        "discount_amount formula reconciles",
        f"{invalid:,} reconciliation failures",
    )

    # --------------------------------------------------------
    # Net revenue
    # --------------------------------------------------------

    expected = (
        items["gross_revenue"]
        - items["discount_amount"]
    )

    invalid = (
        (items["net_revenue"] - expected)
        .abs()
        > 0.02
    ).sum()

    all_passed &= check(
        invalid == 0,
        "net_revenue formula reconciles",
        f"{invalid:,} reconciliation failures",
    )

    # --------------------------------------------------------
    # Total cost
    # --------------------------------------------------------

    expected = (
        items["quantity"]
        * items["unit_cost"]
    )

    invalid = (
        (items["total_cost"] - expected)
        .abs()
        > 0.02
    ).sum()

    all_passed &= check(
        invalid == 0,
        "total_cost formula reconciles",
        f"{invalid:,} reconciliation failures",
    )

    # --------------------------------------------------------
    # Gross profit
    # --------------------------------------------------------

    expected = (
        items["net_revenue"]
        - items["total_cost"]
    )

    invalid = (
        (items["gross_profit"] - expected)
        .abs()
        > 0.02
    ).sum()

    all_passed &= check(
        invalid == 0,
        "gross_profit formula reconciles",
        f"{invalid:,} reconciliation failures",
    )

    return all_passed


# ============================================================
# RETURN VALIDATION
# ============================================================

def validate_returns():
    print("\n" + "=" * 60)
    print("5. RETURN VALIDATION")
    print("=" * 60)

    returns = load_csv(
        "returns.csv"
    )

    order_items = load_csv(
        "order_items.csv"
    )

    all_passed = True

    # --------------------------------------------------------
    # Valid order item references
    # --------------------------------------------------------

    invalid = (
        ~returns["order_item_id"].isin(
            order_items["order_item_id"]
        )
    ).sum()

    all_passed &= check(
        invalid == 0,
        "All return order_item_id values are valid",
        f"{invalid:,} invalid order-item references",
    )

    # --------------------------------------------------------
    # Return quantities
    # --------------------------------------------------------

    item_quantities = (
        order_items[
            [
                "order_item_id",
                "quantity"
            ]
        ]
        .rename(
            columns={
                "quantity": "purchased_quantity"
            }
        )
    )

    merged = returns.merge(
        item_quantities,
        on="order_item_id",
        how="left"
    )

    invalid = (
        (merged["return_quantity"] <= 0)
        | (
            merged["return_quantity"]
            > merged["purchased_quantity"]
        )
    ).sum()

    all_passed &= check(
        invalid == 0,
        "Return quantities are valid",
        f"{invalid:,} invalid return quantities",
    )

    # --------------------------------------------------------
    # Refund amount
    # --------------------------------------------------------

    invalid = (
        returns["refund_amount"] < 0
    ).sum()

    all_passed &= check(
        invalid == 0,
        "Refund amounts >= 0",
        f"{invalid:,} negative refund amounts",
    )

    return all_passed


# ============================================================
# ORDER DATE VALIDATION
# ============================================================

def validate_order_dates():
    print("\n" + "=" * 60)
    print("6. ORDER DATE VALIDATION")
    print("=" * 60)

    orders = load_csv(
        "orders.csv"
    )

    orders["order_date"] = pd.to_datetime(
        orders["order_date"]
    )

    orders["delivery_date"] = pd.to_datetime(
        orders["delivery_date"],
        errors="coerce"
    )

    all_passed = True

    # --------------------------------------------------------
    # Dataset date range
    # --------------------------------------------------------

    invalid = (
        (orders["order_date"] < "2024-01-01")
        | (orders["order_date"] > "2026-08-31")
    ).sum()

    all_passed &= check(
        invalid == 0,
        "Order dates within dataset period",
        f"{invalid:,} invalid order dates",
    )

    # --------------------------------------------------------
    # Delivery date
    # --------------------------------------------------------

    completed = (
        orders["order_status"] == "Completed"
    )

    invalid = (
        completed
        & (
            orders["delivery_date"].isna()
            | (
                orders["delivery_date"]
                < orders["order_date"]
            )
        )
    ).sum()

    all_passed &= check(
        invalid == 0,
        "Completed orders have valid delivery dates",
        f"{invalid:,} invalid delivery dates",
    )

    return all_passed


# ============================================================
# INVENTORY VALIDATION
# ============================================================

def validate_inventory():
    print("\n" + "=" * 60)
    print("7. INVENTORY VALIDATION")
    print("=" * 60)

    inventory_file = (
        DATA_DIR
        / "inventory_snapshots.csv"
    )

    all_passed = True

    negative_count = 0
    equation_failures = 0
    invalid_flags = 0

    for chunk in pd.read_csv(
        inventory_file,
        chunksize=500_000,
    ):

        # ----------------------------------------------------
        # No negative stock
        # ----------------------------------------------------

        negative_count += (
            (
                chunk[
                    [
                        "opening_stock",
                        "units_received",
                        "units_sold",
                        "units_returned",
                        "closing_stock",
                        "reorder_level",
                    ]
                ]
                < 0
            )
            .any(axis=1)
            .sum()
        )

        # ----------------------------------------------------
        # Inventory equation
        # ----------------------------------------------------

        expected_closing = (
            chunk["opening_stock"]
            + chunk["units_received"]
            - chunk["units_sold"]
            + chunk["units_returned"]
        )

        equation_failures += (
            chunk["closing_stock"]
            != expected_closing
        ).sum()

        # ----------------------------------------------------
        # Stockout flag
        # ----------------------------------------------------

        invalid_flags += (
            ~chunk["stockout_flag"].isin(
                [0, 1]
            )
        ).sum()

    all_passed &= check(
        negative_count == 0,
        "No negative inventory values",
        f"{negative_count:,} negative inventory rows",
    )

    all_passed &= check(
        equation_failures == 0,
        "Inventory equation reconciles",
        f"{equation_failures:,} equation failures",
    )

    all_passed &= check(
        invalid_flags == 0,
        "Stockout flags are 0/1",
        f"{invalid_flags:,} invalid stockout flags",
    )

    return all_passed


# ============================================================
# FINAL VALIDATION
# ============================================================

def main():

    print("=" * 60)
    print("AGENTIC BI ANALYST - DATA QUALITY VALIDATION")
    print("=" * 60)

    results = []

    results.append(
        validate_row_counts()
    )

    results.append(
        validate_primary_keys()
    )

    results.append(
        validate_foreign_keys()
    )

    results.append(
        validate_order_items()
    )

    results.append(
        validate_returns()
    )

    results.append(
        validate_order_dates()
    )

    results.append(
        validate_inventory()
    )

    print("\n" + "=" * 60)
    print("FINAL RESULT")
    print("=" * 60)

    if all(results):
        print(
            "\n[SUCCESS] All validation checks passed."
        )
    else:
        print(
            "\n[WARNING] Some validation checks failed."
        )


if __name__ == "__main__":
    main()