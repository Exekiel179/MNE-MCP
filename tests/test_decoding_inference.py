"""Numerical parity and invalid-design tests for decoding group inference."""

import itertools

import mne
import numpy as np
import pytest
from fastmcp import Client
from pydantic import ValidationError

from mne_mcp import operations as ops
from mne_mcp import server
from mne_mcp.kernel import get_session
from mne_mcp.parameters import DecodingGroupTestParameters as Parameters


@pytest.fixture(params=["sliding", "generalizing"])
def study(request, tmp_path, monkeypatch):
    monkeypatch.setenv("MNE_MCP_RESULTS_DIR", str(tmp_path))
    session = get_session()
    session.reset()
    method = request.param
    shape = (4,) if method == "sliding" else (4, 4)
    rng = np.random.default_rng(23)
    values = 0.5 + rng.normal(0.025, 0.04, (8, *shape))
    names = [f"subject_{i}" for i in range(8)]
    for i, name in enumerate(names):
        session.set(name, values[i].copy())
        session.set(
            name + "_details",
            {
                "method": method,
                "scoring": "roc_auc",
                "times": np.arange(4) * 0.1,
                "score_axes": (
                    ["time"] if method == "sliding" else ["train_time", "test_time"]
                ),
                "class_codes": [1, 2],
                "positive_class_code": 2,
                "classifier": {"C": 1.0},
                "warnings": [],
            },
        )
    params = dict(
        score_names=names,
        subject_ids=[f"p{i}" for i in range(8)],
        independent_subjects=True,
        null_value=0.5,
        n_permutations=256,
        plot=False,
    )
    yield session, params, values
    session.reset()


@pytest.mark.parametrize("correction", ["max_t", "cluster"])
def test_mne_parity_and_replay(study, correction):
    session, params, values = study
    params.update(correction=correction)
    if correction == "cluster":
        params["threshold"] = 1.0
    result = ops.decoding_group_test(Parameters(**params))
    out = session.get("decoding_stats")
    X = (values - 0.5).reshape(8, -1)
    kwargs = dict(n_permutations=256, tail=0, seed=97, n_jobs=1)
    if correction == "max_t":
        T, p, h0 = mne.stats.permutation_t_test(X, **kwargs)
        np.testing.assert_allclose(out["p_values"].ravel(), p)
        # Independently enumerate all sign flips, including the observed assignment.
        signs = np.array(list(itertools.product([-1, 1], repeat=8)))
        permuted = signs[:, :, None] * X
        perm_t = permuted.mean(1) / (permuted.std(1, ddof=1) / np.sqrt(8))
        maxima = np.abs(perm_t).max(1)
        manual_p = np.mean(maxima[:, None] >= np.abs(T)[None, :] - 1e-12, axis=0)
        np.testing.assert_allclose(p, manual_p)
    else:
        T, clusters, p, h0 = mne.stats.permutation_cluster_1samp_test(
            X,
            adjacency=mne.stats.combine_adjacency(*values.shape[1:]),
            threshold=1.0,
            out_type="indices",
            **kwargs,
        )
        assert out["p_values"] is None
        np.testing.assert_allclose(out["cluster_p_values"], p)
        for actual, expected in zip(out["clusters"], clusters):
            np.testing.assert_array_equal(actual, expected[0])
    np.testing.assert_allclose(out["statistic"].ravel(), T)
    np.testing.assert_allclose(out["H0"], h0)
    replay = {name: session.get(name) for name in params["score_names"]}
    exec(result["code"], replay)
    np.testing.assert_allclose(replay["decoding_stats"]["statistic"], out["statistic"])
    np.testing.assert_allclose(replay["decoding_stats"]["H0"], out["H0"])
    np.testing.assert_array_equal(
        np.stack([session.get(n) for n in params["score_names"]]), values
    )
    assert out["family_size"] == X.shape[1]
    assert out["n_subjects"] == 8


@pytest.mark.parametrize(
    "change",
    [
        {"independent_subjects": False},
        {"independent_subjects": "true"},
        {"subject_ids": ["p"] * 8},
        {"subject_ids": ["p"]},
        {"score_names": ["x", "x"]},
        {"null_value": float("nan")},
        {"n_permutations": True},
        {"n_permutations": 1},
        {"seed": -1},
        {"alpha": 0},
        {"correction": "fdr"},
        {"tail": 1},
        {"threshold": 1.0},
        {"correction": "cluster", "tail": -1, "threshold": 2.0},
        {"correction": "cluster", "threshold": 0.0},
        {"name": "subject_0"},
        {"name": "subject_0_details"},
        {"name": "np"},
        {"extra": 3},
    ],
)
def test_invalid_parameters(study, change):
    with pytest.raises(ValidationError):
        Parameters(**{**study[1], **change})


