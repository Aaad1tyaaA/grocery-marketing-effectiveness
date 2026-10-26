# Phase 1 model

The output is **grocery_phase1.duckdb**. It contains the same eight verified raw tables, plus the following derived tables. The original grocery.duckdb was open in DBeaver and was not modified.

| Table | Grain | Purpose |
|---|---|---|
| fact_sales | One retained source purchase line | Removes only quantity-zero/sales-zero voids; adds local time, discount metrics, product flags |
| fact_promo | product_id + store_id + week | Collapses repeated promotion keys; retains exposure flags, source row counts, and explicit code conflicts |
| dim_product | product_id | Product metadata plus missing transaction products labelled UNKNOWN |
| dim_household | household_id | Every purchasing household; optional demographics and distinct campaign count |
| dim_campaign | campaign_id | Campaign metadata and partial-observation flag |
| bridge_household_campaign | household_id + campaign_id | Distinct campaign recipients; many-to-many membership |
| daily_sales | Local date with observed grocery purchases | Base for weekday-adjusted anomaly screening |
| daily_anomalies | Flagged local date | Robust z-scores exceeding 3 in magnitude |
| basket_anomalies | basket_id + household_id | Grocery baskets above the 99.9th percentile |
| profile_* | Named diagnostic result | Source missingness, cardinality, relationships, boundaries, and other findings |
| phase1_checks | One verification rule | All rows must have passed=true |

## Join rules

- Join fact_sales to dim_product on product_id and to dim_household on household_id. These are many-to-one joins.
- Join fact_sales to fact_promo on **all three** of product_id, store_id, week. Do not join on product alone. A missing promotion row is not automatically evidence of no exposure.
- Join the recipient bridge to dim_campaign on campaign_id. Joining every purchase directly to campaign recipients multiplies purchases when households receive multiple campaigns. Later analyses must assign time windows and define eligible comparison groups first.
- Coupons map coupon UPCs to eligible products and campaigns. One coupon can apply to multiple products; raw joins can multiply redemptions and purchases.
- No physical primary/foreign-key constraints are declared. Uniqueness and coverage are checked explicitly in the verification SQL.

## Differences from the supplied model

The model keeps the same core names and formulas. It also retains source UTC time, an explicit unknown-product flag, and a distinct recipient bridge. Nullable product attributes do not produce a null non-grocery flag. Promotion code conflicts use MULTIPLE instead of independently selecting maximum codes, which could imply a display/mailer combination never observed together. Later placement-specific analyses must handle MULTIPLE separately.

The guide's statement that a missing Christmas date means stores were closed is not established by purchase records alone. Missing dates and anomaly flags are reported as observed facts; their causes require separate evidence.

## Files and rebuild order

`scripts/build_phase1.py` builds a fresh database from verified Parquet, runs the following SQL in a transaction, verifies it, exports diagnostics, and reopens the completed database. It refuses to overwrite existing phase-1 database files.

1. sql/00_profile.sql
2. sql/00a_profile_columns.sql (generated from the source schemas)
3. sql/01_model.sql
4. sql/01b_anomalies.sql
5. sql/01c_verify.sql

The runner additionally checks source fingerprints before and after modelling and required-field missingness. To rerun SQL manually, disconnect Python, use the phase-1 connection, run BEGIN, execute the files in order, inspect phase1_checks, then COMMIT only if all rows pass. Use ROLLBACK if a check fails.
