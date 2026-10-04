# SQL Analyst Agent Contract

## 1. Purpose

The SQL Analyst Agent is the governed natural-language-to-SQL component of the Agentic BI Analyst system.

Its purpose is to convert a business question into a validated, executable SQL query using the project's frozen semantic layer and SQL Tool Layer.

The agent must produce auditable evidence and provenance for every successful analysis.

The agent is not a general-purpose chatbot and must not bypass the project's semantic, validation, or SQL execution controls.

---

## 2. Scope

### In Scope

The SQL Analyst Agent is responsible for:

1. Understanding the user's business question.
2. Identifying the required business metrics.
3. Resolving metric names and synonyms using the semantic layer.
4. Identifying valid dimensions and filters.
5. Applying authoritative date semantics.
6. Applying governed business rules.
7. Applying safe join rules.
8. Generating candidate SQL.
9. Validating the SQL.
10. Executing SQL through the SQL Tool Layer.
11. Retrying failed queries when appropriate.
12. Returning structured results.
13. Providing evidence and provenance.
14. Reporting failures explicitly.

### Out of Scope

The SQL Analyst Agent does not implement:

* Orchestration across multiple agents
* Data Analyst Agent
* Insight Agent
* Visualization Agent
* Recommendation Agent
* Report Composer Agent
* FastAPI
* Streamlit
* Docker
* Production deployment
* Arbitrary RAG systems
* Direct database access outside the SQL Tool Layer

---

## 3. Input Contract

The initial request contract is:

```python
SQLAgentRequest(
    question: str
)
```

### Input Requirements

* `question` must contain the user's business question.
* The question must be treated as the source of analytical intent.
* The agent must not assume missing business definitions when the semantic layer does not provide them.
* Ambiguous requests must be handled explicitly rather than silently guessed.

---

## 4. Semantic Resolution

The agent must use the existing semantic layer as the authoritative source for business meaning.

The semantic layer contains:

* `metrics.yml`
* `dimensions.yml`
* `business_rules.yml`
* `joins.yml`
* `date_logic.yml`
* `synonyms.yml`

The existing `SemanticCatalog` implementation must be reused.

The agent must not create a second independent semantic-layer loader.

### Metric Resolution

Metric resolution must follow the existing governed resolution mechanism:

1. Canonical metric ID
2. Exact metric display name
3. Governed synonym

If a requested metric cannot be resolved using the semantic layer, the agent must not invent a metric definition.

### Dimension Resolution

Dimensions must be resolved against the governed dimension catalog and actual schema.

Because some dimension names overlap across business domains, resolution must consider the analytical context rather than relying only on string matching.

### Date Resolution

Date semantics must follow:

* The metric's authoritative date
* `date_logic.yml`
* Calendar rules when calendar dimensions are required

The agent must never substitute an unrelated date field merely because it is available.

---

## 5. SQL Generation

The agent generates SQL only after resolving the required semantic concepts.

SQL generation must respect:

* Metric definitions
* Dimension definitions
* Business rules
* Join rules
* Date semantics
* Fact isolation rules
* Native fact grain
* Ratio-of-aggregates requirements
* Point-in-time inventory semantics

The generated SQL must target the project's MySQL database.

The agent must not invent:

* Tables
* Columns
* Metrics
* Dimensions
* Business rules
* KPI formulas
* Query results

---

## 6. SQL Validation

Every generated SQL query must pass the existing SQL Tool validation layer before execution.

The agent must use:

```python
validate_sql()
```

from:

```text
app/tools/sql.py
```

Validation must occur:

* Before the first execution
* Before every retry
* After every SQL revision

The agent must not bypass validation.

Queries containing unsafe fact combinations or destructive SQL must not be executed.

---

## 7. SQL Execution

All database execution must happen through the existing SQL Tool Layer.

The agent must use:

```python
execute_sql()
```

from:

```text
app/tools/sql.py
```

The agent must not create a separate MySQL connection.

The agent must not directly query MySQL using `mysql.connector` or another database library.

The SQL Tool Layer remains responsible for:

* Database connection
* SQL validation
* Query execution
* Result retrieval
* Row limits
* Database errors
* Execution timing

---

## 8. Retry Policy

The agent may retry a failed analytical query.

Maximum retry attempts:

```text
3
```

Each retry must:

1. Inspect the previous failure.
2. Determine whether the failure is recoverable.
3. Revise the SQL or semantic interpretation when appropriate.
4. Revalidate the revised SQL.
5. Execute the revised SQL through the SQL Tool Layer.

The agent must not repeatedly submit the same failed query without modification.

