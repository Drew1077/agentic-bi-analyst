"""
SQL Tool Layer for the Agentic BI Analyst project.

This module provides controlled, read-only SQL access to the
MySQL database for future analytical agents.
"""

import time
from pathlib import Path
import os

import mysql.connector
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

load_dotenv(PROJECT_ROOT / ".env")

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "database": os.getenv("MYSQL_DATABASE", "agentic_bi"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
}


# SQL statements that can modify or destroy database objects/data.
DESTRUCTIVE_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "REPLACE",
}

MAX_RESULT_ROWS = 10_000

FACT_ISOLATION_PATTERNS = [
    (
        {"order_items", "payments"},
        "Unsafe fact combination: order_items and payments must not be joined at raw grain. Aggregate payments independently before combining with order-item sales.",
    ),
    (
        {"orders", "order_items", "payments"},
        "Unsafe fact combination: orders, order_items, and payments must not be joined at raw grain. Aggregate independent facts before combining them.",
    ),
    (
        {"orders", "order_items", "returns"},
        "Unsafe fact combination: orders, order_items, and returns must not be joined at raw grain. Aggregate returns before combining them with sales.",
    ),
    (
        {"order_items", "inventory_snapshots"},
        "Unsafe fact combination: order_items and inventory_snapshots must not be joined at raw row grain.",
    ),
    (
        {"payments", "returns", "order_items"},
        "Unsafe fact combination: raw payments, returns, and order_items must not be combined in one query without independent pre-aggregation.",
    ),
]


@dataclass
class ValidationResult:
    """Result of SQL validation."""

    valid: bool
    normalized_sql: str | None = None
    errors: list[str] | None = None
    warnings: list[str] | None = None


@dataclass
class SQLResult:
    """Structured result returned after SQL execution."""

    success: bool
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    error: str | None = None
    execution_time_ms: float | None = None


@dataclass
class SchemaInfo:
    """Database schema information."""

    tables: dict[str, dict[str, Any]]
    relationships: list[dict[str, Any]]

def _detect_fact_isolation_issues(sql: str) -> list[str]:
    """
    Detect combinations of independent fact tables that can cause
    row multiplication when joined at raw grain.

    Rules are derived from semantic_layer/joins.yml.
    """
    normalized_sql = sql.lower()

    referenced_tables = {
        table
        for table in {
            "orders",
            "order_items",
            "payments",
            "returns",
            "inventory_snapshots",
        }
        if table in normalized_sql
    }

    errors = []

    for required_tables, message in FACT_ISOLATION_PATTERNS:
        if required_tables.issubset(referenced_tables):
            errors.append(message)

    return errors

def validate_sql(sql: str) -> ValidationResult:
    """
    Validate a SQL query before execution.

    The SQL tool is read-only. Only SELECT-based analytical
    statements are permitted.
    """

    errors: list[str] = []
    warnings: list[str] = []

    # ---------------------------------------------------------
    # Basic input validation
    # ---------------------------------------------------------

    if not isinstance(sql, str):
        return ValidationResult(
            valid=False,
            errors=["SQL query must be a string."],
            warnings=[],
        )

    sql_for_analysis = sql.strip()

    normalized_sql = sql.strip()

    if not normalized_sql:
        return ValidationResult(
            valid=False,
            normalized_sql="",
            errors=["SQL query cannot be empty."],
            warnings=[],
        )

    # ---------------------------------------------------------
    # Multi-statement protection
    # ---------------------------------------------------------

    # A semicolon is allowed only as the final SQL terminator.
    sql_without_final_semicolon = normalized_sql.rstrip(";").strip()

    if ";" in sql_without_final_semicolon:
        errors.append(
            "Multiple SQL statements are not allowed."
        )

    # ---------------------------------------------------------
    # Read-only statement check
    # ---------------------------------------------------------

    # Remove SQL comments before safety analysis.
    # MySQL supports both line comments and block comments.

    lines = []

    for line in sql_for_analysis.splitlines():
        stripped_line = line.strip()

        if "--" in stripped_line:
            stripped_line = stripped_line.split("--", 1)[0].rstrip()

        if stripped_line:
            lines.append(stripped_line)

    sql_for_analysis = " ".join(lines).strip()

    # Remove block comments.
    while "/*" in sql_for_analysis and "*/" in sql_for_analysis:
        start = sql_for_analysis.find("/*")
        end = sql_for_analysis.find("*/", start + 2)

        if end == -1:
            errors.append("Unterminated SQL block comment.")
            break

        sql_for_analysis = (
            sql_for_analysis[:start]
            + " "
            + sql_for_analysis[end + 2:]
        )

    sql_for_analysis = sql_for_analysis.strip()

    if not sql_for_analysis:
        errors.append("SQL query contains no executable statement.")
    else:
        first_token = sql_for_analysis.split(None, 1)[0].upper()

        # SELECT is the primary analytical statement.
        # WITH is allowed because analytical queries may use CTEs.
        if first_token not in {"SELECT", "WITH"}:
            errors.append(
                "Only SELECT or WITH ... SELECT queries are allowed."
            )


    # ---------------------------------------------------------
    # Fact-isolation protection
    # ---------------------------------------------------------

    fact_isolation_errors = _detect_fact_isolation_issues(
        sql_for_analysis
    )

    errors.extend(fact_isolation_errors)

    # ---------------------------------------------------------
    # Destructive keyword protection
    # ---------------------------------------------------------

    tokens = {
        token.upper()
        for token in sql_for_analysis.replace("(", " ")
        .replace(")", " ")
        .replace(",", " ")
        .split()
    }

    destructive_found = sorted(
        DESTRUCTIVE_KEYWORDS.intersection(tokens)
    )

    if destructive_found:
        errors.append(
            "Destructive SQL operation(s) are not allowed: "
            + ", ".join(destructive_found)
            + "."
        )

    # ---------------------------------------------------------
    # Result
    # ---------------------------------------------------------

    return ValidationResult(
        valid=not errors,
        normalized_sql=normalized_sql,
        errors=errors,
        warnings=warnings,
    )


