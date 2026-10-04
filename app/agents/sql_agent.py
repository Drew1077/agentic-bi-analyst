import re
from dataclasses import dataclass
from typing import Any

from app.tools.analytics import load_semantic_catalog
from app.tools.sql import execute_sql, inspect_schema, validate_sql

@dataclass
class SQLAgentRequest:
    """Input contract for the SQL Analyst Agent."""

    question: str


@dataclass
class AnalysisSpec:
    """Structured representation of the analytical request."""

    metric: str | None = None
    dimensions: list[str] | None = None
    time_grain: str | None = None
    date_start: str | None = None
    date_end: str | None = None
    filters: dict[str, Any] | None = None

@dataclass
class SQLAgentResponse:
    """Output contract for the SQL Analyst Agent."""

    success: bool
    answer: str | None
    sql: str | None
    columns: list[str]
    rows: list[dict[str, Any]]
    evidence: dict[str, Any]
    provenance: dict[str, Any]
    errors: list[str]

class SQLAnalystAgent:
    """Semantic-aware SQL Analyst Agent."""

    MAX_SQL_REVISIONS = 1

    def __init__(self):
        self.semantic_catalog = load_semantic_catalog()
        self.schema_info = inspect_schema()

    def resolve_metric(self, metric_text: str):
        """Resolve a user-facing metric name through the semantic layer."""
        return self.semantic_catalog.resolve_metric(metric_text)

    def resolve_time_grain(self, question: str) -> str | None:
        """Resolve a supported temporal grouping from the user question."""

        normalized = question.lower()

        grain_aliases = {
            "day": ("day", "daily"),
            "week": ("week", "weekly"),
            "month": ("month", "monthly"),
            "quarter": ("quarter", "quarterly"),
            "year": ("year", "yearly", "annually"),
        }

        for grain, aliases in grain_aliases.items():
            if any(
                re.search(
                    rf"\b{re.escape(alias)}\b",
                    normalized,
                )
                for alias in aliases
            ):
                return grain

        return None

    def validate_query(self, sql: str):
        """Validate SQL through the existing SQL Tool Layer."""
        return validate_sql(sql)

    def schema_has_column(self, table: str, column: str) -> bool:
        """Check whether a table and column exist in the inspected schema."""

        table_info = self.schema_info.tables.get(table)

        if table_info is None:
            return False

        return any(
            column_info.get("name") == column
            for column_info in table_info.get("columns", [])
        )

    def validate_required_schema(
        self,
        required_schema: dict[str, list[str]],
    ) -> list[str]:
        """Validate that required tables and columns exist in the inspected schema."""

        errors = []

        for table, columns in required_schema.items():
            if table not in self.schema_info.tables:
                errors.append(
                    f"Required table does not exist: {table}"
                )
                continue

            for column in columns:
                if not self.schema_has_column(table, column):
                    errors.append(
                        f"Required column does not exist: "
                        f"{table}.{column}"
                    )

        return errors

    def required_schema_for_spec(
        self,
        spec: AnalysisSpec,
    ) -> dict[str, list[str]]:
        """Return the physical schema required by a supported analysis."""

        if spec.metric not in {"net_revenue", "gross_revenue"}:
            raise ValueError(
                f"Unsupported metric for schema resolution: {spec.metric}"
            )

        required_schema = {
            "orders": [
                "order_id",
                "order_date",
            ],
            "order_items": [
                "order_id",
                "product_id",
            ],
        }

        if spec.metric == "net_revenue":
            required_schema["order_items"].append("net_revenue")

        elif spec.metric == "gross_revenue":
            required_schema["order_items"].extend(
                [
                    "quantity",
                    "unit_price",
                ]
            )

        dimension_columns = {
            "category": ("products", "category"),
            "subcategory": ("products", "subcategory"),
            "brand": ("products", "brand"),
            "product": ("products", "product_name"),
            "customer.city": ("customers", "city"),
            "customer.state": ("customers", "state"),
            "customer.region": ("customers", "region"),
            "customer.customer_segment": ("customers", "customer_segment"),
            "customer.gender": ("customers", "gender"),
            "customer.acquisition_channel": (
                "customers",
                "acquisition_channel",
            ),
            "customer.preferred_device": (
                "customers",
                "preferred_device",
            ),
            "customer.customer_status": (
                "customers",
                "customer_status",
            ),
        }

        if spec.dimensions is None:
            raise ValueError(
                "Dimensions must be provided as a list."
            )

        if len(spec.dimensions) > 1:
            raise ValueError(
                "This schema resolver currently supports at most one dimension."
            )

        if not spec.dimensions:
            return required_schema

        dimension = spec.dimensions[0]

        if dimension not in dimension_columns:
            raise ValueError(
                f"Unsupported dimension for schema resolution: {dimension}"
            )

        table, column = dimension_columns[dimension]

        if table == "customers":
            required_schema.setdefault(table, []).extend(
                [
                    "customer_id",
                    column,
                ]
            )
        else:
            required_schema.setdefault(table, []).extend(
                [
                    "product_id",
                    column,
                ]
            )

        return required_schema

    def validate_request(self, request: SQLAgentRequest) -> list[str]:
        """Validate the SQL Analyst Agent request."""

        errors = []

        if not isinstance(request, SQLAgentRequest):
            errors.append("Request must be an SQLAgentRequest.")
            return errors

        if not isinstance(request.question, str):
            errors.append("Question must be a string.")
            return errors

        if not request.question.strip():
            errors.append("Question must not be empty.")

        return errors

    def extract_metric_text(self, question: str) -> str:
        """Extract the metric portion from a simple analytical question."""

        metric_text = re.sub(r"\b(20\d{2})\b", "", question)

        metric_text = re.sub(
            r"\b(in|for|during|of|year|month|quarter|week|day|by|what|was|were|is|are|the|show|give|tell|me|please|how|much|why|did|change|changed|increase|increased|decrease|decreased)\b",
            "",
            metric_text,
            flags=re.IGNORECASE,
        )

        dimensions = [
            "category",
            "subcategory",
            "brand",
            "product",
            "store",
            "customer",
            "city",
            "state",
            "region",
            "segment",
            "customer_segment",
            "gender",
            "acquisition_channel",
            "preferred_device",
            "customer_status",
            "store_type",
            "store_status",
            "campaign",
            "channel",
            "condition",
            "return_reason",
            "return_status",
            "stockout_flag",
        ]

        for dimension in dimensions:
            metric_text = re.sub(
                rf"\b{re.escape(dimension)}\b",
                "",
                metric_text,
                flags=re.IGNORECASE,
            )

        metric_text = re.sub(r"[^\w\s.-]", " ", metric_text)
        metric_text = re.sub(r"\s+", " ", metric_text).strip()

        return metric_text

    def build_analysis_spec(self, request: SQLAgentRequest) -> AnalysisSpec:
        """Build and validate an analytical specification from the user request."""

        metric_text = self.extract_metric_text(request.question)
        metric = self.resolve_metric(metric_text)

        date_start, date_end = self.resolve_year(request.question)
        dimension = self.resolve_dimension(request.question)
        time_grain = self.resolve_time_grain(request.question)

        if metric is None:
            raise ValueError(
                f"Could not resolve a supported metric from the question: "
                f"{request.question}"
            )

        if date_start is None or date_end is None:
            raise ValueError(
                "An explicit four-digit year is required for this analysis."
            )

        return AnalysisSpec(
            metric=metric,
            dimensions=[dimension] if dimension is not None else [],
            time_grain=time_grain,
            date_start=date_start,
            date_end=date_end,
            filters={},
        )

    def generate_sql(self, spec: AnalysisSpec) -> str:
        """Generate governed SQL for a supported analysis specification."""

        if spec.metric not in {"net_revenue", "gross_revenue"}:
            raise ValueError(
                f"Unsupported metric for SQL generation: {spec.metric}"
            )

        dimension_columns = {
            "category": "products.category",
            "subcategory": "products.subcategory",
            "brand": "products.brand",
            "product": "products.product_name",
            "customer.city": "customers.city",
            "customer.state": "customers.state",
            "customer.region": "customers.region",
            "customer.customer_segment": "customers.customer_segment",
            "customer.gender": "customers.gender",
            "customer.acquisition_channel": "customers.acquisition_channel",
            "customer.preferred_device": "customers.preferred_device",
            "customer.customer_status": "customers.customer_status",
        }

        time_grain_columns = {
            "day": "calendar.date",
            "week": "calendar.week",
            "month": "calendar.month",
            "quarter": "calendar.quarter",
            "year": "calendar.year",
        }

        if spec.dimensions is None:
            raise ValueError(
                "Dimensions must be provided as a list."
            )

        if len(spec.dimensions) > 1:
            raise ValueError(
                "This SQL generator currently supports at most one dimension."
            )

        if spec.time_grain is not None and spec.time_grain not in time_grain_columns:
            raise ValueError(
                f"Unsupported time grain for SQL generation: {spec.time_grain}"
            )

        if spec.time_grain is not None and spec.dimensions:
            raise ValueError(
                "This SQL generator currently supports either one time grain "
                "or one categorical dimension, not both."
            )

        metric_expressions = {
            "net_revenue": "SUM(order_items.net_revenue)",
            "gross_revenue": (
                "SUM(order_items.quantity * order_items.unit_price)"
            ),
        }

        metric_expression = metric_expressions[spec.metric]

        if not spec.date_start or not spec.date_end:
            raise ValueError(
                "Date range is required for this SQL generation path."
            )
        from_clause = """
        FROM orders
        JOIN order_items
            ON orders.order_id = order_items.order_id
        """.strip()

        if spec.time_grain is not None:
            time_column = time_grain_columns[spec.time_grain]

            from_clause += """
        JOIN calendar
            ON calendar.date = orders.order_date
        """.rstrip()

            return f"""
SELECT
     {time_column} AS {spec.time_grain},
     {metric_expression} AS {spec.metric}
{from_clause}
WHERE orders.order_date >= '{spec.date_start}'
  AND orders.order_date <= '{spec.date_end}'
GROUP BY {time_column}
ORDER BY {time_column}
""".strip()

        if not spec.dimensions:
            return f"""
SELECT
     {metric_expression} AS {spec.metric}
{from_clause}
WHERE orders.order_date >= '{spec.date_start}'
  AND orders.order_date <= '{spec.date_end}'
""".strip()

        dimension = spec.dimensions[0]

        if dimension not in dimension_columns:
            raise ValueError(
                f"Unsupported dimension for SQL generation: {dimension}"
            )

        dimension_column = dimension_columns[dimension]
        dimension_alias = dimension.split(".")[-1]

        if dimension.startswith("customer."):
            from_clause += """
        JOIN customers
            ON customers.customer_id = orders.customer_id
        """.rstrip()
        else:
            from_clause += """
        JOIN products
            ON products.product_id = order_items.product_id
        """.rstrip()

        return f"""
SELECT
     {dimension_column} AS {dimension_alias},
     {metric_expression} AS {spec.metric}
{from_clause}
WHERE orders.order_date >= '{spec.date_start}'
  AND orders.order_date <= '{spec.date_end}'
GROUP BY {dimension_column}
ORDER BY {dimension_column}
""".strip()

    def verify_result(self, result) -> list[str]:
        """Verify that an executed SQL result is usable."""

        errors = []

        if not result.success:
            errors.append(
                result.error or "SQL execution failed."
            )
            return errors

        if not result.columns:
            errors.append(
                "SQL execution succeeded but returned no columns."
            )

        if result.row_count != len(result.rows):
            errors.append(
                "Reported row count does not match returned rows."
            )

        return errors

    def build_evidence(
        self,
        request: SQLAgentRequest,
        spec: AnalysisSpec,
        result,
    ) -> dict[str, Any]:
        """Build structured evidence for the executed analysis."""

        return {
            "question": request.question,
            "metric": spec.metric,
            "dimensions": spec.dimensions or [],
            "time_grain": spec.time_grain,
            "date_start": spec.date_start,
            "date_end": spec.date_end,
            "columns": result.columns,
            "row_count": result.row_count,
            "rows": result.rows,
        }

    def build_provenance(
        self,
        spec: AnalysisSpec,
        sql: str,
        result,
    ) -> dict[str, Any]:
        """Build audit information about how the result was produced."""

        validation = self.validate_query(sql)

        return {
            "metric": spec.metric,
            "dimensions": spec.dimensions or [],
            "time_grain": spec.time_grain,
            "date_start": spec.date_start,
            "date_end": spec.date_end,
            "sql": sql,
            "sql_valid": validation.valid,
            "execution_success": result.success,
            "execution_time_ms": result.execution_time_ms,
        }

    def revise_sql(
        self,
        sql: str,
        validation_errors: list[str],
    ) -> str | None:
        """Apply a bounded deterministic revision to invalid SQL."""

        revised_sql = sql.strip()

        if not validation_errors:
            return revised_sql

        # Remove non-final semicolons if a candidate contains
        # an accidental statement terminator.
        revised_sql = re.sub(
            r";\s*(?=\S)",
            " ",
            revised_sql,
        )

        # Remove a trailing semicolon because the SQL tool
        # accepts it but does not require it.
        revised_sql = revised_sql.rstrip(";").strip()

        if not revised_sql:
            return None

        return revised_sql

    def run(self, request: SQLAgentRequest) -> SQLAgentResponse:
        """Run the complete SQL Analyst Agent workflow."""

        errors = []

        request_errors = self.validate_request(request)

        if request_errors:
            return SQLAgentResponse(
                success=False,
                answer=None,
                sql=None,
                columns=[],
                rows=[],
                evidence={},
                provenance={},
                errors=request_errors,
            )

        try:
            spec = self.build_analysis_spec(request)
        except Exception as exc:
            return SQLAgentResponse(
                success=False,
                answer=None,
                sql=None,
                columns=[],
                rows=[],
                evidence={},
                provenance={},
                errors=[str(exc)],
            )

        try:
            sql = self.generate_sql(spec)
        except Exception as exc:
            return SQLAgentResponse(
                success=False,
                answer=None,
                sql=None,
                columns=[],
                rows=[],
                evidence={},
                provenance={},
                errors=[str(exc)],
            )

        try:
            required_schema = self.required_schema_for_spec(spec)
            schema_errors = self.validate_required_schema(
                required_schema
            )
        except Exception as exc:
            return SQLAgentResponse(
                success=False,
                answer=None,
                sql=sql,
                columns=[],
                rows=[],
                evidence={},
                provenance={
                    "sql": sql,
                    "schema_valid": False,
                },
                errors=[str(exc)],
            )

        if schema_errors:
            return SQLAgentResponse(
                success=False,
                answer=None,
                sql=sql,
                columns=[],
                rows=[],
                evidence={},
                provenance={
                    "sql": sql,
                    "schema_valid": False,
                    "required_schema": required_schema,
                },
                errors=schema_errors,
            )

        validation = self.validate_query(sql)

        if not validation.valid:
            revised_sql = None

            for _ in range(self.MAX_SQL_REVISIONS):
                revised_sql = self.revise_sql(
                    sql,
                    validation.errors,
                )

                if revised_sql is None:
                    break

                revised_validation = self.validate_query(revised_sql)

                if revised_validation.valid:
                    sql = revised_sql
                    validation = revised_validation
                    break

                sql = revised_sql
                validation = revised_validation

            if not validation.valid:
                return SQLAgentResponse(
                    success=False,
                    answer=None,
                    sql=sql,
                    columns=[],
                    rows=[],
                    evidence={},
                    provenance={
                        "sql": sql,
                        "sql_valid": False,
                        "revision_attempts": self.MAX_SQL_REVISIONS,
                    },
                    errors=validation.errors,
                )

        result = execute_sql(sql)

        verification_errors = self.verify_result(result)

        if verification_errors:
            return SQLAgentResponse(
                success=False,
                answer=None,
                sql=sql,
                columns=result.columns,
                rows=result.rows,
                evidence={},
                provenance={
                    "sql": sql,
                    "sql_valid": True,
                    "execution_success": result.success,
                },
                errors=verification_errors,
            )

        evidence = self.build_evidence(
            request,
            spec,
            result,
        )

        provenance = self.build_provenance(
            spec,
            sql,
            result,
        )

        answer = self.format_answer(spec, result)

        return SQLAgentResponse(
            success=True,
            answer=answer,
            sql=sql,
            columns=result.columns,
            rows=result.rows,
            evidence=evidence,
            provenance=provenance,
            errors=errors,
        )

    def format_answer(
        self,
        spec: AnalysisSpec,
        result,
    ) -> str:
        """Format SQL results into a deterministic natural-language answer."""

        if not result.rows:
            return "No matching data was found."

        if (
            spec.metric in {"net_revenue", "gross_revenue"}
            and spec.time_grain is not None
        ):
            metric_labels = {
                "net_revenue": "Net revenue",
                "gross_revenue": "Gross revenue",
            }

            grain_columns = {
                "day": "day",
                "week": "week",
                "month": "month",
                "quarter": "quarter",
                "year": "year",
            }

            grain_column = grain_columns[spec.time_grain]

            lines = [
                f"{row[grain_column]}: {row[spec.metric]}"
                for row in result.rows
            ]

            date_text = ""

            if spec.date_start and spec.date_end:
                date_text = (
                    f" from {spec.date_start} to {spec.date_end}"
                )

            return (
                f"{metric_labels[spec.metric]} by {spec.time_grain}"
                f"{date_text}:\n"
                + "\n".join(lines)
            )

        if spec.metric in {"net_revenue", "gross_revenue"} and not spec.dimensions:
            metric_labels = {
                "net_revenue": "Net revenue",
                "gross_revenue": "Gross revenue",
            }
            date_text = ""

            if spec.date_start and spec.date_end:
                date_text = f" from {spec.date_start} to {spec.date_end}"

            return (
                f"{metric_labels[spec.metric]}{date_text}: "
                f"{result.rows[0][spec.metric]}"
            )

        if (
            spec.metric in {"net_revenue", "gross_revenue"}
            and spec.dimensions
            and len(spec.dimensions) == 1
            and spec.dimensions[0] in {"category", "subcategory", "brand", "product"}
        ):
            dimension = spec.dimensions[0]

            lines = [
                f"{row[dimension]}: {row[spec.metric]}"
                for row in result.rows
            ]

            date_text = ""

            if spec.date_start and spec.date_end:
                date_text = (
                    f" from {spec.date_start} to {spec.date_end}"
                )
            metric_labels = {
                "net_revenue": "Net revenue",
                "gross_revenue": "Gross revenue",
            }
            return (
                f"{metric_labels[spec.metric]} by {dimension}{date_text}:\n"
                + "\n".join(lines)
            )

        return "\n".join(
            str(row)
            for row in result.rows
        )

    def resolve_year(self, question: str) -> tuple[str | None, str | None]:
        """Resolve an explicit four-digit calendar year within the dataset range."""

        matches = re.findall(r"\b(20\d{2})\b", question)

        if not matches:
            return None, None

        if len(set(matches)) > 1:
            raise ValueError(
                "Multiple years were found in the question. "
                "Please specify a single year."
            )

        year = int(matches[0])

        dataset_start = "2024-01-01"
        dataset_end = "2026-08-31"

        if year < 2024 or year > 2026:
            raise ValueError(
                f"Year {year} is outside the available dataset range "
                f"({dataset_start} to {dataset_end})."
            )

        date_start = f"{year}-01-01"
        date_end = f"{year}-12-31"

        if date_start < dataset_start:
            date_start = dataset_start

        if date_end > dataset_end:
            date_end = dataset_end

        return date_start, date_end

    def resolve_dimension(self, question: str) -> str | None:
        """Resolve a dimension using semantic domain context."""

        question_lower = question.lower()

        domain_specific_dimensions = {
            "customer": {
                "city": "customer.city",
                "state": "customer.state",
                "region": "customer.region",
                "segment": "customer.customer_segment",
                "customer_segment": "customer.customer_segment",
                "gender": "customer.gender",
                "acquisition_channel": "customer.acquisition_channel",
                "preferred_device": "customer.preferred_device",
                "customer_status": "customer.customer_status",
            },
            "store": {
                "city": "store.city",
                "state": "store.state",
                "region": "store.region",
                "type": "store.store_type",
                "store_type": "store.store_type",
                "status": "store.store_status",
                "store_status": "store.store_status",
            },
        }

        for domain, dimensions in domain_specific_dimensions.items():
            if re.search(
                rf"\b{re.escape(domain)}\b",
                question_lower,
            ):
                for dimension, canonical_name in dimensions.items():
                    if re.search(
                        rf"\b{re.escape(dimension)}\b",
                        question_lower,
                    ):
                        return canonical_name

        unambiguous_dimensions = {
            "category": "category",
            "subcategory": "subcategory",
            "brand": "brand",
            "product": "product",
            "campaign": "campaign",
            "channel": "channel",
            "condition": "condition",
            "return_reason": "return_reason",
            "return_status": "return_status",
            "stockout_flag": "stockout_flag",
        }

        for dimension, canonical_name in unambiguous_dimensions.items():
            if re.search(
                rf"\b{re.escape(dimension)}\b",
                question_lower,
            ):
                return canonical_name

        return None

