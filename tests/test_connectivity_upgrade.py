"""Ordered-edge connectivity must agree with the upstream scientific library."""

from pathlib import Path

import mne
import numpy as np
import pytest
from fastmcp import Client
from pydantic import ValidationError

from mne_mcp import operations as ops
from mne_mcp import server
from mne_mcp.kernel import get_session
from mne_mcp.parameters import ConnectivityParameters


@pytest.fixture
def connection_session(tmp_path, monkeypatch):
    pytest.importorskip("mne_connectivity")
    monkeypatch.setenv("MNE_MCP_RESULTS_DIR", str(tmp_path))
    session = get_session()
    session.reset()
    rng = np.random.default_rng(21)
    t = np.arange(301) / 100
    data = rng.normal(0, 0.2, (16, 4, 301))
    for trial in data:
        phase = rng.uniform(0, 2 * np.pi)
        trial[0] += np.sin(2 * np.pi * 10 * t + phase)
        trial[1] += np.sin(2 * np.pi * 10 * t + phase + np.pi / 3)
    info = mne.create_info(["Cz", "Pz", "Oz", "EOG"], 100, ["eeg"] * 3 + ["eog"])
    epochs = mne.EpochsArray(data * 1e-6, info, tmin=-1, verbose="ERROR")
    session.set("epochs", epochs)
    yield session
    session.reset()


@pytest.mark.parametrize(
    "method",
    [
        "coh",
        "cohy",
        "imcoh",
        "plv",
        "ciplv",
        "ppc",
        "pli",
        "pli2_unbiased",
        "dpli",
        "wpli",
        "wpli2_debiased",
    ],
)
def test_measures_and_replay(connection_session, method):
    from mne_connectivity import spectral_connectivity_epochs

    epochs = connection_session.get("epochs")
    before = epochs.get_data().copy()
    params = ConnectivityParameters(
        method=method,
        mode="fourier",
        pairs=[("Cz", "Pz"), ("Pz", "Cz")],
        fmin=[8, 18],
        fmax=[13, 24],
        plot=False,
    )
    result = ops.compute_connectivity(params)
    con = connection_session.get("con")
    expected = spectral_connectivity_epochs(
        epochs.copy().pick("data"),
        method=method,
        mode="fourier",
        indices=([0, 1], [1, 0]),
        fmin=(8, 18),
        fmax=(13, 24),
        faverage=True,
        verbose="ERROR",
    )
    np.testing.assert_allclose(con.get_data(), expected.get_data())
    np.testing.assert_array_equal(epochs.get_data(), before)
    replay = {"epochs": epochs}
    exec(result["code"], replay)
    np.testing.assert_allclose(replay["con"].get_data(), con.get_data())
    if method == "imcoh":
        np.testing.assert_allclose(con.get_data()[0], -con.get_data()[1], atol=1e-12)
        assert abs(con.get_data()[0, 0]) > 0.1
    if method == "cohy":
        assert np.iscomplexobj(con.get_data())
        np.testing.assert_allclose(con.get_data()[0], con.get_data()[1].conj())
    if method == "dpli":
        np.testing.assert_allclose(con.get_data()[0] + con.get_data()[1], 1)
        assert con.get_data()[0, 0] != con.get_data()[1, 0]


@pytest.mark.parametrize("mode", ["multitaper", "fourier", "cwt_morlet"])
@pytest.mark.parametrize("faverage", [True, False])
def test_estimators_frequency_and_time_axes(connection_session, mode, faverage):
    from mne_connectivity import spectral_connectivity_epochs

    options = {}
    if mode == "multitaper":
        options = dict(mt_bandwidth=4, mt_adaptive=True, mt_low_bias=False)
    elif mode == "cwt_morlet":
        options = dict(cwt_freqs=[8, 10, 12, 20, 24], cwt_n_cycles=[2, 2, 3, 4, 4])
    params = ConnectivityParameters(
        mode=mode,
        fmin=[8, 18],
        fmax=[13, 24],
        faverage=faverage,
        picks=["Pz", "Cz"],
        pairs=[("Pz", "Cz")],
        tmin=-0.5,
        tmax=1,
        plot=True,
        **options,
    )
    result = ops.compute_connectivity(params)
    options = options.copy()
    if mode == "cwt_morlet":
        options["cwt_freqs"] = np.array(options["cwt_freqs"])
    expected = spectral_connectivity_epochs(
        connection_session.get("epochs").copy().pick(["Pz", "Cz"]),
        indices=([0], [1]),
        method="coh",
        mode=mode,
        fmin=(8, 18),
        fmax=(13, 24),
        faverage=faverage,
        tmin=-0.5,
        tmax=1,
        verbose="ERROR",
        **options,
    )
    actual = connection_session.get("con")
    np.testing.assert_allclose(actual.get_data(), expected.get_data())
    assert actual.get_data().ndim == (3 if mode == "cwt_morlet" else 2)
    assert len(result["figures"]) == 1
    assert Path(result["figures"][0]).stat().st_size > 1000
    replay = {"epochs": connection_session.get("epochs")}
    exec(result["code"], replay)
    np.testing.assert_allclose(actual.get_data(), replay["con"].get_data())


