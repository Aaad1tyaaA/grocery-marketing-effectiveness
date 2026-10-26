"""Randomized mean contrasts and a training-only cell policy with held-out evaluation."""
import numpy as np
import pandas as pd
from scipy import stats

ARMS=['Mens E-Mail','Womens E-Mail']
CONTROL='No E-Mail'
METRICS=['visit','conversion','spend']


def bootstrap_means(values,rng,reps=2000):
    """Exact empirical bootstrap distribution of a mean, using repeated-value counts."""
    values=np.asarray(values,dtype=float)
    if not len(values) or not np.isfinite(values).all() or reps<2:
        raise ValueError('Bootstrap needs finite nonempty data and at least two replicates')
    support,counts=np.unique(values,return_counts=True)
    result=np.empty(reps)
    # Multinomial counts over identical values are equivalent to sampling customer rows.
    for start in range(0,reps,128):
        size=min(128,reps-start)
        weights=rng.multinomial(len(values),counts/len(values),size=size)
        result[start:start+size]=(weights@support)/len(values)
    return result


def contrast(treatment,control,rng,reps=2000):
    t=np.asarray(treatment,dtype=float);c=np.asarray(control,dtype=float)
    base={'n_treatment':len(t),'n_control':len(c)}
    if min(len(t),len(c))<2:
        return {**base,'status':'not_estimable_insufficient_arm_size',
                **{k:np.nan for k in ['treatment_mean','control_mean','estimate','ci_low','ci_high','p_value']}}
    if not np.isfinite(t).all() or not np.isfinite(c).all():
        raise ValueError('Non-finite outcomes')
    difference=float(t.mean()-c.mean())
    distribution=bootstrap_means(t,rng,reps)-bootstrap_means(c,rng,reps)
    low,high=np.percentile(distribution,[2.5,97.5])
    if t.var()==0 and c.var()==0:
        p=1.0 if difference==0 else 0.0
    else:
        p=float(stats.ttest_ind(t,c,equal_var=False).pvalue)
    return {**base,'status':'estimated','treatment_mean':float(t.mean()),'control_mean':float(c.mean()),
            'estimate':difference,'ci_low':float(low),'ci_high':float(high),'p_value':p}


def fit_policy(frame,seed,quota=10000):
    """Rank observed pre-treatment cells; exact quotas use outcome-free tie breaks."""
    if not frame.source_row.is_unique or not 0<2*quota<=len(frame):
        raise ValueError('Policy needs unique source rows and disjoint feasible quotas')
    ordered=frame.sort_values('source_row').reset_index(drop=True)
    half=np.random.default_rng(seed).integers(0,2,len(ordered))
    training=ordered.loc[half==0]
    means=training.pivot_table(index='cell',columns='segment',values='spend',aggfunc='mean')
    counts=pd.crosstab(training.cell,training.segment)
    required=[CONTROL,*ARMS]
    if not set(required).issubset(means.columns) or not set(required).issubset(counts.columns):
        raise ValueError('Training cells lack randomized-arm support')
    counts=counts.reindex(ordered.cell.unique(),fill_value=0)
    if (counts[required]<2).any().any():
        raise ValueError('Training cells need at least two rows in every randomized arm')
    rules=means[required].rename(columns={CONTROL:'train_control_mean',ARMS[0]:'train_mens_mean',ARMS[1]:'train_womens_mean'})
    rules['train_mens_lift']=rules.train_mens_mean-rules.train_control_mean
    rules['train_womens_lift']=rules.train_womens_mean-rules.train_control_mean
    rules['recommended_email']=np.where(rules.train_mens_lift>=rules.train_womens_lift,ARMS[0],ARMS[1])
    rules['train_best_lift']=rules[['train_mens_lift','train_womens_lift']].max(axis=1)
    rules['population_customers']=ordered.groupby('cell').size()
    for arm,name in [(CONTROL,'control'),(ARMS[0],'mens'),(ARMS[1],'womens')]:
        rules['train_n_'+name]=counts[arm]
    rules=rules.reset_index().sort_values(['train_best_lift','cell'],ascending=[False,True]).reset_index(drop=True)
    rules['target_whole_cell']=rules.population_customers.cumsum()<=quota
    bottom=rules.iloc[::-1].copy()
    bottom['suppress_whole_cell']=bottom.population_customers.cumsum()<=quota
    rules=rules.merge(bottom[['cell','suppress_whole_cell']],on='cell',validate='one_to_one')
    assignments=ordered[['source_row','cell']].assign(half=half)
    assignments=assignments.merge(rules[['cell','train_best_lift','recommended_email','target_whole_cell','suppress_whole_cell']],on='cell',validate='many_to_one')
    assignments['tie_break']=np.random.default_rng(seed+1000).random(len(assignments))
    assignments=assignments.sort_values(['train_best_lift','tie_break','source_row'],ascending=[False,True,True]).reset_index(drop=True)
    assignments['decision_rank']=np.arange(1,len(assignments)+1)
    assignments['decision']='other'
    assignments.loc[assignments.index[:quota],'decision']='target'
    assignments.loc[assignments.index[-quota:],'decision']='suppress'
    allocation=pd.crosstab(assignments.cell,assignments.decision).reindex(columns=['target','suppress'],fill_value=0)
    rules=rules.merge(allocation.add_prefix('exact_').reset_index(),on='cell',validate='one_to_one')
    rules['seed']=seed;assignments['seed']=seed
    return rules,assignments.drop(columns='tie_break')


def policy_value(heldout,metric,rng,reps=2000):
    """Horvitz-Thompson policy value at known assignment probability 1/3."""
    if len(heldout)<2:
        raise ValueError('Held-out audience too small')
    y=heldout[metric].to_numpy(dtype=float)
    arm=heldout.segment.to_numpy();chosen=heldout.recommended_email.to_numpy()
    learned=3*y*((arm==chosen).astype(float)-(arm==CONTROL).astype(float))
    mens=3*y*((arm==ARMS[0]).astype(float)-(arm==CONTROL).astype(float))
    distribution=bootstrap_means(learned,rng,reps)
    improvement=learned-mens
    improvement_boot=bootstrap_means(improvement,rng,reps)
    low,high=np.percentile(distribution,[2.5,97.5])
    ilo,ihi=np.percentile(improvement_boot,[2.5,97.5])
    return {'heldout_customers':len(heldout),'estimate':float(learned.mean()),'ci_low':float(low),'ci_high':float(high),
            'always_mens_estimate':float(mens.mean()),'policy_minus_mens':float(improvement.mean()),
            'policy_minus_mens_ci_low':float(ilo),'policy_minus_mens_ci_high':float(ihi)}
