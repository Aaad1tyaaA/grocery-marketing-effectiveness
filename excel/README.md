# Excel campaign ROI scenario model

The complete, verified workbook is delivered locally as `campaign_roi_model_v3.xlsx`. It is not included in the public repository because its lookup/pivot features contain household-level source-derived data. The public repository contains the model specification and native verification record instead.

## Inputs and formula contract

- Targeted households, campaign weeks, assumed incremental weekly household spend, gross margin, coupon redemptions, coupon amount proxy, **additional** retailer coupon funding share, and distribution cost per household.
- Incremental revenue = targeted households x campaign weeks x assumed spend lift.
- Incremental gross profit = incremental revenue x gross margin.
- Additional coupon cost = redemptions x coupon amount proxy x additional retailer funding share. The manufacturer coupon-line average is a proxy, not an observed campaign cost. The local workbook retains a 100% additional-funding scenario assumption; this is not an observed retailer cost. Set it to zero when manufacturer-funded or already included in margin. The separate summary app defaults to zero. Compare both assumptions to avoid charging manufacturer-funded discounts to the retailer or double-counting source net sales effects.
- Campaign cost = additional coupon cost + households x distribution cost per household.
- Scenario net profit = incremental gross profit - campaign cost.
- Scenario ROI = net profit / campaign cost, unavailable when cost is zero.
- Break-even lift = campaign cost / (households x weeks x gross margin), unavailable for zero/invalid denominators.

The historical campaign point estimate remains separate from editable scenario lift. Historical lift is observational and its interval crosses zero. A positive scenario must not trigger automatic scale-up.

## Verified native features

The seven-sheet desktop workbook includes named inputs, a two-input sensitivity Data Table, scenarios, charts, Goal Seek, household lookups and a category pivot. [The native verification record](../docs/excel/verification_v3.json) documents 127 checks, including blank/invalid inputs, cost and margin changes, formula restoration, and sample-allocation calculations.

The holdout planner uses an eight-week household outcome and baseline variance as a planning proxy. The default break-even-effect scenario needs far more households than the current audience. Re-estimate variance, commercial effect, allocation and power before promising a feasible campaign experiment.
