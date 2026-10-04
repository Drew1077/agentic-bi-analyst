# Recommendation Agent Contract

## 1. Purpose

The Recommendation Agent converts successful, already-validated analytical findings into deterministic, traceable business recommendations.

It does not query MySQL, execute SQL, redefine metrics, or create new analytical evidence.

## 2. Input Contract

```python
@dataclass
class RecommendationAgentRequest:
    question: str
    analytical_result: Any
    findings: list[dict[str, Any]]
```

Requirements:

- `question` must be a non-empty string.
- `analytical_result` must be non-`None`.
- `analytical_result.success` must be `True`.
- Every finding must be a dictionary with a supported type, non-empty statement, and supporting evidence.

## 3. Supported Finding Types

- `observed`
- `evidence_backed`
- `hypothesis`
- `insufficient_evidence`

Only `observed` and `evidence_backed` findings produce operational recommendations.

Hypotheses and insufficient-evidence findings are intentionally not converted into actions.

## 4. Output Contract

```python
@dataclass
class RecommendationAgentResponse:
    success: bool
    recommendations: list[dict[str, Any]]
    evidence: Any
    provenance: Any
    errors: list[str]
```

Each recommendation contains:

- recommendation
- supporting evidence
- owner
- potential impact
- priority
- priority basis
- assumptions
- evidence strength

## 5. Evidence Traceability

Every recommendation must retain the supporting evidence supplied by the Insight/Root-Cause workflow.

The agent does not create replacement evidence.

## 6. Potential Impact

Potential impact is only represented when the supplied evidence explicitly contains `potential_impact` or `impact_estimate`.

Otherwise:

```text
type: not_available
value: null
assumptions: []
```

An estimate supplied by upstream evidence is preserved as `estimated` and its assumptions are preserved.

## 7. Priority

Priority is deterministic and categorical:

- `high`
- `medium`
- `low`

Priority is accompanied by a `priority_basis`.

## 8. Scope Boundaries

The Recommendation Agent does not:

- query MySQL
- execute SQL
- bypass the SQL Tool Layer
- redefine semantic metrics
- calculate new KPIs
- invent numerical impact
- establish causation without supporting evidence
- compose the final report
- implement API/UI/deployment
- implement RAG

## 9. Provenance

The response preserves analytical provenance and adds recommendation-level provenance indicating that recommendations were generated from validated findings.
