# CHAT 03 HANDOFF — MySQL Schema + Database Setup + Loading Pipeline

## 1. Project Context

Project: Agentic BI Analyst

Domain: E-commerce / Retail Intelligence

This chat is responsible for Phase 1 — Data Foundation, specifically:
- MySQL schema design
- MySQL database setup
- CSV loading pipeline
- database constraints and indexes
- loading verification
- database-level data quality checks

Do NOT build agents, LLM orchestration, FastAPI, Streamlit UI, visualization agents, semantic layer, or analytics agents in this chat.

The authoritative project architecture remains in `PROJECT_HANDOFF.md`. Read it first and preserve its decisions.

---

## 2. What Chat 02 Completed

Chat 02 finalized:
- table-level data contracts
- column definitions
- data types at the dataset level
- PK/FK relationships
- table grains
- realistic value ranges
- deterministic synthetic data generation
- intentional business patterns
- data quality rules
- expected row counts
- sample-record strategy
- dataset generation pipeline

The generated dataset passed all validation checks.

### Frozen Dataset

Dataset version: `v1.0`
Seed: `20260915`
Date range: `2024-01-01` to `2026-08-31`

The dataset is now FROZEN.

Do NOT regenerate, alter, or redesign the generated CSV dataset unless a genuine schema/data issue requires an intentional dataset version change.

Generated files are in:

`data/generated/`

Files:

- `calendar.csv`
- `stores.csv`
- `products.csv`
- `customers.csv`
- `orders.csv`
- `order_items.csv`
- `payments.csv`
- `returns.csv`
- `marketing_spend.csv`
- `inventory_snapshots.csv`

Current frozen row counts:

| Table | Rows |
|---|---:|
| calendar | 974 |
| stores | 63 |
| products | 2,000 |
| customers | 20,000 |
| orders | 150,000 |
| order_items | 359,066 |
| payments | 155,412 |
| returns | 20,963 |
| marketing_spend | 21,392 |
| inventory_snapshots | 16,800,000 |

Validation status:

`[SUCCESS] All validation checks passed.`

Validator:

`scripts/validate_data.py`

Generator:

`scripts/generate_data.py`

---

## 3. Core Data Model

The project uses a MySQL database.

Core tables, in dependency order:

1. `calendar`
2. `stores`
3. `products`
4. `customers`
5. `orders`
6. `order_items`
7. `payments`
8. `returns`
9. `marketing_spend`
10. `inventory_snapshots`

### Relationships

- `customers.customer_id → orders.customer_id`
- `stores.store_id → orders.store_id`
- `orders.order_id → order_items.order_id`
- `products.product_id → order_items.product_id`
- `orders.order_id → payments.order_id`
- `orders.order_id → returns.order_id`
- `order_items.order_item_id → returns.order_item_id`
- `products.product_id → inventory_snapshots.product_id`
- `stores.store_id → inventory_snapshots.store_id`
- `calendar.date → orders.order_date`
- `calendar.date → marketing_spend.date`

Preserve these relationships.

---

## 4. Important Financial Contract

The `order_items` table is the primary analytical grain.

One row = one product line within an order.

The following formulas are authoritative:

`gross_revenue = quantity × unit_price`

`discount_amount = gross_revenue × discount_percent`

`net_revenue = gross_revenue − discount_amount`

`total_cost = quantity × unit_cost`

`gross_profit = net_revenue − total_cost`

Do not change these formulas.

---

## 5. Important Inventory Contract

The inventory equation is:

`closing_stock = opening_stock + units_received − units_sold + units_returned`

The generated dataset already satisfies this equation.

Do not alter inventory data during Chat 03.

---

## 6. Required Chat 03 Work

### A. MySQL database setup

Create/document:
- database name
- local MySQL connection configuration
- environment-variable based credentials
- safe `.env` usage
- database initialization procedure

Do not hard-code passwords or secrets.

Recommended environment variables:

- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_DATABASE`
- `MYSQL_USER`
- `MYSQL_PASSWORD`

### B. MySQL schema

Create SQL schema files under:

`sql/`

At minimum, provide a schema initialization script.

Use appropriate MySQL data types.

Define:
- primary keys
- foreign keys
- NOT NULL constraints where appropriate
- UNIQUE constraints where appropriate
- CHECK constraints where practical and compatible with the chosen MySQL version
- indexes for important joins and filtering

Do not create unnecessary schema complexity.

### C. Loading pipeline

Create/update:

`scripts/load_data.py`

The loader must:
- load the frozen CSVs from `data/generated/`
- respect dependency order
- handle dates/timestamps correctly
- load large `inventory_snapshots.csv` efficiently
- avoid loading the entire 16.8M-row inventory file into memory unnecessarily
- provide useful progress/logging
- fail clearly when loading fails
- not modify the source CSV files

Expected loading order should respect foreign keys.

### D. Database verification

Create an appropriate verification script if needed, for example:

`scripts/verify_database.py`

It should verify:
- all 10 tables exist
- row counts match the frozen dataset
- primary keys are unique
- foreign key relationships are valid
- important financial formulas remain valid after loading
- inventory equation remains valid after loading
- no unexpected NULLs in required columns

For very large tables, use efficient SQL queries rather than pulling all rows into Python unnecessarily.

### E. Indexing

Add indexes based on actual expected analytical/query usage.

At minimum consider:
- order dates
- customer IDs
- store IDs
- product IDs
- order-item foreign keys
- return foreign keys
- marketing dates
- inventory snapshot dates/product/store combinations

Do not blindly index every column.

### F. Documentation

Document:
- database setup
- schema initialization
- loading commands
- verification commands
- environment variables
- expected row counts
- any MySQL-specific decisions

---

## 7. Performance Requirements

The dataset contains 16.8 million inventory rows.

Treat this as a real engineering constraint.

The loading pipeline should:
- use chunked/batched loading
- avoid `pd.read_csv()` loading the entire inventory CSV into RAM
- use efficient MySQL bulk-loading or batched inserts where appropriate
- provide progress information
- avoid unnecessary transformations during loading

Do not reduce the inventory dataset simply to make loading easier.

---

## 8. Technology Constraints

Use the project's established stack:

- Python
- MySQL
- SQLAlchemy where appropriate
- Pandas only where appropriate for loading/transformation
- `.env` for configuration
- Git

Do not introduce a different database.

Do not switch back to PostgreSQL.

---

## 9. What Chat 03 Must NOT Do

Do NOT implement:

- LLM agents
- SQL Analyst Agent
- planner/orchestrator
- semantic KPI layer
- deterministic analytics engine
- insight/root-cause agent
- critic/validation agent
- visualization agent
- FastAPI
- Streamlit UI
- recommendation/report agent
- Docker deployment
- unrelated feature expansion

Those belong to later chats.

---

## 10. Important Rules

1. Read `PROJECT_HANDOFF.md` before making changes.
2. Treat the frozen CSV dataset as the source of truth.
3. Do not silently redesign the architecture.
4. Do not regenerate the dataset.
5. Do not change the business domain.
6. Do not change the 10-table model without documenting why.
7. Do not replace MySQL with PostgreSQL.
8. Keep secrets out of source code.
9. Make the database reproducible from the frozen CSVs.
10. Prefer simple, production-oriented implementation over unnecessary complexity.
11. Validate every database load.
12. If a genuine conflict is discovered, stop and explain it rather than silently changing the contract.

---

## 11. Definition of Done

Chat 03 is complete only when:

- [ ] MySQL database can be created successfully
- [ ] All 10 tables exist
- [ ] Schema matches the frozen data contracts
- [ ] PKs are correctly defined
- [ ] FKs are correctly defined
- [ ] Appropriate indexes exist
- [ ] Frozen CSVs load successfully
- [ ] 16.8M inventory rows can be loaded without requiring the entire CSV in RAM
- [ ] Database row counts match the frozen dataset
- [ ] Database verification passes
- [ ] Financial formulas remain consistent
- [ ] Inventory equation remains consistent
- [ ] Setup/load/verify documentation is complete
- [ ] No later-phase agents/features are implemented

---

## 12. Expected Deliverables

At the end of Chat 03, provide:

1. MySQL schema SQL file(s)
2. Database setup instructions
3. `scripts/load_data.py`
4. database verification script if needed
5. any required configuration/template files
6. documentation for setup/load/verify
7. test/verification results
8. list of important decisions
9. updated handoff for Chat 04

The final response must clearly state:

- what was implemented
- files created/modified
- database setup status
- loading status
- verification status
- any known limitations
- important decisions for Chat 04

---

## 13. Next Chat

After Chat 03 is complete:

Chat 04 = Semantic Layer + KPI Definitions + Business Rules

Chat 04 must receive an updated handoff containing the actual MySQL schema, table/column details, indexes, database setup status, and any decisions made during Chat 03.
