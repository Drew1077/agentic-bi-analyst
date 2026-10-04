# Insight Agent Contract

## 1. Purpose

The Insight Agent converts structured, governed analytical evidence into evidence-grounded business findings.

It does not independently query the database, invent metrics, redefine business rules, or perform uncontrolled numerical analysis.

The Insight Agent is responsible for interpreting evidence that has already been produced by governed project components.

---

## 2. Responsibilities

The Insight Agent MUST:

* consume structured analytical evidence;
* distinguish observed evidence from interpretation;
* identify evidence-backed findings;
* explicitly identify when evidence is insufficient;
* preserve the metric and dimension definitions supplied by the evidence;
* avoid claiming causation when the evidence only establishes contribution or correlation;
* return structured findings suitable for the Orchestrator.

The Insight Agent MUST NOT:

* connect directly to MySQL;
* bypass the SQL Tool Layer;
* execute arbitrary SQL;
* invent KPI formulas;
* invent dimensions;
* modify Semantic Layer definitions;
* modify Analytics Engine calculations;
* treat a measured contribution as proof of an underlying business cause;
* fabricate missing evidence.

---

## 3. Input Contract

The Insight Agent receives structured analytical evidence.

### Required request fields

InsightAgentRequest(
question: str,
evidence: list[dict],
)

### Field definitions

#### question

The original user analytical question.

Type:

str

The value MUST be non-empty after trimming whitespace.

#### evidence

A collection of structured evidence records produced by governed analytical components.

Type:

list[dict]

The collection MAY contain:

* KPI results;
* period comparisons;
* contribution results;
* SQL Analyst evidence;
* other explicitly supported analytical evidence.

The Insight Agent MUST NOT assume evidence exists merely because the request was successfully constructed.

---

## 4. Output Contract

The Insight Agent returns:

InsightAgentResponse(
success: bool,
answer: str | None,
findings: list[dict],
evidence: list[dict],
provenance: list[dict],
errors: list[str],
)

### success

Indicates whether the Insight Agent successfully interpreted the supplied evidence.

### answer

A concise business-readable answer derived only from the supplied evidence.

May be None when the request cannot be answered safely.

### findings

Structured findings derived from the evidence.

Each finding MUST distinguish its evidence status.

Supported finding types:

* observed
* evidence_backed
* hypothesis
* insufficient_evidence

### evidence

The evidence used to support the returned findings.

The Insight Agent MUST preserve the source analytical information needed to trace a finding back to its evidence.

### provenance

Metadata describing where the evidence originated and which governed analytical components produced it.

### errors

Structured failure information represented as strings.

An empty list indicates no errors.

---

## 5. Finding Contract

Each finding SHOULD contain:

```
{
    "type": str,
    "statement": str,
    "supporting_evidence": list,
}
```

### observed

Used for directly measured facts.

Example:

Revenue decreased by 8.4% between the two analyzed periods.

### evidence_backed

Used when the supplied evidence supports an analytical interpretation.

Example:

The Electronics category contributed the largest negative change to the observed revenue decline.

### hypothesis

Used only when an explanation is possible but is not established by the available evidence.

Example:

The decline may be related to lower Electronics sales volume, but the available evidence does not establish the underlying operational reason.

### insufficient_evidence

Used when the supplied evidence does not support a reliable finding.

Example:

The available evidence is insufficient to determine the underlying cause of the revenue decline.

---

## 6. Evidence Rules

The Insight Agent MUST follow these rules:

1. Numerical statements MUST be supported by supplied evidence.
2. Findings MUST NOT introduce unsupported metrics or dimensions.
3. Contribution MUST be described as contribution, not automatically as causation.
4. Missing evidence MUST remain missing.
5. Conflicting evidence MUST NOT be silently reconciled.
6. The agent MUST prefer an explicit insufficient-evidence finding over an unsupported explanation.
7. Evidence and provenance MUST remain traceable to the upstream analytical components.

---

## 7. Failure Behavior

The Insight Agent MUST return a structured failure when:

* the request is invalid;
* the question is empty;
* evidence is missing when evidence is required;
* evidence has an unsupported structure;
* the supplied evidence cannot support a safe finding.

Failure MUST NOT result in fabricated business conclusions.

---

## 8. Architectural Boundary

The Insight Agent sits above governed analytical components.

Expected flow:

SQL Tool Layer
↓
SQL Analyst Agent
↓
Analytics Engine
↓
structured evidence
↓
Insight Agent
↓
structured business findings

The Insight Agent is an interpretation layer, not a database access layer.

---

## 9. Relationship with Root-Cause Agent

The Root-Cause Agent may use the Insight Agent after acquiring and deterministically analyzing the required evidence.

The Root-Cause Agent is responsible for root-cause workflow and evidence acquisition.

The Insight Agent is responsible for interpreting the resulting structured evidence.

Neither agent replaces the Semantic Layer, SQL Tool Layer, SQL Analyst Agent, Analytics Engine, or Orchestrator.

---

