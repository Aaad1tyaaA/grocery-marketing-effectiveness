# How I used AI on this project

I built this project with an AI coding assistant. I chose the business questions and the analysis plan, directed each module and reviewed the results. The assistant wrote and ran most of the code, SQL and verification scripts, and helped draft documents. Every number in the README and memo comes from a saved query, notebook or export in this repository, not from the assistant's text.

Below are the places where a plausible first approach would have been wrong, and what the project does instead. These are the checks I'd walk an interviewer through.

## Data model

1. **Conflicting promotion rows.** 12,785 product-store-week keys appear more than once with different display or mailer codes. Taking the maximum code per column would invent combinations that never happened, so conflicting keys are labelled `MULTIPLE` and the original exposure flags and row counts are kept.
2. **Two different scopes.** Clean all-department sales are $4.596M, but grocery sales are $4.185M. The panel has 2,469 households, but only 2,467 bought groceries. Every metric states which scope it uses.
3. **Missing products.** 17 product IDs in transactions aren't in the product table. Their sales are kept under an "unknown" product instead of being dropped.
4. **Average basket value.** It's sales divided by distinct baskets, not the average line value. The app uses the annual ratio, not an average of weekly averages.
5. **Partial week 1.** Week 1 is a single day. It's kept in annual totals and excluded from weekly comparisons and the H1-vs-H2 trend.
6. **Time zones.** Timestamps are stored in UTC; an Eastern local time is added for day-of-week analysis, with a test covering a winter date.
7. **Non-grocery items.** The non-grocery flag is never blank, even when product metadata is missing; a test covers that case.

## Analysis

8. **Campaign selection.** The raw $34.77 gap isn't reported as lift. Four designs are compared, and the one I'd defend (matched on an earlier window, with placebo checks) has intervals that include zero.
9. **Coupon costs.** Manufacturer coupon amounts are kept separate from retailer-funded discounts, so the retailer isn't charged for coupons it gets reimbursed for. In the app the extra coupon cost defaults to zero; every cost input is labelled as an assumption.
10. **Email experiment outcomes.** Spend is measured per assigned customer, including the many zeros, not per buyer. The shared control group is counted once in the 64,000 total.
11. **Targeting results.** A targeting rule that looked good on one random split weakened on a second split. The memo reports the weaker result instead of the flattering one.

## Presentation

12. **Dashboard checks.** Power BI measures were reconciled against the saved source aggregates before export. Clipped text, unclear labels and a chart that mixed different units were fixed, and the grocery and email evidence are kept on separate visuals.
