"""Guarded Docker database initialization for the Agentic BI Analyst.

This wrapper preserves scripts/load_data.py as the single CSV -> MySQL loader.
It prevents the non-idempotent loader from being invoked against a partially
or fully populated database.
"""

from __future__ import annotations

import os
import time

import mysql.connector

from load_data import EXPECTED_COUNTS, LOAD_ORDER, get_connection, main as load_main


def wait_for_database(retries: int = 30, delay_seconds: int = 2) -> None:
    """Wait until MySQL accepts a connection."""
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            connection = get_connection()
            connection.close()
            print(f"[OK] MySQL is reachable (attempt {attempt}/{retries}).")
            return
        except Exception as exc:
            last_error = exc
            print(f"[WAIT] MySQL not ready (attempt {attempt}/{retries}): {exc}")
            time.sleep(delay_seconds)

    raise RuntimeError("MySQL did not become available in time.") from last_error


def get_table_counts(connection: mysql.connector.MySQLConnection) -> dict[str, int]:
    """Return row counts for all governed dataset tables."""
    cursor = connection.cursor()
    try:
        counts: dict[str, int] = {}
        for table_name in LOAD_ORDER:
            cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
            counts[table_name] = int(cursor.fetchone()[0])
        return counts
    finally:
        cursor.close()


def main() -> None:
    print("=" * 70)
    print("AGENTIC BI ANALYST - DOCKER DATABASE INITIALIZATION")
    print("=" * 70)

    # Keep the environment contract explicit for Docker.
    os.environ.setdefault("MYSQL_HOST", "mysql")
    os.environ.setdefault("MYSQL_PORT", "3306")

    wait_for_database()

    connection = get_connection()
    try:
        counts = get_table_counts(connection)

        populated = {
            table: count for table, count in counts.items() if count > 0
        }

        if not populated:
            print("[OK] Database tables are empty.")
            print("[INFO] Running the existing scripts/load_data.py loader...")
            load_main()
            print("[SUCCESS] Docker database initialization completed.")
            return

        complete = all(
            counts[table] == EXPECTED_COUNTS[table]
            for table in LOAD_ORDER
        )

        if complete:
            print("[OK] Dataset is already fully loaded.")
            for table in LOAD_ORDER:
                print(
                    f"  {table}: {counts[table]:,}/"
                    f"{EXPECTED_COUNTS[table]:,}"
                )
            print("[SUCCESS] Nothing to load.")
            return

        print("[ERROR] Existing data detected, but the dataset is incomplete.")
        for table in LOAD_ORDER:
            print(
                f"  {table}: {counts[table]:,}/"
                f"{EXPECTED_COUNTS[table]:,}"
            )

        raise RuntimeError(
            "Refusing to run the non-idempotent loader against a partially "
            "populated database. Reset the Docker MySQL volume and retry."
        )
    finally:
        connection.close()


if __name__ == "__main__":
    main()
