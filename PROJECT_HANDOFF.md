# PROJECT_HANDOFF.md

# Agentic BI Analyst — Chat 02 Handoff

## 1. Project Identity

**Project:** Agentic BI Analyst  
**Goal:** Build an industry-level AI-powered Business Intelligence analyst that can ingest business data, understand natural-language questions, inspect/query data, perform analytical reasoning, generate visualizations, detect important patterns, and produce auditable business recommendations.

**Architecture principle:** The system is not a chatbot wrapped around SQL. It is an agentic analytics system with deterministic tools, structured intermediate outputs, validation, observability, and human-readable evidence.

**Current stage:** Architecture approved. No production coding has started.

---

## 2. Chosen Business Domain

### Domain: E-commerce / Retail Intelligence

Use a realistic omnichannel e-commerce business as the primary case study.

The system should answer questions such as:

- What were sales and profit last month?
- Which products/categories are driving the change in revenue?
- Why did profit fall despite revenue increasing?
- Which regions or customer segments are underperforming?
- What is the month-over-month / year-over-year trend?
- Which products have declining sales?
- Which customers or segments contribute most to revenue?
- What are the top opportunities and risks?
- Can the analyst support the conclusion with evidence?

### Why this domain

It naturally supports:

- revenue, orders, units, discounts, cost, profit
- product/category analysis
- customer segmentation
- geographic analysis
- time-series analysis
- anomaly detection
- KPI analysis
- drill-down/root-cause analysis
- forecasting as a later extension
- executive dashboards

---

## 3. Dataset Strategy

Do NOT build the project around a single toy CSV.

Use a **synthetic-but-realistic enterprise dataset**, with multiple relational tables and controlled business logic.

### Core tables

1. `customers`
2. `products`
3. `orders`
4. `order_items`
5. `payments`
6. `returns`
7. `stores`
8. `marketing_spend`
9. `inventory_snapshots`
10. `calendar`

### Recommended scale

Initial development:

- customers: ~20k
- products: ~2k
- orders: ~150k
- order_items: ~300k–500k
- returns: ~10k–30k
- marketing records: ~20k+
- inventory snapshots: millions only if performance testing requires it

The dataset must contain realistic relationships and intentional analytical patterns.

Examples:

- seasonal demand
- regional differences
- discount/profit trade-offs
- product-level decline
- return-heavy products
- marketing spend spikes
- stock-out periods
- customer repeat-purchase behavior

### Dataset rule

The dataset generator should be deterministic through a fixed seed so that every agent/chat works against the same known data.

Do not randomly regenerate production test data between chats.

---

## 4. Target Architecture

```text
                         USER
                           |
                           v
                  +------------------+
                  |  Analyst API/UI  |
                  +--------+---------+
                           |
                           v
                  +------------------+
                  | Orchestrator     |
                  | / Planner Agent  |
                  +--------+---------+
                           |
             +-------------+-------------+
             |             |             |
             v             v             v
       SQL Analyst    Data Analyst   Insight Agent
             |             |             |
             +-------------+-------------+
                           |
                           v
                  +------------------+
                  | Validation Agent |
                  +--------+---------+
                           |
                 +---------+---------+
                 |                   |
                 v                   v
          Visualization        Recommendation
             Agent                 Agent
                 |                   |
                 +---------+---------+
                           |
                           v
                  +------------------+
                  | Report Composer  |
                  +--------+---------+
                           |
                           v
                    Final Answer
```

### Supporting infrastructure

```text
LLM
 |
 +-- Agent framework
 |
 +-- Tool registry
 |
 +-- MySQL
 |
 +-- Semantic/KPI layer
 |
 +-- Python analytics environment
 |
 +-- Visualization engine
 |
 +-- Redis/cache (later)
 |
 +-- Observability/tracing
 |
 +-- Evaluation framework
```

---

## 5. Agent Design

Keep agents specialized. Do not create one giant agent with every tool.

### Agent 1 — Orchestrator / Planner

Responsibilities:

