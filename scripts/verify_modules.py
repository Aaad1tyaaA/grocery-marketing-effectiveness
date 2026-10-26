"""Verify hashes, databases, CSV parity, notebook freshness, and shared totals."""
from pathlib import Path
import argparse
import hashlib
import json
import duckdb
import nbformat
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
MODULES={1:('grocery_phase1.duckdb','phase1_checks','phase1','01_data_model.ipynb'),
         2:('grocery_business_health.duckdb','business_health_checks','business_health','02_business_health.ipynb'),
         3:('grocery_customers.duckdb','customer_checks','customers','03_customers.ipynb'),
         4:('grocery_promotions.duckdb','promotion_checks','promotions','04_promotions.ipynb'),
         5:('grocery_campaigns.duckdb','campaign_checks','campaigns','05_campaigns.ipynb'),
         6:('grocery_hillstrom.duckdb','hillstrom_checks','hillstrom','06_hillstrom.ipynb')}


def check_notebook(path,root=ROOT):
    nb=nbformat.read(path,as_version=4)
    code=[c for c in nb.cells if c.cell_type=='code']
    assert code and all(c.execution_count is not None for c in code),f'{path.name}: unexecuted cells'
    assert not any(o.output_type=='error' for c in code for o in c.outputs),f'{path.name}: error outputs'
    stamps=nb.metadata.get('grocery_inputs_sha256')
    assert stamps,f'{path.name}: missing input hashes; re-execute with the notebook writer'
    for relative,digest in stamps.items():
        assert hashlib.sha256((root/relative).read_bytes()).hexdigest()==digest,f'{path.name}: stale input {relative}'
    return {'file':path.name,'executed_code_cells':len(code),'input_files_checked':len(stamps)}


def compare_export(con,table,path):
    schema=con.execute(f'DESCRIBE "{table}"').fetchall()
    types='{'+','.join("'"+name.replace("'","''")+"':'"+dtype+"'" for name,dtype,*_ in schema)+'}'
    csv_path=path.as_posix().replace("'","''")
    actual=con.execute(f"SELECT * FROM read_csv('{csv_path}',header=true,columns={types},delim=',',nullstr='')").df()
    expected=con.execute(f'SELECT * FROM "{table}"').df()
    keys=list(expected.columns)
    actual=actual.sort_values(keys,na_position='last').reset_index(drop=True)
    expected=expected.sort_values(keys,na_position='last').reset_index(drop=True)
    pd.testing.assert_frame_equal(expected,actual,check_dtype=False,check_exact=False,rtol=1e-10,atol=1e-9)
    return len(expected)


