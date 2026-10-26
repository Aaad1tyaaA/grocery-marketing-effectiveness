from pathlib import Path
import ast
import hashlib
import sys
import nbformat
import pytest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from verify_modules import check_notebook

def test_python_compiles():
    for file in ROOT.rglob('*.py'):
        if not any(part in {'.venv','venv','__pycache__'} for part in file.relative_to(ROOT).parts):
            ast.parse(file.read_text(encoding='utf-8'),filename=str(file))

def test_notebook_errors_unexecuted_cells_and_stale_inputs_are_detected(tmp_path):
    path=tmp_path/'example.ipynb';source=tmp_path/'input.csv'
    source.write_text('value\n1\n')
    nb=nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell('print(1)')])
    nb.metadata['grocery_inputs_sha256']={'input.csv':hashlib.sha256(source.read_bytes()).hexdigest()}
    nbformat.write(nb,path)
    with pytest.raises(AssertionError,match='unexecuted'):
        check_notebook(path,tmp_path)
    nb.cells[0].execution_count=1
    nb.cells[0].outputs=[nbformat.v4.new_output('error',ename='ValueError',evalue='failed',traceback=[])]
    nbformat.write(nb,path)
    with pytest.raises(AssertionError,match='error outputs'):
        check_notebook(path,tmp_path)
    nb.cells[0].outputs=[];nbformat.write(nb,path)
    assert check_notebook(path,tmp_path)['executed_code_cells']==1
    source.write_text('value\n2\n')
    with pytest.raises(AssertionError,match='stale input'):
        check_notebook(path,tmp_path)
