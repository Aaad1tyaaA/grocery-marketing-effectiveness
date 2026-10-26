"""Keep aggregate notebooks readable without publishing row-level samples."""
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from prepare_publication import ROW_IDENTIFIERS, sanitize_notebook


def test_sanitizer_preserves_aggregate_outputs_and_execution_provenance():
    aggregate = {'output_type': 'stream', 'text': ['sales: 4185055.64']}
    notebook = {'metadata': {'grocery_inputs_sha256': {'input.csv': 'original-digest'}},
                'cells': [{'cell_type': 'markdown', 'source': ['Example household_id query']},
                          {'cell_type': 'code', 'execution_count': 4,
                           'source': ['display(sample)'], 'outputs': [aggregate,
                           {'data': {'text/html': ['<th>household_id</th><td>900</td>']}},
                           {'text': ['basket_id 31198570044']},
                           {'data': {'text/plain': ['source_row 42']}}]}]}
    assert sanitize_notebook(notebook) == 3
    assert notebook['cells'][1]['outputs'] == [aggregate]
    assert notebook['cells'][1]['execution_count'] == 4
    assert notebook['metadata']['grocery_inputs_sha256']['input.csv'] == 'original-digest'
    assert sanitize_notebook(notebook) == 0


def test_committed_notebooks_have_no_identifier_outputs():
    for path in ROOT.glob('0[1-6]_*.ipynb'):
        notebook = json.loads(path.read_text(encoding='utf-8'))
        for cell in notebook['cells']:
            assert not ROW_IDENTIFIERS.search(json.dumps(cell.get('outputs', []), ensure_ascii=False)), path.name


def test_handoff_links_resolve_locally():
    for relative in ['README.md', 'docs/README.md', 'docs/power_bi.md', 'excel/README.md']:
        path = ROOT / relative
        for link in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if '://' not in link and not link.startswith('#'):
                assert (path.parent / unquote(link.split('#')[0])).exists(), (relative, link)
