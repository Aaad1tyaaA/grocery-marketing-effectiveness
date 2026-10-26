"""Complete Word guide Module 3 using the verified sources and saved model SQL."""
from pathlib import Path
import csv
import json
import os
import duckdb
from provenance import build_inputs
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter,FuncFormatter

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'exports/customers'
DOCS=ROOT/'docs/customers'
TABLES=['hh_metrics','customer_cutoffs','hh_segments','customer_segment_summary',
        'customer_trajectory_summary','cohort_retention','income_spend',
        'demographic_coverage_spend','deal_driven_spend','spend_concentration','customer_checks']


def export(con,table):
    cur=con.execute(f'SELECT * FROM main.{table}')
    with (OUT/f'{table}.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f)
        w.writerow([d[0] for d in cur.description])
        w.writerows(cur.fetchall())


def main():
    for path in (OUT,DOCS,ROOT/'charts'):
        path.mkdir(parents=True,exist_ok=True)
    target=ROOT/'grocery_customers.duckdb'
    staging=ROOT/'grocery_customers.building.duckdb'
    if target.exists() or staging.exists():
        raise FileExistsError('Preserving existing customer database. Rename it before rebuilding.')
    baseline=json.loads((ROOT/'docs/verification.json').read_text())['tables']
    with duckdb.connect() as con:
        con.execute("SET memory_limit='512MB'")
        con.execute('SET threads=1')
        for name in ('transactions','products','demographics','campaigns'):
            path=(ROOT/'data/parquet'/f'{name}.parquet').as_posix().replace("'","''")
            con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{path}')")
            actual=con.execute(f'SELECT count(*),bit_xor(hash(t))::VARCHAR FROM {name} t').fetchone()
            assert actual==(baseline[name]['rows'],baseline[name]['content_fingerprint']),name
        statements=con.extract_statements((ROOT/'sql/01_model.sql').read_text())
        # Reuse dim_product, fact_sales, and dim_household; skip the 21m-row promotion table.
        for index in (0,1,3):
            con.execute(statements[index].query)
        n,sales=con.execute('SELECT count(*),round(sum(sales_value),2) FROM fact_sales').fetchone()
        assert n==1_460_487 and abs(sales-4_596_039.58)<0.005
        con.execute((ROOT/'sql/03_customers.sql').read_text())
        checks=con.execute('SELECT * FROM customer_checks ORDER BY check_name').fetchall()
        assert all(p for _,p in checks),checks
        for table in TABLES:
            export(con,table)
        data={t:con.execute(f'SELECT * FROM {t}').df() for t in TABLES}
        segments=data['customer_segment_summary'].sort_values('segment')
        trajectories=data['customer_trajectory_summary']
        cohorts=data['cohort_retention']
        demographics=data['demographic_coverage_spend'].sort_values('has_demographics')
        fig,ax=plt.subplots(figsize=(10,4.8),layout='constrained')
        labels=[f"{r.segment[2:]} (n={r.households:,})" for r in segments.itertuples()]
        bars=ax.barh(labels,segments.value_share,color=['#176B75','#398A8E','#73AFAD','#A5CBC6','#C36B24'])
        ax.invert_yaxis()
        ax.bar_label(bars,labels=[f'{s:.1%}' for s in segments.value_share],padding=5)
        ax.xaxis.set_major_formatter(PercentFormatter(1))
        ax.set_xlim(0,max(segments.value_share)*1.2)
        ax.set_xlabel('Share of annual grocery spend')
        ax.set_title('Customer value | five guide-defined segments',fontweight='bold')
        ax.spines[['top','right']].set_visible(False)
        fig.savefig(ROOT/'charts/customer_segments.png',dpi=160)
        plt.close(fig)

        fig,ax=plt.subplots(figsize=(10,4.5),layout='constrained')
        bars=ax.barh(trajectories.trajectory,trajectories.households,color='#176B75')
        ax.invert_yaxis()
        ax.bar_label(bars,labels=[f'{r.households:,} ({r.household_share:.1%})' for r in trajectories.itertuples()],padding=5)
        ax.set_xlim(0,max(trajectories.households)*1.3)
        ax.set_xlabel('Grocery purchasing households')
        ax.set_title('Spend trajectories | source weeks 2–27 vs 28–53',fontweight='bold')
        ax.spines[['top','right']].set_visible(False)
        fig.savefig(ROOT/'charts/customer_trajectories.png',dpi=160)
        plt.close(fig)

        heat=cohorts.pivot(index='cohort',columns='months_since_first',values='retention')
        sizes=cohorts[cohorts.months_since_first==0].set_index('cohort').cohort_size
        fig,ax=plt.subplots(figsize=(12,6),layout='constrained')
        cmap=plt.get_cmap('Blues').copy()
        cmap.set_bad('#E7E9EB')
        chart=ax.imshow(np.ma.masked_invalid(heat.to_numpy()),cmap=cmap,vmin=0,vmax=1,aspect='auto')
        ax.set_yticks(range(len(heat)),[f'{d:%b} (n={int(sizes.loc[d]):,})' for d in heat.index])
        ax.set_xticks(range(len(heat.columns)),heat.columns)
        ax.set_xlabel('Months since first observed purchase')
        ax.set_ylabel('First observed cohort, 2017')
        for i,row in enumerate(heat.to_numpy()):
            for j,value in enumerate(row):
                if not np.isnan(value):
                    ax.text(j,i,f'{value:.0%}',ha='center',va='center',fontsize=8,color='white' if value>.65 else '#182F43')
        ax.set_title('Observed purchase retention | all clean purchases\nFirst observed month is not proven acquisition; grey cells are not yet observable',fontsize=12,fontweight='bold')
        fig.colorbar(chart,ax=ax,format=PercentFormatter(1),label='Share of starting cohort active')
        fig.savefig(ROOT/'charts/cohort_retention.png',dpi=160)
        plt.close(fig)

        fig,ax=plt.subplots(figsize=(8.5,4.5),layout='constrained')
        labels=[('With demographics' if r.has_demographics else 'Without demographics')+f'\n(n={r.households:,})' for r in demographics.itertuples()]
        bars=ax.bar(labels,demographics.median_spend,color=['#8AA5AA','#176B75'])
        ax.bar_label(bars,labels=[f'${x:,.2f}' for x in demographics.median_spend],padding=5)
        ax.set_ylim(0,max(demographics.median_spend)*1.2)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x,p:f'${x:,.0f}'))
        ax.set_ylabel('Median annual grocery spend (USD)')
        ax.set_title('Demographic coverage is selective',fontweight='bold')
        ax.spines[['top','right']].set_visible(False)
        fig.savefig(ROOT/'charts/demographic_selection.png',dpi=160)
        plt.close(fig)

        path=staging.as_posix().replace("'","''")
        con.execute(f"ATTACH '{path}' AS reporting")
        for table in TABLES:
            con.execute(f'CREATE TABLE reporting.main.{table} AS SELECT * FROM main.{table}')
        con.execute('DETACH reporting')
        report={'guide':'Two_Analytics_Projects_Complete_Guide.docx','guide_steps':'1.3.1–1.3.5',
            'source':'Verified Parquet and reused phase-1 model SQL; open databases not changed',
            'clean_sales_rows':n,'clean_sales_usd':sales,
            'grocery_households':len(data['hh_metrics']),
            'grocery_sales_usd':float(data['hh_metrics'].spend.sum()),
            'segments':segments.to_dict('records'),'trajectories':trajectories.to_dict('records'),
            'concentration':data['spend_concentration'].to_dict('records')[0],
            'demographic_coverage':demographics.to_dict('records'),
            'deal_driven':data['deal_driven_spend'].to_dict('records'),
            'cohort_sizes':cohorts[cohorts.months_since_first==0][['cohort','cohort_size']].to_dict('records'),
            'january_followup_retention':cohorts[(cohorts.cohort==cohorts.cohort.min()) & (cohorts.months_since_first>0)].retention.agg(['min','max']).to_dict(),
            'checks':[{'name':name,'passed':bool(p)} for name,p in checks]}
        report['build_inputs_sha256']=build_inputs(ROOT,['scripts/run_customers.py','sql/01_model.sql','sql/03_customers.sql'])
        (DOCS/'verification.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
        champion=segments[segments.segment=='1 Champions'].iloc[0]
        decline=trajectories[trajectories.trajectory=='Declining'].iloc[0]
        with_demo=demographics[demographics.has_demographics].iloc[0]
        without_demo=demographics[~demographics.has_demographics].iloc[0]
        seg_rows='\n'.join(f'| {r.segment[2:]} | {r.households:,} | ${r.spend:,.2f} | {r.value_share:.1%} |' for r in segments.itertuples())
        trend_rows='\n'.join(f'| {r.trajectory} | {r.households:,} | {r.household_share:.1%} | ${r.spend_h1:,.2f} | ${r.spend_h2:,.2f} |' for r in trajectories.itertuples())
        findings=f'''# Customer value and retention — Word guide Module 3

Completed Steps **1.3.1–1.3.5**. These segments describe observed behaviour; they are not validated predictions of future value or proof of marketing effects.

## Three findings

1. **{int(champion.households):,} Champions generate {champion.value_share:.1%} of grocery spend.** The top 20% by spend (rounded up to {int(report['concentration']['top_20pct_households'])} households) account for **{report['concentration']['top_20pct_value_share']:.1%}**. This identifies a concentrated customer base for service and retention investigation; it does not establish future lifetime value.
2. **{int(decline.households):,} households have declining spend**, using the guide's 20% decline threshold. Their spend moves from **${decline.spend_h1:,.2f}** in H1 to **${decline.spend_h2:,.2f}** in H2, an observed reduction of **${-decline.spend_change:,.2f}**. This is not a forecast of revenue that a retention campaign can recover.
3. Households with demographics have median annual grocery spend of **${with_demo.median_spend:,.2f}**, versus **${without_demo.median_spend:,.2f}** without demographics. Income comparisons therefore describe a selective subset and should not be generalized to all households or treated as causal effects.

## Value segments

| Segment | Households | Annual grocery spend | Spend share |
|---|---:|---:|---:|
{seg_rows}

## Spend trajectories

| Trajectory | Households | Household share | H1 spend | H2 spend |
|---|---:|---:|---:|---:|
{trend_rows}

H1 uses source weeks 2–27; H2 uses weeks 28–53. Partial week 1 is excluded from that comparison but retained in annual spend. Growing means at least +20%; Declining means at least -20%; New/Gone labels mean no recorded positive spend in the other half, not proven acquisition/churn. No-spend-in-both-halves cases have an explicit label instead of being misclassified as new.

## Retention and demographics

The cohort model follows the guide's **all-clean-purchase** scope: 2,469 households, including two non-grocery-only households. Segments use **grocery purchases**: {len(data['hh_metrics']):,} households. Do not mix those denominators.

January is the first observed month for **{int(cohorts[cohorts.months_since_first==0].sort_values('cohort').iloc[0].cohort_size):,} households**. This panel starts in January; first observation does not prove those shoppers were newly acquired. Elapsed months without purchases are zero retention; future months are omitted/masked, never zero-filled. Monthly activity is nonconsecutive retention, so a household may return after a missed month.

Income-band comparisons include household counts and a small-group flag (<30). The flag is a descriptive caution, not a formal significance threshold. Missing attributes are not imputed. The deal-driven flag uses the guide's rounded discount-share upper quartile; ties mean it need not identify exactly 25% of households.

## Verification and files

**{len(checks)} full-data checks passed**, plus source fingerprint/model checks. The main outputs are `exports/customers/`, four chart PNGs, `03_customers.ipynb`, and `sql/03_customers.sql`. Exported retention rates retain full precision; the guide rounds them to three decimals. Segment/trajectory counts are computed from the actual data rather than forced to match the guide.

The reporting database `grocery_customers.duckdb` contains customer tables and checks, not raw purchases. Existing databases and DBeaver scripts were not modified. Next guide section: **Module 4, promotion lift**.
'''
        (DOCS/'findings.md').write_text(findings,encoding='utf-8')
    os.rename(staging,target)
    with duckdb.connect(str(target),read_only=True) as con:
        assert con.execute('SELECT bool_and(passed) FROM customer_checks').fetchone()[0]
    print(f'PASS: {len(checks)} customer checks; {len(data["hh_metrics"])} grocery households')
    print(json.dumps({k:v for k,v in report.items() if k!='checks'},indent=2,default=str))


if __name__=='__main__':
    main()
