from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent.parent / "app" / "needle_app.py")


def _run():
    return AppTest.from_file(APP, default_timeout=60).run()


def test_app_runs_and_league_has_10_rows():
    at = _run()
    assert not at.exception
    assert len(at.tabs) == 5
    assert len(at.selectbox(key="company").options) == 10


def test_switch_to_azn():
    at = _run()
    at.selectbox(key="company").select("AZN").run()
    assert not at.exception
