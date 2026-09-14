"""Numerical parity and MCP-boundary coverage for structured analysis."""

import asyncio
import threading
from pathlib import Path

import mne
import numpy as np
import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from pydantic import ValidationError

from mne_mcp import operations as ops
from mne_mcp import server
from mne_mcp.kernel import get_session
from mne_mcp.parameters import TFRParameters


@pytest.fixture
def analysis_session(tmp_path, monkeypatch):
    monkeypatch.setenv("MNE_MCP_RESULTS_DIR", str(tmp_path))
    s = get_session()
    s.reset()
    info = mne.create_info(["Cz", "Pz", "EOG"], 100, ["eeg", "eeg", "eog"])
    raw = mne.io.RawArray(np.random.default_rng(10).normal(0, 1e-6, (3, 2200)), info)
    s.set("raw", raw)
    s.set("events", np.array([[300, 0, 1], [800, 0, 2], [1300, 0, 1], [1800, 0, 2]]))
    ops.make_epochs(
        event_id={"target": 1, "standard": 2}, tmin=-1, tmax=1, baseline=None, reject={}
    )
    yield s
    s.reset()


def test_json_epochs_match_mne(analysis_session):
    s = analysis_session
    ops.make_epochs(
        event_id={"target": 1, "standard": 2},
        tmin=-0.5,
        tmax=0.7,
        baseline=[None, 0],
        reject={"eeg": 100e-6, "eog": 200e-6},
        flat={"eeg": 1e-10},
        picks=["Cz", "EOG"],
        detrend=1,
    )
    expected = mne.Epochs(
        s.get("raw"),
        s.get("events"),
        event_id={"target": 1, "standard": 2},
        tmin=-0.5,
        tmax=0.7,
        baseline=(None, 0),
        reject={"eeg": 100e-6, "eog": 200e-6},
        flat={"eeg": 1e-10},
        picks=["Cz", "EOG"],
        detrend=1,
        preload=True,
    )
    np.testing.assert_allclose(s.get("epochs").get_data(), expected.get_data())


@pytest.mark.parametrize(
    "kwargs",
    [
        {"reject": {}, "reject_eeg": 1e-4},
        {"baseline": [0]},
        {"reject": {"eeg": -1}},
        {"flat": {"eeg": float("nan")}},
        {"event_id": {"x": True}},
        {"event_id": {}},
    ],
)
def test_invalid_epochs_preserve_output(analysis_session, kwargs):
    previous = analysis_session.get("epochs")
    with pytest.raises(ValueError):
        ops.make_epochs(**kwargs)
    assert analysis_session.get("epochs") is previous


@pytest.mark.parametrize("method", ["morlet", "multitaper"])
@pytest.mark.parametrize("average", [True, False])
def test_tfr_matches_mne_and_code_replay(analysis_session, method, average):
    s = analysis_session
    epochs = s.get("epochs")
    before = epochs.get_data().copy()
    params = TFRParameters(
        method=method,
        freqs=[8, 12, 20],
        n_cycles=[2, 3, 4],
        picks=["Cz", "Pz"],
        average=average,
        return_itc=average,
        time_bandwidth=4 if method == "multitaper" else None,
        decim=2,
        baseline=[-0.5, -0.2],
        baseline_mode="logratio",
        plot=False,
    )
    result = ops.compute_tfr(params)
    kw = {"time_bandwidth": 4} if method == "multitaper" else {}
    expected = epochs.compute_tfr(
        method,
        [8, 12, 20],
        n_cycles=[2, 3, 4],
        picks=["Cz", "Pz"],
        average=average,
        return_itc=average,
        decim=2,
        **kw,
    )
    expected_power = expected[0] if average else expected
    expected_power.apply_baseline((-0.5, -0.2), mode="logratio")
    np.testing.assert_allclose(s.get("power").data, expected_power.data)
    if average:
        np.testing.assert_allclose(s.get("itc").data, expected[1].data)
    np.testing.assert_array_equal(epochs.get_data(), before)
    replay = {"epochs": epochs}
    exec(result["code"], replay)
    np.testing.assert_allclose(replay["power"].data, s.get("power").data)


@pytest.mark.parametrize(
    "options",
    [
        {"freqs": [12, 8]},
        {"freqs": [0]},
        {"freqs": [float("nan")]},
        {"n_cycles": [2]},
        {"average": False, "return_itc": True},
        {"time_bandwidth": 4},
        {"decim": 0},
        {"decim": True},
        {"baseline": [1, 0]},
        {"tfr_name": "np"},
        {"tfr_name": "epochs"},
        {"return_itc": True, "itc_name": "power"},
        {"unsupported": 3},
    ],
)
def test_tfr_validation(options):
    with pytest.raises(ValidationError):
        TFRParameters.model_validate({"freqs": [8, 12], **options})


