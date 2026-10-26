"""Check complete pair panels, promotion sequences, conflicts, and sensitivity scopes."""
from pathlib import Path
import duckdb

ROOT=Path(__file__).resolve().parents[1]


def fixture():
    con=duckdb.connect()
    con.execute("""CREATE TABLE fact_sales(product_id VARCHAR,store_id VARCHAR,week INTEGER,quantity DOUBLE,is_non_grocery BOOLEAN);
    INSERT INTO fact_sales SELECT 'p','s',range,
        CASE range WHEN 2 THEN 2 WHEN 3 THEN 20 WHEN 4 THEN 9 WHEN 5 THEN 30
        WHEN 6 THEN 40 WHEN 7 THEN 10 WHEN 8 THEN 4 WHEN 9 THEN 6 END,false FROM range(2,10);
    INSERT INTO fact_sales SELECT 'zero','s',range,1,false FROM range(2,10);
    INSERT INTO fact_sales SELECT 'short','s',range,1,false FROM range(2,9);
    CREATE TABLE promotions(product_id VARCHAR,store_id VARCHAR,week INTEGER,display_location VARCHAR,mailer_location VARCHAR);
    INSERT INTO promotions SELECT 'p','s',range,
        CASE WHEN range IN(3,6) THEN '1' ELSE '0' END,
        CASE WHEN range IN(5,6) THEN 'A' ELSE '0' END FROM range(2,54) WHERE range<>11;
    INSERT INTO promotions VALUES ('p','s',3,'9','0');
    INSERT INTO promotions SELECT 'zero','s',range,CASE WHEN range<=9 THEN '1' ELSE '0' END,'0' FROM range(2,54);""")
    con.execute((ROOT/'sql/04_promo.sql').read_text())
    return con


def test_complete_panel_and_sequence_flags():
    with fixture() as con:
        assert con.execute('SELECT count(*) FROM pairs').fetchone()[0]==2
        assert con.execute('SELECT count(*) FROM promo_panel').fetchone()[0]==104
        assert con.execute("SELECT units FROM promo_panel WHERE product_id='p' AND week=10").fetchone()[0]==0
        assert con.execute("SELECT week_after,two_back FROM promo_panel_flags WHERE product_id='p' AND week=4").fetchone()==(True,False)
        assert con.execute("SELECT week_after,two_back FROM promo_panel_flags WHERE product_id='p' AND week=7").fetchone()==(True,True)
        assert con.execute("SELECT display_location,has_conflicting_codes,on_display FROM panel_promotions WHERE product_id='p' AND week=3").fetchone()==('MULTIPLE',True,True)
        assert con.execute('SELECT bool_and(passed) FROM promotion_checks').fetchone()[0]
        assert con.execute('SELECT count(*) FROM fact_sales').fetchone()[0]==23


def test_missing_metadata_and_zero_baseline_sensitivities():
    with fixture() as con:
        assert con.execute('SELECT missing_metadata_pair_weeks,zero_unit_baseline_pairs FROM promotion_coverage').fetchone()==(1,1)
        assert con.execute("SELECT promo_observed,promoted FROM promo_panel_flags WHERE product_id='p' AND week=11").fetchone()==(False,False)
        assert con.execute("SELECT previous_promo_observed FROM promo_panel_flags WHERE product_id='p' AND week=12").fetchone()[0] is False
        assert con.execute('SELECT sum(pair_weeks) FROM promo_lift_observed_only').fetchone()[0]==100
        assert con.execute('SELECT sum(pair_weeks) FROM promo_lift_positive_baseline').fetchone()[0]==52
        assert con.execute('SELECT count(*) FROM promo_lift WHERE abs(lift_index-observed_units/expected_baseline_units)>0.000001').fetchone()[0]==0


def test_event_only_metadata_does_not_invent_observed_controls():
    with fixture() as con:
        con.execute("DELETE FROM promotions WHERE display_location='0' AND mailer_location='0'")
        con.execute((ROOT/'sql/04_promo.sql').read_text())
        assert con.execute('SELECT count(*) FROM observed_pair_baseline').fetchone()[0]==0
        assert con.execute('SELECT count(*) FROM promo_lift_observed_only').fetchone()[0]==0
        assert con.execute('SELECT observed_metadata_pair_weeks=promoted_pair_weeks FROM promotion_coverage').fetchone()[0] is True
