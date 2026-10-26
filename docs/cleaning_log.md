# Cleaning log — verified phase 1

Built 25 October 2026 from the commit-pinned completejourney sources. All eight raw-table counts and content fingerprints matched the original verified setup before and after modelling. Rules below apply to derived tables only. Monetary values are USD; affected sales are the value of the flagged lines, not estimated marketing costs.

| Decision | Actual impact | Sales on affected lines | Reason and evidence |
|---|---:|---:|---|
| Exclude quantity-zero/sales-zero voids from fact_sales | 8,820 lines removed | $0.00 | sql/01_model.sql; sql/00b_rule_impacts.sql |
| Retain free purchase lines | 2,406 retained | $0.00 | Real zero-sales lines can matter for discount depth; not automatically errors |
| Retain zero-quantity lines that have positive sales | 49 retained | $12.52 | No evidence justifies deleting their sales; exclude/define carefully for future unit-price metrics |
| Retain large quantities; inspect their departments | 13,510 retained; max 89,638 | $364,119.46 | FUEL and code-like product quantities are not necessarily individual grocery units; profile_large_quantities records the split |
| Flag non-grocery instead of deleting it | 18,526 clean lines flagged | $410,983.94 | FUEL/MISCELLANEOUS departments or COUPON/MISC ITEMS category; sql/01_model.sql |
| Add UNKNOWN product records | 17 missing product IDs; 4,836 source lines retained | $172.57 | profile_missing_products and dim_product.is_unknown_product |
| Retain discounts greater than price paid | 37,634 lines | $80,407.91 | Do not automatically discard deep discounts |
| Collapse repeated promotion keys | 12,785 extra rows consolidated into 20,927,744 product/store/week rows | Not a sales table | All 12,785 repeated keys have differing placement codes. Flags use any nonzero code; differing labels become MULTIPLE |
| Derive US Eastern local purchase time | All 1,460,487 clean lines; UTC also retained | No sales removed | Explicit UTC-to-America/New_York reporting convention; profile_week_boundaries checks calendar alignment, not the physical time zone of every store |
| Leave demographics absent where unknown | 801 of 2,469 purchasing households have demographics | No sales removed | No imputation; has_demographics distinguishes observed from missing |
| Flag partial campaigns | 8 of 27 flagged, all retained | No sales removed | Campaigns 15,20,21,22,23,24,25,26; use eligibility rules in later campaign analysis |
| Retain partial week 1 | One observed local date, all source rows retained | No sales removed | Exclude week 1 only in later like-for-like weekly comparisons |
| Review anomaly flags without deleting rows | 10 dates and 142 baskets flagged | No sales removed | sql/01b_anomalies.sql; review exports/phase1/top_five_basket_lines.csv |
| Preserve orphan coupon mappings | 16 coupon rows lack a product metadata match | Not a sales table | profile_relationships; future coupon-product joins must preserve or explicitly report them |

## Reconciliation

- Source transaction lines: 1,469,307; clean sales lines: 1,460,487. Difference: 8,820 voids.
- Source and clean sales both equal $4,596,039.58 to the cent.
- Grocery: 1,441,961 lines and $4,185,055.64. Non-grocery: 18,526 lines and $410,983.94. UNKNOWN products are retained within the not-explicitly-non-grocery population; do not imply their category has been identified.
- No negative quantity/sales or negative discount rows were observed. Required source fields are non-null; nullable metadata remains nullable.
- 24 database verification rules passed. No sales were removed for anomaly flags, campaign coverage, missing demographics, or unknown products.

The raw source rows are preserved in grocery_phase1.duckdb as well as the original raw-only grocery.duckdb. Diagnostic CSVs and the saved SQL make the decisions reproducible.