def test_tfr_nyquist_does_not_publish(analysis_session):
    with pytest.raises(ValueError, match="Nyquist"):
        ops.compute_tfr(TFRParameters(freqs=[50], plot=False))
    assert not analysis_session.has("power")


@pytest.mark.parametrize("method", ["morlet", "multitaper"])
def test_single_trial_plot_and_failed_baseline(analysis_session, method):
    out = ops.compute_tfr(
        TFRParameters(
            method=method,
            freqs=[8, 12],
            n_cycles=2,
            average=False,
            picks=["Cz", "Pz"],
            plot=True,
        )
    )
    assert analysis_session.get("power").data.ndim == 4
    assert len(out["figures"]) == 1
    assert Path(out["figures"][0]).stat().st_size > 1000
    previous = analysis_session.get("power")
    with pytest.raises(ValueError):
        ops.compute_tfr(
            TFRParameters(freqs=[8, 12], n_cycles=2, baseline=[2, 3], plot=False)
        )
    assert analysis_session.get("power") is previous


def test_filter_json_and_legacy_picks(analysis_session):
    raw = analysis_session.get("raw")
    untouched = raw.get_data(picks="EOG").copy()
    ops.filter_data("raw", 1, 30, picks="Cz,Pz")
    ops.filter_data("raw", 2, 25, picks=["Cz", "Pz"])
    np.testing.assert_array_equal(raw.get_data(picks="EOG"), untouched)


@pytest.mark.asyncio
async def test_mcp_json_schema_and_execution(analysis_session):
    async with Client(server.mcp) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}
        assert "params" in tools["mne_compute_tfr"].inputSchema["properties"]
        result = await client.call_tool(
            "mne_make_epochs",
            {
                "event_id": {"target": 1},
                "baseline": [None, 0],
                "reject": {},
                "picks": ["Cz", "Pz"],
                "tmin": -1,
                "tmax": 1,
            },
        )
        assert not result.is_error
        assert analysis_session.get("epochs").event_id == {"target": 1}
        result = await client.call_tool(
            "mne_compute_tfr",
            {
                "params": {
                    "freqs": [10, 20],
                    "n_cycles": 2,
                    "return_itc": True,
                }
            },
        )
        assert not result.is_error
        assert analysis_session.has("itc")
        assert analysis_session.get("power").data.shape == (2, 2, 201)
        invalid = await client.call_tool(
            "mne_compute_tfr",
            {
                "params": {
                    "freqs": [10],
                    "average": False,
                    "return_itc": True,
                }
            },
            raise_on_error=False,
        )
        assert invalid.is_error
        invalid = await client.call_tool(
            "mne_make_epochs",
            {
                "event_id": {"target": True},
            },
            raise_on_error=False,
        )
        assert invalid.is_error


@pytest.mark.asyncio
async def test_worker_error_releases_lock(monkeypatch):
    monkeypatch.setattr(server, "_require_mne", lambda: None)

    def fail():
        raise ValueError("invalid analysis")

    with pytest.raises(ToolError, match=r"\[INVALID_INPUT\].*invalid analysis"):
        await server._exec(fail, None)
    assert not server._EXEC_LOCK.locked()
    assert await server._exec(lambda: {"markdown": "recovered"}, None) == "recovered"


@pytest.mark.asyncio
@pytest.mark.parametrize("cancel", [False, True])
async def test_worker_owns_lock_until_finished(monkeypatch, cancel):
    monkeypatch.setattr(server, "get_timeout", lambda: 0.05)
    monkeypatch.setattr(server, "_require_mne", lambda: None)
    started, release, finished = threading.Event(), threading.Event(), threading.Event()

    def slow():
        started.set()
        try:
            release.wait(5)
            return {"markdown": "done"}
        finally:
            finished.set()

    task = asyncio.create_task(server._exec(slow, None))
    try:
        assert await asyncio.to_thread(started.wait, 2)
        if cancel:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            with pytest.raises(ToolError, match=r"\[TIMEOUT\].*timed out"):
                await task
        assert server._EXEC_LOCK.locked()
        with pytest.raises(ToolError, match=r"\[SESSION_BUSY\]"):
            await server._exec(lambda: pytest.fail("overlap"), None)
        async with Client(server.mcp) as client:
            for name, args in [
                ("mne_reset_session", {}),
                ("mne_session_info", {}),
                ("mne_run_code", {"code": "1 + 1"}),
            ]:
                response = await client.call_tool(name, args, raise_on_error=False)
                assert response.is_error
                assert "Session busy" in response.content[0].text
    finally:
        release.set()
        assert await asyncio.to_thread(finished.wait, 2)
        # Queue a worker call to allow the original worker's finally to complete.
        for _ in range(100):
            if not server._EXEC_LOCK.locked():
                break
            await asyncio.sleep(0.01)
        if not task.done():
            await task
    assert not server._EXEC_LOCK.locked()
    assert await server._exec(lambda: {"markdown": "next"}, None) == "next"
