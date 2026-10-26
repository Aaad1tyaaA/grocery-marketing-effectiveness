"""Execute Word guide Module 2 and export ready-to-inspect results without locking DBeaver."""
from pathlib import Path
import csv
import json
import os
import duckdb
from provenance import build_inputs
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter,PercentFormatter

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'exports/business_health'
DOCS=ROOT/'docs/business_health'


def csv_export(con,query,path):
    cursor=con.execute(query)
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.writer(f)
        writer.writerow([d[0] for d in cursor.description])
        writer.writerows(cursor.fetchall())


def main():
    for p in (OUT,DOCS,ROOT/'charts'):
        p.mkdir(parents=True,exist_ok=True)
    final=ROOT/'grocery_business_health.duckdb'
    staging=ROOT/'grocery_business_health.building.duckdb'
    if final.exists() or staging.exists():
        raise FileExistsError('Preserving existing business-health database. Rename it before rebuilding.')
    baseline=json.loads((ROOT/'docs/verification.json').read_text())['tables']
    with duckdb.connect() as con:
        con.execute("SET memory_limit='512MB'")
        con.execute('SET threads=1')
        for name in ('transactions','products'):
            path=(ROOT/'data/parquet'/f'{name}.parquet').as_posix().replace("'","''")
            con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{path}')")
            n,fingerprint=con.execute(f'SELECT count(*),bit_xor(hash(t))::VARCHAR FROM {name} t').fetchone()
            assert (n,fingerprint)==(baseline[name]['rows'],baseline[name]['content_fingerprint'])
        # Reuse the exact verified dimension/sales transformation; no second model implementation.
        model=con.extract_statements((ROOT/'sql/01_model.sql').read_text())
        for statement in model[:2]:
            con.execute(statement.query)
        n,sales=con.execute('SELECT count(*),round(sum(sales_value),2) FROM fact_sales').fetchone()
        assert n==1_460_487 and abs(sales-4_596_039.58)<0.005
        con.execute((ROOT/'sql/02_health.sql').read_text())
        checks=con.execute('SELECT * FROM business_health_checks ORDER BY check_name').fetchall()
        assert all(p for _,p in checks),checks
        for table in ('weekly_kpis','category_discount','business_health_summary','business_health_checks'):
            csv_export(con,f'SELECT * FROM {table}',OUT/f'{table}.csv')
        weekly=con.execute('SELECT * FROM weekly_kpis ORDER BY week').df()
        category=con.execute('SELECT * FROM category_discount ORDER BY share_sold_on_discount DESC').df()
        summary=con.execute('SELECT * FROM business_health_summary').df().iloc[0].to_dict()
        corr=con.execute('SELECT corr(discount_depth,sales) FROM weekly_kpis').fetchone()[0]
        average=con.execute('SELECT avg(households),avg(sales),avg(aov),avg(visits_per_hh),avg(discount_depth) FROM weekly_kpis').fetchone()
        fig,axes=plt.subplots(2,1,figsize=(11,6.5),sharex=True,layout='constrained')
        fig.suptitle('Grocery business health | comparable source weeks 2–53',fontsize=15,fontweight='bold')
        axes[0].plot(weekly.week,weekly.sales,color='#176B75',linewidth=2)
        axes[0].yaxis.set_major_formatter(FuncFormatter(lambda x,pos:f'${x/1000:.0f}k'))
        axes[0].set_ylabel('Weekly sales (USD)')
        axes[1].plot(weekly.week,weekly.discount_depth,color='#C36B24',linewidth=2)
        axes[1].yaxis.set_major_formatter(PercentFormatter(1))
        axes[1].set_ylabel('Retailer-funded discount depth')
        axes[1].set_xlabel('Source store week')
        for ax in axes:
            ax.grid(alpha=.2)
            ax.spines[['top','right']].set_visible(False)
        fig.savefig(ROOT/'charts/weekly_health.png',dpi=160)
        fig.savefig(ROOT/'charts/weekly_health.svg')
        plt.close(fig)
        top=category.head(8).iloc[::-1]
        fig,ax=plt.subplots(figsize=(11,5.5),layout='constrained')
        labels=(top.department+' / '+top.product_category).tolist()
        bars=ax.barh(labels,top.share_sold_on_discount,color='#176B75')
        ax.bar_label(bars,labels=[f'{x:.1%}' for x in top.share_sold_on_discount],padding=5)
        ax.set_xlim(0,1)
        ax.xaxis.set_major_formatter(PercentFormatter(1))
        ax.set_xlabel('Share of shelf value sold with retailer-funded discounts')
        ax.set_title('Highest discount dependency | categories with ≥ $10,000 sales',fontweight='bold')
        ax.spines[['top','right']].set_visible(False)
        fig.savefig(ROOT/'charts/category_discount_dependency.png',dpi=160)
        plt.close(fig)
        path=staging.as_posix().replace("'","''")
        con.execute(f"ATTACH '{path}' AS reporting")
        for table in ('weekly_kpis','category_discount','business_health_summary','business_health_checks'):
            con.execute(f'CREATE TABLE reporting.main.{table} AS SELECT * FROM main.{table}')
        con.execute('DETACH reporting')
        report={'guide':'Two_Analytics_Projects_Complete_Guide.docx','guide_steps':'1.2.1–1.2.4',
                'source':'Verified Parquet; reused first two statements of sql/01_model.sql because DBeaver holds the phase-1 file',
                'clean_sales_rows':n,'all_department_sales':sales,'comparable_weeks':len(weekly),
                'eligible_categories':len(category),'summary':summary,'weekly_sales_discount_correlation':corr,
                'average_week':dict(zip(['households','sales','aov','visits_per_hh','discount_depth'],average)),
                'largest_week':weekly.loc[weekly.sales.idxmax()].to_dict(),
                'smallest_week':weekly.loc[weekly.sales.idxmin()].to_dict(),
                'checks':[{'name':name,'passed':bool(passed)} for name,passed in checks]}
        report['build_inputs_sha256']=build_inputs(ROOT,['scripts/run_business_health.py','sql/01_model.sql','sql/02_health.sql'])
        (DOCS/'verification.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
        biggest=report['largest_week'];smallest=report['smallest_week'];leading=category.iloc[0]
        findings=f'''# Business health — Word guide Module 2

Completed Steps 1.2.1–1.2.4 using the verified grocery model. These are descriptive results, not estimates of what would happen if discounts were removed.

## Three findings

1. Comparable grocery weeks average **${average[1]:,.2f} sales**, **{average[0]:,.0f} active households**, and **${average[2]:.2f} average basket value**. Week {int(biggest['week'])} leads with **${biggest['sales']:,.2f}**; week {int(smallest['week'])} is lowest at **${smallest['sales']:,.2f}**. Use this baseline to investigate changes rather than compare partial week 1 against full weeks.
2. Average weekly retailer-funded discount depth is **{average[4]:.2%}**. Its correlation with weekly sales is **{corr:.3f}**. The weak weekly association does not establish whether discounts increase sales; promotion-level and campaign analyses are still needed.
3. **{len(category)} categories** meet the $10,000 sales floor. **{leading['product_category']}** has the highest shelf-value-weighted share sold on discount at **{leading['share_sold_on_discount']:.1%}**. This identifies a category for closer margin and promotion analysis; it does not measure sales that would be lost without discounts.

## Scope and reconciliation

- Weekly trends use source weeks **2–53**, excluding partial week 1: **${summary['comparable_week_sales']:,.2f}** sales over {len(weekly)} weeks.
- Week labels are the actual Monday calendar starts. The first recorded purchase date is exported separately; week 53 starts 25 December even though its first observed purchase is 26 December.
- Annual/category analysis includes all source weeks: **${summary['annual_grocery_sales']:,.2f}** sales. Partial week 1 contributes **${summary['partial_week_1_sales']:,.2f}**, explaining the difference.
- As in the guide, the grocery filter excludes explicitly flagged non-grocery products. It still contains **${summary['unclassified_product_sales']:,.2f}** of UNKNOWN-product sales; their actual categories are unknown.
- Manufacturer coupon amounts are excluded from retailer-funded discount cost.
- Category discount share weights shelf value, not units or purchase lines. Categories below $10,000 are excluded only from the ranking.
- Ratios have exported base amounts so Power BI can recompute weighted totals. Do not sum weekly household counts to report annual distinct households or average category percentages without weighting.
- The supplied guide rounds category sales to whole dollars and category ratios to three decimals. These outputs retain cents and more ratio precision; the underlying definitions and sales floor are the same.
- **{len(checks)} business-health checks passed**, plus source fingerprint and clean-model reconciliation checks. No existing database was modified.

## Files to inspect

`exports/business_health/weekly_kpis.csv`, `category_discount.csv`, `business_health_summary.csv`, and `business_health_checks.csv`; `charts/weekly_health.png`; `charts/category_discount_dependency.png`; `02_business_health.ipynb`; and `sql/02_health.sql`.

Next in the Word guide: Module 3, customer value and segments. The CSVs are also ready to import into Power BI. The final dashboard remains a later guide step.
'''
        (DOCS/'findings.md').write_text(findings,encoding='utf-8')
    os.rename(staging,final)
    with duckdb.connect(str(final),read_only=True) as con:
        assert con.execute('SELECT bool_and(passed) FROM business_health_checks').fetchone()[0]
    print(f'PASS: {len(checks)} checks; {len(weekly)} weeks; {len(category)} categories; correlation {corr:.4f}')
    print(json.dumps({k:v for k,v in report.items() if k not in ('checks','source')},indent=2,default=str))


if __name__=='__main__':
    main()
