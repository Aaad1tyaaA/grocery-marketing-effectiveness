"""Export completed-module summaries from their actual reporting databases."""
from pathlib import Path
import json
import duckdb

ROOT=Path(__file__).resolve().parents[1]
SOURCES={'grocery_business_health.duckdb':{'weekly_kpis':'weekly_kpis','category_discount':'category_discount'},
         'grocery_customers.duckdb':{'customer_segment_summary':'segments','customer_trajectory_summary':'trajectories','cohort_retention':'cohort_retention'},
         'grocery_promotions.duckdb':{'promo_lift':'promo_lift','promotion_coverage':'promotion_coverage'},
         'grocery_campaigns.duckdb':{'campaign_estimates':'campaign_estimates','placebo_tests':'placebo_tests'}}


def main():
    out=ROOT/'app/data';out.mkdir(parents=True,exist_ok=True)
    with duckdb.connect(str(ROOT/'grocery_phase1.duckdb'),read_only=True) as con:
        con.execute('''SELECT sum(sales_value) AS sales,count(DISTINCT basket_id) AS baskets,
count(DISTINCT household_id) AS households,sum(shelf_value) AS shelf_value,
sum(retailer_funded_disc) AS retailer_discounts FROM fact_sales WHERE NOT is_non_grocery''').df().to_csv(out/'annual_kpis.csv',index=False,encoding='utf-8-sig')
    for filename,mapping in SOURCES.items():
        if not (ROOT/filename).exists():
            raise FileNotFoundError(f'{filename} is missing. Build completed modules with scripts/run_all.py first.')
        with duckdb.connect(str(ROOT/filename),read_only=True) as con:
            for table,name in mapping.items():
                con.execute(f'SELECT * FROM {table}').df().to_csv(out/f'{name}.csv',index=False,encoding='utf-8-sig')
    benchmark=ROOT/'grocery_hillstrom.duckdb'
    if benchmark.exists():
        with duckdb.connect(str(benchmark),read_only=True) as con:
            assert con.execute('SELECT bool_and(passed) FROM main.hillstrom_checks').fetchone()[0]
            for table,name in [('hillstrom_effects','hillstrom_readout'),('email_head_to_head','email_head_to_head')]:
                con.execute(f'SELECT * FROM main.{table}').df().to_csv(out/f'{name}.csv',index=False,encoding='utf-8-sig')
    else:
        for name in ['hillstrom_readout.csv','email_head_to_head.csv']:
            (out/name).unlink(missing_ok=True)
    status={'completed_modules':list(range(1,7 if benchmark.exists() else 6)),
            'hillstrom_available':benchmark.exists(),
            'app_status':'summary app; Power BI, Excel and memo available' if benchmark.exists() and (ROOT/'docs/memo.md').exists()
                         else 'analysis preview' if benchmark.exists()
                         else 'preview; Modules 6-7 remain pending'}
    (out/'status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
    print(f'Exported {len(list(out.glob("*.csv")))} summary CSVs; Hillstrom available: {benchmark.exists()}')


if __name__=='__main__':
    main()
