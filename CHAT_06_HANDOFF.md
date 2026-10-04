# Chat 06 Handoff — SQL Tool Layer + Validation

## 1. Project Context

Project: **Agentic BI Analyst**

Domain: **E-commerce / Retail Intelligence**

Database: **MySQL**

Chat 06 is responsible for building the deterministic SQL/database tool layer that future agents will use to safely query the MySQL database.

This is **not** the SQL Analyst Agent yet.

The goal is to create reliable tools that can:

1. execute validated SQL,
2. retrieve structured tabular results,
3. enforce safety constraints,
4. respect semantic-layer definitions,
5. prevent dangerous fact-table joins,
6. provide predictable outputs to future agents.

---

# 2. Frozen Architecture

The project architecture is already finalized.

Do NOT redesign the architecture.

Current pipeline:

```text
User
  ↓
Future Orchestrator / Planner
  ↓
SQL Analyst Agent
  ↓
SQL Tool Layer
  ↓
MySQL
  ↓
Structured Results
  ↓
Analytics / Insight / Visualization / Recommendation Agents
```

The deterministic analytics engine from Chat 05 is already complete.

---

# 3. Previous Phases

## Chat 01 — Architecture

Completed.

Defined:

* project architecture
* business domain
* agent architecture
* tools
* technology stack
* development phases
* folder structure
* project rules

---

## Chat 02 — Dataset

Completed.

Frozen synthetic-but-realistic enterprise dataset:

```text
Seed: 20260915
Date range: 2024-01-01 → 2026-08-31
```

---

## Chat 03 — MySQL Database

Completed.

Database:

```text
agentic_bi
```

Tables:

```text
customers
products
orders
order_items
payments
returns
stores
marketing_spend
inventory_snapshots
calendar
```

Existing authoritative database scripts include:

```text
scripts/load_data.py
scripts/validate_data.py
scripts/verify_database.py
scripts/validate_semantic_layer.py
```

Use the existing MySQL connection convention from Chat 03.

Do not create a competing database configuration system unless there is a genuine technical requirement.

---

# 4. Chat 04 — Semantic Layer

Completed.

Location:

```text
semantic_layer/
├── metrics.yml
├── dimensions.yml
├── business_rules.yml
├── joins.yml
├── date_logic.yml
├── synonyms.yml
└── catalog.yml
```

Documentation:

```text
docs/
└── semantic_layer/
    └── SEMANTIC_LAYER.md
```

Validation:

```text
SEMANTIC VALIDATION: PASS
```

The semantic layer is authoritative for business definitions.

---

# 5. Chat 05 — Deterministic Analytics Engine

Completed.

Main implementation:

```text
app/
└── tools/
    └── analytics.py
```

Tests:

```text
tests/
└── unit/
    └── test_analytics.py
```

Implemented:

* semantic catalog loading
* governed metric resolution
* KPI calculations
* period comparison
* contribution analysis
* trend analysis
* anomaly detection
* edge-case handling

Final test result:

```text
54 passed
```

MySQL verification also passed.

---

# 6. Governed Financial Definitions

These formulas are FROZEN.

```text
gross_revenue = quantity × unit_price

discount_amount = gross_revenue × discount_percent

net_revenue = gross_revenue − discount_amount

total_cost = quantity × unit_cost

gross_profit = net_revenue − total_cost
```

Do not change these formulas.

---

# 7. Inventory Definition

FROZEN:

```text
closing_stock =
    opening_stock
    + units_received
    − units_sold
    + units_returned
```

Do not modify this definition.

---

# 8. Important Fact-Grain Rules

This is one of the most important requirements for Chat 06.

Native grains:

```text
orders
    → order grain

order_items
    → order-item grain

customers
    → customer grain

inventory_snapshots
    → store × product × snapshot-date grain
```

Examples:

```text
Revenue / profit
→ order_items

Order count
→ distinct orders

Customer count
→ distinct customers

Inventory position
→ inventory_snapshots
```

---

# 9. Critical Double-Counting Rule

Never blindly join independent fact tables before aggregation.

