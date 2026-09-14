"""Synthetic numerical parity, leakage checks and MCP decoding contracts."""

from pathlib import Path

import mne
import numpy as np
import pytest
from fastmcp import Client
from mne.decoding import GeneralizingEstimator, SlidingEstimator, cross_val_multiscore
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from mne_mcp import operations as ops
from mne_mcp import server
from mne_mcp.kernel import get_session


@pytest.fixture
def decoding_session(tmp_path, monkeypatch):
    monkeypatch.setenv("MNE_MCP_RESULTS_DIR", str(tmp_path))
    session = get_session()
    session.reset()
    labels = np.tile([3, 7, 9], 12)
    data = np.random.default_rng(32).normal(0, 1e-6, (36, 3, 9))
    data[labels == 7, 0, 4:] += 2e-6
    epochs = mne.EpochsArray(
        data,
        mne.create_info(["Cz", "Pz", "EOG"], 20, ["eeg", "eeg", "eog"]),
        events=np.column_stack([np.arange(36) * 20, np.zeros(36, int), labels]),
        event_id={"a": 3, "b": 7, "other": 9},
        tmin=-0.2,
    )
    session.set("epochs", epochs)
    yield session
    session.reset()


@pytest.mark.parametrize("method", ["sliding", "generalizing"])
@pytest.mark.parametrize(
    "strategy", ["stratified", "stratified_group", "leave_one_group_out"]
)
def test_numerical_parity_replay_and_group_alignment(
    decoding_session, method, strategy
):
    s = decoding_session
    epochs = s.get("epochs")
    original = epochs.get_data().copy()
    groups = (
        np.repeat(["s1", "s2", "s3", "s4"], 9).tolist()
        if strategy != "stratified"
        else None
    )
    result = ops.decode_time(
        cond_a="a",
        cond_b="b",
        cv=3,
        method=method,
        cv_strategy=strategy,
        groups=groups,
        picks=["Cz", "Pz"],
        tmin=-0.1,
        tmax=0.1,
        C=0.3,
        class_weight="balanced",
        max_iter=200,
        plot=False,
    )
    details = s.get("decoding_details")
    rows = np.flatnonzero(epochs.events[:, 2] != 9)
    np.testing.assert_array_equal(details["input_rows"], rows)
    sub = epochs[rows].copy().pick(["Cz", "Pz"]).crop(-0.1, 0.1)
    y = (sub.events[:, 2] == 7).astype(int)
    clf = make_pipeline(
        StandardScaler(),
        LogisticRegression(
            C=0.3,
            class_weight="balanced",
            max_iter=200,
            random_state=97,
        ),
    )
    estimator = SlidingEstimator if method == "sliding" else GeneralizingEstimator
    expected = cross_val_multiscore(
        estimator(clf, scoring="roc_auc", n_jobs=1, verbose="ERROR"),
        sub.get_data(),
        y,
        cv=details["splits"],
        n_jobs=1,
    )
    np.testing.assert_allclose(s.get("decoding_folds"), expected)
    np.testing.assert_allclose(s.get("decoding"), expected.mean(0))
    assert details["positive_class_code"] == 7
    assert details["class_counts"] == [12, 12]
    assert details["n_folds"] == (4 if strategy == "leave_one_group_out" else 3)
    for index, (train, test) in enumerate(details["splits"]):
        assert not np.intersect1d(train, test).size
        assert (
            details["fold_class_counts"][index]["train"]
            == np.bincount(y[train]).tolist()
        )
        if groups is not None:
            selected_groups = np.asarray(groups)[rows]
            np.testing.assert_array_equal(details["groups"], selected_groups)
            assert not np.intersect1d(
                selected_groups[train], selected_groups[test]
            ).size
    replay = {"epochs": epochs}
    exec(result["code"], replay)
    np.testing.assert_allclose(replay["decoding_folds"], expected)
    np.testing.assert_array_equal(epochs.get_data(), original)
    assert epochs.ch_names == ["Cz", "Pz", "EOG"]
    assert result["figures"] == []


