"""Build missing completed modules, execute notebooks, and verify all delivered artifacts."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
BUILDERS={1:('grocery_phase1.duckdb','build_phase1.py'),
          2:('grocery_business_health.duckdb','run_business_health.py'),
          3:('grocery_customers.duckdb','run_customers.py'),
          4:('grocery_promotions.duckdb','run_promotions.py'),
          5:('grocery_campaigns.duckdb','run_campaigns.py'),
          6:('grocery_hillstrom.duckdb','run_hillstrom.py')}


def run(*args):
    # Keep numerical-library worker stacks small on laptops while notebooks execute.
    env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    subprocess.run([sys.executable,*args],cwd=ROOT,env=env,check=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--through',type=int,choices=range(1,7),default=6,
                        help='Last analysis module to build/check (default: 6). Presentation artifacts have separate verification.')
    args=parser.parse_args()
    required=['transactions','promotions','campaigns','campaign_descriptions','coupons','coupon_redemptions','demographics','products']
    manifest=ROOT/'docs/source_manifest.json'
    source_files=json.loads(manifest.read_text(encoding='utf-8'))['files'] if manifest.exists() else []
    if (not source_files or any(not (ROOT/'data/parquet'/f'{name}.parquet').exists() for name in required)
        or any(not (ROOT/'data/raw'/s['name']).exists() or 'parquet_sha256' not in s for s in source_files)):
        run('scripts/get_data.py')
    if not (ROOT/'grocery.duckdb').exists() or not (ROOT/'docs/verification.json').exists():
        run('scripts/setup_db.py')
    if args.through>=6 and any(not (ROOT/p).exists() for p in
        ['docs/hillstrom_source.json','data/raw/hillstrom.csv','data/parquet/hillstrom.parquet']):
        run('scripts/get_hillstrom.py')
    for module,(database,script) in BUILDERS.items():
        if module>args.through:
            break
        if (ROOT/database).exists():
            print(f'Preserving existing {database}; it will be verified below.',flush=True)
        else:
            run('scripts/'+script)
    run('scripts/write_notebooks.py','--through',str(min(4,args.through)))
    if args.through>=5:
        run('scripts/write_campaign_deliverables.py')
        run('scripts/export_app_data.py')
    if args.through>=6:
        run('scripts/write_hillstrom_deliverables.py')
    run('scripts/verify_modules.py','--through',str(args.through))
    print(f'Analysis modules 1-{args.through} verified. See README for the Excel and Power BI deliverables.')


if __name__=='__main__':
    main()
