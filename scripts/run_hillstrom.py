"""Word guide Module 6: randomized contrasts, exploratory cuts, and frozen-policy validation."""
from pathlib import Path
import hashlib
import json
import os
import duckdb
import numpy as np
import pandas as pd
from scipy import stats

from campaign_methods import holm_adjust
from hillstrom_methods import ARMS,CONTROL,METRICS,contrast,fit_policy,policy_value
from provenance import build_inputs

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'exports/hillstrom'
DOCS=ROOT/'docs/hillstrom'
REPS=2000


def adjusted(frame):
    frame=frame.copy();frame['p_holm']=np.nan
    supported=frame.status.eq('estimated')
    frame.loc[supported,'p_holm']=holm_adjust(frame.loc[supported,'p_value'])
    frame['reject_zero_holm_05']=frame.p_holm<.05
    return frame


def baseline_balance(h):
    features={name:h[name].astype(float) for name in ['recency','history','newbie','mens','womens']}
    for name in ['zip_code','channel']:
        for level in sorted(h[name].unique()):
            features[name+'='+level]=h[name].eq(level).astype(float)
    rows=[]
    for arm in ARMS:
        for name,values in features.items():
            t=values[h.segment==arm];c=values[h.segment==CONTROL]
            scale=np.sqrt((t.var(ddof=1)+c.var(ddof=1))/2)
            rows.append({'arm':arm,'baseline_feature':name,'treatment_mean':t.mean(),'control_mean':c.mean(),
                         'standardized_mean_difference':(t.mean()-c.mean())/scale if scale else 0.0})
    return pd.DataFrame(rows)