@pytest.mark.parametrize(
    "options",
    [
        {"fmin": []},
        {"fmin": [8, 20], "fmax": [13]},
        {"fmin": 15, "fmax": 10},
        {"fmin": [20, 8], "fmax": [30, 13]},
        {"fmin": float("nan")},
        {"method": "gc"},
        {"mode": "fourier", "mt_bandwidth": 4},
        {"mode": "fourier", "mt_adaptive": True},
        {"mode": "fourier", "mt_low_bias": False},
        {"mode": "cwt_morlet"},
        {"cwt_freqs": [8, 12]},
        {"cwt_n_cycles": 3},
        {"mode": "cwt_morlet", "cwt_freqs": [12, 8]},
        {"mode": "cwt_morlet", "cwt_freqs": [8, 12], "cwt_n_cycles": [2]},
        {"mode": "cwt_morlet", "cwt_freqs": [20, 30]},
        {"pairs": []},
        {"pairs": [["Cz", "Cz"]]},
        {"pairs": [["Cz", "Pz"], ["Cz", "Pz"]]},
        {"con_name": "np"},
        {"con_name": "epochs"},
        {"block_size": 0},
        {"block_size": True},
        {"tmin": 1, "tmax": 0},
        {"unsupported": True},
    ],
)
def test_parameter_validation(options):
    with pytest.raises(ValidationError):
        ConnectivityParameters(**options)


@pytest.mark.parametrize(
    "options",
    [
        {"pairs": [["Cz", "missing"]]},
        {"picks": ["Cz"]},
        {"fmax": 50},
        {"tmin": -2},
        {"tmax": 3},
    ],
)
def test_invalid_data_preserves_output(connection_session, options):
    connection_session.set("con", "previous")
    with pytest.raises(ValueError):
        ops.compute_connectivity(ConnectivityParameters(plot=False, **options))
    assert connection_session.get("con") == "previous"


def test_default_selection_and_directed_pairs(connection_session):
    connection_session.get("epochs").info["bads"] = ["Oz"]
    ops.compute_connectivity(ConnectivityParameters(method="dpli", plot=False))
    con = connection_session.get("con")
    assert con.names == ["Cz", "Pz"]
    assert len(con.indices[0]) == 2
    with pytest.raises(ValueError, match="absent"):
        ops.compute_connectivity(
            ConnectivityParameters(pairs=[("Cz", "Oz")], plot=False)
        )


def test_single_epoch_rejected(connection_session):
    connection_session.set("epochs", connection_session.get("epochs")[:1])
    with pytest.raises(ValueError, match="two"):
        ops.compute_connectivity(ConnectivityParameters(plot=False))


@pytest.mark.asyncio
async def test_mcp_boundary(connection_session):
    async with Client(server.mcp) as client:
        result = await client.call_tool(
            "mne_compute_connectivity",
            {
                "params": {
                    "mode": "fourier",
                    "method": "cohy",
                    "pairs": [["Cz", "Pz"]],
                    "fmin": [8, 18],
                    "fmax": [13, 24],
                    "plot": False,
                }
            },
        )
        assert not result.is_error
        assert np.iscomplexobj(connection_session.get("con").get_data())
        invalid = await client.call_tool(
            "mne_compute_connectivity",
            {
                "params": {
                    "method": "gc",
                }
            },
            raise_on_error=False,
        )
        assert invalid.is_error


def test_legacy_plot_retains_complex_values(connection_session):
    result = ops.connectivity(method="cohy")
    assert len(result["figures"]) == 1
    assert np.iscomplexobj(connection_session.get("con").get_data())
    assert connection_session.get("con").get_data().shape == (9, 1)


def test_upstream_warnings_surface(connection_session, monkeypatch):
    import warnings

    import mne_connectivity

    original = mne_connectivity.spectral_connectivity_epochs

    def warning_result(*args, **kwargs):
        warnings.warn("Synthetic spectral support warning", RuntimeWarning)
        return original(*args, **kwargs)

    monkeypatch.setattr(
        mne_connectivity, "spectral_connectivity_epochs", warning_result
    )
    result = ops.compute_connectivity(ConnectivityParameters(plot=False))
    assert "Synthetic spectral support warning" in result["markdown"]


def test_nonfinite_values_not_hidden(connection_session):
    epochs = connection_session.get("epochs")
    epochs._data[:, 0, :] = 0
    out = ops.compute_connectivity(
        ConnectivityParameters(
            mode="fourier",
            pairs=[("Cz", "Pz")],
            plot=False,
        )
    )
    assert "non-finite" in out["markdown"]
    assert not np.isfinite(connection_session.get("con").get_data()).all()


def test_legacy_directed_storage(connection_session):
    ops.connectivity(method="dpli")
    con = connection_session.get("con")
    assert con.get_data().shape == (9, 1)
    dense = con.get_data(output="dense")
    np.testing.assert_allclose(dense[0, 1] + dense[1, 0], 1)
