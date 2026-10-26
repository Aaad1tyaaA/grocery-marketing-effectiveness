# Campaign incrementality

Completed **Steps 1.5.1–1.5.5** with verified Complete Journey Parquet sources. The analysis uses grocery household-week spend, campaigns 8, 13 and 18, four comparison designs, placebo checks, an overlap audit, and the later ROI inputs.

## What the analysis says

The targeted households spend about **$32–$35 more per week** than the untargeted households during the campaigns. That gap mostly predates the campaign: the unmatched before/after differences are small. Matching on the immediate pre-period then produces estimates around **+$3 to +$7 per household per week**, but a fake campaign start eight weeks earlier produces a positive **+$5.68** for Campaign 8 (95% interval **+$2.13 to +$9.24**, Holm-adjusted p **0.009**). That placebo weakens the causal interpretation of the attractive pre-period-matched estimate.

The earlier-window matched estimates are **+$0.80** for Campaign 8, **+$0.39** for Campaign 13 and **+$2.95** for Campaign 18. Every 95% interval includes zero. These are the most defensible observational estimates in this analysis, and they do not distinguish a small lift from no lift. The fake-start checks for Campaigns 13 and 18 include zero; Campaign 8's earlier-window placebo cannot be estimated because the required history falls outside the dataset.

## The four designs, dollars per household per week

The table below shows the common-support comparison. Intervals are pointwise 95% HC1 intervals, treating the estimated matching weights as fixed.

| Campaign | Naive gap | Unmatched DiD | Matched on pre-period | Matched on earlier weeks | Pre-match placebo | Earlier-match placebo |
|---|---:|---:|---:|---:|---:|---:|
| 8 | +32.10 (+29.24 to +34.96) | -2.24 (-4.10 to -0.38) | +3.10 (-0.06 to +6.26) | +0.80 (-2.71 to +4.31) | +5.68 (+2.13 to +9.24; Holm p=0.009) | Not estimable: insufficient earlier history |
| 13 | +34.31 (+31.49 to +37.13) | -0.20 (-2.00 to +1.59) | +6.63 (+3.28 to +9.99) | +0.39 (-3.25 to +4.04) | +3.67 (-0.79 to +8.13; Holm p=0.320) | -3.50 (-8.75 to +1.75; Holm p=0.384) |
| 18 | +34.77 (+31.81 to +37.73) | +1.68 (-0.01 to +3.38) | +6.27 (+3.07 to +9.48) | +2.95 (-0.74 to +6.64) | +4.85 (+0.73 to +8.96; Holm p=0.084) | -1.51 (-5.71 to +2.69; Holm p=0.481) |

The naive and unmatched comparisons use the same common-support households shown for the pre-period match, to make the sequence comparable. The exported `campaign_estimates.csv` also includes full-sample naive and unmatched estimates. Matching retains only households in strata containing both targeted and untargeted households; the campaign-specific counts are in the CSVs and database.

## Pre-period contrasts, weights, and week boundaries

Using the actual earlier-matched sample and weights, compare the last four pre-campaign weeks with the first four. These contrasts are a falsification check separate from the fake-start placebos; a wide interval that includes zero does not establish parallel trends.

| Campaign | Pre-period change in targeted/control gap ($/week) | 95% HC1 interval | Holm p across three checks |
|---|---:|---:|---:|
| 8 | -2.20 | -6.97 to +2.58 | 0.735 |
| 13 | +3.94 | -2.27 to +10.15 | 0.640 |
| 18 | +1.32 | -3.41 to +6.05 | 0.735 |

| Campaign | Supported targeted households | Supported controls | Effective control sample size | Largest control weight |
|---|---:|---:|---:|---:|
| 8 | 1,073 | 1,252 | 320.5 | 11.67 |
| 13 | 1,076 | 1,376 | 289.0 | 11.28 |
| 18 | 1,131 | 1,331 | 260.8 | 24.71 |

Weights are positive and stratum shares reconcile, but a few controls carry substantial weight. The reported HC1 intervals condition on these weights; they are not a full uncertainty analysis of selecting/matching households. Equal activity values are split by household ordering in the guide-compatible method. The tie-preserving sensitivity keeps them together and is exported separately.

The analysis uses whole source weeks. **Campaign 13 actually starts Tuesday 8 August, while modeled week 33 starts Monday 7 August**, so its during-period includes one pre-campaign day (49 modeled days versus 48 calendar campaign days). Campaigns 8 and 18 align with week boundaries. `campaign_window_audit.csv` reports the exact dates, extra days, and grocery sales on those off-date days across all households. Those amounts are not campaign effects. An exact-day analysis would be needed to remove this approximation; the primary values retain the guide's weekly definition.

## Campaigns and audience

There are **27 campaigns**. The available source data covers **2,467 grocery households**; **1,559** received at least one campaign and **908** received none. Type A has four campaigns: Campaign 27 begins too early to supply the guide's eight-week pre-period; Campaigns 8, 13 and 18 are the large campaigns used for the incrementality analysis. Type B and C audiences are much smaller. See `campaign_overview.csv` for each audience and redemption count.

The 910 never-assigned households use all 2,469 purchasing households. The grocery cohort excludes two non-grocery-only, never-assigned households, leaving 908. This denominator difference is intentional.

Campaign assignment overlaps are substantial inside these analysis windows: **1,076**, **1,077** and **1,133** households were assigned to the respective campaign, and many were also assigned to other campaigns during the pre-period or campaign window. The overlap audit lists treated and control overlap counts. Excluding other-campaign recipients is exported as a sensitivity; its smaller samples still have intervals spanning zero.

## What to use in the ROI model later

Campaign 18 lasted **8 weeks**, targeted **1,133 households**, and recorded **653 coupon redemptions by 214 households**. Positive coupon-discount purchase lines average **$1.05** (median **$0.75**). These are data inputs; manufacturer-funded coupon value is not necessarily retailer cost. The data contains no print or distribution costs. `campaign_roi_inputs.csv` keeps costs marked unobserved and does not validate extrapolation from the matched sample to every recipient.

## Limits and recommendation

Campaign targeting used prior purchase behavior, so the randomized-treatment assumption does not apply. Earlier-week matching and placebo checks help reveal selection and regression-to-the-mean problems, but they do not eliminate seasonal trends, concurrent campaign exposure, or other unmeasured differences. The household-level HC1 intervals are conditional on the matching weights and do not include uncertainty from selecting strata. This analysis is not proof that campaigns caused incremental sales or profit.

For a business decision, run a randomized household holdout for the next campaign and track incremental net revenue, retailer-funded discounts, and delivery costs. The later Excel model can calculate break-even lift under explicit margin and cost assumptions; it must label those assumptions separately from observed data.

**Verification:** 25 campaign checks passed. The executed notebook presents the workflow and outputs. See `verification.json` for the machine-readable estimates and check details.
