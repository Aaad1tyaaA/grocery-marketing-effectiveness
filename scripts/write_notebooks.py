"""Execute learning notebooks and record their exact input-file hashes."""
from pathlib import Path
import argparse
import hashlib
import nbformat
from nbclient import NotebookClient

ROOT=Path(__file__).resolve().parents[1]
NOTEBOOKS={1:'01_data_model.ipynb',2:'02_business_health.ipynb',3:'03_customers.ipynb',4:'04_promotions.ipynb',5:'05_campaigns.ipynb',6:'06_hillstrom.ipynb'}
FOLDERS={1:'phase1',2:'business_health',3:'customers',4:'promotions',5:'campaigns',6:'hillstrom'}
SQL={1:'01_model.sql',2:'02_health.sql',3:'03_customers.sql',4:'04_promo.sql',5:'05_campaigns.sql',6:'06_hillstrom.sql'}
RUNNERS={1:'build_phase1.py',2:'run_business_health.py',3:'run_customers.py',4:'run_promotions.py',5:'run_campaigns.py',6:'run_hillstrom.py'}


def execute_notebook(path,module):
    nb=nbformat.read(path,as_version=4)
    for cell in nb.cells:
        if cell.cell_type=='code':
            cell.outputs=[]
            cell.execution_count=None
    NotebookClient(nb,timeout=180,kernel_name='python3',resources={'metadata':{'path':str(ROOT)}}).execute()
    files=list((ROOT/'exports'/FOLDERS[module]).glob('*.csv'))
    files += [ROOT/'sql/01_model.sql',ROOT/'sql'/SQL[module],ROOT/'scripts'/RUNNERS[module],
              ROOT/'docs/source_manifest.json',ROOT/'docs/verification.json']
    if module==5:
        files.append(ROOT/'scripts/campaign_methods.py')
    if module==6:
        files += [ROOT/p for p in ['scripts/hillstrom_methods.py','scripts/campaign_methods.py',
                  'scripts/get_hillstrom.py','docs/hillstrom_source.json','requirements-hillstrom.txt',
                  'docs/experiment_readout.md']]
    findings=ROOT/'docs'/FOLDERS[module]/'findings.md' if module>1 else ROOT/'docs/phase1_findings.md'
    files.append(findings)
    nb.metadata['grocery_inputs_sha256']={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                                        for p in sorted(set(files))}
    nbformat.write(nb,path)
    print(f'Executed: {path.name}',flush=True)


def create_phase1():
    nb=nbformat.v4.new_notebook()
    nb.metadata['kernelspec']={'display_name':'Python 3','language':'python','name':'python3'}
    md=nbformat.v4.new_markdown_cell;code=nbformat.v4.new_code_cell
    nb.cells=[md('''# Module 1 — Data model and quality

Word guide Steps 1.1.1–1.1.7. Source conversions are in `scripts/get_data.py`; the model is `sql/01_model.sql`; the builder is `scripts/build_phase1.py`. This notebook reads their saved results so DBeaver can remain open. Raw inputs are preserved. Monetary values are USD.'''),
        code('''from pathlib import Path
import json
import pandas as pd
from IPython.display import display, Markdown
ROOT = Path.cwd()
DATA = ROOT / 'exports/phase1'
def load(name):
    return pd.read_csv(DATA / f'{name}.csv')
manifest = json.loads((ROOT / 'docs/source_manifest.json').read_text(encoding='utf-8'))
display(pd.DataFrame([{'source': f['name'], 'rows': f['rows'], 'sha256': f['sha256']} for f in manifest['files']]))
print('Source commit:', manifest['commit'])'''),
        md('''## 1. Learn the fields and profile the sources

IDs are labels. `sales_value` is retailer receipts; retailer-funded discounts combine loyalty discounts and coupon matching. Manufacturer coupons are reported separately. Inspect nulls before joining or replacing values.'''),
        code('''display(load('profile_transaction_summary').T)
columns = load('profile_columns')
display(columns[columns.null_rows > 0])
display(load('profile_relationships'))'''),
        md('''## 2. Build the model and document cleaning

The model removes only quantity-zero/sales-zero voids. It retains free lines, zero-quantity lines with sales, unknown products and large quantities. Promotion conflicts use MULTIPLE and preserve recorded display/mailer exposure.'''),
        code('''display(load('fact_sales_sample').head(10))
display(load('profile_missing_products'))
display(load('profile_promotion_quality'))
display(Markdown((ROOT / 'docs/cleaning_log.md').read_text(encoding='utf-8')))'''),
        md('''## 3. Review anomalies and time boundaries

Flags prompt inspection, not deletion. Local dates use America/New_York; UTC timestamps are retained. A missing purchase date does not prove a store was closed.'''),
        code('''display(load('daily_anomalies'))
display(load('basket_anomalies').sort_values('basket_value', ascending=False).head(10))
display(load('profile_missing_days'))
display(load('profile_campaign_windows'))'''),
        md('''## 4. Reconcile the model

Every check must pass. In DBeaver connect to `grocery_phase1.duckdb` and inspect `sql/01d_inspect.sql`; use Ctrl+Enter for one query at a time. The builder reproduces the module in a fresh project copy.'''),
        code('''checks = load('phase1_checks')
assert checks.passed.astype(str).str.lower().eq('true').all()
print(f'{len(checks)} model checks passed')
display(checks)
display(Markdown((ROOT / 'docs/phase1_findings.md').read_text(encoding='utf-8')))''')]
    nbformat.write(nb,ROOT/NOTEBOOKS[1])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--through',type=int,choices=range(1,5),default=4)
    args=parser.parse_args()
    create_phase1()
    for module in range(1,args.through+1):
        execute_notebook(ROOT/NOTEBOOKS[module],module)


if __name__=='__main__':
    main()