def verify(through=6):
    manifest=json.loads((ROOT/'docs/source_manifest.json').read_text(encoding='utf-8'))
    baseline=json.loads((ROOT/'docs/verification.json').read_text(encoding='utf-8'))['tables']
    report={'completed_modules_verified':list(range(1,through+1)),'source_commit':manifest['commit'],
            'sources':[],'modules':[],'cross_module_checks':[]}
    with duckdb.connect() as con:
        con.execute("SET memory_limit='512MB'");con.execute('SET threads=1')
        for source in manifest['files']:
            raw=ROOT/'data/raw'/source['name'];name=raw.stem
            payload=raw.read_bytes()
            assert len(payload)==source['size'] and hashlib.sha256(payload).hexdigest()==source['sha256'],name
            assert hashlib.sha1(b'blob '+str(len(payload)).encode()+b'\0'+payload).hexdigest()==source['sha'],name
            parquet=ROOT/'data/parquet'/f'{name}.parquet'
            assert hashlib.sha256(parquet.read_bytes()).hexdigest()==source['parquet_sha256'],name
            path=parquet.as_posix().replace("'","''")
            counts=con.execute(f"SELECT count(*),bit_xor(hash(t))::VARCHAR FROM read_parquet('{path}') t").fetchone()
            assert counts==(baseline[name]['rows'],baseline[name]['content_fingerprint']),name
            report['sources'].append({'name':name,'rows':counts[0],'raw_sha256_verified':True,'parquet_sha256_verified':True})
    if through>=6:
        source=json.loads((ROOT/'docs/hillstrom_source.json').read_text(encoding='utf-8'))
        for relative,key in [('data/raw/hillstrom.csv','csv_sha256'),('data/parquet/hillstrom.parquet','parquet_sha256')]:
            assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==source[key],relative
        raw=pd.read_csv(ROOT/'data/raw/hillstrom.csv')
        pd.testing.assert_frame_equal(raw,pd.read_parquet(ROOT/'data/parquet/hillstrom.parquet'))
        with duckdb.connect(str(ROOT/MODULES[6][0]),read_only=True) as con:
            rebuilt=con.execute('SELECT '+','.join(source['columns'])+' FROM main.hillstrom ORDER BY source_row').df()
            pd.testing.assert_frame_equal(raw,rebuilt,check_dtype=False)
            assert len(raw)==source['rows']==64000
        report['sources'].append({'name':'hillstrom','rows':len(raw),'raw_sha256_verified':True,
                                  'parquet_sha256_verified':True,'reporting_rows_order_verified':True})
    for number,(database,check_table,folder,notebook) in MODULES.items():
        if number>through:
            break
        evidence=ROOT/'docs'/folder/'verification.json' if number>1 else ROOT/'docs/phase1_verification.json'
        stamps=json.loads(evidence.read_text(encoding='utf-8')).get('build_inputs_sha256')
        assert stamps,f'{database}: missing build provenance; rebuild in a fresh project copy'
        for relative,digest in stamps.items():
            assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==digest,f'{database}: changed calculation/source input {relative}'
        with duckdb.connect(str(ROOT/database),read_only=True) as con:
            checks=con.execute(f'SELECT * FROM {check_table}').fetchall()
            assert checks and all(p is True for _,p in checks),(database,checks)
            tables={r[0] for r in con.execute('SHOW TABLES').fetchall()}
            exports={}
            for path in sorted((ROOT/'exports'/folder).glob('*.csv')):
                if path.stem in tables:
                    exports[path.name]=compare_export(con,path.stem,path)
            if number>1:
                assert tables.issubset({Path(p).stem for p in exports}),(database,'missing CSV')
            report['modules'].append({'module':number,'database':database,'passing_checks':len(checks),
                                      'exports_verified':exports,'notebook':check_notebook(ROOT/notebook)})
    if through>=3:
        with duckdb.connect(str(ROOT/MODULES[2][0]),read_only=True) as h,duckdb.connect(str(ROOT/MODULES[3][0]),read_only=True) as c:
            annual=h.execute('SELECT annual_grocery_sales,annual_grocery_households FROM business_health_summary').fetchone()
            customer=c.execute('SELECT sum(spend),count(*) FROM hh_metrics').fetchone()
            assert abs(annual[0]-customer[0])<.005 and annual[1]==customer[1]
            report['cross_module_checks'].append('annual_grocery_customer_totals_reconcile')
    if through>=5:
        with duckdb.connect(str(ROOT/MODULES[2][0]),read_only=True) as h,duckdb.connect(str(ROOT/MODULES[5][0]),read_only=True) as c:
            weekly=h.execute('SELECT sum(sales) FROM weekly_kpis').fetchone()[0]
            panel=c.execute('SELECT sum(spend) FROM hh_week').fetchone()[0]
            assert abs(weekly-panel)<.005
            report['cross_module_checks'].append('campaign_panel_and_health_sales_reconcile')
            for cid,start,end in c.execute("SELECT campaign_id,start_week,end_week FROM campaign_roi_inputs WHERE campaign_id IN('8','13','18')").fetchall():
                for method in ['matched_pre','matched_earlier']:
                    direct=c.execute('''WITH household_change AS (
                        SELECT household_id,avg(spend) FILTER(WHERE week BETWEEN ? AND ?)
                            -avg(spend) FILTER(WHERE week BETWEEN ? AND ?) AS delta
                        FROM hh_week GROUP BY household_id
                    ) SELECT sum(w*delta) FILTER(WHERE treated)/sum(w) FILTER(WHERE treated)
                             -sum(w*delta) FILTER(WHERE NOT treated)/sum(w) FILTER(WHERE NOT treated)
                    FROM matching_samples JOIN household_change USING(household_id)
                    WHERE campaign_id=? AND method=? AND analysis_kind='primary' ''',
                    [start,end,start-8,start-1,cid,method]).fetchone()[0]
                    saved=c.execute('SELECT estimate FROM campaign_estimates WHERE campaign_id=? AND method=?',[cid,method]).fetchone()[0]
                    assert abs(direct-saved)<1e-8,(cid,method,direct,saved)
            report['cross_module_checks'].append('six_matched_campaign_estimates_recomputed_from_weights')
    if through>=6:
        with duckdb.connect(str(ROOT/MODULES[6][0]),read_only=True) as con:
            for arm,metric,saved in con.execute('SELECT arm,metric,estimate FROM main.hillstrom_effects').fetchall():
                estimate=con.execute(f'''SELECT avg({metric}) FILTER(WHERE segment=?)
                    -avg({metric}) FILTER(WHERE segment='No E-Mail') FROM main.hillstrom''',[arm]).fetchone()[0]
                assert abs(estimate-saved)<1e-10,(arm,metric)
            for decision in ['target','suppress']:
                candidate=pd.read_csv(ROOT/'exports/hillstrom'/f'{decision}_10000.csv')
                expected=con.execute('SELECT source_row FROM main.policy_assignments WHERE seed=7 AND decision=?',[decision]).df()
                assert len(candidate)==10000 and candidate.source_row.is_unique
                assert set(candidate.source_row)==set(expected.source_row)
                assert candidate.population_default_email.eq('Mens E-Mail').all()
                assert candidate.variant_suggestion_status.eq('training_only_not_validated').all()
            readout=pd.read_csv(ROOT/'exports/hillstrom_readout.csv')
            expected=con.execute('SELECT * FROM main.hillstrom_effects').df()
            pd.testing.assert_frame_equal(readout,expected,check_dtype=False,rtol=1e-10,atol=1e-12)
        report['cross_module_checks'] += ['six_randomized_effects_recomputed_from_raw_rows',
                                         'exact_candidate_exports_match_frozen_training_policy']
    return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--through',type=int,choices=range(1,7),default=6)
    args=parser.parse_args()
    report=verify(args.through)
    (ROOT/'docs/module_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(f"PASS: {len(report['sources'])} source files, {sum(m['passing_checks'] for m in report['modules'])} database checks, "
          f"{sum(len(m['exports_verified']) for m in report['modules'])} CSV/database comparisons, and {len(report['modules'])} executed notebooks")


if __name__=='__main__':
    main()
