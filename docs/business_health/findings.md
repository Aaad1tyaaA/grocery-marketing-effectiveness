# Business health — Word guide Module 2

Completed Steps 1.2.1–1.2.4 using the verified grocery model. These are descriptive results, not estimates of what would happen if discounts were removed.

## Three findings

1. Comparable grocery weeks average **$80,287.48 sales**, **1,303 active households**, and **$29.67 average basket value**. Week 52 leads with **$103,168.27**; week 26 is lowest at **$69,610.66**. Use this baseline to investigate changes rather than compare partial week 1 against full weeks.
2. Average weekly retailer-funded discount depth is **15.77%**. Its correlation with weekly sales is **-0.125**. The weak weekly association does not establish whether discounts increase sales; promotion-level and campaign analyses are still needed.
3. **122 categories** meet the $10,000 sales floor. **INFANT FORMULA** has the highest shelf-value-weighted share sold on discount at **89.2%**. This identifies a category for closer margin and promotion analysis; it does not measure sales that would be lost without discounts.

## Scope and reconciliation

- Weekly trends use source weeks **2–53**, excluding partial week 1: **$4,174,948.79** sales over 52 weeks.
- Week labels are the actual Monday calendar starts. The first recorded purchase date is exported separately; week 53 starts 25 December even though its first observed purchase is 26 December.
- Annual/category analysis includes all source weeks: **$4,185,055.64** sales. Partial week 1 contributes **$10,106.85**, explaining the difference.
- As in the guide, the grocery filter excludes explicitly flagged non-grocery products. It still contains **$172.57** of UNKNOWN-product sales; their actual categories are unknown.
- Manufacturer coupon amounts are excluded from retailer-funded discount cost.
- Category discount share weights shelf value, not units or purchase lines. Categories below $10,000 are excluded only from the ranking.
- Ratios have exported base amounts so Power BI can recompute weighted totals. Do not sum weekly household counts to report annual distinct households or average category percentages without weighting.
- The supplied guide rounds category sales to whole dollars and category ratios to three decimals. These outputs retain cents and more ratio precision; the underlying definitions and sales floor are the same.
- **11 business-health checks passed**, plus source fingerprint and clean-model reconciliation checks. No existing database was modified.

## Files to inspect

`exports/business_health/weekly_kpis.csv`, `category_discount.csv`, `business_health_summary.csv`, and `business_health_checks.csv`; `charts/weekly_health.png`; `charts/category_discount_dependency.png`; `02_business_health.ipynb`; and `sql/02_health.sql`.

Next in the Word guide: Module 3, customer value and segments. The CSVs are also ready to import into Power BI. The final dashboard remains a later guide step.
