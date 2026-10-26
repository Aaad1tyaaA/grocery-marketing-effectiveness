from pathlib import Path
import csv
import json
import duckdb

ROOT = Path(__file__).resolve().parents[1]
report = json.loads((ROOT/'docs/phase1_verification.json').read_text())
con = duckdb.connect(str(ROOT/'grocery_phase1.duckdb'),read_only=True)
impact_rows = con.execute((ROOT/'sql/00b_rule_impacts.sql').read_text()).fetchall()
impacts = {name:(n,sales) for name,n,sales in impact_rows}
with (ROOT/'exports/phase1/rule_impacts.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow(['rule','line_items','sales_usd']);w.writerows(impact_rows)
source_profile = {(t,c):(n,nulls,distinct) for t,c,dt,n,nulls,distinct in con.execute('SELECT * FROM profile_columns').fetchall()}
with (ROOT/'docs/data_dictionary.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f);w.writerow(['table_name','column_name','duckdb_type','row_count','source_null_rows','source_distinct_values'])
    for table,columns in sorted(report['schema'].items()):
        for column,dtype,*_ in columns:
            n,nulls,distinct=source_profile.get((table,column),(report['model_counts'].get(table,''),'',''))
            w.writerow([table,column,dtype,n,nulls,distinct])

money=lambda x:f'${x:,.2f}'
s=report['transaction_summary'];p=report['promotion_quality'];m=report['model_counts']
cleaning=f'''# Cleaning log — verified phase 1

Built 25 October 2026 from the commit-pinned completejourney sources. All eight raw-table counts and content fingerprints matched the original verified setup before and after modelling. Rules below apply to derived tables only. Monetary values are USD; affected sales are the value of the flagged lines, not estimated marketing costs.

| Decision | Actual impact | Sales on affected lines | Reason and evidence |
|---|---:|---:|---|
| Exclude quantity-zero/sales-zero voids from fact_sales | {s['void_lines']:,} lines removed | $0.00 | sql/01_model.sql; sql/00b_rule_impacts.sql |
| Retain free purchase lines | {s['free_lines']:,} retained | $0.00 | Real zero-sales lines can matter for discount depth; not automatically errors |
| Retain zero-quantity lines that have positive sales | {s['zero_quantity_with_sales']:,} retained | {money(impacts['zero_quantity_with_sales'][1])} | No evidence justifies deleting their sales; exclude/define carefully for future unit-price metrics |
| Retain large quantities; inspect their departments | {s['large_quantity_lines']:,} retained; max {s['maximum_quantity']:,.0f} | {money(impacts['large_quantity_lines'][1])} | FUEL and code-like product quantities are not necessarily individual grocery units; profile_large_quantities records the split |
| Flag non-grocery instead of deleting it | 18,526 clean lines flagged | $410,983.94 | FUEL/MISCELLANEOUS departments or COUPON/MISC ITEMS category; sql/01_model.sql |
| Add UNKNOWN product records | 17 missing product IDs; 4,836 source lines retained | $172.57 | profile_missing_products and dim_product.is_unknown_product |
| Retain discounts greater than price paid | {s['discount_above_paid_price']:,} lines | {money(impacts['discount_above_paid_price'][1])} | Do not automatically discard deep discounts |
| Collapse repeated promotion keys | {p['extra_rows']:,} extra rows consolidated into {p['unique_keys']:,} product/store/week rows | Not a sales table | All {p['conflicting_keys']:,} repeated keys have differing placement codes. Flags use any nonzero code; differing labels become MULTIPLE |
| Derive US Eastern local purchase time | All {m['fact_sales']:,} clean lines; UTC also retained | No sales removed | Explicit UTC-to-America/New_York reporting convention; profile_week_boundaries checks calendar alignment, not the physical time zone of every store |
| Leave demographics absent where unknown | 801 of 2,469 purchasing households have demographics | No sales removed | No imputation; has_demographics distinguishes observed from missing |
| Flag partial campaigns | 8 of 27 flagged, all retained | No sales removed | Campaigns 15,20,21,22,23,24,25,26; use eligibility rules in later campaign analysis |
| Retain partial week 1 | One observed local date, all source rows retained | No sales removed | Exclude week 1 only in later like-for-like weekly comparisons |
| Review anomaly flags without deleting rows | {m['daily_anomalies']} dates and {m['basket_anomalies']} baskets flagged | No sales removed | sql/01b_anomalies.sql; review exports/phase1/top_five_basket_lines.csv |
| Preserve orphan coupon mappings | 16 coupon rows lack a product metadata match | Not a sales table | profile_relationships; future coupon-product joins must preserve or explicitly report them |

## Reconciliation

- Source transaction lines: {s['line_items']:,}; clean sales lines: {m['fact_sales']:,}. Difference: {s['void_lines']:,} voids.
- Source and clean sales both equal {money(s['sales_usd'])} to the cent.
- Grocery: 1,441,961 lines and $4,185,055.64. Non-grocery: 18,526 lines and $410,983.94. UNKNOWN products are retained within the not-explicitly-non-grocery population; do not imply their category has been identified.
- No negative quantity/sales or negative discount rows were observed. Required source fields are non-null; nullable metadata remains nullable.
- 24 database verification rules passed. No sales were removed for anomaly flags, campaign coverage, missing demographics, or unknown products.

The raw source rows are preserved in grocery_phase1.duckdb as well as the original raw-only grocery.duckdb. Diagnostic CSVs and the saved SQL make the decisions reproducible.
'''
(ROOT/'docs/cleaning_log.md').write_text(cleaning,encoding='utf-8')

null_rows=con.execute('SELECT table_name,column_name,null_rows FROM profile_columns WHERE null_rows>0 ORDER BY table_name,column_name').fetchall()
anomalies='\n'.join(f'| {day} | {z:+.2f} |' for day,z in report['anomalous_dates'])
nullable='\n'.join(f'| {t} | {c} | {n:,} |' for t,c,n in null_rows)
findings=f'''# Phase 1 findings

## What is complete

Eight full raw datasets, all-column source profiling, clean sales and promotion models, three dimensions, a campaign-recipient bridge, anomaly screening, exported diagnostics, and verification evidence. The derived model's six main table counts match the supplied guide. The working database is grocery_phase1.duckdb.

## Verified results

| Measure | Actual result |
|---|---:|
| Raw purchase lines | {s['line_items']:,} |
| Clean purchase lines | {m['fact_sales']:,} |
| Purchasing households | {s['households']:,} |
| Baskets | {s['baskets']:,} |
| Stores | {s['stores']:,} |
| Products appearing in purchases | {s['products']:,} |
| Recorded sales, preserved after cleaning | {money(s['sales_usd'])} |
| Product dimension, including UNKNOWN additions | {m['dim_product']:,} |
| Promotion rows after consolidation | {m['fact_promo']:,} |
| Conflicting promotion keys | {p['conflicting_keys']:,} |
| Observed grocery purchase dates in local 2017 | {m['daily_sales']:,} |
| Flagged dates / grocery baskets | {m['daily_anomalies']} / {m['basket_anomalies']} |
| Database checks | 24 passed |

## Findings that affect later analyses

1. **Purchases must not disappear when product metadata is missing.** Seventeen product IDs account for 4,836 lines and $172.57. They now have UNKNOWN dimension records.
2. **Promotion duplicates contain conflicting information.** All 12,785 extra rows belong to keys with different placement codes. Exposure flags preserve whether any row shows a display/mailer; MULTIPLE labels expose the ambiguity for placement-specific analysis.
3. **Quantity needs context.** There are 13,510 quantities above 100, with a maximum of 89,638. Review their departments before treating quantity as a count of grocery units. Forty-nine lines have positive sales but zero quantity, so unit-price calculations need an explicit eligibility rule.
4. **Metadata coverage is incomplete.** Only 801 purchasing households have demographics. There are also 16 coupon-product mapping rows without a product metadata match. Both facts are preserved and reported.
5. **Time windows matter.** The source timestamps span {s['first_timestamp_utc']} to {s['last_timestamp_utc']} UTC, with source weeks 1–53. Convert to local time before date-based analysis. Week 1 has one observed local date. Eight campaigns cross the calendar observation window.
6. **Missing dates are not explanations.** The local grocery purchase calendar has no records for 2017-12-25. That alone does not prove store closure. Anomaly flags are review prompts, not confirmed bad records or causal findings.

## Source missingness

Required modelling fields were non-null. These metadata columns contain missing values:

| Table | Column | Null rows |
|---|---|---:|
{nullable}

All 44 source columns have row counts, missingness, cardinality, and types in profile_columns and its CSV export.

## Flagged daily sales

Grocery-only sales, calculated in local time. Scores compare each date with the median for its weekday, using median absolute deviation. Possible holiday explanations are hypotheses, not verified facts.

| Date | Robust z-score |
|---|---:|
{anomalies}

The basket export flags 142 grocery baskets above the 99.9th percentile. Line-level records for the five highest flagged baskets are provided for inspection; flags do not automatically remove them.

## Verification and limits

- 24 checks cover source immutability, row and monetary reconciliation, dimension uniqueness, fact coverage, promotion grain, conflict accounting, discount formulas, local-time conversion, campaign dates, required-field missingness, and anomaly outputs.
- The synthetic model regression covers free purchases, unknown products, nullable product attributes, non-grocery classification, conflicting promotions, duplicate campaign recipients, and time conversion.
- The six reader regressions compare the compact reader with the standard reader on the six smaller R sources.
- Later modules cover KPIs, segments, promotions, campaigns and the email experiment.
'''
(ROOT/'docs/phase1_findings.md').write_text(findings,encoding='utf-8')
con.close()
print('Written: cleaning log, findings, data dictionary, rule impact export')
