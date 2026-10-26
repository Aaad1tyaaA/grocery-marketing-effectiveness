"""Independent checks for matching, HC1 inference, placebo history, and week boundaries."""
from pathlib import Path
import sys

import duckdb
import numpy as np
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from campaign_methods import build_frame,match_frame,estimate,holm_adjust,HistoryUnavailable


def test_hc1_matches_general_matrix_sandwich_and_weight_scaling():
    frame=pd.DataFrame({'treated':[True]*4+[False]*5,
                        'change':[4.,-3.,8.,2.,1.,-1.,4.,6.,-2.],
                        'w':[1.,1.,1.,1.,.2,.8,1.5,2.,.5]})
    result=estimate(frame)
    x=np.column_stack([np.ones(len(frame)),frame.treated.astype(float)])
    y=frame.change.to_numpy();w=frame.w.to_numpy()
    bread=np.linalg.inv(x.T@np.diag(w)@x)
    beta=bread@x.T@np.diag(w)@y
    residual=y-x@beta
    covariance=(len(frame)/(len(frame)-2))*bread@(x.T@np.diag((w*residual)**2)@x)@bread
    assert result['estimate']==pytest.approx(beta[1])
    assert result['se']==pytest.approx(np.sqrt(covariance[1,1]))
    assert result['ci_low']==pytest.approx(beta[1]-1.959963984540054*np.sqrt(covariance[1,1]))
    scaled=estimate(frame.assign(w=frame.w*100))
    assert scaled['estimate']==pytest.approx(result['estimate'])
    assert scaled['se']==pytest.approx(result['se'])
    assert scaled['control_ess']==pytest.approx(result['control_ess'])
    assert estimate(frame,weighted=False)['estimate']==pytest.approx(
        frame.loc[frame.treated,'change'].mean()-frame.loc[~frame.treated,'change'].mean())


def test_matching_balances_stratum_shares_and_preserves_ties():
    group=np.repeat(np.arange(20),8)
    frame=pd.DataFrame({'m_spend':group.astype(float),'m_active':4,
                        'treated':np.arange(160)%8<(group%3+1),'w':1.0,'change':0.0})
    matched=match_frame(frame,tie_preserving=True)
    assert len(matched)==len(frame)
    treated=matched[matched.treated].groupby('stratum').w.sum()
    control=matched[~matched.treated].groupby('stratum').w.sum()
    np.testing.assert_allclose(treated/treated.sum(),control/control.sum())
    assert matched.w.gt(0).all() and matched.loc[matched.treated,'w'].eq(1).all()
    tied=match_frame(frame.assign(m_spend=1),tie_preserving=True)
    assert tied.stratum.nunique()==1
    assert match_frame(frame.assign(treated=True)).empty
    assert match_frame(frame.iloc[:0]).empty
    assert estimate(frame.iloc[:0])['status']=='not_estimable_insufficient_common_support'


def panels():
    spend=pd.DataFrame(np.tile(np.arange(2,54),(4,1)),index=['1','2','3','4'],columns=range(2,54),dtype=float)
    return spend,spend.gt(0),pd.DataFrame({'campaign_id':[8],'household_id':[1]})


def test_matching_never_uses_during_outcomes_and_ids_are_labels():
    spend,active,recipients=panels()
    original=build_frame(spend,active,recipients,'8',20,26,match_on='earlier')
    altered=spend.copy();altered.loc[:,20:26]+=10000
    changed=build_frame(altered,active,recipients,8,20,26,match_on='earlier')
    assert original.loc['1','treated']
    assert original.treated.sum()==1
    assert original.m_spend.eq(np.mean(range(4,12))).all()
    assert original.pre.eq(np.mean(range(12,20))).all()
    pd.testing.assert_frame_equal(original[['m_spend','m_active','pre']],changed[['m_spend','m_active','pre']])
    assert (changed.during-original.during).eq(10000).all()


def test_missing_history_and_invalid_panels_are_rejected():
    spend,active,recipients=panels()
    with pytest.raises(HistoryUnavailable):
        build_frame(spend,active,recipients,8,20,26,match_on='earlier',shift=8)
    with pytest.raises(ValueError,match='match_on'):
        build_frame(spend,active,recipients,8,20,26,match_on='typo')
    with pytest.raises(ValueError,match='identical'):
        build_frame(spend,active.iloc[::-1],recipients,8,20,26)
    spend.loc['1',12]=np.nan
    with pytest.raises(ValueError,match='non-finite'):
        build_frame(spend,active,recipients,8,20,26)


def test_holm_adjustment_order_ties_and_invalid_values():
    np.testing.assert_allclose(holm_adjust([.04,.01,.03]),[.06,.03,.06])
    np.testing.assert_allclose(holm_adjust([.01,.01,1]),[.03,.03,1])
    assert len(holm_adjust([]))==0
    for values in [[np.nan],[1.1],[-.1]]:
        with pytest.raises(ValueError):
            holm_adjust(values)


def test_campaign_week_audit_exposes_tuesday_start():
    with duckdb.connect() as con:
        con.execute("""CREATE TABLE fact_sales AS
          SELECT 'h' AS household_id,week::INTEGER AS week,
                 TIMESTAMP '2017-01-02'+(week-2)*INTERVAL 7 DAY AS local_ts,
                 10.0 AS sales_value,false AS is_non_grocery,0.0 AS coupon_disc
          FROM range(2,54) w(week);
        CREATE TABLE dim_campaign(campaign_id VARCHAR,campaign_type VARCHAR,start_date DATE,end_date DATE,partially_observed BOOLEAN);
        INSERT INTO dim_campaign VALUES ('13','Type A','2017-08-08','2017-09-24',false);
        CREATE TABLE campaigns(campaign_id VARCHAR,household_id VARCHAR);
        INSERT INTO campaigns VALUES ('13','h');
        CREATE TABLE coupon_redemptions(campaign_id VARCHAR,household_id VARCHAR);""")
        con.execute((ROOT/'sql/05_campaigns.sql').read_text(encoding='utf-8'))
        assert con.execute('SELECT start_week,end_week FROM campaign_windows').fetchone()==(33,39)
        assert con.execute('SELECT campaign_calendar_days,modeled_calendar_days,extra_days_before_start,extra_days_after_end,off_date_grocery_sales_all_households FROM campaign_window_audit').fetchone()==(48,49,1,0,10)