- understand user intent
- classify analytical task
- decompose complex questions
- decide which agents/tools are needed
- maintain execution state
- enforce workflow order

Output must be structured.

Example:

```json
{
  "intent": "root_cause_analysis",
  "metrics": ["revenue", "profit"],
  "dimensions": ["month", "category", "region"],
  "time_range": "last_6_months",
  "steps": [
    "calculate_kpis",
    "compare_periods",
    "find_contributors",
    "validate_results",
    "generate_insights"
  ]
}
```

---

### Agent 2 — Data/SQL Analyst

Responsibilities:

- inspect schema
- identify relevant tables
- generate SQL
- execute SQL through controlled tools
- return structured results

Rules:

- never directly modify production data
- SELECT-only analytical access
- use parameterized queries
- never trust generated SQL without validation
- always expose query provenance

---

### Agent 3 — Statistical/Data Analysis Agent

Responsibilities:

- pandas/polars analysis
- descriptive statistics
- correlations
- segmentation
- trend calculations
- anomaly detection
- contribution analysis
- statistical comparisons

This agent should work from controlled data returned by tools rather than unrestricted database access.

---

### Agent 4 — Visualization Agent

Responsibilities:

- select appropriate chart type
- generate chart specification
- create charts
- ensure labels/units are understandable
- avoid misleading visualizations

Examples:

- line chart → trends
- bar chart → category comparison
- waterfall → contribution to change
- scatter plot → relationships
- heatmap → regional/category patterns

---

### Agent 5 — Insight / Root-Cause Agent

Responsibilities:

- turn analytical outputs into business insights
- distinguish correlation from causation
- rank findings by business importance
- explain WHY a KPI changed

Required output:

```text
Finding
Evidence
Magnitude
Likely driver
Confidence
Recommended next step
```

---

### Agent 6 — Validation / Critic Agent

This is mandatory.

Responsibilities:

- verify SQL result consistency
- check arithmetic
- detect unsupported claims
- check whether charts match numbers
- check whether conclusions are supported by evidence
- identify hallucinations
- reject weak analysis

The critic can force a re-plan/re-query.

---

### Agent 7 — Recommendation Agent

Responsibilities:

- convert validated insights into actions
- estimate potential impact where possible
- identify owner/function
- state assumptions
- prioritize recommendations

Recommendations must never be invented from unsupported assumptions.

---

### Agent 8 — Report Composer

Responsibilities:

- combine validated findings
- create executive summary
- present KPIs
- include charts
- include methodology/evidence
- present recommendations
- preserve traceability

---

## 6. Tool Layer

Agents should not directly manipulate infrastructure.

Create a controlled tool layer.

### Database tools

- `get_schema()`
- `describe_table(table)`
- `get_column_metadata(table)`
- `execute_readonly_sql(query, params)`
- `explain_query(query)` — later
- `get_distinct_values(table, column)`

### Analytics tools

- `load_query_result()`
- `profile_dataframe()`
- `calculate_kpi()`
- `compare_periods()`
- `calculate_contribution()`
- `detect_anomalies()`
- `segment_customers()`

### Visualization tools

- `create_chart_spec()`
- `render_chart()`

### Business intelligence tools

- `get_kpi_definition()`
- `get_metric_dictionary()`
- `get_business_rules()`

### System tools

- `log_event()`
- `record_trace()`
- `store_analysis_run()`

---

## 7. Semantic Layer

This is a major differentiator.

The agent must not invent KPI definitions.

Create a metric dictionary.

Example:

```text
Revenue
= SUM(order_items.quantity * order_items.unit_price)

Gross Profit
= Revenue - Cost

Profit Margin
= Gross Profit / Revenue

Average Order Value
= Revenue / Distinct Orders

Return Rate
= Returned Units / Sold Units
```

The semantic layer should eventually contain:

- metric name
- business definition
- SQL expression
- allowed dimensions
- grain
- unit
- caveats
- owner/source
- synonyms