Unsafe examples:

```sql
orders
JOIN order_items
JOIN payments
```

```sql
orders
JOIN order_items
JOIN returns
```

Especially unsafe:

```sql
orders
JOIN order_items
JOIN payments
JOIN returns
```

Reason:

One order can have:

* multiple order items
* multiple payments
* multiple returns

This can multiply rows and inflate aggregate values.

Chat 05 verified this against the real MySQL database.

Correct order-item revenue:

```text
6,961,011,725.06
```

Unsafe `order_items → payments` revenue:

```text
7,218,961,569.71
```

Therefore the SQL tool layer must actively respect fact isolation.

---

# 10. Date Semantics

Do not assume every metric uses `orders.order_date`.

Process-specific dates:

```text
orders
→ orders.order_date

payments
→ payments.payment_date

returns
→ returns.return_date

marketing
→ marketing_spend.date

inventory
→ inventory_snapshots.snapshot_date

customer acquisition
→ customers.signup_date
```

Use the semantic layer's date definitions.

---

# 11. Business Rules

Important existing rules:

* No authoritative order-status eligibility rule has been established.
* Do not silently exclude cancelled orders.
* Base sales metrics use the loaded order_items population as-is.
* Base net revenue is NOT automatically reduced by returns.
* Refunds must not be subtracted from net revenue unless a future governed metric explicitly defines this.
* Customer-normalized metrics use distinct customer IDs.
* NULL customer IDs are excluded from customer counts.
* Inventory metrics respect snapshot grain.
* No extra marketing validity filter should be invented.
* Payment-status eligibility remains unresolved.
* Marketing attribution remains unresolved where schema alone cannot determine the intended definition.

Do not invent business rules.

---

# 12. Chat 06 Objective

Build the **SQL Tool Layer + Validation**.

The layer should provide safe deterministic database operations for future agents.

Likely responsibilities:

```text
SQL generation input
        ↓
SQL validation
        ↓
Safety checks
        ↓
Database execution
        ↓
Structured result
        ↓
Validation / metadata
```

The exact internal implementation can be designed within these constraints.

---

# 13. Expected Tool Capabilities

Chat 06 should investigate and implement appropriate deterministic tools such as:

### Database connection tool

Responsible for:

* establishing MySQL connection
* handling configuration
* connection errors
* closing resources safely

Reuse the existing project database configuration pattern.

### Schema inspection tool

Should provide controlled access to:

* table names
* columns
* data types
* primary keys
* foreign keys
* relevant schema metadata

### SQL validation tool

Should validate generated SQL before execution.

At minimum investigate protection against:

* destructive statements
* unsupported statements
* invalid tables/columns
* dangerous unrestricted operations
* unsafe fact-table joins
* queries violating project constraints

### SQL execution tool

Should:

* execute approved read-only analytical SQL
* return structured results
* handle errors cleanly
* expose useful metadata
* avoid returning uncontrolled database objects

### Result validation / normalization

Results should be returned in a predictable structure that future agents can consume.

---

# 14. Read-Only Principle

For the analytical agent workflow, SQL execution should be **read-only**.

The tool layer must not allow future agents to execute arbitrary:

```sql
INSERT
UPDATE
DELETE
DROP
ALTER
TRUNCATE
CREATE
REPLACE
```

unless a completely separate administrative workflow is intentionally introduced later.

Do not introduce such an administrative workflow in Chat 06.

---

# 15. Semantic Integration

The SQL layer must not redefine business metrics.

For example, if a future request asks:

```text
What was net revenue last month?
```

The SQL layer should ultimately respect the governed definition:

```text
net_revenue =
gross_revenue − discount_amount
```

The semantic layer answers:

> What does net revenue mean?

The SQL tool answers:

> How can the database safely retrieve the required data?

The analytics engine answers:

> How should deterministic analytical calculations be performed?

Keep these responsibilities separate.

---

# 16. Suggested Project Location

Start by evaluating an appropriate structure under:

```text
app/
└── tools/
```

Possible organization:

```text
app/
└── tools/
    ├── analytics.py
    └── sql.py
```

