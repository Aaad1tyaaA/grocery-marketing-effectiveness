"""Write the Module 5 learning sheet, executed notebook, readout, and module packet."""
from pathlib import Path
import csv
import json
import zipfile

import nbformat
import pandas as pd
from write_notebooks import execute_notebook

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'exports/campaigns'
DOCS = ROOT / 'docs/campaigns'


def main():
    overview = pd.read_csv(OUT / 'campaign_overview.csv', dtype={'campaign_id': str})
    guide = pd.read_csv(OUT / 'guide_compatibility_estimates.csv', dtype={'campaign_id': str})
    placebo = pd.read_csv(OUT / 'placebo_tests.csv', dtype={'campaign_id': str})
    placebo_index = placebo.set_index(['campaign_id','method'])
    roi = pd.read_csv(OUT / 'campaign_roi_inputs.csv', dtype={'campaign_id': str})
    checks = pd.read_csv(OUT / 'campaign_checks.csv')
    coupon = pd.read_csv(OUT / 'coupon_amount_summary.csv').iloc[0]
    pretrend = pd.read_csv(OUT / 'pretrend_tests.csv',dtype={'campaign_id':str})
    windows = pd.read_csv(OUT / 'campaign_window_audit.csv',dtype={'campaign_id':str})
    descriptions = pd.read_parquet(ROOT / 'data/parquet/campaigns.parquet')

    type_summary = overview.groupby('campaign_type').agg(
        campaigns=('campaign_id', 'count'), smallest_audience=('households', 'min'),
        largest_audience=('households', 'max')).reset_index()
    unique_recipients = descriptions.household_id.nunique()
    all_grocery_households = 2467
    unassigned_households = all_grocery_households - unique_recipients

    # DBeaver worksheet: short, separately runnable queries against the small reporting DB.
    sql = r'''-- Module 5: Campaign incrementality results (run each statement with Ctrl+Enter)
-- Connect DBeaver to grocery_campaigns.duckdb first. These are compact reporting tables.

-- 1. List the Module 5 tables.
SHOW TABLES;

-- 2. Understand the 27 campaign audiences and redemption counts.
SELECT campaign_id, campaign_type, start_date, end_date, households,
       redemptions, redeeming_households
FROM main.campaign_overview
ORDER BY start_date;

-- 3. Focus on the four large Type A campaigns and see the analysis weeks.
SELECT campaign_id, start_week, end_week, weeks, households,
       redemptions, redeeming_households
FROM main.campaign_roi_inputs
ORDER BY start_week;

-- 4. Compare all four designs on the same matched support, as in the Word guide.
-- Estimates are dollars per household per week; intervals crossing zero are uncertain.
SELECT campaign_id, method, n_treated, n_control,
       round(estimate, 2) AS estimate,
       round(ci_low, 2) AS ci_low, round(ci_high, 2) AS ci_high
FROM main.guide_compatibility_estimates
WHERE campaign_id IN ('8','13','18')
ORDER BY campaign_id,
  CASE method WHEN 'naive' THEN 1 WHEN 'unmatched' THEN 2
               WHEN 'matched_pre' THEN 3 ELSE 4 END;

-- 5. Check the fake-start placebo. A lift before the real campaign warns of bias.
SELECT campaign_id, method, status, n_treated, n_control,
       round(estimate, 2) AS estimate,
       round(ci_low, 2) AS ci_low, round(ci_high, 2) AS ci_high,
       round(p_holm, 4) AS holm_adjusted_p
FROM main.placebo_tests
ORDER BY campaign_id, method;

-- 6. Inspect overlap with other campaign assignments in each analysis window.
SELECT * FROM main.campaign_overlap_audit ORDER BY campaign_id;

-- 7. See the numbers needed by the later ROI spreadsheet.
-- Costs are not observed; the last two columns prevent treating estimates as validated ROI.
SELECT * FROM main.campaign_roi_inputs ORDER BY start_week;

-- 8. Coupon amounts are line-item discounts recorded on purchases.
SELECT * FROM main.coupon_amount_summary;

-- 9. Inspect the campaign 18 weekly gap. These are pointwise intervals, not a formal trend test.
SELECT week, relative_week, during_campaign, n_treated, n_control,
       round(estimate, 2) AS gap, round(ci_low, 2) AS ci_low, round(ci_high, 2) AS ci_high
FROM main.campaign_pretrends
WHERE campaign_id='18'
ORDER BY week;

-- 10. All checks should show TRUE.
SELECT * FROM main.campaign_checks ORDER BY check_name;

-- 11. Pre-period falsification using the actual earlier-matched households and weights.
-- A nonsignificant result does not prove parallel trends.
SELECT * FROM main.pretrend_tests ORDER BY campaign_id;

-- 12. Expose source-week approximations to actual campaign dates.
-- Campaign 13's weekly outcome includes Monday 7 August, one day before its Tuesday start.
SELECT * FROM main.campaign_window_audit ORDER BY start_week;
'''
    (ROOT / 'sql/05_campaigns_learning.sql').write_text(sql, encoding='utf-8')

    rows = []
    for cid in ['8', '13', '18']:
        subset = guide[guide.campaign_id == cid].set_index('method')
        p = placebo[placebo.campaign_id == cid].set_index('method')
        def cell(method):
            r = subset.loc[method]
            return f"{r.estimate:+.2f} ({r.ci_low:+.2f} to {r.ci_high:+.2f})"
        def placebo_cell(method):
            r = p.loc[method]
            return (f"{r.estimate:+.2f} ({r.ci_low:+.2f} to {r.ci_high:+.2f}; Holm p={r.p_holm:.3f})"
                    if r.status == 'estimated' else 'Not estimable: insufficient earlier history')
        rows.append(f"| {cid} | {cell('naive')} | {cell('unmatched')} | {cell('matched_pre')} | {cell('matched_earlier')} | {placebo_cell('matched_pre')} | {placebo_cell('matched_earlier')} |")

    focus = roi[roi.campaign_id.isin(['8','13','18'])].set_index('campaign_id')
    r18 = focus.loc['18']
    pretrend_rows='\n'.join(f'| {r.campaign_id} | {r.estimate:+.2f} | {r.ci_low:+.2f} to {r.ci_high:+.2f} | {r.p_holm:.3f} |'
                           for r in pretrend.itertuples())
    support_rows='\n'.join(f'| {r.campaign_id} | {r.n_treated:,} | {r.n_control:,} | {r.control_ess:.1f} | {r.maximum_control_weight:.2f} |'
                          for r in guide[guide.method=='matched_earlier'].itertuples())
    findings = f'''# Campaign incrementality — Word guide Module 5

Completed **Steps 1.5.1–1.5.5** with verified Complete Journey Parquet sources. The analysis uses grocery household-week spend, campaigns 8, 13 and 18, four comparison designs, placebo checks, an overlap audit, and the later ROI inputs.

## What the analysis says

The targeted households spend about **$32–$35 more per week** than the untargeted households during the campaigns. That gap mostly predates the campaign: the unmatched before/after differences are small. Matching on the immediate pre-period then produces estimates around **+$3 to +$7 per household per week**, but a fake campaign start eight weeks earlier produces a positive **+$5.68** for Campaign 8 (95% interval **+$2.13 to +$9.24**, Holm-adjusted p **{placebo_index.loc[('8','matched_pre'),'p_holm']:.3f}**). That placebo weakens the causal interpretation of the attractive pre-period-matched estimate.

The earlier-window matched estimates are **+$0.80** for Campaign 8, **+$0.39** for Campaign 13 and **+$2.95** for Campaign 18. Every 95% interval includes zero. These are the most defensible observational estimates in this analysis, and they do not distinguish a small lift from no lift. The fake-start checks for Campaigns 13 and 18 include zero; Campaign 8's earlier-window placebo cannot be estimated because the required history falls outside the dataset.

## The four designs, dollars per household per week

The table below reproduces the guide's common-support comparison. Intervals are pointwise 95% HC1 intervals, treating the estimated matching weights as fixed.

| Campaign | Naive gap | Unmatched DiD | Matched on pre-period | Matched on earlier weeks | Pre-match placebo | Earlier-match placebo |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

The naive and unmatched comparisons use the same common-support households shown for the pre-period match, to make the guide's sequence comparable. The exported `campaign_estimates.csv` also includes full-sample naive and unmatched estimates. Matching retains only households in strata containing both targeted and untargeted households; the campaign-specific counts are in the CSVs and database.

## Pre-period contrasts, weights, and week boundaries

Using the actual earlier-matched sample and weights, compare the last four pre-campaign weeks with the first four. These contrasts are a falsification check separate from the fake-start placebos; a wide interval that includes zero does not establish parallel trends.

| Campaign | Pre-period change in targeted/control gap ($/week) | 95% HC1 interval | Holm p across three checks |
|---|---:|---:|---:|
{pretrend_rows}

| Campaign | Supported targeted households | Supported controls | Effective control sample size | Largest control weight |
|---|---:|---:|---:|---:|
{support_rows}

Weights are positive and stratum shares reconcile, but a few controls carry substantial weight. The reported HC1 intervals condition on these weights; they are not a full uncertainty analysis of selecting/matching households. Equal activity values are split by household ordering in the guide-compatible method. The tie-preserving sensitivity keeps them together and is exported separately.

The guide uses whole source weeks. **Campaign 13 actually starts Tuesday 8 August, while modeled week 33 starts Monday 7 August**, so its during-period includes one pre-campaign day (49 modeled days versus 48 calendar campaign days). Campaigns 8 and 18 align with week boundaries. `campaign_window_audit.csv` reports the exact dates, extra days, and grocery sales on those off-date days across all households. Those amounts are not campaign effects. An exact-day analysis would be needed to remove this approximation; the primary values retain the guide's weekly definition.

## Campaigns and audience

There are **27 campaigns**. The available source data covers **{all_grocery_households:,} grocery households**; **{unique_recipients:,}** received at least one campaign and **{unassigned_households:,}** received none. Type A has four campaigns: Campaign 27 begins too early to supply the guide's eight-week pre-period; Campaigns 8, 13 and 18 are the large campaigns used for the incrementality analysis. Type B and C audiences are much smaller. See `campaign_overview.csv` for each audience and redemption count.

The guide's 910 never-assigned households use all 2,469 purchasing households. The grocery cohort excludes two non-grocery-only, never-assigned households, leaving 908. This denominator difference is intentional.

Campaign assignment overlaps are substantial inside these analysis windows: **{int(roi.loc[roi.campaign_id=='8','households'].iloc[0]):,}**, **{int(roi.loc[roi.campaign_id=='13','households'].iloc[0]):,}** and **{int(roi.loc[roi.campaign_id=='18','households'].iloc[0]):,}** households were assigned to the respective campaign, and many were also assigned to other campaigns during the pre-period or campaign window. The overlap audit lists treated and control overlap counts. Excluding other-campaign recipients is exported as a sensitivity; its smaller samples still have intervals spanning zero.

## What to use in the ROI model later

Campaign 18 lasted **{int(r18.weeks)} weeks**, targeted **{int(r18.households):,} households**, and recorded **{int(r18.redemptions):,} coupon redemptions by {int(r18.redeeming_households):,} households**. Positive coupon-discount purchase lines average **${coupon.average_manufacturer_coupon_line_amount:.2f}** (median **${coupon.median_manufacturer_coupon_line_amount:.2f}**). These are data inputs; manufacturer-funded coupon value is not necessarily retailer cost. The data contains no print or distribution costs. `campaign_roi_inputs.csv` keeps costs marked unobserved and does not validate extrapolation from the matched sample to every recipient.

## Limits and recommendation

Campaign targeting used prior purchase behavior, so the randomized-treatment assumption does not apply. Earlier-week matching and placebo checks help reveal selection and regression-to-the-mean problems, but they do not eliminate seasonal trends, concurrent campaign exposure, or other unmeasured differences. The household-level HC1 intervals are conditional on the matching weights and do not include uncertainty from selecting strata. This analysis is not proof that campaigns caused incremental sales or profit.

For a business decision, run a randomized household holdout for the next campaign and track incremental net revenue, retailer-funded discounts, and delivery costs. The later Excel model can calculate break-even lift under explicit margin and cost assumptions; it must label those assumptions separately from observed data.

**Verification:** {len(checks)} campaign checks passed. The executed notebook presents the workflow and outputs. See `verification.json` for the machine-readable estimates and check details.
'''
    (DOCS / 'findings.md').write_text(findings, encoding='utf-8')

    start = '''# Campaign incrementality is ready — Word guide Module 5

Completed **Steps 1.5.1–1.5.5**. You can inspect the finished results without manually building the 128,284-row household-week panel or pasting each setup query.

## Open these first

1. `docs/campaigns/findings.md` — interpretation and limitations.
2. `charts/campaign_estimate_path.png` — how the estimate changes across four designs.
3. `charts/campaign_pretrends.png` and `charts/campaign18_pretrend.png` — weekly treated/control gaps.
4. `05_campaigns.ipynb` — executed learning notebook.
5. `sql/05_campaigns_learning.sql` — twelve short DBeaver queries, one at a time.

## Main result

The earlier-window matched estimate is **+$0.80** for Campaign 8 (95% CI −$2.71 to +$4.31), **+$0.39** for Campaign 13 (−$3.25 to +$4.04), and **+$2.95** for Campaign 18 (−$0.74 to +$6.64) per supported household per week. All intervals include zero. The pre-period-matched estimate looks larger, but Campaign 8's fake-start placebo is also positive and significant after Holm correction.

## Open in DBeaver

Double-click `Open Campaign Analysis in DBeaver.cmd`. If a DuckDB driver prompt appears, choose **Download**. Then open `sql/05_campaigns_learning.sql`. Run each statement with **Ctrl+Enter**. It queries the compact `grocery_campaigns.duckdb` reporting database, so it won't scan the 21-million-row promotions table or write into your raw database.

The SQL worksheet starts with `SHOW TABLES`, then shows campaign audiences, the four estimates, placebo checks, campaign overlap, ROI inputs, weekly gaps, and final checks. `main.` is included in the table names for DBeaver.

The audit also added pre-period contrasts, effective control sample sizes, and an explicit date-boundary check: Campaign 13's whole-week outcome includes one day before its actual Tuesday start. This approximation is disclosed in the readout; it is not an exact-day causal estimate.

## Rebuild

The project requires the packages in `requirements-business-health.txt`. Run `python scripts/run_campaigns.py` to build the verified campaign results, then `python scripts/write_campaign_deliverables.py` to regenerate the notebook and readout. The builder refuses to overwrite an existing `grocery_campaigns.duckdb`; rename the prior report database first if intentionally rebuilding. Keep DBeaver disconnected from that report file while rebuilding.

The packet `Grocery_Campaign_Incrementality_Module.zip` contains the module files and reproducible scripts. Raw data and other modules are not duplicated in the packet; the complete project folder contains them.
'''
    (ROOT / 'CAMPAIGNS_START_HERE.md').write_text(start, encoding='utf-8')

    # Tutorial notebook reads compact outputs, leaving the expensive transformations reproducible in SQL/Python.
    nb = nbformat.v4.new_notebook()
    nb['metadata']['kernelspec'] = {'display_name':'Python 3','language':'python','name':'python3'}
    cells = [
        nbformat.v4.new_markdown_cell('''# Module 5 — Campaign incrementality

This follows Word guide Steps 1.5.1–1.5.5. The campaign assignment was observational, not randomized. We compare four designs, use fake-start placebo checks to look for bias, and collect inputs for the later ROI model. Dollar estimates are per household per week.'''),
        nbformat.v4.new_code_cell('''from pathlib import Path
import pandas as pd
from IPython.display import display, Image
ROOT = Path.cwd()
OUT = ROOT / "exports" / "campaigns"
def load(name):
    return pd.read_csv(OUT / f"{name}.csv")
overview = load("campaign_overview")
display(overview[["campaign_id", "campaign_type", "start_date", "end_date", "households", "redemptions"]].sort_values("start_date"))'''),
        nbformat.v4.new_markdown_cell('''## 1. Which campaigns can we compare?

The guide focuses on large Type A campaigns 8, 13 and 18. Campaign 27 begins too early for the required eight-week pre-period. Campaign assignment used past purchases, so targeted households started out different from everyone else.'''),
        nbformat.v4.new_code_cell('''roi = load("campaign_roi_inputs")
display(roi[["campaign_id", "start_week", "end_week", "weeks", "households", "redemptions", "redeeming_households"]])
print("Grocery households x 52 weeks:", 2_467 * 52)'''),
        nbformat.v4.new_markdown_cell('''## 2. Follow the estimate as the design improves

The naive gap compares spending during the campaign. Difference-in-differences (DiD) subtracts each group's earlier spending. Matching also balances the groups on prior spending and activity. The earlier-window method matches on weeks separate from the eight-week before-period to reduce regression-to-the-mean bias.'''),
        nbformat.v4.new_code_cell('''est = load("guide_compatibility_estimates")
est = est[est.campaign_id.astype(str).isin(["8", "13", "18"])].copy()
est["interval"] = est.apply(lambda r: f"({r.ci_low:+.2f}, {r.ci_high:+.2f})", axis=1)
display(est.pivot(index="campaign_id", columns="method", values="estimate").round(2))
display(est[["campaign_id", "method", "n_treated", "n_control", "estimate", "ci_low", "ci_high"]].round(2))'''),
        nbformat.v4.new_markdown_cell('''The naive +$32–$35 weekly gap is not incremental lift: it largely reflects who was selected. Pre-period matching creates a larger estimate, but a campaign fake-start can create a similar apparent lift before the real campaign. Earlier-window matching yields smaller estimates whose intervals include zero.'''),
        nbformat.v4.new_code_cell('''placebo = load("placebo_tests")
placebo = placebo[placebo.campaign_id.astype(str).isin(["8", "13", "18"])]
display(placebo[["campaign_id", "method", "status", "estimate", "ci_low", "ci_high", "p_holm"]].round(3))'''),
        nbformat.v4.new_markdown_cell('''Campaign 8's earlier-window placebo is not estimable because its fake-start would require weeks before the dataset begins. Campaigns 13 and 18 have earlier-window placebo intervals that include zero. A passing placebo does not prove the real estimate is causal; it only removes one warning.'''),
        nbformat.v4.new_code_cell('''display(load("campaign_overlap_audit"))
display(load("campaign_sensitivities")[["campaign_id", "method", "n_treated", "n_control", "estimate", "ci_low", "ci_high"]].round(2))
display(load("pretrend_tests")[["campaign_id", "contrast", "estimate", "ci_low", "ci_high", "p_holm"]].round(3))
display(load("campaign_window_audit"))'''),
        nbformat.v4.new_markdown_cell('''## 3. Inspect the weekly pattern and the money inputs

The weekly chart shows the noisy gap for Campaign 18. Pointwise intervals are separate from the pre-period contrasts above and do not validate parallel trends. Campaigns overlap, and the source has no print or distribution cost data. Whole source weeks approximate campaign dates: Campaign 13 includes one day before its actual Tuesday start.'''),
        nbformat.v4.new_code_cell('''display(Image(filename=str(ROOT / "charts" / "campaign18_pretrend.png")))
display(load("campaign_roi_inputs"))
display(load("coupon_amount_summary"))'''),
        nbformat.v4.new_markdown_cell('''## 4. Run the workflow yourself in DBeaver

Open `grocery_campaigns.duckdb` with `Open Campaign Analysis in DBeaver.cmd`, then run one statement at a time from `sql/05_campaigns_learning.sql` with Ctrl+Enter. These are small reporting tables. The full household-week model and statistical estimates are reproducible with `scripts/run_campaigns.py`.

**Conclusion:** the best observational design finds a small, uncertain spend change. Recommend a randomized household holdout and measure net revenue and retailer costs before claiming campaign ROI.'''),
        nbformat.v4.new_code_cell('''checks = load("campaign_checks")
assert checks["passed"].astype(str).str.lower().eq("true").all()
print(f"{len(checks)} campaign checks passed")
display(checks)''')
    ]
    nb['cells'] = cells
    path = ROOT / '05_campaigns.ipynb'
    nbformat.write(nb, path)
    execute_notebook(path,module=5)

    # Point the project landing page to the latest finished module.
    landing = ROOT / 'START_HERE.md'
    text = landing.read_text(encoding='utf-8')
    old = '**Latest completed section: Word guide Module 4, promotion analysis. Open PROMOTIONS_START_HERE.md for its notebook, charts, exports, and interpretation limits. Earlier sections are documented in CUSTOMERS_START_HERE.md and BUSINESS_HEALTH_START_HERE.md.**'
    new = '**Latest completed section: Word guide Module 5, campaign incrementality. Open CAMPAIGNS_START_HERE.md for its notebook, charts, exports, DBeaver worksheet, and interpretation limits. Earlier sections are documented in PROMOTIONS_START_HERE.md, CUSTOMERS_START_HERE.md, and BUSINESS_HEALTH_START_HERE.md.**'
    if old in text:
        landing.write_text(text.replace(old,new,1), encoding='utf-8')

    packet = ROOT.parent / 'Grocery_Campaign_Incrementality_Module.zip'
    include = [
        ROOT/'CAMPAIGNS_START_HERE.md', ROOT/'05_campaigns.ipynb', ROOT/'Open Campaign Analysis in DBeaver.cmd',
        ROOT/'grocery_campaigns.duckdb', ROOT/'sql/05_campaigns.sql',
        ROOT/'sql/05_campaigns_learning.sql', ROOT/'scripts/run_campaigns.py',
        ROOT/'scripts/campaign_methods.py', ROOT/'scripts/write_campaign_deliverables.py',
        ROOT/'docs/campaigns/findings.md', ROOT/'docs/campaigns/verification.json',
        ROOT/'charts/campaign_estimate_path.png', ROOT/'charts/campaign_earlier_estimates.png',
        ROOT/'charts/campaign_pretrends.png', ROOT/'charts/campaign18_pretrend.png',
        ROOT/'scripts/write_notebooks.py',ROOT/'scripts/provenance.py',ROOT/'sql/01_model.sql',
        ROOT/'requirements-business-health.txt',ROOT/'requirements-setup.txt',ROOT/'tests/test_campaigns.py',
        ROOT/'docs/source_manifest.json',ROOT/'docs/verification.json',
    ] + list(OUT.glob('*.csv'))
    with zipfile.ZipFile(packet,'w',zipfile.ZIP_DEFLATED) as z:
        for file in include:
            z.write(file,file.relative_to(ROOT))
    with zipfile.ZipFile(packet) as z:
        assert z.testzip() is None
    print('Notebook executed; findings, DBeaver worksheet, start page, and packet written.')
    print(f'Packet: {packet} ({packet.stat().st_size:,} bytes)')


if __name__ == '__main__':
    main()
