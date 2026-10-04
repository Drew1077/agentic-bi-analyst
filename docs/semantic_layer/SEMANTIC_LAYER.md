# Semantic Layer — Chat 04

## Purpose

The semantic layer is the governed business-definition layer between MySQL and future analytics/agents.

It standardizes:
- KPI definitions
- dimensions
- date semantics
- business filters
- joins
- aggregation
- double-counting protection
- business terminology

## Authoritative contracts preserved

The financial formulas remain:
- `gross_revenue = quantity × unit_price`
- `discount_amount = gross_revenue × discount_percent`
- `net_revenue = gross_revenue − discount_amount`
- `total_cost = quantity × unit_cost`
- `gross_profit = net_revenue − total_cost`

Inventory remains:
- `closing_stock = opening_stock + units_received − units_sold + units_returned`

## Important semantic policy

The supplied authoritative handoffs do not establish which order statuses count toward revenue. Therefore Chat 04 does **not** silently exclude cancelled orders or any other order status.

The same principle applies to payment-status filtering and return-adjusted revenue: where the handoff does not establish a rule, the catalog records an explicit unresolved assumption instead of inventing one.

## Grain governance

- `orders`: one row per order
- `order_items`: one row per order line; primary analytical grain
- `payments`: one row per payment transaction
- `returns`: one row per return
- `marketing_spend`: one row per marketing activity
- `inventory_snapshots`: one row per store × product × snapshot date

Independent one-to-many fact tables must be pre-aggregated before being combined.

## Implementation note

The semantic layer has now been schema-verified against the supplied Chat 03 `01_init.sql`. The validator checks qualified table/column references used by metrics, joins, and date semantics across the 10 expected tables. Schema verification confirms column availability; it does not by itself establish unresolved business eligibility or attribution rules.

## Metrics deliberately not finalized

The following candidate metrics remain outside the finalized machine-readable KPI set. Their source columns are now confirmed by the schema, but their complete business definitions/eligibility or attribution semantics still require explicit governance:
- return quantity
- refund amount
- marketing spend
- impressions
- clicks
- conversions
- CTR
- conversion rate
- CPC
- CPA
- ROAS

This is intentional governance, not missing implementation. They may be added after their business definitions are explicitly approved and recorded in the semantic catalog.
