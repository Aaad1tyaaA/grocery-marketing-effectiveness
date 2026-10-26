"""Household-level comparisons for the Word guide; no campaign outcomes enter matching."""
import numpy as np
import pandas as pd
from math import erfc, sqrt


class HistoryUnavailable(ValueError):
    pass


def build_frame(spend,active,recipients,campaign_id,start,end,match_on='pre',shift=0):
    if match_on not in {'pre','earlier'}:
        raise ValueError('match_on must be pre or earlier')
    if not spend.index.is_unique or not spend.columns.is_unique:
        raise ValueError('Household-week keys must be unique')
    if not spend.index.equals(active.index) or not spend.columns.equals(active.columns):
        raise ValueError('Spend and activity panels must have identical household and week keys')
    start,end=int(start)-shift,int(end)-shift
    pre=list(range(start-8,start))
    during=list(range(start,end+1))
    match=pre if match_on=='pre' else list(range(start-16,start-8))
    if not set(pre+during+match).issubset(spend.columns):
        raise HistoryUnavailable('Required matching, pre, or outcome weeks are outside the observed panel')
    f=pd.DataFrame({'pre':spend[pre].mean(axis=1),'during':spend[during].mean(axis=1),
                    'm_spend':spend[match].mean(axis=1),'m_active':active[match].sum(axis=1)})
    if not np.isfinite(spend[sorted(set(pre+during+match))].to_numpy(dtype=float)).all():
        raise ValueError('Requested spend weeks contain missing or non-finite values')
    if active[match].isna().any().any():
        raise ValueError('Requested activity weeks contain missing values')
    targets=set(recipients.loc[recipients.campaign_id.astype(str)==str(campaign_id),'household_id'].astype(str))
    f['treated']=f.index.astype(str).isin(targets)
    f['change']=f['during']-f['pre']
    f['w']=1.0
    f.index.name='household_id'
    return f.sort_index()


def match_frame(frame,tie_preserving=False):
    f=frame.copy()
    if f.empty:
        f['stratum']=pd.Series(index=f.index,dtype=str)
        return f
    def bands(values,q):
        # Guide compatibility splits ties by sorted household ID; sensitivity keeps equal values together.
        values=values if tie_preserving else values.rank(method='first')
        if values.nunique()<=1:
            return pd.Series(0,index=values.index)
        return pd.qcut(values,q,labels=False,duplicates='drop').fillna(0).astype(int)
    f['stratum']=bands(f.m_spend,20).astype(str)+'_'+bands(f.m_active,4).astype(str)
    counts=pd.crosstab(f.stratum,f.treated).reindex(columns=[False,True],fill_value=0)
    counts=counts[(counts[False]>0)&(counts[True]>0)]
    f=f[f.stratum.isin(counts.index)].copy()
    if f.empty:
        return f
    ratio=(counts[True]/counts[False])*(counts[False].sum()/counts[True].sum())
    f['w']=np.where(f.treated,1.0,f.stratum.map(ratio))
    return f


def estimate(frame,outcome='change',weighted=True):
    t=frame.treated if len(frame) else pd.Series(dtype=bool)
    nt,nc=int(t.sum()),int((~t).sum())
    base={'n_treated':nt,'n_control':nc}
    if min(nt,nc)<2:
        return {**base,'status':'not_estimable_insufficient_common_support',
                'estimate':np.nan,'se':np.nan,'ci_low':np.nan,'ci_high':np.nan,'p_value':np.nan,
                'control_ess':np.nan,'maximum_control_weight':np.nan}
    weights=frame.w if weighted else pd.Series(1.0,index=frame.index)
    assert np.isfinite(weights).all() and (weights>0).all()
    assert np.isfinite(frame[outcome]).all()
    values=frame[outcome].to_numpy(dtype=float)
    treated=t.to_numpy(dtype=bool)
    w=weights.to_numpy(dtype=float)
    wt,wc=w[treated],w[~treated]
    yt,yc=values[treated],values[~treated]
    mean_t=np.average(yt,weights=wt)
    mean_c=np.average(yc,weights=wc)
    direct=mean_t-mean_c
    # For an intercept plus treatment indicator, the HC1 sandwich variance
    # reduces to the sum of the two weighted group residual variances.
    residual_t,residual_c=yt-mean_t,yc-mean_c
    correction=len(frame)/(len(frame)-2)
    variance=correction*((wt**2 @ residual_t**2)/(wt.sum()**2)
                         +(wc**2 @ residual_c**2)/(wc.sum()**2))
    se=float(sqrt(max(variance,0.0)))
    z=direct/se if se else (float('inf') if direct>0 else float('-inf') if direct<0 else 0.0)
    critical=1.959963984540054
    low,high=direct-critical*se,direct+critical*se
    control=weights[~t]
    return {**base,'status':'estimated','estimate':float(direct),
            'se':se,'ci_low':float(low),'ci_high':float(high),
            'p_value':float(erfc(abs(z)/sqrt(2))),
            'control_ess':float(control.sum()**2/(control**2).sum()),
            'maximum_control_weight':float(control.max())}


def balance_rows(original,matched,campaign_id,method):
    rows=[]
    for feature in ['m_spend','m_active']:
        t=original.treated
        scale=np.sqrt((original.loc[t,feature].var()+original.loc[~t,feature].var())/2)
        for name,frame,weighted in [('before',original,False),('after',matched,True)]:
            if frame.empty or frame.treated.nunique()<2:
                continue
            treated=frame.treated
            weights=frame.w if weighted else pd.Series(1.0,index=frame.index)
            mean_t=np.average(frame.loc[treated,feature],weights=weights[treated])
            mean_c=np.average(frame.loc[~treated,feature],weights=weights[~treated])
            smd=(mean_t-mean_c)/scale if scale>0 else (0.0 if mean_t==mean_c else np.nan)
            rows.append({'campaign_id':str(campaign_id),'method':method,'stage':name,'feature':feature,
                         'treated_mean':mean_t,'control_mean':mean_c,'standardized_mean_difference':smd})
    return rows


def holm_adjust(p_values):
    """Holm step-down adjusted p-values in original order."""
    p=np.asarray(p_values,dtype=float)
    if not np.isfinite(p).all() or ((p<0)|(p>1)).any():
        raise ValueError('Holm adjustment requires finite p-values in [0,1]')
    order=np.argsort(p)
    adjusted=np.maximum.accumulate((len(p)-np.arange(len(p)))*p[order])
    result=np.empty(len(p),dtype=float)
    result[order]=np.minimum(adjusted,1.0)
    return result