def main():
    final=ROOT/'grocery_hillstrom.duckdb';staging=ROOT/'grocery_hillstrom.building.duckdb'
    if final.exists() or staging.exists():
        raise FileExistsError('Preserving existing Hillstrom database; use a fresh copy to recalculate.')
    OUT.mkdir(parents=True,exist_ok=True);DOCS.mkdir(parents=True,exist_ok=True)
    source=json.loads((ROOT/'docs/hillstrom_source.json').read_text(encoding='utf-8'))
    for relative,key in [('data/raw/hillstrom.csv','csv_sha256'),('data/parquet/hillstrom.parquet','parquet_sha256')]:
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==source[key],relative
    raw=pd.read_csv(ROOT/'data/raw/hillstrom.csv')
    pd.testing.assert_frame_equal(raw,pd.read_parquet(ROOT/'data/parquet/hillstrom.parquet'))
    raw.insert(0,'source_row',np.arange(1,len(raw)+1))
    rng=np.random.default_rng(42)
    with duckdb.connect() as con:
        con.execute("SET memory_limit='512MB'");con.execute('SET threads=1')
        con.register('hillstrom_input',raw)
        con.execute((ROOT/'sql/06_hillstrom.sql').read_text(encoding='utf-8'))
        checks=[{'check_name':name,'passed':bool(p)} for name,p in con.execute('SELECT * FROM hillstrom_checks').fetchall()]
        assert all(c['passed'] for c in checks),checks
        h=con.execute('SELECT * FROM hillstrom ORDER BY source_row').df()
        summary=con.execute('SELECT * FROM hillstrom_arm_summary ORDER BY segment').df()
        profile=con.execute('SELECT * FROM hillstrom_profile').df()
        srm_test=stats.chisquare(summary.customers.to_numpy())
        srm=pd.DataFrame([{'expected_assignment_probability':1/3,'arms':3,'customers':len(h),
                           'chi_square':float(srm_test.statistic),'degrees_of_freedom':2,
                           'p_value':float(srm_test.pvalue),'warning_threshold':.01,
                           'sample_ratio_warning':bool(srm_test.pvalue<.01)}])
        control=h[h.segment==CONTROL]
        primary=[];direct=[];segments=[]
        for arm in ARMS:
            for metric in METRICS:
                primary.append({'arm':arm,'reference_arm':CONTROL,'metric':metric,
                                **contrast(h.loc[h.segment==arm,metric],control[metric],rng,REPS)})
        for metric in METRICS:
            direct.append({'arm':ARMS[0],'reference_arm':ARMS[1],'metric':metric,
                           **contrast(h.loc[h.segment==ARMS[0],metric],h.loc[h.segment==ARMS[1],metric],rng,REPS)})
        primary=adjusted(pd.DataFrame(primary));direct=adjusted(pd.DataFrame(direct))
        cuts=['buyer','newbie','channel','zip_code','history_segment','recency_band']
        for cut in cuts:
            for level,group in h.groupby(cut,observed=True,sort=True):
                for arm in ARMS:
                    for metric in METRICS:
                        segments.append({'cut':cut,'level':str(level),'arm':arm,'metric':metric,
                            **contrast(group.loc[group.segment==arm,metric],group.loc[group.segment==CONTROL,metric],rng,REPS)})
        segments=adjusted(pd.DataFrame(segments))
        all_rules=[];all_assignments=[];evaluations=[];values=[];audiences=[]
        for seed in [7,8]:
            rules,assignments=fit_policy(h,seed)
            all_rules.append(rules);all_assignments.append(assignments)
            evaluation=assignments.merge(h[['source_row','segment',*METRICS]],on='source_row',validate='one_to_one')
            groups=[('exact','target',evaluation.decision.eq('target')),
                    ('exact','suppress',evaluation.decision.eq('suppress')),
                    ('exact','other',evaluation.decision.eq('other')),
                    ('guide_whole_cells','target',evaluation.target_whole_cell),
                    ('guide_whole_cells','suppress',evaluation.suppress_whole_cell),
                    ('guide_whole_cells','not_targeted',~evaluation.target_whole_cell)]
            for scope,audience,mask in groups:
                heldout=evaluation.loc[mask & evaluation.half.eq(1)]
                audiences.append({'seed':seed,'scope':scope,'audience':audience,
                                  'population_customers':int(mask.sum()),'heldout_customers':len(heldout)})
                for arm in ARMS:
                    for metric in METRICS:
                        evaluations.append({'seed':seed,'scope':scope,'audience':audience,'arm':arm,'metric':metric,
                            **contrast(heldout.loc[heldout.segment==arm,metric],heldout.loc[heldout.segment==CONTROL,metric],rng,REPS)})
                if scope=='exact':
                    for metric in METRICS:
                        values.append({'seed':seed,'audience':audience,'metric':metric,
                                       **policy_value(heldout,metric,rng,REPS)})
        rules=pd.concat(all_rules,ignore_index=True)
        assignments=pd.concat(all_assignments,ignore_index=True)
        heldout=adjusted(pd.DataFrame(evaluations));values=pd.DataFrame(values)
        counts=pd.DataFrame(audiences)
        balance=baseline_balance(h)
        checks.extend([
            {'check_name':'source_csv_parquet_agree','passed':True},
            {'check_name':'no_sample_ratio_warning','passed':bool(srm.p_value.iloc[0]>=.01)},
            {'check_name':'six_primary_three_direct_contrasts','passed':len(primary)==6 and len(direct)==3},
            {'check_name':'primary_effects_finite','passed':bool(np.isfinite(primary[['estimate','ci_low','ci_high','p_holm']]).all().all())},
            {'check_name':'primary_means_match_sql','passed':all(abs(r.control_mean-summary.loc[summary.segment==CONTROL,{'visit':'visit_rate','conversion':'conversion_rate','spend':'spend_per_assigned_customer'}[r.metric]].iloc[0])<1e-12 for r in primary.itertuples())},
            {'check_name':'bootstrap_intervals_ordered','passed':bool((primary.ci_low<=primary.ci_high).all())},
            {'check_name':'holm_not_below_raw_p','passed':bool((primary.p_holm>=primary.p_value-1e-12).all())},
            {'check_name':'two_seed_frozen_cell_rules','passed':len(rules)==2*int(profile.pre_treatment_cells.iloc[0]) and not rules[['seed','cell']].duplicated().any()},
            {'check_name':'128000_unique_seed_customer_assignments','passed':len(assignments)==128000 and not assignments[['seed','source_row']].duplicated().any()},
            {'check_name':'exact_target_suppression_quotas','passed':bool(counts.loc[(counts.scope=='exact') & counts.audience.isin(['target','suppress']),'population_customers'].eq(10000).all())},
            {'check_name':'no_target_suppression_overlap','passed':all(len(g[g.decision=='target'].source_row.isin(g[g.decision=='suppress'].source_row).loc[lambda x:x])==0 for _,g in assignments.groupby('seed'))},
            {'check_name':'assignment_rows_partition_population','passed':bool(counts[counts.scope=='exact'].groupby('seed').population_customers.sum().eq(64000).all())},
            {'check_name':'training_arm_counts_reconcile','passed':all(int(g[['train_n_control','train_n_mens','train_n_womens']].sum().sum())==int(((assignments.seed==seed)&(assignments.half==0)).sum()) for seed,g in rules.groupby('seed'))},
            {'check_name':'heldout_policy_results_finite','passed':bool(np.isfinite(values.select_dtypes(include='number')).all().all())},
            {'check_name':'baseline_balance_finite','passed':bool(np.isfinite(balance.standardized_mean_difference).all())},
        ])
        assert all(bool(c['passed']) for c in checks),checks
        datasets={'hillstrom':h,'hillstrom_arm_summary':summary,'hillstrom_profile':profile,
                  'hillstrom_srm':srm,'hillstrom_balance':balance,'hillstrom_effects':primary,
                  'email_head_to_head':direct,'segment_effects':segments,'policy_rules':rules,
                  'policy_assignments':assignments,'heldout_effects':heldout,'heldout_policy_value':values,
                  'policy_audience_counts':counts,'hillstrom_checks':pd.DataFrame(checks)}
        for name,frame in datasets.items():
            frame.to_csv(OUT/f'{name}.csv',index=False,encoding='utf-8-sig')
        primary.to_csv(ROOT/'exports/hillstrom_readout.csv',index=False,encoding='utf-8-sig')
        for decision in ['target','suppress']:
            candidates=assignments[(assignments.seed==7)&(assignments.decision==decision)].copy()
            candidates['population_default_email']=ARMS[0]
            candidates['variant_suggestion_status']='training_only_not_validated'
            candidates.to_csv(OUT/f'{decision}_10000.csv',index=False,encoding='utf-8-sig')
        path=staging.as_posix().replace("'","''")
        con.execute(f"ATTACH '{path}' AS reporting")
        for name,frame in datasets.items():
            con.register('report_frame',frame)
            con.execute(f'CREATE TABLE reporting.main.{name} AS SELECT * FROM report_frame')
            con.unregister('report_frame')
        con.execute('DETACH reporting')
        report={'guide_steps':'1.6.1–1.6.5','source':source,'bootstrap_replicates':REPS,'bootstrap_seed':42,
                'policy_seeds':[7,8],'primary_policy_seed':7,'quota':10000,
                'bootstrap_method':'Empirical multinomial resampling of repeated values; exact distribution of ordinary row-bootstrap means',
                'multiplicity':'Holm families: 6 primary, 3 head-to-head, all exploratory segment rows, all held-out fixed-arm rows; bootstrap intervals remain pointwise',
                'policy_method':'Training half ranks pre-treatment cells; seeded outcome-free tie breaks fill exact quotas; validation uses held-out half only',
                'policy_value_method':'Horvitz-Thompson at known 1/3 assignment probability; conditional on learned rule; paired difference versus always-Mens',
                'arm_summary':summary.to_dict('records'),'srm':srm.to_dict('records'),
                'primary_results':primary.to_dict('records'),'head_to_head':direct.to_dict('records'),
                'audience_counts':counts.to_dict('records'),'checks':checks}
        report['build_inputs_sha256']=build_inputs(ROOT,['scripts/run_hillstrom.py','scripts/get_hillstrom.py',
            'scripts/hillstrom_methods.py','scripts/campaign_methods.py','sql/06_hillstrom.sql',
            'docs/hillstrom_source.json','requirements-hillstrom.txt'])
        clean=json.loads(pd.Series({'report':report}).to_json())['report']
        (DOCS/'verification.json').write_text(json.dumps(clean,indent=2),encoding='utf-8')
    os.rename(staging,final)
    with duckdb.connect(str(final),read_only=True) as con:
        assert con.execute('SELECT bool_and(passed) FROM hillstrom_checks').fetchone()[0]
    print(f'PASS: {len(checks)} Hillstrom checks; SRM p={float(srm.p_value.iloc[0]):.6f}')
    print(primary[['arm','metric','estimate','ci_low','ci_high','p_holm']].to_string(index=False))
    print('DIRECT EMAIL COMPARISON\n'+direct[['metric','estimate','ci_low','ci_high','p_holm']].to_string(index=False))
    print('HELD-OUT SPEND\n'+heldout[heldout.metric.eq('spend')][['seed','scope','audience','arm','n_treatment','n_control','estimate','ci_low','ci_high']].to_string(index=False))


if __name__=='__main__':
    main()
