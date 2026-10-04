#!/usr/bin/env python3
"""Validate the Chat 04 semantic catalog and bind qualified references to 01_init.sql."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SEM = ROOT / "semantic_layer"
DEFAULT_SCHEMA = ROOT.parent.parent.parent / "01_init.sql"

REQUIRED_FILES = [
    "metrics.yml", "dimensions.yml", "business_rules.yml", "joins.yml",
    "date_logic.yml", "synonyms.yml", "catalog.yml",
]
REQUIRED_METRIC_FIELDS = [
    "name", "definition", "formula", "source_tables", "primary_grain",
    "required_joins", "allowed_dimensions", "authoritative_date_field",
    "filters", "aggregation", "null_handling", "double_counting_risk",
    "unit", "synonyms",
]
VALID_AGGREGATIONS = {"SUM", "COUNT_DISTINCT", "RATIO_OF_AGGREGATES", "RATIO_OF_COUNTS"}


def metric_blocks(text: str):
    matches = list(re.finditer(r"^  ([a-z0-9_]+):\s*$", text, re.M))
    return [
        (m.group(1), text[m.start():(matches[i + 1].start() if i + 1 < len(matches) else len(text))])
        for i, m in enumerate(matches)
    ]


def parse_schema(sql: str):
    tables = {}
    for table_match in re.finditer(r"CREATE TABLE IF NOT EXISTS\s+([a-zA-Z_][\w]*)\s*\((.*?)\) ENGINE=InnoDB;", sql, re.S):
        table = table_match.group(1)
        body = table_match.group(2)
        cols = set()
        for line in body.splitlines():
            line = line.strip()
            m = re.match(r"(`?[a-zA-Z_][\w]*`?)\s+[A-Z]", line)
            if m:
                cols.add(m.group(1).strip('`'))
        tables[table] = cols
    return tables


def qualified_refs(text: str):
    return set(re.findall(r"\b([a-zA-Z_][\w]*)\.([a-zA-Z_][\w]*)\b", text))


def main():
    errors = []
    notes = []
    for name in REQUIRED_FILES:
        if not (SEM / name).exists():
            errors.append(f"missing file: {SEM / name}")

    metrics_path = SEM / "metrics.yml"
    metrics_text = metrics_path.read_text(encoding="utf-8") if metrics_path.exists() else ""
    blocks = metric_blocks(metrics_text)
    names = [name for name, _ in blocks]

    if len(names) != len(set(names)):
        errors.append("metric names are not unique")
    for name, block in blocks:
        for field in REQUIRED_METRIC_FIELDS:
            if re.search(rf"(?m)^    {re.escape(field)}:", block) is None:
                errors.append(f"{name}: missing required field '{field}'")
        agg = re.search(r"(?m)^    aggregation:\s*([A-Z_]+)", block)
        if agg and agg.group(1) not in VALID_AGGREGATIONS:
            errors.append(f"{name}: invalid aggregation '{agg.group(1)}'")

    for token in [
        "quantity * order_items.unit_price",
        "gross_revenue * order_items.discount_percent",
        "net_revenue",
        "quantity * order_items.unit_cost",
        "closing_stock",
    ]:
        if token not in metrics_text:
            errors.append(f"frozen semantic token missing: {token}")

    schema_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SCHEMA
    if not schema_path.exists():
        errors.append(f"schema file not found: {schema_path}")
    else:
        schema_tables = parse_schema(schema_path.read_text(encoding="utf-8"))
        expected_tables = {"calendar", "stores", "products", "customers", "orders", "order_items", "payments", "returns", "marketing_spend", "inventory_snapshots"}
        missing_tables = expected_tables - set(schema_tables)
        if missing_tables:
            errors.append(f"schema missing expected tables: {sorted(missing_tables)}")

        # Validate every qualified table.column reference appearing in metrics.
        for metric_name, block in blocks:
            for table, column in qualified_refs(block):
                if table not in schema_tables:
                    errors.append(f"{metric_name}: unknown table reference '{table}'")
                elif column not in schema_tables[table]:
                    errors.append(f"{metric_name}: unknown column reference '{table}.{column}'")

        # Validate qualified join/date references in the supporting semantic files.
        for semantic_file in ["joins.yml", "date_logic.yml"]:
            text = (SEM / semantic_file).read_text(encoding="utf-8")
            for table, column in qualified_refs(text):
                if table not in schema_tables:
                    errors.append(f"{semantic_file}: unknown table reference '{table}'")
                elif column not in schema_tables[table]:
                    errors.append(f"{semantic_file}: unknown column reference '{table}.{column}'")

        notes.append(f"schema binding checked against {schema_path.name}: {len(schema_tables)} tables")

    if errors:
        print("SEMANTIC VALIDATION: FAIL")
        for error in errors:
            print(f"[FAIL] {error}")
        return 1

    print("SEMANTIC VALIDATION: PASS")
    print(f"[PASS] files: {len(REQUIRED_FILES)}")
    print(f"[PASS] metrics: {len(blocks)}")
    print("[PASS] required metric fields")
    print("[PASS] aggregation methods")
    print("[PASS] frozen financial/inventory semantic references")
    print("[PASS] MySQL schema-column binding")
    for note in notes:
        print(f"[INFO] {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