This makes the system more reliable than a generic text-to-SQL chatbot.

---

## 8. Database Architecture

### Primary database

**MySQL**

Use a warehouse-style analytical schema.

```text
                 MySQL
                     |
       +-------------+-------------+
       |                           |
   Dimension                     Fact
    Tables                     Tables
       |                           |
 customers                    orders
 products                     order_items
 stores                       payments
 calendar                     returns
                              marketing_spend
                              inventory_snapshots
```

### Modeling

Use a star-schema-inspired design:

- dimensions → descriptive entities
- facts → measurable business events

Primary analytical grain:

**order item**

Do not mix grains accidentally.

For example:

- order-level metrics → orders
- item-level revenue → order_items
- customer-level metrics → aggregated customer/order data
- daily inventory → inventory_snapshots

---

## 9. Data Pipeline

```text
Synthetic Data Generator
          |
          v
       Raw CSV
          |
          v
     Data Validation
          |
          v
   MySQL Raw Layer
          |
          v
   Clean/Analytics Layer
          |
          v
      Semantic Layer
          |
          v
        Agents
```

Use three conceptual layers:

### Raw

Original loaded data.

### Analytics

Cleaned, typed, constrained relational data.

### Semantic

Business-ready views/definitions for agents.

---

## 10. Tech Stack

### Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- MySQL

### Data analysis

- Pandas
- NumPy
- optionally Polars for performance experiments

### Agent layer

Use a modern agent framework only where it provides real value.

Preferred design:

- Python orchestration
- structured tool calling
- Pydantic state/output schemas
- explicit workflow/state machine

Do not hide the architecture behind a framework.

### LLM

Design the project so the model provider is configurable.

Use environment variables for:

- API key
- model
- temperature/configuration

Do not hard-code provider-specific logic throughout the codebase.

### Visualization

- Plotly
- optional Matplotlib for analytical plots

### Frontend

Preferred:

- Streamlit for the first complete working product

Later, if time permits:

- React/Next.js frontend

Do not delay the analytical engine just to build a fancy frontend.

### DevOps

- Docker
- Docker Compose
- Git/GitHub
- `.env`
- pytest
- Ruff/Black
- logging
- OpenTelemetry/Langfuse or equivalent observability layer

Use lightweight infrastructure first. Add Redis/background workers only when justified.

---

## 11. API Architecture

Suggested endpoints:

```text
POST /api/v1/analyze
GET  /api/v1/runs/{run_id}
GET  /api/v1/schema
GET  /api/v1/metrics
GET  /api/v1/health
```

Example:

```text
POST /analyze
{
  "question": "Why did profit fall last quarter?"
}
```

Response should eventually contain:

```json
{
  "run_id": "...",
  "answer": "...",
  "kpis": [],
  "insights": [],
  "charts": [],
  "recommendations": [],
  "evidence": [],
  "validation": {}
}
```

---

## 12. Observability

Every analytical run should eventually have:

- run ID
- user question
- plan
- agent sequence
- tool calls
- SQL queries
- execution times
- row counts
- intermediate outputs
- validation results
- final answer
- errors/retries
- token/cost metadata where available

The goal is:

**Every important claim should be traceable to evidence.**

---

## 13. Security Rules

Mandatory:

- secrets only in `.env`
- never commit API keys
- database user used by agents should have read-only analytical permissions
- validate SQL before execution
- block DDL/DML for agent queries
- parameterize user-controlled values
- limit query execution time
- limit returned rows where appropriate
- sanitize rendered content
- do not expose internal prompts or secrets in final answers

---

## 14. Hallucination-Control Rules

The system must follow these rules:

1. Never invent a number.
2. Never claim a KPI without calculating it.
3. Never claim causation when only correlation/evidence of association exists.
4. Every major insight must have supporting evidence.
5. If data is insufficient, say so.
6. If a query fails, do not fabricate a result.
7. If validation fails, revise the analysis.
8. KPI definitions come from the semantic layer.
9. Use exact time periods in conclusions.
10. Preserve the difference between:
   - observed fact
   - calculated metric
   - inference
   - recommendation

