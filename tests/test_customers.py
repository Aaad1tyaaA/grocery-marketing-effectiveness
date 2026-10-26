"""Regressions for segmentation precedence, trajectory boundaries and cohort censoring."""
from pathlib import Path
import duckdb

ROOT=Path(__file__).resolve().parents[1]


def fixture():
    con=duckdb.connect()
    con.execute("""CREATE TABLE fact_sales(household_id VARCHAR,basket_id VARCHAR,week INTEGER,
        local_ts TIMESTAMP,sales_value DOUBLE,retailer_funded_disc DOUBLE,shelf_value DOUBLE,is_non_grocery BOOLEAN);
    INSERT INTO fact_sales VALUES
        ('lapsed','b1',2,'2017-01-03',20000,0,20000,false),
        ('grow','b2',2,'2017-01-03',100,10,110,false),
        ('grow','b3',53,'2017-12-31',120,0,120,false),
        ('decline','b4',2,'2017-01-03',100,0,100,false),
        ('decline','b5',53,'2017-12-31',80,0,80,false),
        ('stable','b6',2,'2017-01-03',100,0,100,false),
        ('stable','b7',53,'2017-12-31',100,0,100,false),
        ('new','b8',53,'2017-12-31',100,0,100,false),
        ('partial','b9',1,'2017-01-01',500,0,500,false),
        ('fuel','b10',2,'2017-01-03',1000,0,1000,true),
        ('free','b11',2,'2017-01-03',0,10,10,false);
    CREATE TABLE dim_household AS SELECT DISTINCT household_id,household_id='grow' AS has_demographics FROM fact_sales;
    CREATE TABLE demographics(household_id VARCHAR,income VARCHAR);
    INSERT INTO demographics VALUES ('grow','50-74K');""")
    con.execute((ROOT/'sql/03_customers.sql').read_text())
    return con


def test_trajectory_boundaries_and_lapsed_precedence():
    with fixture() as con:
        results=dict(con.execute('SELECT household_id,trajectory FROM hh_segments').fetchall())
        assert results['grow']=='Growing'
        assert results['decline']=='Declining'
        assert results['stable']=='Stable'
        assert results['new']=='New in H2'
        assert results['lapsed']=='Gone in H2'
        assert results['partial']=='Only partial week 1 or zero spend'
        assert results['free']=='Only partial week 1 or zero spend'
        assert 'fuel' not in results
        assert con.execute("SELECT segment FROM hh_segments WHERE household_id='lapsed'").fetchone()[0]=='5 Lapsed'
        assert con.execute('SELECT bool_and(passed) FROM customer_checks').fetchone()[0]


def test_retention_zero_months_and_future_cells():
    with fixture() as con:
        assert con.execute("SELECT active,retention FROM cohort_retention WHERE cohort=DATE '2017-01-01' AND months_since_first=1").fetchone()==(0,0)
        assert con.execute("SELECT count(*),max(months_since_first) FROM cohort_retention WHERE cohort=DATE '2017-12-01'").fetchone()==(1,0)
        # The all-purchase cohort includes the non-grocery-only household; segments do not.
        assert con.execute('SELECT sum(cohort_size) FROM cohort_retention WHERE months_since_first=0').fetchone()[0]==8
        assert con.execute('SELECT count(*) FROM hh_segments').fetchone()[0]==7
        assert con.execute('SELECT count(*) FROM cohort_retention WHERE months_since_first=0 AND retention<>1').fetchone()[0]==0
