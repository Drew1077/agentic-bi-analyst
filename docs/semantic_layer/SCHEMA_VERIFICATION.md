# Chat 04 — MySQL Schema Verification

## Source

Authoritative schema: Chat 03 `01_init.sql` (dataset v1.0).

## Result

**PASS** — the Chat 04 semantic layer's qualified table/column references were checked against the supplied schema.

- Expected tables: 10
- Tables found: 10
- Finalized semantic metrics checked: 15
- Supporting join/date references checked: yes
- MySQL schema modified: no

## Confirmed areas

### Sales / financials
`orders` provides `order_id`, `customer_id`, `store_id`, `order_date`, `order_status`, and `payment_status`. `order_items` provides `quantity`, `unit_price`, `unit_cost`, `discount_percent`, `gross_revenue`, `net_revenue`, `total_cost`, and `gross_profit`.

### Customers / dimensions
`customers` provides customer identity and segmentation fields, including `customer_segment`, `gender`, `region`, `acquisition_channel`, `preferred_device`, and `customer_status`.

### Returns / refunds
`returns` provides `return_date`, `return_quantity`, `refund_amount`, `return_status`, `return_reason`, and `condition`.

### Payments
`payments` provides `payment_date`, `payment_status`, `amount`, and `refund_amount`.

### Marketing
`marketing_spend` provides `date`, `channel`, `campaign_name`, `region`, `spend`, `impressions`, `clicks`, and `conversions`.

### Inventory
`inventory_snapshots` provides `snapshot_date`, `store_id`, `product_id`, `opening_stock`, `units_received`, `units_sold`, `units_returned`, `closing_stock`, `reorder_level`, and `stockout_flag`.

## Governance conclusion

Schema availability does not automatically define business semantics. Therefore candidate return/marketing KPIs remain outside the governed 15-metric catalog until their business definitions, filters, date semantics, and attribution rules are explicitly approved.

Order-status eligibility, payment-status eligibility, and return-adjusted revenue also remain unresolved semantic questions. The schema contains the relevant fields, but the schema alone does not specify which statuses should be included or how returns should alter revenue.