If all attempts fail, the agent must return a structured failure.

The agent must never claim successful analysis when execution failed.

---

## 9. Output Contract

The initial response structure is:

```python
SQLAgentResponse(
    success: bool,
    answer: ...,
    sql: ...,
    columns: ...,
    rows: ...,
    evidence: ...,
    provenance: ...,
    errors: ...
)
```

The exact Python types will be defined during implementation.

### Successful Response

A successful response must contain sufficient information to identify:

* The analytical result
* The SQL used
* Returned columns
* Returned rows
* Supporting evidence
* Provenance

### Failed Response

A failed response must clearly identify:

* That the analysis failed
* The relevant error
* The stage at which failure occurred
* Any useful diagnostic information

The agent must not fabricate an answer when SQL execution fails.

---

## 10. Evidence Requirements

Every successful analytical response must provide evidence derived from the executed SQL result.

Evidence should allow another component or developer to understand how the answer was obtained.

Evidence may include:

* SQL query
* Returned columns
* Returned rows
* Row count
* Resolved metrics
* Resolved dimensions
* Applied date range
* Applied filters
* Semantic definitions used

The agent must distinguish between:

* Retrieved database facts
* Semantic definitions
* Derived calculations
* Model interpretation

The agent must not present model-generated assumptions as database facts.

---

## 11. Provenance

The agent must maintain provenance for the analytical request.

Provenance should identify relevant sources such as:

```text
semantic_layer/metrics.yml
semantic_layer/dimensions.yml
semantic_layer/business_rules.yml
semantic_layer/joins.yml
semantic_layer/date_logic.yml
semantic_layer/synonyms.yml
app/tools/sql.py
```

Provenance should also capture the executed SQL and relevant execution information.

The purpose of provenance is auditability and reproducibility.

---

## 12. Failure Handling

The agent must explicitly handle failures including:

* Unknown metric
* Unknown dimension
* Ambiguous business question
* Invalid SQL
* Unsafe fact combination
* Database connection failure
* SQL execution failure
* Empty result
* Result exceeding the SQL Tool Layer limit
* Unsupported analytical requirement
* Semantic-layer conflict or missing definition

The agent must not silently recover by inventing business logic.

When a request cannot be safely answered using the governed system, the agent must report the limitation.

---

## 13. Forbidden Behaviors

The SQL Analyst Agent must never:

1. Invent KPI definitions.
2. Invent database tables.
3. Invent database columns.
4. Invent query results.
5. Invent business rules.
6. Bypass the semantic layer.
7. Bypass SQL validation.
8. Bypass the SQL Tool Layer.
9. Directly connect to MySQL.
10. Use unsafe fact combinations.
11. Silently change date semantics.
12. Silently exclude or include business populations.
13. Silently truncate query results.
14. Claim success when execution failed.
15. Repeatedly execute the same failed query without revision.
16. Treat model assumptions as authoritative business rules.

---

## 14. Responsibility Boundaries

### Semantic Layer

Responsible for:

* KPI definitions
* Dimensions
* Synonyms
* Business rules
* Join safety
* Date semantics

### SQL Tool Layer

Responsible for:

* SQL validation
* Fact-isolation protection
* Database connection
* SQL execution
* Result retrieval
* Row-limit enforcement
* Database error handling

### SQL Analyst Agent

Responsible for:

* Understanding the business question
* Semantic resolution
* Governed SQL construction
* Validation orchestration
* Execution orchestration
* Retry handling
* Evidence
* Provenance
* Structured response

### Analytics Engine

The existing Analytics Engine remains separate from the SQL Analyst Agent.

It must not be duplicated or absorbed into the SQL Agent.

---

## 15. Non-Goals

This implementation does not include:

* Multi-agent orchestration
* Automatic insight generation
* Natural-language recommendations
* Visualization generation
* Dashboard generation
* Report generation
* API deployment
* UI development
* Containerization
* Cloud deployment
* Production monitoring

These belong to later project phases.

---

## 16. Initial Design Principle

The SQL Analyst Agent must not follow a simplistic:

```text
LLM → SQL → Database
```

architecture.

The intended architecture is:

```text
Business Question
       ↓
Semantic Resolution
       ↓
Governed SQL Construction
       ↓
SQL Validation
       ↓
SQL Tool Execution
       ↓
Result Verification
       ↓
Evidence + Provenance
       ↓
Structured Response
```

The agent should therefore be:

* Semantic-aware
* Tool-constrained
* Deterministic where possible
* Auditable
* Evidence-producing
* Failure-aware

The semantic layer and SQL Tool Layer remain the authoritative governance boundaries.
