"""Check business scope and ratio definitions independently of the full dataset."""
from pathlib import Path
import duckdb

ROOT=Path(__file__).resolve().parents[1]


def test_week_scope_and_discount_weights():
    with duckdb.connect() as con:
        con.execute("""CREATE TABLE fact_sales(week INTEGER,local_ts TIMESTAMP,
            household_id VARCHAR,basket_id VARCHAR,sales_value DOUBLE,
            retailer_funded_disc DOUBLE,shelf_value DOUBLE,is_non_grocery BOOLEAN,
            is_unknown_product BOOLEAN,department VARCHAR,product_category VARCHAR);
        INSERT INTO fact_sales VALUES
            (1,'2017-01-01','h1','b1',500,0,500,false,false,'GROCERY','Mixed'),
            (2,'2017-01-02','h1','b2',6000,1000,7000,false,false,'GROCERY','Mixed'),
            (2,'2017-01-03','h2','b3',6000,0,6000,false,false,'GROCERY','Mixed'),
            (3,'2017-01-10','h1','b4',2000,0,2000,false,true,'UNKNOWN',NULL),
            (3,'2017-01-11','h2','b5',10000,0,10000,false,false,'GROCERY','NoDiscount'),
            (2,'2017-01-03','h1','fuel',100000,1000,101000,true,false,'FUEL','Fuel');""")
        con.execute((ROOT/'sql/02_health.sql').read_text())
        assert con.execute('SELECT week,sales,baskets,households FROM weekly_kpis ORDER BY week').fetchall()==[(2,12000,2,2),(3,12000,2,2)]
        sales,share,depth=con.execute("SELECT sales,share_sold_on_discount,discount_depth FROM category_discount WHERE product_category='Mixed'").fetchone()
        assert sales==12500
        assert abs(share-7000/13500)<1e-12
        assert abs(depth-1000/13500)<1e-12
        assert con.execute("SELECT share_sold_on_discount,discount_depth FROM category_discount WHERE product_category='NoDiscount'").fetchone()==(0,0)
        assert con.execute('SELECT count(*) FROM category_discount').fetchone()[0]==2
        assert con.execute('SELECT annual_grocery_sales,partial_week_1_sales,comparable_week_sales,unclassified_product_sales FROM business_health_summary').fetchone()==(24500,500,24000,2000)


def test_christmas_week_uses_calendar_monday_even_without_monday_sales():
    with duckdb.connect() as con:
        con.execute("""CREATE TABLE fact_sales AS SELECT 53 AS week,TIMESTAMP '2017-12-26 12:00:00' AS local_ts,
            'h' AS household_id,'b' AS basket_id,10000.0 AS sales_value,
            0.0 AS retailer_funded_disc,10000.0 AS shelf_value,false AS is_non_grocery,
            false AS is_unknown_product,'GROCERY' AS department,'Example' AS product_category;""")
        con.execute((ROOT/'sql/02_health.sql').read_text())
        start,observed=con.execute('SELECT week_start,first_observed_purchase_date FROM weekly_kpis').fetchone()
        assert str(start)=='2017-12-25' and str(observed)=='2017-12-26'
