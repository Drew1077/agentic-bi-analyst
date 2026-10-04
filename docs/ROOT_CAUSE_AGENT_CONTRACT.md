# Root-Cause Agent Contract

## 1. Purpose

The Root-Cause Agent handles user questions that ask why a governed business metric changed.

It is responsible for acquiring the required analytical evidence through existing governed components, performing deterministic comparison and contribution analysis, and producing an evidence-grounded root-cause analysis.

The Root-Cause Agent MUST distinguish between:

* observed metric changes;
* measured contributors to those changes;
* possible explanations that are not established by the available evidence.

A contribution is not automatically proof of an underlying business cause.

---

## 2. Responsibilities

The Root-Cause Agent MUST:

* validate the root-cause request;
* identify the governed metric involved;
* identify the relevant analytical periods;
* obtain evidence through the SQL Analyst Agent and existing governed components;
* use the Analytics Engine for deterministic period comparison and contribution analysis;
* identify dimensions that explain the measured change when sufficient evidence exists;
* pass structured evidence to the Insight Agent for business-readable interpretation;
* preserve evidence and provenance;
* explicitly report insufficient evidence when the available evidence cannot establish a reliable finding.

The Root-Cause Agent MUST NOT:

* connect directly to MySQL;
* bypass the SQL Tool Layer;
* execute arbitrary SQL;
* invent KPI formulas;
* invent dimensions;
* redefine business rules;
* modify Semantic Layer definitions;
* replace the SQL Analyst Agent;
* replace the Analytics Engine;
* treat contribution as automatic proof of causation;
* fabricate explanations when evidence is insufficient.

---

## 3. Input Contract

The Root-Cause Agent receives a structured request.

### Required request fields

RootCauseAgentRequest(
question: str,
)

### question

The original user root-cause question.

Type:

str

The value MUST be non-empty after trimming whitespace.

Examples of supported question patterns include:

* Why did revenue decline in 2025?
* Why did revenue decrease in 2025?
* What caused revenue to decline in 2025?
* What is the reason for the revenue decline in 2025?

The exact supported metric, period, dimension, and analytical scope MUST be determined by governed project components rather than invented by the agent.

---

## 4. Output Contract

The Root-Cause Agent returns:

RootCauseAgentResponse(
success: bool,
answer: str | None,
findings: list[dict],
evidence: list[dict],
provenance: list[dict],
errors: list[str],
)

### success

Indicates whether the root-cause workflow completed successfully.

### answer

A concise business-readable root-cause analysis derived only from the available evidence.

May be None when the workflow cannot safely produce an answer.

### findings

Structured findings produced from deterministic analytical evidence.

Each finding MUST identify its evidence status.

Supported finding types:

* observed
* evidence_backed
* hypothesis
* insufficient_evidence

### evidence

Structured analytical evidence used to produce the findings.

Evidence MAY include:

* period comparison results;
* contribution results;
* SQL Analyst evidence;
* metric and dimension information;
* relevant period information.

### provenance

Metadata describing the governed components and analytical operations that produced the evidence.

### errors

Structured failure information represented as strings.

An empty list indicates no errors.

---

## 5. Root-Cause Workflow

The expected workflow is:

User root-cause question
↓
Root-Cause Agent
↓
Identify governed metric and periods
↓
SQL Analyst Agent
↓
Governed SQL evidence
↓
Analytics Engine
↓
Period comparison
↓
Contribution analysis
↓
Structured evidence
↓
Insight Agent
↓
Evidence-grounded findings
↓
Root-cause response

The Root-Cause Agent MUST use existing project components rather than implementing duplicate database or metric logic.

---

## 6. Period Comparison

For a period-based root-cause question, the agent SHOULD establish:

* current period;
* comparison period;
* metric;
* current metric value;
* previous metric value;
* absolute change;
* percentage change;
* direction of change.

The period comparison MUST use the existing Analytics Engine.

The Root-Cause Agent MUST NOT independently implement a competing percentage-change or period-comparison formula.

---

## 7. Contribution Analysis

When sufficient dimensional evidence is available, the Root-Cause Agent SHOULD determine which dimension groups contributed to the observed metric change.