Additional modules may be introduced if genuinely justified.

Do not create unnecessary abstractions.

---

# 17. Testing Requirements

Chat 06 must include unit tests for:

### SQL validation

Test:

* valid SELECT
* destructive SQL rejection
* malformed SQL
* unsafe statements
* invalid table references where practical
* fact-isolation protection

### Database execution

Test:

* successful query
* empty result
* invalid query
* connection failure handling

### Schema inspection

Test:

* expected tables
* expected columns
* primary/foreign-key metadata where applicable

### Result structure

Test that SQL results have a predictable machine-readable structure.

---

# 18. Integration Verification

After implementation, perform real MySQL verification.

Do not rely only on mocked tests.

At minimum verify:

```text
SQL Tool
   ↓
MySQL
   ↓
Known analytical query
   ↓
Expected result
```

The result should be compared with known values from the existing database where appropriate.

Do not modify the frozen dataset to make a test pass.

---

# 19. Existing MySQL Verification Knowledge

Chat 05 established these verified values:

Sales:

```text
gross_revenue       = 6961011725.06
net_revenue         = 6370409367.51671
gross_profit        = 1188111163.01671
orders              = 150000
units_sold          = 563727
customer_count      = 19378
```

Latest inventory snapshot:

```text
2026-08-31
```

Latest snapshot:

```text
closing_stock       = 6833195
stockout_rate       = 0.0
```

These can be used for integration verification.

---

# 20. Important Existing Warning

The current verification script uses pandas with a `mysql.connector` DBAPI connection and produces this warning:

```text
UserWarning:
pandas only supports SQLAlchemy connectable ...
```

This is currently only a warning.

Do not redesign the database connection architecture solely because of this warning unless Chat 06 identifies a concrete need for SQLAlchemy.

---

# 21. What Chat 06 Must NOT Build

Do NOT build:

* SQL Analyst Agent
* LLM planner
* orchestrator
* root-cause agent
* critic agent
* visualization agent
* recommendation agent
* report composer
* FastAPI
* Streamlit
* Docker deployment

Those belong to later chats.

---

# 22. What Chat 06 Must NOT Change

Do not change:

* dataset
* MySQL schema
* semantic-layer KPI definitions
* financial formulas
* inventory equation
* business rules
* date semantics
* existing analytics-engine behavior
* project architecture

If a genuine conflict is discovered, stop and report it before changing the frozen architecture.

---

# 23. Required Chat 06 Workflow

Follow this sequence:

```text
Step 1
Review existing database + semantic layer
        ↓
Step 2
Design SQL tool contract
        ↓
Step 3
Implement safe SQL validation
        ↓
Step 4
Implement SQL execution
        ↓
Step 5
Implement schema inspection
        ↓
Step 6
Implement result normalization
        ↓
Step 7
Unit tests
        ↓
Step 8
Real MySQL integration tests
        ↓
Step 9
Security / safety verification
        ↓
Step 10
Final validation
        ↓
CHAT_07_HANDOFF.md
```

Do not skip directly to an LLM agent.

---

# 24. Definition of Done

Chat 06 is complete when:

```text
[ ] SQL tool contract defined
[ ] Read-only enforcement implemented
[ ] SQL validation implemented
[ ] Schema inspection implemented
[ ] SQL execution implemented
[ ] Structured results implemented
[ ] Fact-isolation safety considered
[ ] Unit tests pass
[ ] MySQL integration tests pass
[ ] Existing semantic rules remain unchanged
[ ] Existing analytics tests still pass
[ ] Final documentation created
[ ] CHAT_07_HANDOFF.md created
```

---

# 25. Final Principle

The project is being built as an **auditable agentic BI system**, not as an LLM chatbot that directly executes arbitrary SQL.

Therefore:

```text
Semantic Layer
      ↓
SQL Tool Layer
      ↓
Deterministic Analytics
      ↓
Validation
      ↓
Agents
```

The SQL tool layer must remain deterministic, constrained, testable, and explainable.

**Chat 06 should build on Chat 05, not redesign it.**
