# Metric glossary

All monetary values are source USD. Definitions cover completed Modules 1–5. Campaign results are observational; no proven causal marketing effect or profit has been established.

| Metric | Definition |
|---|---|
| Purchase line | One product line in a basket. `count(*)` on fact_sales is not the number of shopping trips. |
| Sales | `sum(sales_value)`. Preserve the source definition and do not subtract discounts a second time. |
| Basket / shopping trip | One distinct `basket_id`; confirm its household/store consistency before changing the grain. |
| Average basket value | `sum(sales_value) / nullif(count(DISTINCT basket_id),0)` with the same filters in numerator and denominator. |
| Active household | A distinct household purchasing in the selected period. |
| Shelf value | `sales_value + retail_disc + coupon_match_disc`, following the supplied guide. |
| Retailer-funded discount | `retail_disc + coupon_match_disc`. Manufacturer-funded `coupon_disc` is excluded. |
| Discount depth | `sum(retailer_funded_disc) / nullif(sum(shelf_value),0)`. This is a ratio of totals, not an average of line ratios. |
| Free line | `sales_value=0 AND quantity>0`. Retained in the model. |
| Void line | `quantity=0 AND sales_value=0`. Excluded from fact_sales only. |
| Non-grocery | Department is FUEL or MISCELLANEOUS, or product category is COUPON/MISC ITEMS. Retained and flagged. |
| Unknown product | A transaction product absent from products. Added to dim_product with department UNKNOWN; its sales are retained. |
| Store week | Source week 1–53. Keep this column; do not replace it with ISO week numbers. Exclude partial week 1 in later comparable-week trends. |
| Local purchase time | Source UTC timestamp converted to America/New_York, including daylight saving. The original UTC timestamp is also retained. |
| On display / in mailer | At least one source row for that product/store/week has a nonzero placement code. These flags are associations, not randomized treatment assignments. |
| Multiple placement codes | More than one distinct display or mailer code at the product/store/week grain. Reported as MULTIPLE rather than choosing an arbitrary source code. |
| Partially observed campaign | Campaign starts before 2017-01-01 or ends after 2017-12-31. Flagged, not removed. Later campaign analysis must also check usable pre/post windows and overlap. |
| Daily anomaly | Grocery daily sales differ by more than 3 robust standard deviations from their weekday median; scale is `1.4826 * median absolute deviation`. A zero scale produces no score. |
| Basket anomaly | Grocery basket value strictly above the observed 99.9th percentile. A review flag, not proof of bad data. |

Missing demographics mean unknown attributes, not zero income or a particular household type. Customer and promotion definitions are below. Campaign definitions follow below; the final ROI model remains Module 7.

## Module 3 customer measures

| Metric | Definition |
|---|---|
| Annual customer spend | Grocery-filtered clean sales summed by household, including partial week 1. |
| Recency | Days from the last observed grocery purchase to 2017-12-31. |
| Lapsed | Recency greater than 60 days; this classification takes precedence over other segment rules. |
| Champions | Non-lapsed households meeting both the 75th-percentile spend and basket thresholds. |
| Loyal regulars | Remaining non-lapsed households at or above median spend. |
| Light regulars | Remaining non-lapsed households with at least 12 baskets. |
| Occasional | Remaining non-lapsed households. |
| Deal-driven flag | Discount share at or above its 75th percentile, using the guide's three-decimal rounded household discount shares. Ties can include more than 25%. |
| H1 / H2 spend | Source weeks 2-27 / 28-53; excludes partial week 1. |
| Growing / Declining | At least 20% higher / lower H2 spend relative to H1, after separately handling zero-spend periods. |
| New in H2 / Gone in H2 | Guide labels for zero positive spend in H1 / H2. These are observed patterns, not proven acquisition/churn. |
| Cohort | First observed purchase month in the clean all-purchase panel; not verified acquisition month. |
| Monthly activity retention | Distinct households purchasing in a cohort-month divided by initial cohort size. Includes returning households after missed months. Elapsed inactive months are zero; future months are unobserved. |

Segments use 2,467 grocery households. Cohorts follow the guide's all-purchase scope of 2,469 households. Income associations apply only to the demographic subset; they are not causal effects or population-wide estimates.

## Module 4 promotion measures

| Metric | Definition |
|---|---|
| Eligible product/store pair | Recorded grocery panel purchases in at least eight source weeks, using weeks 2-53. |
| Pair-week panel | Every eligible pair crossed with 52 weeks; absent panel purchases are zero. This does not measure all store sales. |
| Promotion flag | Recorded nonzero display and/or mailer code. Primary guide-style flags treat absent promotion records as no recorded exposure, not proven no price discount. |
| Baseline units | Each pair's average panel units in weeks with no recorded promotion, excluding the week immediately after a promotion; requires at least four weeks. |
| Unit lift index | Sum of observed panel units divided by the sum of pair-specific baseline units for the same condition's pair-weeks. An index of 3.14 is 214% above baseline; it is not a causal estimate. |
| Post-promotion week | A non-promoted week immediately after a promoted week. Two consecutive prior promoted weeks define the multi-week category; left-boundary history is incomplete and reported. |
| Positive-baseline sensitivity | Same index excluding pairs whose baseline average is zero. Separate scope; do not mix its totals with the primary result. |
| Observed-metadata-only sensitivity | Attempts to require explicit current/prior promotion metadata. Not estimable on the actual data because explicitly observed eligible records contain no nonpromotion baselines. |

