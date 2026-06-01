"""Tests for the persistent analysis kernel."""

from mne_mcp.kernel import Session


def test_run_code_returns_last_expression():
    s = Session()
    res = s.run_code("a = 10\nb = 5\na + b")
    assert res["error"] is None
    assert res["result_repr"] == "15"


def test_run_code_captures_stdout():
    s = Session()
    res = s.run_code("print('hi there')")
    assert "hi there" in res["stdout"]


def test_run_code_reports_error_without_crashing():
    s = Session()
    res = s.run_code("1 / 0")
    assert res["error"] is not None
    assert "ZeroDivisionError" in res["error"]
    assert res["traceback"]


def test_run_code_syntax_error():
    s = Session()
    res = s.run_code("def (")
    assert res["error"] and "SyntaxError" in res["error"]


def test_state_persists_across_calls():
    s = Session()
    s.run_code("counter = 1")
    s.run_code("counter += 41")
    res = s.run_code("counter")
    assert res["result_repr"] == "42"


def test_set_get_and_summary():
    s = Session()
    s.set("arr", __import__("numpy").zeros((3, 4)))
    assert s.has("arr")
    assert "arr" in s.data_names()
    summary = s.summary()
    assert "arr" in summary and "ndarray" in summary


def test_figure_capture(tmp_path, monkeypatch):
    monkeypatch.setenv("MNE_MCP_RESULTS_DIR", str(tmp_path))
    s = Session()
    res = s.run_code("plt.figure(); plt.plot([1,2,3]); 'done'")
    assert len(res["figures"]) == 1
    assert res["figures"][0].endswith(".png")
    import os

    assert os.path.exists(res["figures"][0])


def test_reset_clears_objects():
    s = Session()
    s.run_code("keep = 99")
    assert s.has("keep")
    s.reset()
    assert not s.has("keep")
    # preloaded modules survive reset
    assert "mne" in s.namespace and "np" in s.namespace