def test_generalizing_diagonal_and_plot(decoding_session):
    s = decoding_session
    ops.decode_time(cond_a="a", cond_b="b", cv=3, name="sliding", plot=False)
    result = ops.decode_time(cond_a="a", cond_b="b", cv=3, method="generalizing")
    np.testing.assert_allclose(np.diag(s.get("decoding")), s.get("sliding"))
    assert s.get("decoding").shape == (9, 9)
    assert s.get("decoding_details")["score_axes"] == ["train_time", "test_time"]
    assert len(result["figures"]) == 1
    assert Path(result["figures"][0]).stat().st_size > 1000


@pytest.mark.parametrize(
    "options",
    [
        {"method": "unknown"},
        {"C": 0},
        {"C": float("nan")},
        {"C": True},
        {"max_iter": 0},
        {"max_iter": True},
        {"cv": True},
        {"random_state": -1},
        {"class_weight": "auto"},
        {"tmin": 0.1, "tmax": -0.1},
        {"tmin": -10},
        {"tmax": 10},
        {"tmin": float("inf")},
        {"groups": ["s1"] * 36},
        {"cv_strategy": "stratified_group"},
        {"name": "epochs"},
        {"cond_b": None},
        {"cond_b": "a"},
        {"cv": 13},
        {"cv_strategy": "leave_one_group_out", "groups": ["s1"] * 36},
        {"cv_strategy": "stratified_group", "groups": ["s1", 2] * 18},
        {"cv_strategy": "stratified_group", "groups": ["s1"] * 24},
    ],
)
def test_invalid_calls_preserve_session(decoding_session, options):
    s = decoding_session
    sentinel = object()
    for name in ["decoding", "decoding_folds", "decoding_details"]:
        s.set(name, sentinel)
    original = s.get("epochs")
    with pytest.raises(ValueError):
        ops.decode_time(**{"cond_a": "a", "cond_b": "b", "plot": False, **options})
    for name in ["decoding", "decoding_folds", "decoding_details"]:
        assert s.get(name) is sentinel
    assert s.get("epochs") is original


def test_group_fold_missing_class_rejected(decoding_session):
    with pytest.raises(ValueError, match="both classes"):
        ops.decode_time(
            cond_a="a",
            cond_b="b",
            cv_strategy="leave_one_group_out",
            groups=decoding_session.get("epochs").events[:, 2].tolist(),
            plot=False,
        )


def test_nonfinite_data_rejected(decoding_session):
    decoding_session.get("epochs")._data[0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="non-finite"):
        ops.decode_time(cond_a="a", cond_b="b", plot=False)
    assert not decoding_session.has("decoding")


@pytest.mark.asyncio
async def test_mcp_decoding_contract(decoding_session):
    async with Client(server.mcp) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}
        props = tools["mne_decode"].inputSchema["properties"]
        assert props["method"]["enum"] == ["sliding", "generalizing"]
        result = await client.call_tool(
            "mne_decode",
            {
                "cond_a": "a",
                "cond_b": "b",
                "method": "generalizing",
                "cv": 3,
                "tmin": -0.1,
                "tmax": 0.1,
                "C": 0.5,
                "class_weight": "balanced",
                "plot": False,
            },
        )
        assert not result.is_error
        assert decoding_session.get("decoding").shape == (5, 5)
        previous = decoding_session.get("decoding")
        for invalid in [
            {"C": True},
            {"C": -1},
            {"cv": True},
            {"max_iter": True},
            {"method": "bad"},
        ]:
            result = await client.call_tool(
                "mne_decode",
                {
                    "cond_a": "a",
                    "cond_b": "b",
                    "plot": False,
                    **invalid,
                },
                raise_on_error=False,
            )
            assert result.is_error
            assert decoding_session.get("decoding") is previous
