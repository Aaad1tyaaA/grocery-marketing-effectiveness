"""Checks for empirical resampling, holdout isolation, quota boundaries and policy value."""
from pathlib import Path
import itertools
import sys
import duckdb
import numpy as np
import pandas as pd
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from hillstrom_methods import ARMS,CONTROL,bootstrap_means,contrast,fit_policy,policy_value


def test_count_bootstrap_matches_exhaustive_row_bootstrap_moments():
    data=np.array([0.,0.,1.,7.])
    exact=np.array([np.mean(x) for x in itertools.product(data,repeat=len(data))])
    sampled=bootstrap_means(data,np.random.default_rng(14),50000)
    assert sampled.mean()==pytest.approx(exact.mean(),abs=.03)
    assert sampled.var()==pytest.approx(exact.var(),rel=.025)
    assert np.array_equal(bootstrap_means([3,3],np.random.default_rng(1),30),np.full(30,3.0))
    for values in [[],[np.nan],[np.inf]]:
        with pytest.raises(ValueError):
            bootstrap_means(values,np.random.default_rng(1))


def test_contrasts_use_all_assigned_customers_not_buyers():
    result=contrast([0,0,0,8],[0,0,0,4],np.random.default_rng(42),100)
    assert result['estimate']==1 and result['treatment_mean']==2 and result['control_mean']==1
    assert result['n_treatment']==result['n_control']==4
    zero=contrast([0,0],[0,0],np.random.default_rng(1),100)
    assert zero['estimate']==0 and zero['p_value']==1
    assert contrast([1],[0,1],np.random.default_rng(1),100)['status'].startswith('not_estimable')


def policy_fixture():
    n=900
    return pd.DataFrame({'source_row':np.arange(1,n+1),'cell':np.repeat(['A','B','C'],300),
        'segment':np.tile([*ARMS,CONTROL],300),
        'spend':np.tile([5.,3.,1.],300)+np.repeat([0.,2.,4.],300)})


def test_policy_quotas_disjoint_and_deterministic_under_reordering():
    h=policy_fixture();rules,a=fit_policy(h,7,quota=50)
    _,b=fit_policy(h.sample(frac=1,random_state=4),7,quota=50)
    pd.testing.assert_frame_equal(a,b)
    assert len(a[a.decision=='target'])==len(a[a.decision=='suppress'])==50
    assert not set(a[a.decision=='target'].source_row)&set(a[a.decision=='suppress'].source_row)
    assert rules.exact_target.sum()==rules.exact_suppress.sum()==50
    assert set(a.half)=={0,1}


def test_policy_does_not_learn_from_holdout_outcomes_or_assignments():
    h=policy_fixture();rules,a=fit_policy(h,7,quota=100)
    ids=set(a.loc[a.half==1,'source_row'])
    changed=h.copy()
    changed.loc[changed.source_row.isin(ids),'spend']=100000
    changed.loc[changed.source_row.isin(ids),'segment']=CONTROL
    rules_after,a_after=fit_policy(changed,7,quota=100)
    pd.testing.assert_frame_equal(rules,rules_after)
    pd.testing.assert_frame_equal(a,a_after)


def test_unsupported_training_cells_and_infeasible_quota_rejected():
    h=policy_fixture()
    with pytest.raises(ValueError,match='feasible'):
        fit_policy(h,7,quota=451)
    with pytest.raises(ValueError,match='support'):
        fit_policy(h[h.segment!=CONTROL],7,quota=20)


def test_policy_value_uses_known_randomization_probability_and_paired_difference():
    h=pd.DataFrame({'segment':[*ARMS,CONTROL],'recommended_email':ARMS[1], 'spend':[10.,8.,2.]})
    result=policy_value(h,'spend',np.random.default_rng(42),100)
    assert result['estimate']==6 and result['always_mens_estimate']==8
    assert result['policy_minus_mens']==-2
    h['recommended_email']=ARMS[0]
    same=policy_value(h,'spend',np.random.default_rng(42),100)
    assert same['policy_minus_mens']==same['policy_minus_mens_ci_low']==same['policy_minus_mens_ci_high']==0


def test_feature_boundaries_and_no_merchandise_gender_inference():
    h=pd.DataFrame({'source_row':[1,2,3,4],'recency':[3,4,8,9],
        'history_segment':['x']*4,'history':[199.99,200.,250.,500.],
        'mens':[1,0,1,0],'womens':[0,1,1,0],'zip_code':['Urban']*4,
        'newbie':[0,1,0,1],'channel':['Web']*4,'segment':[CONTROL]*4,
        'visit':[0]*4,'conversion':[0]*4,'spend':[0.]*4})
    with duckdb.connect() as con:
        con.register('hillstrom_input',h)
        con.execute((ROOT/'sql/06_hillstrom.sql').read_text(encoding='utf-8'))
        assert con.execute('SELECT recency_band,value_band,buyer FROM hillstrom ORDER BY source_row').fetchall()==[
            ('1-3','low','mens only'),('4-8','high','womens only'),('4-8','high','both'),('9-12','high','neither')]