---

## 15. Project Folder Structure

```text
agentic-bi-analyst/
│
├── README.md
├── PROJECT_HANDOFF.md
├── ARCHITECTURE.md
├── .env.example
├── .gitignore
├── docker-compose.yml
├── pyproject.toml
│
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── routes_analyze.py
│   │   ├── routes_runs.py
│   │   └── routes_metadata.py
│   │
│   ├── agents/
│   │   ├── orchestrator.py
│   │   ├── sql_agent.py
│   │   ├── analytics_agent.py
│   │   ├── visualization_agent.py
│   │   ├── insight_agent.py
│   │   ├── validation_agent.py
│   │   ├── recommendation_agent.py
│   │   └── report_agent.py
│   │
│   ├── tools/
│   │   ├── database.py
│   │   ├── analytics.py
│   │   ├── visualization.py
│   │   ├── semantic.py
│   │   └── observability.py
│   │
│   ├── schemas/
│   │   ├── agent.py
│   │   ├── analysis.py
│   │   ├── chart.py
│   │   └── response.py
│   │
│   ├── services/
│   │   ├── orchestration.py
│   │   ├── query_service.py
│   │   ├── validation_service.py
│   │   └── report_service.py
│   │
│   ├── db/
│   │   ├── connection.py
│   │   ├── models.py
│   │   └── repositories/
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── security.py
│   │
│   └── prompts/
│       ├── orchestrator.txt
│       ├── sql_agent.txt
│       ├── insight_agent.txt
│       └── validation_agent.txt
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── generated/
│
├── scripts/
│   ├── generate_data.py
│   ├── load_data.py
│   └── seed_database.py
│
├── sql/
│   ├── schema/
│   ├── views/
│   ├── metrics/
│   └── validation/
│
├── semantic_layer/
│   ├── metrics.yml
│   ├── dimensions.yml
│   └── business_rules.yml
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── agent/
│   └── evaluation/
│
├── evaluation/
│   ├── questions.json
│   ├── expected_results.json
│   └── scoring.py
│
├── frontend/
│   └── streamlit_app.py
│
├── notebooks/
│   └── exploration/
│
└── docs/
    ├── architecture/
    ├── decisions/
    └── demos/
```

---

## 16. Development Phases

### Phase 0 — Architecture
Status: **COMPLETE**

Deliverables:

- domain
- dataset strategy
- architecture
- agent design
- tool design
- stack
- folder structure
- project rules

### Phase 1 — Data Foundation

Build:

- synthetic dataset generator
- CSVs
- MySQL schema
- loading pipeline
- data quality checks
- analytical views
- seed data

### Phase 2 — Semantic Layer

Build:

- KPI definitions
- metric dictionary
- dimension definitions
- business rules
- synonym mapping

### Phase 3 — Deterministic Analytics Engine

Before agents, build reliable functions for:

- KPI calculation
- period comparison
- contribution analysis
- trend analysis
- anomaly detection

This provides a trustworthy foundation.

### Phase 4 — SQL Analyst Agent

Build:

- schema inspection
- SQL generation
- SQL validation
- read-only execution
- structured results
- error recovery

### Phase 5 — Orchestrator

Build:

- intent classification
- planning
- agent routing
- state management
- retries
- stopping conditions

### Phase 6 — Insight + Critic Loop

Build:

```text
Analysis
   ↓
Insight
   ↓
Critic
   ↓
Pass? ── No ──> Re-analysis
   |
  Yes
   ↓
Recommendation
```

### Phase 7 — Visualization

Build:

- chart selection
- chart specifications
- rendering
- chart validation

### Phase 8 — API + UI

Build:

- FastAPI
- Streamlit
- analysis history
- charts
- evidence
- recommendations

### Phase 9 — Evaluation

Create a benchmark of realistic BI questions.

Categories:

