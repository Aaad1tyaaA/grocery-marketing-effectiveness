from pathlib import Path

import duckdb
import pytest

ROOT=Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not (ROOT/'grocery_phase1.duckdb').exists(), reason="local data only")


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect(str(ROOT/'grocery_phase1.duckdb'), read_only=True)
    c.execute("SET memory_limit='512MB'")
    c.execute('SET threads=1')
    yield c
    c.close()


@pytest.fixture(scope='module')
def health_con():
    path=ROOT/'grocery_business_health.duckdb'
    if not path.exists():
        pytest.skip('Build Module 2 first')
    with duckdb.connect(str(path),read_only=True) as c:
        yield c


one = lambda con, sql: con.sql(sql).fetchone()[0]


def test_fact_sales_rows(con):
    assert one(con, "SELECT count(*) FROM fact_sales") == 1_460_487


def test_households(con):
    assert one(con, "SELECT count(*) FROM dim_household") == 2_469


def test_promo_grain_unique(con):
    assert one(con, "SELECT count(*) FROM (SELECT product_id,store_id,week FROM fact_promo GROUP BY ALL HAVING count(*)>1)") == 0


def test_no_voids_left(con):
    assert one(con, "SELECT count(*) FROM fact_sales WHERE quantity = 0 AND sales_value = 0") == 0


def test_every_sale_has_product(con):
    assert one(con, "SELECT count(*) FROM fact_sales f ANTI JOIN dim_product p USING (product_id)") == 0


def test_weekly_kpis_52_weeks(health_con):
    assert one(health_con, "SELECT count(*) FROM weekly_kpis") == 52


def test_discount_depth_range(health_con):
    assert one(health_con, "SELECT count(*) FROM weekly_kpis WHERE discount_depth NOT BETWEEN 0 AND 1") == 0
