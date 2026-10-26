"""Recreate the local Power BI CSV inputs after building Modules 1-6."""
from pathlib import Path
from datetime import date,timedelta
import csv,json,hashlib,argparse
import duckdb
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'dashboard/data')
OUT=parser.parse_args().output.resolve();OUT.mkdir(parents=True,exist_ok=True)
def sqlstr(p):return "'"+str(p).replace("'","''")+"'"
sources=[]
def export(name,db,query):
    if not (ROOT/db).exists():raise FileNotFoundError('Build Modules 1-6 first: '+db)
    with duckdb.connect(str(ROOT/db),read_only=True) as c:
        c.execute("SET memory_limit='384MB'");c.execute('SET threads=1')
        c.execute(f'COPY ({query}) TO {sqlstr(OUT/(name+".csv"))} (HEADER,FORMAT CSV)')
        count=c.execute(f'SELECT count(*) FROM ({query})').fetchone()[0]
    sources.append({'table':name,'rows':count,'sha256':hashlib.sha256((OUT/(name+'.csv')).read_bytes()).hexdigest()})
    print(f'{name}: {count:,}')
export('Sales','grocery_phase1.duckdb','SELECT household_id,basket_id,product_id,week,sales_value,shelf_value,retailer_funded_disc,CASE WHEN retailer_funded_disc>0 THEN shelf_value ELSE 0 END AS discounted_shelf_value FROM fact_sales WHERE NOT is_non_grocery')
export('Products','grocery_phase1.duckdb',"SELECT product_id,department,product_category,brand,department || ' / ' || coalesce(product_category,'UNKNOWN') AS category_label FROM dim_product")
export('Departments','grocery_phase1.duckdb','SELECT DISTINCT department FROM fact_sales WHERE NOT is_non_grocery ORDER BY 1')
segments=ROOT/'exports/customers/hh_segments.csv'
export('Households','grocery_phase1.duckdb',f"SELECT h.household_id,coalesce(h.age,'Unknown') AS age,coalesce(h.income,'Unknown') AS income,h.has_demographics,coalesce(s.segment,'No grocery purchases') AS segment,coalesce(s.trajectory,'No grocery purchases') AS trajectory,s.deal_driven,s.spend,s.baskets,s.recency_days FROM dim_household h LEFT JOIN read_csv_auto({sqlstr(segments)},types={{'household_id':'VARCHAR'}}) s USING(household_id)")
with (OUT/'Weeks.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.writer(f);w.writerow(['week','week_start','comparable_week'])
    for week in range(1,54):w.writerow([week,str(date(2017,1,2)+timedelta(weeks=week-2)),week>=2])
export('Cohorts','grocery_customers.duckdb','SELECT * FROM cohort_retention')
export('Promotion associations','grocery_promotions.duckdb','SELECT * FROM promo_lift')
export('Campaigns','grocery_campaigns.duckdb','SELECT * FROM campaign_overview')
designs={'naive':('1 Targeted vs untargeted',1),'unmatched':('2 Unmatched DiD',2),'matched_pre':('3 Match on recent pre-period',3),'matched_earlier':('4 Match on earlier weeks',4)}
with (ROOT/'exports/campaigns/guide_compatibility_estimates.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
with (OUT/'Campaign estimates.csv').open('w',newline='',encoding='utf-8') as f:
    fields=['campaign_id','method','design','design_order','estimate','ci_low','ci_high','n_treated','n_control','control_ess'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
    for r in rows:
        if r['method'] in designs:
            label,order=designs[r['method']];w.writerow({**{k:r[k] for k in fields if k in r},'design':label,'design_order':order})
export('Email experiment','grocery_hillstrom.duckdb',"SELECT arm,n_treatment,n_control,treatment_mean,control_mean,estimate,ci_low,ci_high,p_holm FROM hillstrom_effects WHERE metric='spend'")
export('Daily anomalies','grocery_phase1.duckdb','SELECT day,sales,robust_z FROM daily_anomalies')
(ROOT/'dashboard/csv_export_verification.json').write_text(json.dumps(sources,indent=2),encoding='utf-8')
