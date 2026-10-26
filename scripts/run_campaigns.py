"""Complete Word guide Module 5 with explicit samples, placebo checks and exposure audits."""
from pathlib import Path
import json
import os
import duckdb
from provenance import build_inputs
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from campaign_methods import build_frame,match_frame,estimate,balance_rows,HistoryUnavailable,holm_adjust

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'exports/campaigns'
DOCS=ROOT/'docs/campaigns'
METHODS=['naive','unmatched','matched_pre','matched_earlier']


def save(frame,name):
    frame.to_csv(OUT/f'{name}.csv',index=False,encoding='utf-8-sig')


def main():
    for p in [OUT,DOCS,ROOT/'charts']:
        p.mkdir(parents=True,exist_ok=True)
    final=ROOT/'grocery_campaigns.duckdb'
    staging=ROOT/'grocery_campaigns.building.duckdb'
    if final.exists() or staging.exists():
        raise FileExistsError('Preserving existing campaign reporting database; rename it before rebuilding.')
    baseline=json.loads((ROOT/'docs/verification.json').read_text())['tables']
    with duckdb.connect() as con:
        con.execute("SET memory_limit='512MB'")
        con.execute('SET threads=1')
        for name in ['transactions','products','campaigns','campaign_descriptions','coupon_redemptions']:
            path=(ROOT/'data/parquet'/f'{name}.parquet').as_posix().replace("'","''")
            con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{path}')")
            actual=con.execute(f'SELECT count(*),bit_xor(hash(t))::VARCHAR FROM {name} t').fetchone()
            assert actual==(baseline[name]['rows'],baseline[name]['content_fingerprint']),name
        statements=con.extract_statements((ROOT/'sql/01_model.sql').read_text())
        for index in [0,1,4]:
            con.execute(statements[index].query)
        con.execute((ROOT/'sql/05_campaigns.sql').read_text())
        checks=[{'check_name':n,'passed':bool(p)} for n,p in con.execute('SELECT * FROM campaign_checks ORDER BY check_name').fetchall()]
        assert all(c['passed'] for c in checks),checks
        hw=con.execute('SELECT * FROM hh_week ORDER BY household_id,week').df()
        recipients=con.execute('SELECT DISTINCT campaign_id,household_id FROM campaigns').df()
        descriptions=con.execute('SELECT * FROM campaign_descriptions').df()
        wins=con.execute("SELECT * FROM campaign_windows WHERE campaign_type='Type A' AND start_week>=20 AND end_week<=53 ORDER BY start_week").df()
        overview=con.execute('SELECT * FROM campaign_overview ORDER BY start_date').df()
        roi=con.execute('SELECT * FROM campaign_roi_inputs ORDER BY start_week').df()
        coupon=con.execute('SELECT * FROM coupon_amount_summary').df()
        window_audit=con.execute('SELECT * FROM campaign_window_audit ORDER BY start_week').df()
        weeks=con.execute('SELECT * FROM dim_week ORDER BY week').df().set_index('week')
        spend=hw.pivot(index='household_id',columns='week',values='spend').sort_index()
        active=hw.pivot(index='household_id',columns='week',values='active').sort_index()
        rows=[];guide=[];placebos=[];sensitivities=[];balance=[];overlaps=[];trends=[];samples=[];pretrends=[]
        common_support_ok=True

        def record(cid,method,frame,kind='primary',outcome='change',weighted=True):
            nonlocal common_support_ok
            result={'campaign_id':str(cid),'method':method,'analysis_kind':kind,**estimate(frame,outcome,weighted)}
            result['supported_strata']=int(frame.stratum.nunique()) if 'stratum' in frame else 0
            if 'stratum' in frame and not frame.empty:
                shares=[]
                for treated in [False,True]:
                    x=frame[frame.treated==treated]
                    shares.append(x.groupby('stratum').w.sum()/x.w.sum())
                common_support_ok &= bool(np.allclose(shares[0].sort_index(),shares[1].sort_index()))
                s=frame[['treated','w','stratum']].reset_index()
                s['campaign_id']=str(cid);s['method']=method;s['analysis_kind']=kind
                samples.append(s)
            return result

        for win in wins.itertuples():
            cid=str(win.campaign_id);start=int(win.start_week);end=int(win.end_week)
            pre=build_frame(spend,active,recipients,cid,start,end)
            earlier=build_frame(spend,active,recipients,cid,start,end,match_on='earlier')
            a=match_frame(pre);b=match_frame(earlier)
            trend=b.copy()
            trend['pretrend_change']=(spend.loc[b.index,list(range(start-4,start))].mean(axis=1)
                                      -spend.loc[b.index,list(range(start-8,start-4))].mean(axis=1))
            pretrends.append({'campaign_id':cid,'contrast':'last_4_pre_weeks_minus_first_4',
                              **estimate(trend,'pretrend_change')})
            for method,frame,outcome,weighted in [('naive',pre,'during',False),('unmatched',pre,'change',False),('matched_pre',a,'change',True),('matched_earlier',b,'change',True)]:
                row=record(cid,method,frame,outcome=outcome,weighted=weighted)
                row.update(start_week=start,end_week=end,weeks=end-start+1,
                           eligible_treated=int(pre.treated.sum()),eligible_control=int((~pre.treated).sum()))
                rows.append(row)
            # The guide trims to pre-matching support even for its naive/unmatched comparisons.
            for method,frame,outcome,weighted in [('naive',a,'during',False),('unmatched',a,'change',False),('matched_pre',a,'change',True),('matched_earlier',b,'change',True)]:
                guide.append(record(cid,method,frame,'guide_shared_support',outcome,weighted))
            for method,base,matched in [('matched_pre',pre,a),('matched_earlier',earlier,b)]:
                balance.extend(balance_rows(base,matched,cid,method))
            for match_on in ['pre','earlier']:
                method='matched_'+match_on
                try:
                    fake=build_frame(spend,active,recipients,cid,start,end,match_on=match_on,shift=8)
                    result=record(cid,method,match_frame(fake),'placebo')
                except HistoryUnavailable:
                    result={'campaign_id':cid,'method':method,'analysis_kind':'placebo',
                            'status':'not_estimable_insufficient_history','estimate':np.nan,
                            'se':np.nan,'ci_low':np.nan,'ci_high':np.nan,'p_value':np.nan,'n_treated':0,'n_control':0}
                result.update(pseudo_start_week=start-8,pseudo_end_week=end-8,
                              last_pseudo_week_before_actual=(end-8<start))
                placebos.append(result)
            tied=match_frame(earlier,tie_preserving=True)
            sensitivities.append(record(cid,'earlier_tie_preserving_quantiles',tied,'sensitivity'))
            balance.extend(balance_rows(earlier,tied,cid,'earlier_tie_preserving_quantiles'))

            # Audit any other assigned campaign intersecting the 8-week pre + campaign window.
            lo=pd.Timestamp(weeks.loc[start-8,'week_start'])
            hi=pd.Timestamp(weeks.loc[end,'week_start'])+pd.Timedelta(days=6)
            others=descriptions[(descriptions.campaign_id!=cid)&(descriptions.start_date<=hi)&(descriptions.end_date>=lo)]
            exposed=set(recipients.loc[recipients.campaign_id.isin(others.campaign_id),'household_id'])
            contaminated=earlier.index.isin(exposed)
            overlaps.append({'campaign_id':cid,'audit_start':lo,'audit_end':hi,
                'other_campaigns':len(others),'eligible_treated':int(earlier.treated.sum()),
                'treated_receiving_other_campaign':int((earlier.treated & contaminated).sum()),
                'eligible_controls':int((~earlier.treated).sum()),
                'controls_receiving_other_campaign':int((~earlier.treated & contaminated).sum())})
            clean=earlier.loc[~contaminated].copy()
            clean_matched=match_frame(clean)
            sensitivities.append(record(cid,'earlier_excluding_other_campaign_recipients',clean_matched,'sensitivity'))
            for week in range(start-8,end+1):
                f=b.copy();f['week_gap']=spend.loc[f.index,week]
                result=estimate(f,'week_gap')
                trends.append({'campaign_id':cid,'week':week,'relative_week':week-start,
                               'during_campaign':week>=start,**result})

        estimates=pd.DataFrame(rows);guide=pd.DataFrame(guide);placebos=pd.DataFrame(placebos)
        sensitivity=pd.DataFrame(sensitivities);balance=pd.DataFrame(balance)
        overlaps=pd.DataFrame(overlaps);trends=pd.DataFrame(trends)
        pretrends=pd.DataFrame(pretrends)
        pretrends['p_holm']=holm_adjust(pretrends.p_value)
        pretrends['reject_zero_holm_05']=pretrends.p_holm<0.05
        placebos['p_holm']=np.nan
        available=placebos.status=='estimated'
        placebos.loc[available,'p_holm']=holm_adjust(placebos.loc[available,'p_value'])
        placebos['reject_zero_holm_05']=placebos.p_holm<0.05
        placebos.loc[~available,'reject_zero_holm_05']=False
        primary=estimates[estimates.method=='matched_earlier'].copy()
        primary['estimated_change_supported_sample']=primary.estimate*primary.weeks*primary.n_treated
        primary['ci_low_supported_sample']=primary.ci_low*primary.weeks*primary.n_treated
        primary['ci_high_supported_sample']=primary.ci_high*primary.weeks*primary.n_treated
        roi=roi.merge(primary[['campaign_id','n_treated','n_control','estimate','ci_low','ci_high',
                    'estimated_change_supported_sample','ci_low_supported_sample','ci_high_supported_sample']],
                    on='campaign_id',how='left').rename(columns={'n_treated':'matched_supported_treated','n_control':'matched_supported_controls'})
        roi['costs_observed']=False
        roi['extrapolation_to_all_recipients_validated']=False
        datasets={'campaign_estimates':estimates,'guide_compatibility_estimates':guide,
                  'placebo_tests':placebos,'campaign_sensitivities':sensitivity,'matching_balance':balance,
                  'campaign_overlap_audit':overlaps,'campaign_pretrends':trends,
                  'pretrend_tests':pretrends,'campaign_window_audit':window_audit,
                  'campaign_overview':overview,'campaign_roi_inputs':roi,'coupon_amount_summary':coupon,
                  'matching_samples':pd.concat(samples,ignore_index=True),'hh_week':hw}
        checks.extend([
            {'check_name':'twelve_primary_estimates','passed':len(estimates)==12 and estimates.status.eq('estimated').all()},
            {'check_name':'primary_intervals_bracket_estimates','passed':bool((estimates.ci_low<=estimates.estimate).all() and (estimates.estimate<=estimates.ci_high).all())},
            {'check_name':'primary_results_finite','passed':bool(np.isfinite(estimates[['estimate','se','ci_low','ci_high']]).all().all())},
            {'check_name':'common_support_stratum_weights_balance','passed':bool(common_support_ok)},
            {'check_name':'positive_matching_weights','passed':bool((datasets['matching_samples'].w>0).all())},
            {'check_name':'five_supported_placebo_tests','passed':int(available.sum())==5},
            {'check_name':'three_pretrend_contrasts_estimated','passed':len(pretrends)==3 and pretrends.status.eq('estimated').all()},
            {'check_name':'placebo_outcomes_precede_actual_campaign','passed':bool(placebos.last_pseudo_week_before_actual.all())},
            {'check_name':'holm_adjustments_do_not_reduce_p','passed':bool((placebos.loc[available,'p_holm']>=placebos.loc[available,'p_value']-1e-12).all())},
            {'check_name':'effective_controls_not_above_count','passed':bool((estimates.control_ess<=estimates.n_control+1e-6).all())},
            {'check_name':'matching_does_not_add_treated','passed':bool((estimates.n_treated<=estimates.eligible_treated).all())}])
        assert all(bool(c['passed']) for c in checks),checks
        checkframe=pd.DataFrame(checks)
        datasets['campaign_checks']=checkframe
        for name,frame in datasets.items():
            save(frame,name)

        wide=[]
        for cid in wins.campaign_id:
            row={'campaign':str(cid)}
            for method,label in [('naive','1 naive gap'),('unmatched','2 DiD unmatched'),('matched_pre','3 DiD matched on pre'),('matched_earlier','4 DiD matched earlier')]:
                r=guide[(guide.campaign_id==cid)&(guide.method==method)].iloc[0]
                row[label]=f"{r.estimate:+.2f} ({r.ci_low:+.2f} to {r.ci_high:+.2f})"
            for method,label in [('matched_pre','3p placebo'),('matched_earlier','4p placebo')]:
                r=placebos[(placebos.campaign_id==cid)&(placebos.method==method)].iloc[0]
                row[label]=f"{r.estimate:+.2f} ({r.ci_low:+.2f} to {r.ci_high:+.2f})" if r.status=='estimated' else 'Not estimable: insufficient history'
            wide.append(row)
        pd.DataFrame(wide).to_csv(ROOT/'exports/campaign_estimates.csv',index=False,encoding='utf-8-sig')

        fig,axes=plt.subplots(1,3,figsize=(14,5),sharey=True,layout='constrained')
        for ax,cid in zip(axes,wins.campaign_id):
            f=estimates[estimates.campaign_id==cid].set_index('method').loc[METHODS]
            ax.errorbar(range(4),f.estimate,yerr=[f.estimate-f.ci_low,f.ci_high-f.estimate],fmt='o-',color='#176B75',capsize=4)
            ax.axhline(0,color='#C36B24',linestyle='--')
            ax.set_xticks(range(4),['Naive\nfull sample','DiD\nunmatched','Matched\non pre','Matched\nearlier'],fontsize=8)
            ax.set_title('Campaign '+str(cid),fontweight='bold')
            ax.spines[['top','right']].set_visible(False)
        axes[0].set_ylabel('USD per household per week')
        fig.suptitle('Estimates across designs | pointwise 95% HC1 intervals\nMatched designs trim support; changes reflect both design and sample',fontsize=12,fontweight='bold')
        fig.savefig(ROOT/'charts/campaign_estimate_path.png',dpi=160);plt.close(fig)

        fig,ax=plt.subplots(figsize=(10,4.6),layout='constrained')
        y=np.arange(len(primary))
        ax.errorbar(primary.estimate,y,xerr=[primary.estimate-primary.ci_low,primary.ci_high-primary.estimate],fmt='o',color='#176B75',capsize=5)
        ax.set_yticks(y,['Campaign '+str(c) for c in primary.campaign_id]);ax.invert_yaxis()
        ax.axvline(0,color='#C36B24',linestyle='--')
        ax.set_xlabel('Estimated change, USD per supported household per week')
        ax.set_title('Earlier-window matched DiD | pointwise 95% HC1 intervals\nObservational estimates; not proven causal effects',fontweight='bold',fontsize=12)
        ax.spines[['top','right']].set_visible(False)
        fig.savefig(ROOT/'charts/campaign_earlier_estimates.png',dpi=160);plt.close(fig)

        fig,axes=plt.subplots(3,1,figsize=(11,9),layout='constrained')
        for ax,win in zip(axes,wins.itertuples()):
            f=trends[trends.campaign_id==win.campaign_id]
            ax.plot(f.week,f.estimate,marker='o',color='#176B75',linewidth=1.5)
            ax.fill_between(f.week,f.ci_low,f.ci_high,color='#176B75',alpha=.13)
            ax.axvline(win.start_week-.5,color='#C36B24',linestyle='--')
            ax.axhline(0,color='gray',linewidth=.8)
            ax.set_ylabel('Targeted − control ($/week)')
            ax.set_title('Campaign '+str(win.campaign_id),fontweight='bold')
            ax.spines[['top','right']].set_visible(False)
        axes[-1].set_xlabel('Source week')
        fig.suptitle('Weekly gaps with earlier-window matching\nShading: pointwise HC1 intervals, not simultaneous pre-trend validation',fontsize=12,fontweight='bold')
        fig.savefig(ROOT/'charts/campaign_pretrends.png',dpi=160);plt.close(fig)
        f=trends[trends.campaign_id=='18']
        fig,ax=plt.subplots(figsize=(10,4.5),layout='constrained')
        ax.plot(f.week,f.estimate,marker='o',color='#176B75')
        ax.axvline(44.5,color='#C36B24',linestyle='--',label='Campaign begins')
        ax.axhline(0,color='gray',linewidth=.8)
        ax.set(title='Campaign 18: targeted minus matched control',xlabel='Source week',ylabel='USD per household per week')
        ax.legend();ax.spines[['top','right']].set_visible(False)
        fig.savefig(ROOT/'charts/campaign18_pretrend.png',dpi=160);plt.close(fig)

        # Save compact reporting tables, including audit-level household weights.
        path=staging.as_posix().replace("'","''")
        con.execute(f"ATTACH '{path}' AS reporting")
        for name,frame in datasets.items():
            con.register('export_frame',frame)
            con.execute(f'CREATE TABLE reporting.main.{name} AS SELECT * FROM export_frame')
            con.unregister('export_frame')
        con.execute('DETACH reporting')
        report={'guide':'Two_Analytics_Projects_Complete_Guide.docx','guide_steps':'1.5.1–1.5.5',
                'household_weeks':len(hw),'grocery_households':len(spend),
                'primary_estimates':estimates.to_dict('records'),'guide_compatibility_estimates':guide.to_dict('records'),
                'placebos':placebos.to_dict('records'),'sensitivities':sensitivity.to_dict('records'),
                'overlap_audit':overlaps.to_dict('records'),'roi_inputs':roi.to_dict('records'),
                'pretrend_tests':pretrends.to_dict('records'),'campaign_window_audit':window_audit.to_dict('records'),
                'coupon_amounts':coupon.to_dict('records'),'checks':checks,
                'inference':'Household-level WLS, HC1 normal intervals; estimated weights treated as fixed; not causal identification',
                'unsupported_case':'Campaign 8 earlier-window placebo lacks required history'}
        report['build_inputs_sha256']=build_inputs(ROOT,['scripts/run_campaigns.py','scripts/campaign_methods.py','sql/01_model.sql','sql/05_campaigns.sql'])
        # Pandas uses NaN for unsupported fields; JSON uses explicit nulls.
        clean=json.loads(pd.Series({'report':report}).to_json(date_format='iso'))['report']
        (DOCS/'verification.json').write_text(json.dumps(clean,indent=2),encoding='utf-8')
    os.rename(staging,final)
    with duckdb.connect(str(final),read_only=True) as con:
        assert con.execute('SELECT bool_and(passed) FROM campaign_checks').fetchone()[0]
    print(f'PASS: {len(checks)} campaign checks')
    print(estimates[['campaign_id','method','estimate','ci_low','ci_high','n_treated','n_control']].to_string(index=False))
    print('\nPLACEBOS\n'+placebos[['campaign_id','method','status','estimate','ci_low','ci_high','p_holm']].to_string(index=False))
    print('\nSENSITIVITIES\n'+sensitivity[['campaign_id','method','estimate','ci_low','ci_high','n_treated','n_control']].to_string(index=False))
    print('\nOVERLAP\n'+overlaps.to_string(index=False))


if __name__=='__main__':
    main()
