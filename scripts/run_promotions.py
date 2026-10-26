"""Execute Word guide Module 4, including explicit metadata/baseline sensitivity checks."""
from pathlib import Path
import csv
import json
import os
import duckdb
from provenance import build_inputs
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'exports/promotions'
DOCS=ROOT/'docs/promotions'
TABLES=['promo_lift','display_lift','mailer_lift','post_promo_lift',
        'promo_lift_observed_only','promo_lift_positive_baseline','promotion_coverage','promotion_checks']
DISPLAY={'1':'Store front','2':'Store rear','3':'Front end cap','4':'Mid-aisle end cap',
         '5':'Rear end cap','6':'Side-aisle end cap','7':'In-aisle','9':'Secondary display','A':'In-shelf','MULTIPLE':'Multiple codes'}
MAILER={'A':'Interior page feature','C':'Interior line item','D':'Front page feature','F':'Back page feature',
        'H':'Wrap front feature','J':'Wrap interior coupon','L':'Wrap back feature','P':'Interior coupon',
        'X':'Free on interior page','Z':'Free front/back/wrap','MULTIPLE':'Multiple codes'}


def export(con,table):
    cur=con.execute(f'SELECT * FROM {table}')
    with (OUT/f'{table}.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.writer(f)
        w.writerow([d[0] for d in cur.description])
        w.writerows(cur.fetchall())


def main():
    for p in (OUT,DOCS,ROOT/'charts'):
        p.mkdir(parents=True,exist_ok=True)
    final=ROOT/'grocery_promotions.duckdb'
    staging=ROOT/'grocery_promotions.building.duckdb'
    if final.exists() or staging.exists():
        raise FileExistsError('Preserving existing promotion reporting database. Rename it before rebuilding.')
    baseline=json.loads((ROOT/'docs/verification.json').read_text())['tables']
    with duckdb.connect() as con:
        con.execute("SET memory_limit='512MB'")
        con.execute('SET threads=1')
        for name in ('transactions','products','promotions'):
            path=(ROOT/'data/parquet'/f'{name}.parquet').as_posix().replace("'","''")
            con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{path}')")
            actual=con.execute(f'SELECT count(*),bit_xor(hash(t))::VARCHAR FROM {name} t').fetchone()
            assert actual==(baseline[name]['rows'],baseline[name]['content_fingerprint']),name
            print(f'Source verified: {name}',flush=True)
        for s in con.extract_statements((ROOT/'sql/01_model.sql').read_text())[:2]:
            con.execute(s.query)
        assert con.execute('SELECT count(*) FROM fact_sales').fetchone()[0]==1_460_487
        con.execute((ROOT/'sql/04_promo.sql').read_text())
        checks=con.execute('SELECT * FROM promotion_checks ORDER BY check_name').fetchall()
        assert all(p is True for _,p in checks),checks
        data={t:con.execute(f'SELECT * FROM {t}').df() for t in TABLES}
        for table,mapping in [('display_lift',DISPLAY),('mailer_lift',MAILER)]:
            con.execute(f'ALTER TABLE {table} ADD COLUMN placement_label VARCHAR')
            for code,label in mapping.items():
                con.execute(f'UPDATE {table} SET placement_label=? WHERE placement_code=?',[label,code])
            con.execute(f'UPDATE {table} SET placement_label=placement_code WHERE placement_label IS NULL')
            data[table]=con.execute(f'SELECT * FROM {table}').df()
        for table in TABLES:
            export(con,table)
        # An inspectable panel sample, rather than a million-row export.
        cur=con.execute('SELECT * FROM promo_panel_flags ORDER BY product_id,store_id,week LIMIT 104')
        with (OUT/'panel_sample.csv').open('w',newline='',encoding='utf-8-sig') as f:
            w=csv.writer(f);w.writerow([d[0] for d in cur.description]);w.writerows(cur.fetchall())
        coverage=data['promotion_coverage'].iloc[0].to_dict()
        for table,file,title in [
            ('promo_lift','promotion_lift.png','Recorded promotion conditions vs pair-specific baseline'),
            ('post_promo_lift','post_promotion.png','Weeks after promotions | descriptive comparison')]:
            frame=data[table].sort_values('lift_index')
            fig,ax=plt.subplots(figsize=(11,5),layout='constrained')
            bars=ax.barh(frame.condition,frame.lift_index,color='#176B75')
            ax.bar_label(bars,labels=[f'{x:.2f}×' for x in frame.lift_index],padding=5)
            ax.axvline(1,color='#C36B24',linestyle='--',label='Baseline = 1.00')
            ax.set_xlim(0,max(frame.lift_index)*1.2)
            ax.set_xlabel('Observed panel units / expected baseline panel units')
            ax.set_title(title+'\nAssociation, not a causal effect',fontweight='bold',fontsize=12)
            ax.spines[['top','right']].set_visible(False)
            ax.legend(loc='lower right')
            fig.savefig(ROOT/'charts'/file,dpi=160)
            plt.close(fig)
        fig,axes=plt.subplots(1,2,figsize=(14,6),layout='constrained')
        for ax,table,title in zip(axes,['display_lift','mailer_lift'],['Display only','Mailer only']):
            frame=data[table]
            # The chart suppresses tiny groups but the full export retains them.
            frame=frame[~frame.small_group].sort_values('lift_index').tail(8)
            labels=[f'{r.placement_label} [{r.placement_code}]' for r in frame.itertuples()]
            bars=ax.barh(labels,frame.lift_index,color='#176B75')
            ax.bar_label(bars,labels=[f'{x:.2f}×' for x in frame.lift_index],padding=4)
            ax.axvline(1,color='#C36B24',linestyle='--')
            ax.set_xlim(0,max(frame.lift_index)*1.2)
            ax.set_title(title,fontweight='bold')
            ax.set_xlabel('Observed units / baseline units')
            ax.spines[['top','right']].set_visible(False)
        fig.suptitle('Placement associations | groups with ≥100 pair-weeks\nMULTIPLE preserves conflicting source codes; results are not causal',fontsize=13,fontweight='bold')
        fig.savefig(ROOT/'charts/promotion_placements.png',dpi=160)
        plt.close(fig)
        path=staging.as_posix().replace("'","''")
        con.execute(f"ATTACH '{path}' AS reporting")
        for table in TABLES:
            con.execute(f'CREATE TABLE reporting.main.{table} AS SELECT * FROM main.{table}')
        con.execute('DETACH reporting')
        report={'guide':'Two_Analytics_Projects_Complete_Guide.docx','guide_steps':'1.4.1–1.4.4',
                'source':'Verified Parquet and saved phase-1 sales transformation; open databases unchanged',
                'coverage':coverage,
                'primary_lift':data['promo_lift'].to_dict('records'),
                'post_promotion':data['post_promo_lift'].to_dict('records'),
                'observed_only_sensitivity':data['promo_lift_observed_only'].to_dict('records'),
                'observed_only_status':'estimated' if len(data['promo_lift_observed_only']) else 'not_estimable_no_observed_nonpromotion_baselines',
                'positive_baseline_sensitivity':data['promo_lift_positive_baseline'].to_dict('records'),
                'placement_results':{t:data[t].to_dict('records') for t in ['display_lift','mailer_lift']},
                'checks':[{'name':name,'passed':bool(p)} for name,p in checks]}
        report['build_inputs_sha256']=build_inputs(ROOT,['scripts/run_promotions.py','sql/01_model.sql','sql/04_promo.sql'])
        (DOCS/'verification.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
        lift=data['promo_lift'].set_index('condition').lift_index
        post=data['post_promo_lift'].set_index('condition').lift_index
        rows='\n'.join(f'| {r.condition} | {r.pair_weeks:,} | {r.lift_index:.2f}× |' for r in data['promo_lift'].itertuples())
        sensitivity=data['promo_lift_observed_only'].set_index('condition').lift_index
        positive=data['promo_lift_positive_baseline'].set_index('condition').lift_index
        sensitivity_rows='\n'.join(f'| {condition} | {value:.2f}× | '+(f'{sensitivity[condition]:.2f}×' if condition in sensitivity.index else 'Not estimable')+' |' for condition,value in lift.items())
        findings=f'''# Promotion associations — Word guide Module 4

Completed **Steps 1.4.1–1.4.4**. Units are purchases by the panel households, not total store sales. These indices compare observed units with a pair-specific baseline; they are not randomized treatment effects.

## Three findings

1. Display plus mailer pair-weeks have **{lift['Display + mailer']:.2f}×** baseline panel units, versus **{lift['Mailer only']:.2f}×** for mailer only and **{lift['Display only']:.2f}×** for display only. This ranks observed promotion packages, not the isolated causal effect of a display or mailer. An index of 3.14 means 214% above baseline, not a 314% increase.
2. The week after a single-week promotion has **{post['Week after a single-week promotion']:.2f}×** baseline units; after multiple consecutive promoted weeks, **{post['Week after a multi-week promotion']:.2f}×**. The guide-style comparison does not show a dip below baseline. It cannot determine whether discounts continued, demand was seasonal, or purchases were pulled forward.
3. Metadata is absent for **{int(coverage['missing_metadata_pair_weeks']):,} of {int(coverage['pair_weeks']):,} pair-weeks**. All explicitly listed eligible records indicate a display or mailer, so an observed-metadata-only baseline is **not estimable**: it has no explicitly observed nonpromotion controls. The primary result follows the guide's convention that an absent row means no recorded display/mailer; that convention cannot be independently validated from explicit nonpromotion records in this source.

## Primary guide-style results

| Condition | Pair-weeks with usable baseline | Unit index |
|---|---:|---:|
{rows}

## Universe and coverage

- **{int(coverage['eligible_pairs']):,} product/store pairs** purchased in at least eight source weeks; 52 weeks per pair gives **{int(coverage['pair_weeks']):,} panel rows**.
- **{int(coverage['baseline_pairs']):,} pairs** have at least four baseline weeks (not promoted and not directly after a promotion).
- **{coverage['promoted_share']:.1%}** of the full eligible panel has recorded promotion flags.
- **{int(coverage['conflicting_metadata_pair_weeks']):,} eligible pair-weeks** contain conflicting placement codes. Flags use any nonzero code; labels use MULTIPLE instead of selecting an arbitrary maximum. Placement-specific values may therefore differ from the guide's maximum-code method.
- **{int(coverage['zero_unit_baseline_pairs']):,} pairs** have zero average baseline units. The primary result retains the guide's ratio-of-totals definition; the positive-baseline-only export shows a sensitivity excluding these pairs.
- Missing purchase rows are zero-filled within this panel, meaning no observed panel purchase. This does not prove no store sales or product availability.

## Observed-metadata sensitivity

| Condition | Guide-style primary | Observed-current-and-prior metadata only |
|---|---:|---:|
{sensitivity_rows}

The stricter sample has {int(coverage['observed_only_baseline_pairs']):,} usable baseline pairs. Its CSV intentionally contains headers and no estimates. This is a support limitation, not a zero effect or a failed query. It excludes boundary week 2 and missing-metadata transitions. Primary lag indicators default to no previous promotion at the left boundary as in the guide; boundary-history counts are exported for the post-promotion comparison.

The positive-baseline sensitivity remains estimable: excluding {int(coverage['zero_unit_baseline_pairs'])} zero-baseline pairs changes the Display + mailer index to {positive['Display + mailer']:.2f}×, Mailer only to {positive['Mailer only']:.2f}×, and Display only to {positive['Display only']:.2f}×. These are alternate descriptive estimates, not corrected causal effects. The complete base amounts and counts are exported.

Placement-code definitions follow the [official completejourney documentation](https://github.com/bradleyboehmke/completejourney/blob/master/man/promotions_sample.Rd). The event-style support limitation above is an observation from this full dataset, not a claim that the documentation independently proves missing-record coverage.

## Interpretation and verification

Price discounts can accompany display and mailer exposure. Seasonality, selection of products into promotion, availability, and other confounders remain uncontrolled. Small placement groups (<100 pair-weeks) are flagged and omitted from the placement chart; the full CSV retains them. This threshold is a descriptive display rule, not a statistical significance test. No confidence intervals or profit/ROI claims are made.

**{len(checks)} full-data checks passed**, covering panel grain, zero filling, baseline support, condition totals, coverage, and ratios. Source fingerprints were verified before analysis. The raw data, user SQL scripts, and open databases were not modified.

Files: `exports/promotions/`, `sql/04_promo.sql`, `04_promotions.ipynb`, three PNG charts, and `grocery_promotions.duckdb` (summary/check tables only). Next guide section: **Module 5, campaign incrementality**.
'''
        (DOCS/'findings.md').write_text(findings,encoding='utf-8')
    os.rename(staging,final)
    with duckdb.connect(str(final),read_only=True) as con:
        assert con.execute('SELECT bool_and(passed) FROM promotion_checks').fetchone()[0]
    print(f'PASS: {len(checks)} promotion checks')
    print(json.dumps({k:v for k,v in report.items() if k not in ['checks','placement_results']},indent=2,default=str))


if __name__=='__main__':
    main()
