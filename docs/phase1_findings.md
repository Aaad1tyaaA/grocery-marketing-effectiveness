# Phase 1 findings

## What is complete

Eight full raw datasets, all-column source profiling, clean sales and promotion models, three dimensions, a campaign-recipient bridge, anomaly screening, exported diagnostics, and verification evidence. The derived model's six main table counts match the supplied guide. The working database is grocery_phase1.duckdb.

## Verified results

| Measure | Actual result |
|---|---:|
| Raw purchase lines | 1,469,307 |
| Clean purchase lines | 1,460,487 |
| Purchasing households | 2,469 |
| Baskets | 155,848 |
| Stores | 457 |
| Products appearing in purchases | 68,509 |
| Recorded sales, preserved after cleaning | $4,596,039.58 |
| Product dimension, including UNKNOWN additions | 92,348 |
| Promotion rows after consolidation | 20,927,744 |
| Conflicting promotion keys | 12,785 |
| Observed grocery purchase dates in local 2017 | 364 |
| Flagged dates / grocery baskets | 10 / 142 |
| Database checks | 24 passed |

## Findings that affect later analyses

1. **Purchases must not disappear when product metadata is missing.** Seventeen product IDs account for 4,836 lines and $172.57. They now have UNKNOWN dimension records.
2. **Promotion duplicates contain conflicting information.** All 12,785 extra rows belong to keys with different placement codes. Exposure flags preserve whether any row shows a display/mailer; MULTIPLE labels expose the ambiguity for placement-specific analysis.
3. **Quantity needs context.** There are 13,510 quantities above 100, with a maximum of 89,638. Review their departments before treating quantity as a count of grocery units. Forty-nine lines have positive sales but zero quantity, so unit-price calculations need an explicit eligibility rule.
4. **Metadata coverage is incomplete.** Only 801 purchasing households have demographics. There are also 16 coupon-product mapping rows without a product metadata match. Both facts are preserved and reported.
5. **Time windows matter.** The source timestamps span 2017-01-01 11:53:26 to 2018-01-01 04:01:20 UTC, with source weeks 1–53. Convert to local time before date-based analysis. Week 1 has one observed local date. Eight campaigns cross the calendar observation window.
6. **Missing dates are not explanations.** The local grocery purchase calendar has no records for 2017-12-25. That alone does not prove store closure. Anomaly flags are review prompts, not confirmed bad records or causal findings.

## Source missingness

Required modelling fields were non-null. These metadata columns contain missing values:

| Table | Column | Null rows |
|---|---|---:|
| demographics | home_ownership | 233 |
| demographics | marital_status | 137 |
| products | package_size | 30,586 |
| products | product_category | 540 |
| products | product_type | 528 |

All 44 source columns have row counts, missingness, cardinality, and types in profile_columns and its CSV export.

## Flagged daily sales

Grocery-only sales, calculated in local time. Scores compare each date with the median for its weekday, using median absolute deviation. Potential holiday explanations from the guide have not been independently verified here.

| Date | Robust z-score |
|---|---:|
| 2017-11-22 | +10.19 |
| 2017-12-23 | +9.21 |
| 2017-11-21 | +6.07 |
| 2017-07-04 | +6.06 |
| 2017-02-04 | +4.70 |
| 2017-12-22 | +4.65 |
| 2017-04-15 | +3.54 |
| 2017-11-04 | +3.31 |
| 2017-01-01 | -3.38 |
| 2017-11-25 | -4.14 |

The basket export flags 142 grocery baskets above the 99.9th percentile. Line-level records for the five highest flagged baskets are provided for inspection; flags do not automatically remove them.

## Verification and limits

- 24 checks cover source immutability, row and monetary reconciliation, dimension uniqueness, fact coverage, promotion grain, conflict accounting, discount formulas, local-time conversion, campaign dates, required-field missingness, and anomaly outputs.
- The synthetic model regression covers free purchases, unknown products, nullable product attributes, non-grocery classification, conflicting promotions, duplicate campaign recipients, and time conversion.
- The six reader regressions compare the compact reader with the standard reader on the six smaller R sources.
- DBeaver's native visual connection test remains unconfirmed. Later KPI/segmentation models, marketing estimates, Hillstrom analysis, Excel, Power BI, and deployment are not part of phase 1.