def _get_connection():
    """Create a MySQL connection using the project's existing DB configuration."""
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as exc:
        raise RuntimeError(f"MySQL connection failed: {exc}") from exc


def execute_sql(
    sql: str,
    params: tuple | dict | None = None,
) -> SQLResult:
    """
    Execute a validated read-only SQL query.
    """
    validation = validate_sql(sql)

    if not validation.valid:
        return SQLResult(
            success=False,
            columns=[],
            rows=[],
            row_count=0,
            error="SQL validation failed: " + "; ".join(validation.errors),
        )
    start_time = time.perf_counter()

    connection = None
    cursor = None

    try:
        connection = _get_connection()
        cursor = connection.cursor()

        cursor.execute(sql, params)

        columns = (
            [description[0] for description in cursor.description]
            if cursor.description
            else []
        )

        raw_rows = (
            cursor.fetchmany(MAX_RESULT_ROWS + 1)
            if cursor.description
            else []
        )

        if len(raw_rows) > MAX_RESULT_ROWS:
            cursor.fetchall()
            return SQLResult(
                success=False,
                columns=columns,
                rows=[],
                row_count=0,
                error=(
                    f"Query returned more than {MAX_RESULT_ROWS:,} rows, "
                    f"which exceeds the maximum allowed result size "
                    f"of {MAX_RESULT_ROWS:,} rows."
                ),
                execution_time_ms=(
                    time.perf_counter() - start_time
                ) * 1000,
            )

        rows = [
            dict(zip(columns, row))
            for row in raw_rows
        ]
        

        return SQLResult(
            success=True,
            columns=columns,
            rows=rows,
            row_count=len(rows),
            error=None,
            execution_time_ms=(time.perf_counter() - start_time) * 1000,
        )

    except (mysql.connector.Error, RuntimeError) as exc:
        return SQLResult(
            success=False,
            columns=[],
            rows=[],
            row_count=0,
            error=f"MySQL execution failed: {exc}",
            execution_time_ms=(time.perf_counter() - start_time) * 1000,
        )

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()


def inspect_schema() -> SchemaInfo:
    """
    Inspect the current MySQL database schema.

    Returns tables, columns, primary keys, and foreign-key
    relationships from MySQL INFORMATION_SCHEMA.
    """
    connection = None
    cursor = None

    try:
        connection = _get_connection()
        cursor = connection.cursor(dictionary=True)

        # Get tables and columns
        cursor.execute(
            """
            SELECT
                TABLE_NAME,
                COLUMN_NAME,
                DATA_TYPE,
                IS_NULLABLE,
                COLUMN_KEY,
                ORDINAL_POSITION
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
            ORDER BY TABLE_NAME, ORDINAL_POSITION
            """,
            (DB_CONFIG["database"],),
        )

        column_rows = cursor.fetchall()

        tables: dict[str, dict[str, Any]] = {}

        for row in column_rows:
            table_name = row["TABLE_NAME"]

            if table_name not in tables:
                tables[table_name] = {
                    "columns": [],
                    "primary_key": [],
                }

            tables[table_name]["columns"].append(
                {
                    "name": row["COLUMN_NAME"],
                    "data_type": row["DATA_TYPE"],
                    "nullable": row["IS_NULLABLE"] == "YES",
                    "column_key": row["COLUMN_KEY"],
                    "ordinal_position": row["ORDINAL_POSITION"],
                }
            )

            if row["COLUMN_KEY"] == "PRI":
                tables[table_name]["primary_key"].append(
                    row["COLUMN_NAME"]
                )

        # Get foreign-key relationships
        cursor.execute(
            """
            SELECT
                TABLE_NAME,
                COLUMN_NAME,
                REFERENCED_TABLE_NAME,
                REFERENCED_COLUMN_NAME,
                CONSTRAINT_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s
              AND REFERENCED_TABLE_NAME IS NOT NULL
            ORDER BY TABLE_NAME, COLUMN_NAME
            """,
            (DB_CONFIG["database"],),
        )

        relationship_rows = cursor.fetchall()

        relationships = [
            {
                "constraint_name": row["CONSTRAINT_NAME"],
                "table": row["TABLE_NAME"],
                "column": row["COLUMN_NAME"],
                "referenced_table": row["REFERENCED_TABLE_NAME"],
                "referenced_column": row["REFERENCED_COLUMN_NAME"],
            }
            for row in relationship_rows
        ]

        return SchemaInfo(
            tables=tables,
            relationships=relationships,
        )

    except mysql.connector.Error as exc:
        raise RuntimeError(
            f"MySQL schema inspection failed: {exc}"
        ) from exc

    finally:
        if cursor is not None:
            cursor.close()

        if connection is not None:
            connection.close()