Contribution analysis MUST use the existing Analytics Engine.

For example, a revenue decline may produce evidence such as:

* Category A: negative contribution;
* Category B: negative contribution;
* Category C: positive contribution.

The Root-Cause Agent may identify the largest measured negative contributor.

However, the statement MUST remain limited to what the contribution evidence establishes.

For example:

> Category A had the largest negative contribution to the observed revenue decline.

It MUST NOT automatically convert that finding into:

> Category A was the underlying business cause of the revenue decline.

The latter requires additional evidence.

---

## 8. Evidence Classification

### observed

Used for directly measured changes.

Example:

Revenue decreased by 8.4% between the analyzed periods.

### evidence_backed

Used when the available evidence supports a measured contributor.

Example:

The Electronics category contributed the largest negative change to the observed revenue decline.

### hypothesis

Used when an explanation is plausible but not established by the available evidence.

Example:

The decline may be related to lower Electronics sales volume, but the available evidence does not establish the operational reason.

### insufficient_evidence

Used when the available evidence cannot establish a reliable contributor or explanation.

Example:

The available evidence is insufficient to determine the underlying cause of the revenue decline.

---

## 9. Insufficient-Evidence Behavior

The Root-Cause Agent MUST explicitly return an insufficient-evidence finding when:

* the requested metric cannot be resolved;
* the required comparison period cannot be established;
* the required evidence cannot be obtained;
* the evidence does not contain sufficient dimensional information;
* the available evidence does not support a reliable contributor;
* evidence conflicts in a way that prevents a reliable conclusion.

The agent MUST NOT invent a root cause to make the response appear complete.

A valid response may therefore state that the available evidence identifies a measured change but does not establish its underlying cause.

---

## 10. Evidence and Provenance

Every substantive finding SHOULD be traceable to the evidence that supports it.

Evidence SHOULD preserve:

* original question;
* governed metric;
* dimensions used;
* analyzed periods;
* comparison results;
* contribution results;
* source SQL Analyst evidence where applicable.

Provenance SHOULD identify the governed analytical components used to obtain the evidence.

The Root-Cause Agent MUST NOT discard evidence required for downstream verification or auditing.

---

## 11. Failure Behavior

The Root-Cause Agent MUST return a structured failure when:

* the request is invalid;
* the question is empty;
* the metric cannot be resolved;
* required evidence acquisition fails;
* deterministic analysis fails;
* the evidence structure is invalid;
* the workflow cannot safely produce a root-cause finding.

Failures from upstream components MUST be preserved rather than replaced with fabricated conclusions.

---

## 12. Architectural Boundaries

The Root-Cause Agent sits above the existing governed analytical stack.

The intended dependency direction is:

Semantic Layer
↓
SQL Tool Layer
↓
SQL Analyst Agent
↓
Analytics Engine
↓
Root-Cause Agent
↓
Insight Agent
↓
Orchestrator

The Root-Cause Agent MUST NOT introduce a second database access path or duplicate governed metric logic.

---

## 13. Relationship with Insight Agent

The Root-Cause Agent is responsible for the analytical workflow and evidence acquisition.

The Insight Agent is responsible for interpreting structured evidence into business-readable findings.

The Root-Cause Agent MAY invoke the Insight Agent after deterministic analytical evidence has been produced.

The Insight Agent MUST NOT be required to independently discover or invent the evidence needed for root-cause analysis.

---

## 14. Relationship with Orchestrator

The Orchestrator is responsible for:

* intent classification;
* workflow planning;
* agent registration;
* step execution;
* retry handling;
* final response assembly.

The Root-Cause Agent is responsible for the root-cause analytical workflow itself.

The Root-Cause Agent MUST NOT replace or redesign the Orchestrator.

---

## 15. Scope Boundary

Chat 09 implements the Root-Cause and Insight layer only.

The following are outside the scope of this contract:

* Validation/Critic Agent;
* Visualization Agent;
* Recommendation Agent;
* FastAPI;
* Streamlit;
* frontend implementation;
* unrestricted RAG;
* direct database access from Insight or Root-Cause agents.

---

