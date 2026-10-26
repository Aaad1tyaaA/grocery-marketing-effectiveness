from pathlib import Path
import pytest
AppTest=pytest.importorskip('streamlit.testing.v1',reason='Optional Streamlit preview dependency is not installed').AppTest
ROOT=Path(__file__).resolve().parents[1]

def test_app_runs():
    if not (ROOT/'app/data/weekly_kpis.csv').exists():
        pytest.skip('Run scripts/export_app_data.py first')
    at = AppTest.from_file(str(ROOT/'app/streamlit_app.py'), default_timeout=60).run()
    assert not at.exception
    assert len(at.metric) >= 3
    assert at.metric[0].value=='$4.19M'
    assert at.metric[1].value=='2,467'
    assert at.metric[2].value=='$29.67'
    assert at.metric[3].value=='15.8%'


def test_missing_preview_data_gives_instructions_instead_of_crashing(tmp_path):
    path=tmp_path/'streamlit_app.py'
    path.write_text((ROOT/'app/streamlit_app.py').read_text(encoding='utf-8'),encoding='utf-8')
    at=AppTest.from_file(str(path),default_timeout=60).run()
    assert not at.exception
    assert len(at.info)==1
    assert 'summary files' in at.info[0].value
