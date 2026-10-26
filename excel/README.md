# Campaign ROI workbook

`campaign_roi_model_v3.xlsx` answers one question: **at what lift does a campaign pay for itself, and how sure can we be?** Blue cells are editable assumptions; black cells are formulas.

The completed workbook is a local deliverable because its household lookup sheet contains household-level data. This folder publishes its specification and the recorded verification evidence, rather than the workbook itself.

## Model

- **Inputs:** targeted households, campaign weeks, incremental spend per household per week, gross margin, coupon redemptions, coupon amount per redemption, the share of coupon cost the retailer pays, and distribution cost per household.
- **Incremental revenue** = households × weeks × lift.
- **Incremental gross profit** = revenue × margin.
- **Coupon cost** = redemptions × coupon amount × retailer share. Manufacturer coupons are reimbursed, so set the share to 0% unless the retailer funds extra coupons.
- **Net profit** = gross profit − coupon cost − households × distribution cost. **ROI** = net profit ÷ cost.
- **Break-even lift** = cost ÷ (households × weeks × margin).

## Features

Named inputs, a two-way Data Table (lift × margin), Goal Seek for the maximum affordable distribution cost, a holdout-size planner, a household segment lookup (XLOOKUP), a category discount PivotTable and charts. Checks are recorded in [`docs/excel/verification_v3.json`](../docs/excel/verification_v3.json).

## How to read it

The campaign 18 lift ($2.95 per household per week) comes from an observational estimate whose 95% interval (−$0.74 to $6.64) includes zero. A positive scenario is not proof the campaign paid; the holdout planner shows how large a randomized test would need to be to settle it. Margin, coupon funding and distribution cost are assumptions, not data.