Placement labels preserve conflicting codes as MULTIPLE. Groups below 100 pair-weeks are flagged for descriptive presentation, not declared statistically insignificant. Prices, seasonality, selection, and availability remain uncontrolled.

## Calendar and campaign measures, audited Module 5

| Metric | Definition |
|---|---|
| Week start | Monday calendar boundary, 2017-01-02 + 7 × (source week − 2), for weeks 2–53. Separate from first observed purchase date. |
| Household-week spend | Grocery sales per household per source week, with absent panel purchases filled to zero; 2,467 × 52 rows. |
| Naive campaign gap | Targeted minus current-campaign-untargeted mean weekly during-period spend. Not incremental lift. |
| Unmatched DiD | Difference between groups in during-period minus preceding-eight-week mean spend. |
| Pre-period matched DiD | Same change, restricted to shared spend/activity strata defined in the pre-period; control weights balance treated stratum shares. |
| Earlier-window matched DiD | Strata use weeks 9–16 before the campaign; changes compare weeks 1–8 before with campaign weeks. |
| Supported sample | Households in strata containing both groups. The target count can be below the campaign's full assigned audience. |
| Effective control size | (sum of control weights)² / sum of squared control weights; accounts for concentration of weights, not proof of sufficient causal information. |
| HC1 interval | Household-level weighted comparison with heteroskedasticity-robust HC1 variance and normal 95% critical value, conditional on matching weights. |
| Fake-start placebo | The same analysis shifted eight weeks earlier. Campaign 8's earlier-match placebo has insufficient observed history. |
| Pre-period contrast | Last four minus first four pre-campaign weeks, on the real earlier-matched sample and weights. Failure to reject zero does not establish parallel trends. |
| Whole-week campaign window | Includes every day in overlapping source weeks. Campaign 13 includes one pre-campaign Monday; the audit table exposes the approximation. |
| Coupon amount proxy | Global mean positive manufacturer-coupon discount per purchase line. Not necessarily a coupon's face value, a campaign-specific redemption average, or retailer cost. |
| ROI input | Observed campaign duration/audience/redemptions plus uncertain spend estimates. Margin, funding share and distribution costs remain assumptions, not observed campaign profit. |

Weekly household and category buyer counts are not additive. Customer cohorts use all 2,469 purchasing households while grocery customer and campaign panels use 2,467. Promotion ratios must use compatible scopes and the ratio of base totals, not an average of indices.

## Module 6 randomized email measures

| Metric | Definition |
|---|---|
| Assigned-customer outcome | Two-week outcome across everyone assigned to that arm, including zeros. Does not condition on email opening, visiting or buying. |
| Incremental email spend | Email-arm mean spend minus no-email mean spend, USD per assigned customer over two weeks. A separate retailer experiment; not a grocery campaign ROI input. |
| Percentage-point change | Binary rate difference multiplied by 100. A 0.01 rate difference is 1 pp, not a 1% relative change. |
| Primary inference | Six email-versus-control Welch tests adjusted together with Holm; 2,000-resample empirical bootstrap intervals remain pointwise 95%. Three direct version comparisons form a separate family. |
| Sample-ratio mismatch | Chi-square comparison of arm counts to equal thirds. Warning threshold .01; absence of a warning does not prove randomization integrity. |
| Merchandise buyer type | Historical purchase of men's merchandise, women's merchandise or both; not customer sex or gender. |
| Frozen cell policy | Thirty observed pre-treatment cells ranked by the better email spend lift in the training half only. Holdout outcomes and assignments do not choose the rule. |
| Exact capacity list | Seeded outcome-free boundary tie breaks fill exactly 10,000 targets and 10,000 suppressed with no overlap. Source_row is a synthetic row position, not a real contact ID. |
| Whole-cell policy | Word guide rule selecting complete cells without exceeding 10,000; seed 7 selects 8,486 targets. Retained separately from exact-capacity selection. |
| Held-out version-policy value | Horvitz–Thompson estimate using the trained version for each cell and known 1/3 random assignment. The learned-minus-always-Men's comparison is paired. Intervals condition on the fitted rule. |
| Targeting sensitivity | Seed 8 reuses the same experiment in an overlapping split and fails to confirm a strong targeting advantage. A sensitivity check, not independent replication or an opportunity to pick the most favorable seed. |
| Suppression | Forced capacity ranking based on lowest training scores; not established negative email effects, net losses or an unsubscribe recommendation. |

Exploratory segment tests share a 126-test Holm family; held-out fixed-arm contrasts share a 72-test family. Their intervals remain pointwise. Different within-group significance does not test whether two subgroup effects differ. Net email profit is unknown without costs and margin.
