"""Exercise cleaning edge cases on synthetic rows, without opening the local database."""
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]


def test_model_preserves_unknowns_free_sales_and_conflicting_promotions():
    with duckdb.connect() as con:
        con.execute("""
        CREATE TABLE transactions(household_id VARCHAR,store_id VARCHAR,basket_id VARCHAR,product_id VARCHAR,
            quantity DOUBLE,sales_value DOUBLE,retail_disc DOUBLE,coupon_disc DOUBLE,coupon_match_disc DOUBLE,
            week INTEGER,transaction_timestamp TIMESTAMP);
        INSERT INTO transactions VALUES
            ('h','s','b','p1',1,0,1,0,0,2,'2017-01-03 05:30:00'),
            ('h','s','b','missing',1,10,1,5,2,2,'2017-01-03 05:30:00'),
            ('h','s','b','fuel',5,20,0,0,0,2,'2017-01-03 05:30:00'),
            ('h','s','void','p1',0,0,0,0,0,2,'2017-01-03 05:30:00');
        CREATE TABLE products(product_id VARCHAR,manufacturer_id VARCHAR,department VARCHAR,brand VARCHAR,
            product_category VARCHAR,product_type VARCHAR,package_size VARCHAR);
        INSERT INTO products VALUES ('p1','m',NULL,'b',NULL,'t','x'),('fuel','m','FUEL','b','FUEL','t','x');
        CREATE TABLE promotions(product_id VARCHAR,store_id VARCHAR,display_location VARCHAR,mailer_location VARCHAR,week INTEGER);
        INSERT INTO promotions VALUES ('p1','s','0','A',2),('p1','s','1','0',2);
        CREATE TABLE demographics(household_id VARCHAR,age VARCHAR);
        INSERT INTO demographics VALUES ('h','35-44');
        CREATE TABLE campaigns(household_id VARCHAR,campaign_id VARCHAR);
        INSERT INTO campaigns VALUES ('h','c'),('h','c');
        CREATE TABLE campaign_descriptions(campaign_id VARCHAR,campaign_type VARCHAR,start_date DATE,end_date DATE);
        INSERT INTO campaign_descriptions VALUES ('c','A','2016-12-20','2017-01-31');
        """)
        con.execute((ROOT / "sql/01_model.sql").read_text(encoding="utf-8"))
        assert con.execute("SELECT count(*) FROM transactions").fetchone()[0] == 4
        assert con.execute("SELECT count(*),sum(sales_value),count(*) FILTER(WHERE sales_value=0) FROM fact_sales").fetchone() == (3,30,1)
        assert con.execute("SELECT department,is_unknown_product,is_non_grocery,shelf_value,retailer_funded_disc FROM fact_sales WHERE product_id='missing'").fetchone() == ('UNKNOWN',True,False,13,3)
        assert con.execute("SELECT is_non_grocery FROM fact_sales WHERE product_id='p1'").fetchone() == (False,)
        assert con.execute("SELECT is_non_grocery FROM fact_sales WHERE product_id='fuel'").fetchone() == (True,)
        assert con.execute("SELECT on_display,in_mailer,display_location,mailer_location,source_row_count,has_conflicting_codes FROM fact_promo").fetchone() == (True,True,'MULTIPLE','MULTIPLE',2,True)
        assert con.execute("SELECT n_campaigns FROM dim_household").fetchone() == (1,)
        assert con.execute("SELECT count(*) FROM bridge_household_campaign").fetchone() == (1,)
        assert con.execute("SELECT partially_observed FROM dim_campaign").fetchone() == (True,)
        assert str(con.execute("SELECT local_ts FROM fact_sales LIMIT 1").fetchone()[0]) == '2017-01-03 00:30:00'