@pytest.mark.parametrize(
    "failure",
    [
        "times",
        "metric",
        "axes",
        "folds",
        "nan",
        "variance",
        "alias",
        "warnings",
        "missing",
    ],
)
def test_bad_data_preserves_existing_result(study, failure):
    session, params, values = study
    name = params["score_names"][0]
    details = session.get(name + "_details")
    if failure == "times":
        details["times"] = np.arange(4) * 0.2
    elif failure == "metric":
        details["scoring"] = "accuracy"
    elif failure == "axes":
        details["score_axes"] = ["fold", "time"]
    elif failure == "folds":
        session.set(name, np.stack([session.get(name)] * 3))
    elif failure == "nan":
        session.get(name).flat[0] = np.nan
    elif failure == "variance":
        for score in params["score_names"]:
            session.set(score, np.full(values.shape[1:], 0.6))
    elif failure == "alias":
        session.set(params["score_names"][1], session.get(name))
    elif failure == "warnings":
        details["warnings"] = ["fit did not converge"]
    else:
        del session.namespace[name + "_details"]
    sentinel = object()
    session.set("decoding_stats", sentinel)
    with pytest.raises(ValueError):
        ops.decoding_group_test(Parameters(**params))
    assert session.get("decoding_stats") is sentinel


def test_no_clusters(study):
    session, params, _ = study
    ops.decoding_group_test(
        Parameters(**{**params, "correction": "cluster", "threshold": 1e10})
    )
    out = session.get("decoding_stats")
    assert not out["clusters"]
    assert out["H0"].size == 0
    assert not out["significant_mask"].any()


@pytest.mark.parametrize("tail", [-1, 1])
def test_cluster_tail_and_figure(study, tail):
    from pathlib import Path

    session, params, _ = study
    result = ops.decoding_group_test(
        Parameters(
            **{
                **params,
                "correction": "cluster",
                "tail": tail,
                "plot": True,
            }
        )
    )
    assert Path(result["figures"][0]).stat().st_size > 1000
    assert session.get("decoding_stats")["p_values"] is None


@pytest.mark.asyncio
async def test_mcp_contract(study):
    session, params, _ = study
    async with Client(server.mcp) as client:
        response = await client.call_tool("mne_decoding_group_test", {"params": params})
        assert not response.is_error
        before = session.get("decoding_stats")
        response = await client.call_tool(
            "mne_decoding_group_test",
            {
                "params": {**params, "independent_subjects": False},
            },
            raise_on_error=False,
        )
        assert response.is_error
        assert session.get("decoding_stats") is before


def test_epochs_to_group_inference(tmp_path, monkeypatch):
    monkeypatch.setenv("MNE_MCP_RESULTS_DIR", str(tmp_path))
    session = get_session()
    session.reset()
    rng = np.random.default_rng(144)
    names = []
    try:
        for i in range(6):
            labels = np.tile([1, 2], 12)
            data = rng.normal(0, 1e-6, (24, 2, 4))
            data[labels == 2, 0] += (0.2 + i * 0.05) * 1e-6
            epochs = mne.EpochsArray(
                data,
                mne.create_info(["Cz", "Pz"], 20, "eeg"),
                events=np.column_stack([np.arange(24) * 10, np.zeros(24, int), labels]),
                event_id={"a": 1, "b": 2},
            )
            session.set("epochs", epochs)
            name = f"decode_p{i}"
            ops.decode_time(cond_a="a", cond_b="b", name=name, cv=3, plot=False)
            names.append(name)
        ops.decoding_group_test(
            Parameters(
                score_names=names,
                subject_ids=[f"p{i}" for i in range(6)],
                independent_subjects=True,
                null_value=0.5,
                n_permutations=64,
                plot=True,
            )
        )
        out = session.get("decoding_stats")
        assert out["statistic"].shape == (4,)
        assert np.all((out["p_values"] >= 0) & (out["p_values"] <= 1))
        assert out["null_samples"] == 32
    finally:
        session.reset()
