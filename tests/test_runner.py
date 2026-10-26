import json
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import run_all


@pytest.mark.parametrize('raw_database_exists',[False,True])
def test_runner_builds_missing_raw_database_despite_published_verification(tmp_path,monkeypatch,raw_database_exists):
    for folder in ['docs','data/raw','data/parquet']:
        (tmp_path/folder).mkdir(parents=True,exist_ok=True)
    for name in ['transactions','promotions','campaigns','campaign_descriptions','coupons','coupon_redemptions','demographics','products']:
        (tmp_path/'data/parquet'/f'{name}.parquet').touch()
    (tmp_path/'data/raw/source.rda').touch()
    (tmp_path/'docs/source_manifest.json').write_text(json.dumps({'files':[{'name':'source.rda','parquet_sha256':'fixture'}]}))
    (tmp_path/'docs/verification.json').write_text('{}')
    (tmp_path/'grocery_phase1.duckdb').touch()
    if raw_database_exists:
        (tmp_path/'grocery.duckdb').touch()
    calls=[]
    monkeypatch.setattr(run_all,'ROOT',tmp_path)
    monkeypatch.setattr(run_all,'run',lambda *args:calls.append(args))
    monkeypatch.setattr(sys,'argv',['run_all.py','--through','1'])
    run_all.main()
    assert (('scripts/setup_db.py',) in calls) is not raw_database_exists
