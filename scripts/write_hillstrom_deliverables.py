"""Render the verified Module 6 experiment as learning files and a portable packet."""
from pathlib import Path
import json
import zipfile

import duckdb
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import nbformat
import numpy as np
import pandas as pd

from write_notebooks import execute_notebook

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'exports/hillstrom'
DOCS=ROOT/'docs/hillstrom'
CHARTS=ROOT/'charts'
COLORS={'Mens E-Mail':'#176B87','Womens E-Mail':'#B44C78'}


def load(name):
    return pd.read_csv(OUT/f'{name}.csv')


def md_table(frame):
    def clean(value):
        return str(value).replace('|',' / ')
    return '| '+' | '.join(map(clean,frame.columns))+' |\n| '+' | '.join(['---']*len(frame.columns))+' |\n'+''.join(
        '| '+' | '.join(map(clean,row))+' |\n' for row in frame.itertuples(index=False,name=None))


def main():
    DOCS.mkdir(parents=True,exist_ok=True);CHARTS.mkdir(parents=True,exist_ok=True)
    effects=load('hillstrom_effects');direct=load('email_head_to_head')
    segments=load('segment_effects');heldout=load('heldout_effects')
    rules=load('policy_rules');counts=load('policy_audience_counts');values=load('heldout_policy_value')
    profile=load('hillstrom_profile').iloc[0];srm=load('hillstrom_srm').iloc[0]
    checks=load('hillstrom_checks');summary=load('hillstrom_arm_summary')
    assert checks.passed.astype(str).str.lower().eq('true').all()

    # Intervals are pointwise bootstrap intervals; p values use separately defined Holm families.
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                         'axes.spines.right':False,'figure.facecolor':'white'})
    fig,axes=plt.subplots(1,3,figsize=(12,4.1))
    for ax,metric,title in zip(axes,['visit','conversion','spend'],
                              ['Visits: percentage points','Conversion: percentage points','Spend: USD per assigned customer']):
        rows=effects[effects.metric.eq(metric)]
        scale=1 if metric=='spend' else 100
        for y,r in enumerate(rows.itertuples()):
            ax.plot([scale*r.ci_low,scale*r.ci_high],[y,y],color=COLORS[r.arm],lw=3)
            ax.scatter(scale*r.estimate,y,color=COLORS[r.arm],s=55,zorder=3)
        ax.axvline(0,color='#89939a',lw=1);ax.set_yticks([0,1],['Men’s version','Women’s version'])
        ax.set_title(title,fontsize=10);ax.set_ylim(-.65,1.65);ax.invert_yaxis();ax.grid(axis='x',alpha=.18)
    fig.suptitle('Both emails improve two-week outcomes versus no email',fontsize=15)
    fig.text(.5,.025,'64,000 randomized customers • 95% pointwise bootstrap intervals • all six Holm-adjusted p < .002',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.07,1,.91]);fig.savefig(CHARTS/'hillstrom_effects.png',dpi=170);plt.close(fig)

    fig,ax=plt.subplots(figsize=(9.5,4.6))
    sensitivity=heldout[(heldout.scope=='exact')&(heldout.arm=='Mens E-Mail')&(heldout.metric=='spend')&heldout.audience.isin(['target','other'])].copy()
    sensitivity=sensitivity.sort_values(['seed','audience'],ascending=[True,False])
    for y,r in enumerate(sensitivity.itertuples()):
        color='#176B87' if r.audience=='target' else '#8a9299'
        ax.plot([r.ci_low,r.ci_high],[y,y],color=color,lw=3)
        ax.scatter(r.estimate,y,color=color,s=55,zorder=3)
        ax.text(r.ci_high+.045,y,f'${r.estimate:.2f}',va='center',fontsize=9)
    ax.set_yticks(range(len(sensitivity)),[f'Seed {r.seed} · '+('top 10,000' if r.audience=='target' else 'other 44,000') for r in sensitivity.itertuples()])
    ax.axvline(0,color='#89939a',lw=1);ax.invert_yaxis();ax.grid(axis='x',alpha=.18)
    ax.set_xlabel('Held-out Men’s version minus no email (USD per assigned customer)')
    ax.set_title('The strong targeting advantage does not survive the second split',pad=16)
    fig.text(.5,.025,'95% pointwise bootstrap intervals • overlapping splits of one experiment, not independent replications',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.07,1,1]);fig.savefig(CHARTS/'hillstrom_targeting_validation.png',dpi=170);plt.close(fig)

    fig,ax=plt.subplots(figsize=(9.5,4.6))
    buyer_levels=['both','mens only','womens only']
    for i,arm in enumerate(COLORS):
        rows=segments[(segments.cut=='buyer')&(segments.metric=='spend')&(segments.arm==arm)].set_index('level').loc[buyer_levels]
        y=np.arange(3)+(i-.5)*.21
        for pos,r in zip(y,rows.itertuples()):
            ax.plot([r.ci_low,r.ci_high],[pos,pos],color=COLORS[arm],lw=2)
        ax.scatter(rows.estimate,y,color=COLORS[arm],label=arm.replace(' E-Mail',' version'),s=45)
    ax.set_yticks(range(3),['Previously bought both lines','Previously bought men’s only','Previously bought women’s only'])
    ax.axvline(0,color='#89939a',lw=1);ax.invert_yaxis();ax.legend(frameon=False)
    ax.set_xlabel('Two-week spend lift versus no email (USD per assigned customer)')
    ax.set_title('Merchandise history suggests hypotheses; segment spend is noisy',pad=16)
    fig.text(.5,.025,'Exploratory cuts • 95% pointwise intervals • subgroup significance is not a test of differences between subgroups',ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.07,1,1]);fig.savefig(CHARTS/'hillstrom_buyer_segments.png',dpi=170);plt.close(fig)

    table=[]
    for r in effects.itertuples():
        binary=r.metric!='spend';scale=100 if binary else 1
        fmt=(lambda x:f'{x*100:.2f}%') if binary else (lambda x:f'${x:.2f}')
        interval=f'{scale*r.estimate:+.2f} [{scale*r.ci_low:.2f}, {scale*r.ci_high:.2f}]'+(' pp' if binary else ' USD')
        table.append({'Version':r.arm,'Outcome':r.metric,'No email':fmt(r.control_mean),'Email':fmt(r.treatment_mean),
                      'Difference [95% CI]':interval,'Holm p':f'{r.p_holm:.3g}'})
    primary_table=md_table(pd.DataFrame(table))
    chosen=rules[(rules.seed==7)&(rules.exact_target>0)].copy()
    chosen['Training suggestion']=chosen.recommended_email.str.replace(' E-Mail','',regex=False)
    target_table=md_table(chosen[['cell','population_customers','exact_target','Training suggestion']].rename(
        columns={'cell':'Pre-treatment cell','population_customers':'Cell population','exact_target':'Selected'}))
    bottom=rules[(rules.seed==7)&(rules.exact_suppress>0)][['cell','population_customers','exact_suppress']]
    suppression_table=md_table(bottom.rename(columns={'cell':'Pre-treatment cell','population_customers':'Cell population','exact_suppress':'Suppressed'}))
    comparison=heldout[(heldout.scope=='exact')&(heldout.arm=='Mens E-Mail')&(heldout.metric=='spend')].copy()
    comparison['Lift [95% CI]']=comparison.apply(lambda r:f'${r.estimate:.2f} [{r.ci_low:.2f}, {r.ci_high:.2f}]',axis=1)
    sensitivity_table=md_table(comparison[['seed','audience','n_treatment','n_control','Lift [95% CI]','p_holm']].rename(columns={'p_holm':'Holm p (72 tests)'}).round(4))
    direct_spend=direct[direct.metric=='spend'].iloc[0]
    balance=load('hillstrom_balance').standardized_mean_difference.abs().max()
    mix=values[(values.seed==7)&(values.audience=='target')&(values.metric=='spend')].iloc[0]
    buyers=segments[(segments.cut=='buyer')&(segments.metric=='visit')].copy()
    buyers['Visit lift (pp)']=(100*buyers.estimate).round(2)
    buyer_table=md_table(buyers[['level','arm','Visit lift (pp)']])

    readout=f'''# Module 6 — Randomized email experiment

## Decision

Prefer the **Men's email version for the experiment population** over the Women's version or no email, based on two-week outcomes. Incremental spend is **+$0.77 per assigned customer** versus no email; Women's is **+$0.42**. The direct Men's-minus-Women's spend difference is **${direct_spend.estimate:.2f}**, with 95% pointwise bootstrap CI **[${direct_spend.ci_low:.2f}, ${direct_spend.ci_high:.2f}]** and Holm-adjusted p **{direct_spend.p_holm:.4f}** across the three head-to-head outcomes. Email costs, margin and longer-term effects are unavailable, so this is a revenue recommendation, not proven net ROI. Cell targeting remains provisional: its strong gain is not stable across split seeds.

## Design and checks

The [original experiment description](https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html) describes customers with a purchase in the previous year, randomized among two merchandise emails and no email, followed for two weeks. The mirror contains **64,000 rows**: Men's **21,307**, Women's **21,387**, no email **21,306**. The equal-third sample-ratio test gives **p={srm.p_value:.4f}**; no warning at the predeclared .01 threshold. The maximum absolute standardized baseline difference is **{balance:.4f}**. These checks detect some assignment/data issues; they do not prove every aspect of randomization was implemented correctly. Outcomes use all assigned customers, including zeros, rather than just buyers or email openers.

The original download endpoint could not be fetched with valid HTTPS in this environment. The included [scikit-uplift scientific mirror](https://github.com/maks-sh/scikit-uplift/blob/master/sklift/datasets/datasets.py) matches its published compressed MD5. The raw CSV SHA-256 is `00a6a868e05a9ffe7382da51629f6d6dce88c5acfc945e79d314ebc78fd3a2c0`. CSV and Parquet rows match exactly; source row order is preserved. This is a checksum-pinned mirror copy, without a claim of byte equality to the unavailable original. Provenance is in `docs/hillstrom_source.json`.

## Primary results

{primary_table}
Binary differences are **percentage points**, not percent changes. Spend is USD per assigned customer over two weeks. Intervals use 2,000 independent empirical row-bootstrap resamples per arm (seed 42); multinomial counts over repeated values produce the same bootstrap-mean distribution efficiently. Welch tests supply p values, with Holm adjustment across the six primary comparisons. Intervals remain **pointwise 95%**, not simultaneous Holm-adjusted intervals. All six primary comparisons reject zero at Holm .05. A separate three-test family supports the direct Men's-versus-Women's comparison on all three outcomes.

![Primary outcome differences](../charts/hillstrom_effects.png)

## Targeting: frozen training rule and held-out check

The 36 theoretical cells combine merchandise history (both / men's only / women's only), newbie 0/1, recency 1–3 / 4–8 / 9–12 months, and prior spend **at least $200** / below $200. Only **30 cells occur**; the six both-lines/low-spend combinations are absent. We do not invent observations for empty cells. With seed 7, a random half trains cell spend lifts versus no email; each cell is ranked by its better training email. The other half evaluates frozen selections. No holdout outcome or assignment chooses a cell, version or tie break. Baseline cell counts from the full population only determine quota sizes.

A whole-cell rule selects **8,486**, not exactly 10,000, and suppresses **9,420**. We retain that result separately as `guide_whole_cells`. To answer the exact-capacity question, a seeded outcome-free tie break fills the boundary cell, giving **10,000 target**, **10,000 suppress**, and **44,000 other**, with no overlap. The primary exact target rule is:

{target_table}
Read cells as `merchandise history | newbie | months since purchase | prior-spend band`. Newbie 1 denotes a new customer in the source definition. For example, `both|0|1-3|high` is an existing customer who bought both merchandise lines, purchased within three months, and spent at least $200 previously. Selection within a partly selected cell is random and fixed, not a claim that its selected individuals have higher uplift. Complete training means, counts, both seeds and decisions are in `policy_rules.csv` and `policy_assignments.csv`.

The exact suppression rule is:

{suppression_table}
Suppression here means a forced capacity/budget scenario based on the lowest training scores. It does **not** show these customers are harmed by email, unprofitable, or should unsubscribe. The held-out suppression spend intervals include zero. Choosing cells that look poor on both training and validation would reuse validation to fit the rule; that was avoided.

{sensitivity_table}
Seed 7's whole-cell Men's lift is **$1.60** versus **$0.70** for its complement. Its exact 10,000 target yields **$1.62** versus **$0.66** among the other 44,000. With the additional seed 8, exact target lift falls to **$0.73** versus **$0.67** for other customers, and the target interval crosses zero. **The strong targeting gain does not survive this sensitivity check.** The table's intervals are pointwise; its p values are Holm-adjusted over all 72 held-out fixed-arm comparisons. Seed 7 target-spend p after that adjustment is about .161. Splits overlap within one experiment and are not independent replications; the second seed was not used to optimize the chosen rule. A difference between subgroup point estimates alone is not a formal test of targeting gain.

![Targeting sensitivity](../charts/hillstrom_targeting_validation.png)

The training-selected mix of Men's/Women's versions also lacks validation. On seed 7's held-out target, the learned policy's Horvitz–Thompson incremental spend is **${mix.estimate:.2f}** with 95% CI **[{mix.ci_low:.3f}, {mix.ci_high:.3f}]**; its paired difference versus always sending Men's is **${mix.policy_minus_mens:.2f}** **[{mix.policy_minus_mens_ci_low:.2f}, {mix.policy_minus_mens_ci_high:.2f}]**. This uses the known 1/3 assignment probability and accounts for the trained variant in each cell; averaging a subset's two fixed-arm lifts would not evaluate the mixed rule. Intervals condition on the fitted rule and do not cover all training-selection uncertainty. Use Men's as the population default; treat `recommended_email` as a training suggestion only.

`target_10000.csv` and `suppress_10000.csv` are reproducible research candidate lists, not production contact lists. `source_row` is a synthetic one-based CSV position; there is no real customer/email identifier. Lists include `population_default_email` and `variant_suggestion_status` so training version suggestions are not mistaken for validated recommendations. A fresh randomized validation with a frozen rule is needed before claiming a targeting advantage.

## Exploratory segment findings

All requested cuts are present: buyer merchandise history, newbie, channel, ZIP type, history segment and recency band; 126 outcome comparisons share one exploratory Holm family. Spend differences are noisy with few buyers. Different within-group significance does not establish a difference between groups; no confirmatory treatment-by-segment interaction claim is made. Men's email raises visits even for women's-only merchandise buyers:

{buyer_table}
![Exploratory spend by merchandise history](../charts/hillstrom_buyer_segments.png)

## Answers to the eight guide questions

1. **Which email performed best?** Men's, with higher visits, conversion and spend than no email and than Women's in direct comparisons. This is about merchandise versions, not the sex or gender of customers.
2. **Incremental sales per customer?** Men's +$0.77 [0.48, 1.04]; Women's +$0.42 [0.18, 0.70], over two weeks, including all assigned customers.
3. **Best 10,000 to email?** The seed 7 frozen training ranking selects the six cells and boundary allocation shown above. It is a provisional research shortlist: the second split fails to confirm a strong advantage, so do not promise better results than broad Men's email from this ranking.
4. **Which 10,000 to suppress?** Use the frozen bottom-rank cells only if a capacity rule requires it; the exact list is exported. Evidence does not establish negative email effects for these customers.
5. **Do segments differ?** Descriptive point estimates vary by merchandise history, recency, channel and other baseline cuts. Small buyer counts and exploratory multiplicity make spend-based subgroup conclusions uncertain; differences between subgroup effects require direct interaction tests or a fresh experiment.
6. **Do outcomes differ?** Men's improves visits by 7.66 pp and conversion by 0.68 pp; Women's by 4.52 pp and 0.31 pp. Revenue gains are positive overall but less precise in small segments. Do not replace per-assigned revenue with per-buyer spend.
7. **Anomalies?** Only 578 customers have positive spend; 63,422 have zero, maximum spend is $499. Source label `Surburban` is retained. Only 30/36 possible cells exist; women's-only merchandise buyers respond to Men's, and target rankings change materially with the split.
8. **Who gets which version?** Men's is the supported population default. Training rules suggest Women's in some cells, but the held-out learned mix does not beat always-Men's, so no validated customer-level Women's allocation is established.

## Why this matters for Module 5

Random assignment supports a causal comparison of these email versions within this experiment's population and two-week horizon, subject to usual assumptions such as no outcome-changing interference. The grocery campaign analysis is observational and its best estimates remain uncertain. This separate retailer experiment illustrates the value of a randomized holdout; **its dollar lift must not be transferred into grocery campaign ROI** or presented as validation of the grocery estimates. Recommend a grocery-specific randomized holdout, measured costs and a preregistered primary outcome for the next campaign.

## Reproduce and inspect

Open `06_hillstrom.ipynb` for executed outputs, `sql/06_hillstrom_learning.sql` for short inspection queries, `scripts/run_hillstrom.py` for the build, and `scripts/hillstrom_methods.py` for the statistics. The run passed **{len(checks)} database checks**. Unit tests cover bootstrap equivalence, frozen holdout isolation, exact disjoint quotas, unsupported cells, feature boundaries and policy-value arithmetic.
'''
    (ROOT/'docs/experiment_readout.md').write_text(readout,encoding='utf-8')
    (DOCS/'findings.md').write_text(readout.replace('(../charts/','(../../charts/'),encoding='utf-8')

    sql='''-- Module 6: use grocery_hillstrom.duckdb. Run ONE statement with Ctrl+Enter.
-- The calculations are already saved; these queries inspect verified outputs.

-- 1. What is randomized? Counts and outcomes per assigned customer, including zeros.
-- Why: the denominator must not depend on whether a customer bought after treatment.
SELECT * FROM main.hillstrom_arm_summary ORDER BY segment;

-- 2. Does allocation resemble the intended equal thirds? p ~ .904; warning FALSE.
-- Why: large sample ratio mismatch can indicate assignment or data-pipeline trouble.
SELECT * FROM main.hillstrom_srm;

-- 3. Are pre-email attributes reasonably balanced? Maximum absolute SMD ~ .014.
SELECT * FROM main.hillstrom_balance
ORDER BY abs(standardized_mean_difference) DESC;

-- 4. Primary six effects: rates use 0-1 units; multiply binary lifts by 100 for pp.
-- Why: compare email vs no email, not raw sales totals of slightly unequal arms.
-- CI is pointwise bootstrap; p_holm corrects six Welch tests.
SELECT arm, metric, n_treatment, n_control, treatment_mean, control_mean,
       estimate, ci_low, ci_high, p_holm
FROM main.hillstrom_effects ORDER BY arm, metric;

-- 5. Direct Men's minus Women's comparison; positive favors Men's.
-- Why: being significant against control alone does not prove one email beats another.
SELECT metric, estimate, ci_low, ci_high, p_holm
FROM main.email_head_to_head ORDER BY metric;

-- 6. Exploratory merchandise-history cuts (these labels do not identify gender).
-- Why: find hypotheses; separate subgroup p values are not interaction tests.
SELECT level, arm, metric, n_treatment, n_control, estimate, ci_low, ci_high, p_holm
FROM main.segment_effects WHERE cut='buyer' ORDER BY level, metric, arm;

-- 7. Exact quotas versus the whole-cell rule.
-- Why: whole cells select 8,486 with seed 7; boundary tie breaks fill exactly 10,000.
SELECT * FROM main.policy_audience_counts ORDER BY seed, scope, audience;

-- 8. Training-only seed 7 rules, including exact selected and suppressed counts.
-- recommended_email is a TRAINING suggestion, not a validated deployment recommendation.
SELECT cell, train_n_control, train_n_mens, train_n_womens,
       train_mens_lift, train_womens_lift, recommended_email,
       population_customers, exact_target, exact_suppress
FROM main.policy_rules WHERE seed=7 ORDER BY train_best_lift DESC;

-- 9. Does the target advantage survive a second split? It does not stay strong.
-- These overlapping splits are sensitivity checks, not independent replications.
SELECT seed, audience, n_treatment, n_control, estimate, ci_low, ci_high, p_holm
FROM main.heldout_effects
WHERE scope='exact' AND metric='spend' AND arm='Mens E-Mail'
ORDER BY seed, audience;

-- 10. Evaluate the learned per-cell VERSION mix against always sending Men's.
-- Why: a group's Men's-only lift does not evaluate its mixed version policy.
SELECT seed, audience, heldout_customers, estimate, ci_low, ci_high,
       always_mens_estimate, policy_minus_mens,
       policy_minus_mens_ci_low, policy_minus_mens_ci_high
FROM main.heldout_policy_value WHERE metric='spend' ORDER BY seed, audience;

-- 11. Check sparse spend and the number of actually observed cells (30, not 36).
SELECT * FROM main.hillstrom_profile;

-- 12. Every check should be TRUE. These verify implementation, not targeting usefulness.
SELECT * FROM main.hillstrom_checks ORDER BY check_name;
'''
    (ROOT/'sql/06_hillstrom_learning.sql').write_text(sql,encoding='utf-8')
    with duckdb.connect(str(ROOT/'grocery_hillstrom.duckdb'),read_only=True) as con:
        statements=con.extract_statements(sql)
        for statement in statements:
            con.execute(statement).fetchall()

    nb=nbformat.v4.new_notebook()
    nb.metadata['kernelspec']={'display_name':'Python 3','language':'python','name':'python3'}
    md=nbformat.v4.new_markdown_cell;code=nbformat.v4.new_code_cell
    nb.cells=[md('''# Module 6 — Randomized email experiment

This notebook reads verified exports; the complete calculation is in `scripts/run_hillstrom.py`, `scripts/hillstrom_methods.py` and `sql/06_hillstrom.sql`. Monetary values are USD. This is a separate retailer experiment, not the grocery campaign population.'''),
        code('''from pathlib import Path
import json
import pandas as pd
from IPython.display import display, Image, Markdown
ROOT=Path.cwd()
DATA=ROOT/'exports/hillstrom'
def load(name):
    return pd.read_csv(DATA/f'{name}.csv')
source=json.loads((ROOT/'docs/hillstrom_source.json').read_text(encoding='utf-8'))
print('Customers:', source['rows'], '| CSV SHA-256:', source['csv_sha256'])
display(load('hillstrom_arm_summary'))
display(load('hillstrom_srm'))
display(load('hillstrom_balance').sort_values('standardized_mean_difference',key=abs,ascending=False).head())'''),
        md('''## 1. Compare outcomes per randomized customer

Keep zeros. Compare each version with no email; then compare the two versions directly. Rates use 0–1 units; 0.01 is one percentage point. All intervals are pointwise 95% bootstrap intervals, with 2,000 resamples and seed 42. Welch p values use Holm families of six primary and three direct contrasts; intervals are not multiplicity-adjusted.'''),
        code('''display(load('hillstrom_effects'))
display(load('email_head_to_head'))
display(Image(filename=str(ROOT/'charts/hillstrom_effects.png')))'''),
        md('''## 2. Explore baseline customer cuts

Six cuts produce 126 exploratory comparisons with one Holm family. Merchandise purchase history does not identify customer sex or gender. A different significance label across two subgroups is not evidence of an interaction. Segment spending is sparse and noisy.'''),
        code('''segments=load('segment_effects')
display(segments[(segments['cut']=='buyer') & (segments['metric']=='visit')])
print('Exploratory tests:',len(segments),'| Cuts:',', '.join(segments['cut'].unique()))
display(Image(filename=str(ROOT/'charts/hillstrom_buyer_segments.png')))'''),
        md('''## 3. Freeze targeting before looking at validation outcomes

Thirty observed cells out of 36 possible; the six both-lines/low-spend cells are empty. Random half seed 7 trains the better-version spend score per cell. Outcomes or assignments from the held-out half cannot choose rules. Whole cells select 8,486, so outcome-free seeded boundary ties fill the exact 10,000 quota. Suppression is a forced capacity ranking, not evidence of harmful email.'''),
        code('''rules=load('policy_rules')
display(load('policy_audience_counts'))
display(rules[(rules['seed']==7)&(rules['exact_target']>0)])
heldout=load('heldout_effects')
display(heldout[(heldout['scope']=='exact')&(heldout['metric']=='spend')&(heldout['arm']=='Mens E-Mail')])
display(Image(filename=str(ROOT/'charts/hillstrom_targeting_validation.png')))'''),
        md('''## 4. Evaluate the policy, not just one arm in its audience

The learned per-cell version policy needs its own value estimate. The Horvitz–Thompson estimator uses the known 1/3 randomized assignment probability and a paired comparison against always sending Men's. Validation intervals condition on the trained rule. Seed 8 is an overlapping sensitivity split, not a new experiment: it fails to confirm a strong targeting gain. Do not tune the policy using these validation results.'''),
        code('''value=load('heldout_policy_value')
display(value[(value['metric']=='spend')&(value['audience']=='target')])
for decision in ['target','suppress']:
    candidates=load(decision+'_10000')
    assert len(candidates)==10000 and candidates['source_row'].is_unique
    print(decision, len(candidates), '| version suggestion status:',candidates['variant_suggestion_status'].unique())
display(load('hillstrom_profile'))
checks=load('hillstrom_checks')
assert checks['passed'].astype(str).str.lower().eq('true').all()
print(len(checks),'database checks passed')
display(checks)'''),
        md('''## 5. Make a decision and learn the SQL workflow

Men's is supported as the population default; the selected cell version mix and ranking remain provisional. No email cost or margin is supplied, so do not claim net profit. To inspect the results in SQL, open `grocery_hillstrom.duckdb` in any SQL client and run `sql/06_hillstrom_learning.sql` one query at a time. The readout below answers eight questions about the experiment.'''),
        code("display(Markdown((ROOT/'docs/experiment_readout.md').read_text(encoding='utf-8')))"),
    ]
    nbformat.write(nb,ROOT/'06_hillstrom.ipynb')
    execute_notebook(ROOT/'06_hillstrom.ipynb',module=6)

    print(f'Executed Module 6 notebook; {len(statements)} inspection queries passed.')


if __name__=='__main__':
    main()