- simple lookup
- aggregation
- comparison
- trend
- ranking
- drill-down
- root cause
- anomaly
- multi-step analysis
- ambiguous question

Measure:

- answer correctness
- SQL correctness
- numerical correctness
- evidence grounding
- plan quality
- latency
- failure rate
- cost

### Phase 10 — Production Hardening

Add:

- Docker
- authentication if required
- database permissions
- observability
- caching
- rate limiting
- query limits
- robust error handling
- deployment

---

## 17. Industry-Level Acceptance Criteria

The project is NOT considered complete merely because:

> User asks question → LLM generates SQL → answer appears.

Minimum final standard:

- multi-agent workflow
- semantic metric layer
- relational analytical database
- deterministic analytics tools
- SQL validation
- validation/critic loop
- evidence-backed insights
- visualizations
- recommendations
- API
- usable UI
- automated evaluation
- logging/tracing
- tests
- Dockerized setup
- clear documentation

---

## 18. Chat-to-Chat Continuation Protocol

Each future chat has one responsibility.

Every chat MUST:

1. Read `PROJECT_HANDOFF.md` first.
2. Preserve all architectural decisions unless explicitly changed.
3. Never silently redesign the project.
4. Never restart completed phases.
5. State what phase/subphase it is working on.
6. Produce concrete deliverables.
7. Record important decisions for the next chat.
8. End with an updated handoff section for the next chat.
9. Avoid unrelated feature expansion.
10. Do not code outside the current chat's assigned scope.

### If a design change is necessary

Use:

```text
PROPOSED CHANGE
Current:
New:
Reason:
Impact:
Decision required:
```

Do not silently change architecture.

---

## 19. Chat Responsibilities

### Chat 01
Architecture only.

### Chat 02
Dataset design + synthetic data generation + data contracts.

### Chat 03
MySQL schema + database setup + loading pipeline.

### Chat 04
Semantic layer + KPI definitions + business rules.

### Chat 05
Deterministic analytics engine.

### Chat 06
SQL tool layer + SQL validation.

### Chat 07
SQL Analyst Agent.

### Chat 08
Orchestrator/planner.

### Chat 09
Insight + root-cause agent.

### Chat 10
Validation/critic agent + retry loop.

### Chat 11
Visualization agent.

### Chat 12
Recommendation + report composer.

### Chat 13
FastAPI backend + API contracts.

### Chat 14
Streamlit UI.

### Chat 15
Evaluation benchmark + automated scoring.

### Chat 16
Observability, security, performance and hardening.

### Chat 17
Docker/deployment/documentation.

### Chat 18
Final audit, demo scenarios, resume/project documentation and interview explanation.

Chats may be merged only when the actual scope remains manageable. Do not cram unrelated phases into one chat just to finish faster.

---

## 20. Definition of Done for Chat 02

Chat 02 must produce:

- finalized table-level data contracts
- column definitions
- data types
- primary/foreign keys
- relationships
- grain for every table
- realistic value ranges
- data-generation rules
- intentional business patterns
- seed strategy
- data quality constraints
- expected row counts
- sample records
- dataset generation plan/code if appropriate

Chat 02 must NOT build:

- agents
- FastAPI
- UI
- LLM orchestration
- visualization agent

Its output must prepare Chat 03 for MySQL implementation.

---

## 21. Final Project Positioning

Position the project as:

**"An agentic BI analyst that combines natural-language reasoning with governed SQL, deterministic analytics, a semantic KPI layer, automated validation, visualization, and evidence-backed business recommendations."**

Avoid positioning it as merely:

- chatbot
- text-to-SQL demo
- dashboard generator
- generic RAG chatbot
- LLM wrapper

The key differentiator is the **closed-loop analytical workflow with governance and validation**.

---

## 22. First Instruction for Chat 02

Start by reviewing this handoff.

Then design the complete synthetic e-commerce dataset contract.

Do not jump into MySQL implementation yet.

The immediate objective is to make the data model realistic enough that later agents can perform genuine BI analysis rather than simple demo queries.
