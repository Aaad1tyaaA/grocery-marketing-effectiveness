# Resume and interview notes

## Resume bullets

- Built a reproducible grocery marketing analysis with SQL, DuckDB and Python, modelling 1.44 million clean grocery purchase lines across 141,063 baskets and 2,467 active households; delivered a four-page Power BI report and an Excel ROI scenario workbook.
- Compared raw, difference-in-differences and two matched campaign designs; reduced Campaign 18's apparent $34.77 weekly household spend gap to an uncertain $2.95 estimate (95% CI -$0.74 to $6.64), motivating randomized validation rather than a causal profit claim.
- Evaluated a separate 64,000-customer randomized email experiment using per-assigned-customer outcomes, bootstrap intervals and multiple-testing checks; found +$0.77 two-week incremental spend for the Men's merchandise version and rejected an unstable targeting-gain story.

These describe an analytical portfolio project, not employment, a production marketing rollout or realized business savings. Do not claim recovered revenue, improved ROI, a deployed Streamlit service or a business impact that was not measured.

## Two-minute walkthrough

1. **Problem:** a CRM manager must decide whether observed campaign sales justify more spend.
2. **Data model:** purchase-line facts, unique baskets and households; unknown products retained; voids excluded; non-grocery flagged. Keep annual and comparable-week scopes explicit.
3. **Commercial context:** Champions contribute 44.7% of spend, while declining households show a $319k H1/H2 drop. These locate opportunities, not causal returns.
4. **Evidence:** the raw campaign gap shrinks after adjustment; all preferred earlier-match intervals cross zero. State the pre-trend, overlap, support and weighting caveats.
5. **Benchmark:** randomization in a different retailer's email test gives stronger evidence within that population, but does not validate grocery effect sizes.
6. **Decision:** plan a feasible grocery holdout, freeze eligibility, measure spend per assigned household plus costs, and compare contribution after costs with a commercial threshold.

## Questions to be ready for

- Why is average basket value sales divided by distinct baskets rather than average line value?
- Why omit partial week 1 from weekly comparisons but retain it in annual totals?
- Why does demographic coverage create selection bias?
- Why can coupon redemption be positive when incremental lift is uncertain?
- What does an interval that includes zero mean, and what does it not mean?
- How do matching support, pre-trends and effective control size limit an observational claim?
- Why is the workbook's sample-size result conditional on variance, allocation, effect and horizon assumptions?
- Why can the email experiment's result not be copied into grocery ROI?

## LinkedIn draft - not posted

The largest campaign sales gap in my grocery analytics project was also the easiest number to misread. Campaign 18's targeted households spent about $34.77 more per week; after earlier-window matching, the estimate was $2.95, with a confidence interval crossing zero.

I built the workflow in SQL, DuckDB and Python, then created a four-page Power BI report, an Excel scenario workbook and a separate randomized email benchmark. I checked metric grain, partial weeks, missing products, promotion duplicates, selection and experiment uncertainty.

My recommendation was a feasible randomized retention test with measured costs before scaling. The project is a portfolio analysis, not a claim of realized savings. Repository: https://github.com/Aaad1tyaaA/grocery-marketing-effectiveness
