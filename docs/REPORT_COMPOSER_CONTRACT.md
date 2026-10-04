# Report Composer Contract

## 1. Purpose

The Report Composer combines validated analytical results, findings, optional visualization output, and evidence-backed recommendations into one deterministic structured report.

It is a presentation/composition component, not an analytical agent.

## 2. Input Contract

```python
@dataclass
class ReportComposerRequest:
    question: str
    analytical_result: Any
    findings: list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
    visualization: Any = None
```

Requirements:

- `question` must be a non-empty string.
- `analytical_result.success` must be `True`.
- findings and recommendations must be lists.
- every recommendation must contain supporting evidence.
- an optional visualization must be successful when supplied.

## 3. Output Contract

```python
@dataclass
class ReportComposerResponse:
    success: bool
    report: dict[str, Any] | None
    evidence: Any
    provenance: Any
    validation: dict[str, Any]
    errors: list[str]
```

## 4. Report Sections

The structured report contains:

1. title
2. question
3. executive_summary
4. key_results
5. findings
6. visualization
7. recommendations
8. methodology
9. evidence
10. provenance
11. limitations

## 5. Traceability

The report preserves:

- analytical evidence
- analytical provenance
- finding-level supporting evidence
- recommendation-level supporting evidence
- visualization validation metadata

## 6. Scope Boundaries

The Report Composer does not:

- query MySQL
- execute SQL
- redefine metrics
- perform new analytical calculations
- invent missing evidence
- alter validated findings
- turn estimates into observed facts
- implement PDF/HTML/UI rendering
- implement API infrastructure
- implement RAG

## 7. Validation

The composer validates that the final report contains the required sections and that findings/recommendations match the supplied validated inputs.

The report remains structured data so later API/UI phases can choose their presentation format.
