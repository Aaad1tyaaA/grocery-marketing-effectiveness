"""Remove row-level notebook outputs before publishing the source checkout."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
ROW_IDENTIFIERS = re.compile(r'\b(?:household_id|basket_id|source_row)\b')


def sanitize_notebook(notebook):
    removed = 0
    for cell in notebook['cells']:
        if cell['cell_type'] != 'code':
            continue
        outputs = cell.get('outputs', [])
        kept = [output for output in outputs
                if not ROW_IDENTIFIERS.search(json.dumps(output, ensure_ascii=False))]
        removed += len(outputs) - len(kept)
        cell['outputs'] = kept
    if removed:
        notebook['metadata']['grocery_publication_note'] = (
            'Outputs containing household, basket or source-row identifiers were removed. '
            'Aggregate outputs, execution counts and original input hashes were preserved. '
            'A local rebuild restores the complete outputs.')
    return removed


def main():
    for path in sorted(ROOT.glob('0[1-6]_*.ipynb')):
        notebook = json.loads(path.read_text(encoding='utf-8'))
        removed = sanitize_notebook(notebook)
        if removed:
            path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
        print(f'{path.name}: removed {removed} outputs containing row identifiers')


if __name__ == '__main__':
    main()
