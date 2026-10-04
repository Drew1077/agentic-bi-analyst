# Visualization Agent Contract

## 1. Purpose

The Visualization Agent converts a successful, already-validated analytical result into a deterministic chart specification and, when meaningful, a rendered PNG chart.

It is a downstream presentation component. It does not query MySQL, execute SQL, redefine metrics, or create analytical evidence.

## 2. Input Contract

`VisualizationAgentRequest`

```python
@dataclass
class VisualizationAgentRequest:
    question: str
    result: Any
```

Requirements:

- `question` must be a non-empty string.
- `result` must not be `None`.
- `result.success` must be `True`.
- The result may expose tabular `columns`/`rows` or structured root-cause `evidence`.

## 3. Output Contract

`VisualizationAgentResponse`

```python
@dataclass
class VisualizationAgentResponse:
    success: bool
    chart_spec: dict[str, Any] | None
    rendered_chart: bytes | None
    chart_format: str | None
    validation: dict[str, Any]
    evidence: Any
    provenance: Any
    errors: list[str]
```

`rendered_chart` is PNG bytes when a chart is rendered. A valid result with no meaningful chart has `chart_spec["chart_type"] == "none"` and no rendered chart.

## 4. Supported Chart Types

The initial deterministic selector supports:

- `line` — date/time field plus numeric metric
- `bar` — one categorical dimension plus numeric metric
- `scatter` — at least two numeric fields
- `heatmap` — two categorical dimensions plus numeric metric
- `waterfall` — root-cause contribution evidence
- `none` — no meaningful chart can be derived

## 5. Selection Rules

Selection is deterministic and based only on the validated result structure.

Priority:

1. Root-cause contribution evidence with at least two contributions → `waterfall`
2. Date/time field + numeric field → `line`
3. Two categorical fields + numeric field → `heatmap`
4. One categorical field + numeric field → `bar`
5. Two numeric fields → `scatter`
6. Otherwise → `none`

The agent does not invent missing fields.

## 6. Chart Specification

A chart specification contains:

- chart type
- title
- x-axis field and label
- y-axis field and label
- series
- chart data
- source metadata

For heatmaps, the specification additionally identifies the numeric value field.

For waterfalls, source data comes from contribution evidence.

## 7. Validation

Before rendering, the agent validates:

- chart type is supported
- required axis fields exist
- chart data is present for rendered charts
- referenced fields exist in the analytical source
- chart data exactly matches source rows/evidence
- no fabricated analytical values are introduced

A failed validation prevents rendering.

## 8. Rendering

Rendering uses the project's available Matplotlib dependency with the non-interactive `Agg` backend.

Rendered charts are returned as PNG bytes. No database or external service is required.

## 9. Evidence and Provenance

The response preserves the analytical result's `evidence` and `provenance`.

Visualization does not replace, reinterpret, or regenerate those structures.

## 10. Scope Boundaries

The Visualization Agent does not:

- query MySQL
- execute SQL
- bypass the SQL Tool Layer
- redefine semantic metrics
- recalculate governed KPIs from raw tables
- invent missing values
- perform recommendations
- compose reports
- implement UI/API/deployment infrastructure
- implement RAG

## 11. Integration Boundary

Chat 11 provides the Visualization Agent as a downstream capability consuming validated analytical results.

The existing Chat 10 Orchestrator execution and Critic retry path remains unchanged unless a source-backed integration requirement is demonstrated by later workflow phases.

## 12. Verification

Chat 11 focused tests verify:

- request validation
- deterministic chart selection
- line/bar/scatter/heatmap selection
- root-cause waterfall selection
- no-chart behavior for single KPIs
- chart rendering
- source-data preservation
- fabricated-data rejection
- unknown-field rejection
- evidence/provenance preservation
