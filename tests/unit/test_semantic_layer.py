from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SEM = ROOT / "semantic_layer"

def test_required_files_exist():
    required = [
        "metrics.yml", "dimensions.yml", "business_rules.yml",
        "joins.yml", "date_logic.yml", "synonyms.yml", "catalog.yml"
    ]
    assert all((SEM / name).exists() for name in required)

def test_metric_names_unique_and_required_fields_present():
    text = (SEM / "metrics.yml").read_text(encoding="utf-8")
    matches = list(re.finditer(r"^  ([a-z0-9_]+):\s*$", text, re.M))
    names = [m.group(1) for m in matches]
    assert len(names) == len(set(names))
    required = [
        "name", "definition", "formula", "source_tables",
        "primary_grain", "allowed_dimensions", "authoritative_date_field",
        "filters", "aggregation", "null_handling",
        "double_counting_risk", "unit", "synonyms"
    ]
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[match.start():end]
        for field in required:
            assert re.search(rf"(?m)^    {field}:", block), (names[i], field)

def test_unsafe_fact_join_rule_present():
    text = (SEM / "joins.yml").read_text(encoding="utf-8")
    assert "orders JOIN order_items JOIN payments" in text
    assert "orders JOIN order_items JOIN returns" in text
    assert "pre-aggregation" in text

def test_date_semantics_present():
    text = (SEM / "date_logic.yml").read_text(encoding="utf-8")
    for field in [
        "orders.order_date", "payments.payment_date",
        "returns.return_date", "marketing_spend.date",
        "inventory_snapshots.snapshot_date", "customers.signup_date"
    ]:
        assert field in text
