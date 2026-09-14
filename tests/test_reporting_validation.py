"""Evidence-bound narratives and preflight rejection without data mutation."""

import mne
import numpy as np
import pytest
from fastmcp import Client

from mne_mcp import operations as ops
from mne_mcp import server
from mne_mcp.kernel import get_session
from mne_mcp.reporting import group_interpretation, render_interpretation


@pytest.fixture
def recording():
    session = get_session()
    session.reset()
    raw = mne.io.RawArray(
        np.random.default_rng(21).normal(0, 1e-6, (2, 2000)),
        mne.create_info(["Cz", "Pz"], 200, "eeg"),
    )
    session.set("raw", raw)
    yield session, raw
    session.reset()


@pytest.mark.parametrize(
    "params",
    [
        {"l_freq": 1, "h_freq": 40, "notch": 100},
        {"l_freq": 1, "h_freq": 40, "notch": -1},
        {"l_freq": float("nan")},
        {"h_freq": float("inf")},
        {"l_freq": True},
        {"h_freq": 0},
        {"l_freq": 40, "h_freq": 10},
    ],
)
def test_filter_preflight_does_not_partially_filter(recording, params):
    _, raw = recording
    original = raw.get_data().copy()
    with pytest.raises(ValueError):
        ops.filter_data("raw", **params)
    np.testing.assert_array_equal(raw.get_data(), original)
    assert raw.info["highpass"] == 0


def test_notch_unsupported_epochs_fails_before_bandpass(recording):
    session, raw = recording
    epochs = mne.make_fixed_length_epochs(raw, duration=1, preload=True)
    session.set("epochs", epochs)
    original = epochs.get_data().copy()
    with pytest.raises(ValueError, match="notch_filter"):
        ops.filter_data("epochs", 1, 40, notch=50)
    np.testing.assert_array_equal(epochs.get_data(), original)


@pytest.mark.parametrize("value", [0, -1, True, float("nan"), float("inf")])
def test_resample_validation(recording, value):
    _, raw = recording
    with pytest.raises(ValueError):
        ops.resample("raw", value)
    assert raw.info["sfreq"] == 200


@pytest.mark.parametrize("window", [(-1, 1), (1, 0), (0, 100), (float("nan"), None)])
def test_crop_validation(recording, window):
    _, raw = recording
    with pytest.raises(ValueError):
        ops.crop("raw", *window)
    assert raw.n_times == 2000


@pytest.mark.parametrize("reference", ["REST", " , "])
def test_reference_preflight(recording, reference):
    _, raw = recording
    original = raw.get_data().copy()
    with pytest.raises(ValueError):
        ops.set_reference("raw", reference)
    np.testing.assert_array_equal(raw.get_data(), original)


def test_valid_filter_matches_mne_and_guidance(recording):
    _, raw = recording
    expected = raw.copy().filter(1, 40).notch_filter(50)
    result = ops.filter_data("raw", 1, 40, notch=50)
    np.testing.assert_allclose(raw.get_data(), expected.get_data())
    assert result["guidance"]["status"] == "processed_not_quality_certified"
    assert "Scientific Checks" in server._format(result)


def _inference_result(cluster=False):
    return dict(
        parameters=dict(
            correction="cluster" if cluster else "max_t",
            alpha=0.05,
            null_value=0.5,
            tail=0,
            n_permutations=1024,
            seed=97,
        ),
        cluster_p_values=np.array([0.02, 0.3]) if cluster else np.array([]),
        p_values=None if cluster else np.array([0.02, 0.3]),
        n_subjects=12,
        scoring="roc_auc",
        family_size=2,
        null_samples=1024,
        warnings=[],
        statistic=np.array([3.0, 1.0]),
        mean_effect=np.array([0.1, 0.03]),
        clusters=[np.array([0]), np.array([1])] if cluster else [],
        times=np.array([0.1, 0.2]),
        score_axes=["time"],
    )


@pytest.mark.parametrize("cluster", [False, True])
def test_report_numbers_and_claim_level(cluster):
    result = _inference_result(cluster)
    report = group_interpretation("stats", result)
    assert report["status"] == "requires_design_review"
    assert "12" in report["methods"][0]
    assert "p=0.02" in report["evidence"][0]
    assert ("1 clusters" if cluster else "1 tested points") in report["draft"]
    assert "Confidence intervals" in report["missing"][0]
    if cluster:
        assert report["cluster_extents"][0]["bounds_seconds"] == {"time": [0.1, 0.1]}
        assert "not to every cell" in report["limitations"][-1]
    assert "Results Draft (Needs Review)" in render_interpretation(report)


def test_report_negative_effect_not_called_above_chance():
    result = _inference_result()
    result["statistic"] *= -1
    result["mean_effect"] *= -1
    report = group_interpretation("stats", result)
    assert "above chance" not in report["draft"]
    assert "against the specified null" in report["interpretation"][0]


def test_report_no_clusters_not_equivalence():
    result = _inference_result(True)
    result["cluster_p_values"] = np.array([])
    result["clusters"] = []
    result["null_samples"] = 0
    report = group_interpretation("stats", result)
    assert "no cluster p values" in report["evidence"][0]
    assert "not evidence of equivalence" in report["interpretation"][0]


@pytest.mark.asyncio
async def test_mcp_decoding_explanation(recording):
    session, _ = recording
    labels = np.tile([1, 2], 12)
    session.set(
        "epochs",
        mne.EpochsArray(
            np.random.default_rng(21).normal(0, 1e-6, (24, 2, 5)),
            mne.create_info(["Cz", "Pz"], 20, "eeg"),
            events=np.column_stack([np.arange(24) * 10, np.zeros(24, int), labels]),
            event_id={"a": 1, "b": 2},
        ),
    )
    async with Client(server.mcp) as client:
        result = await client.call_tool("mne_decode", {"cv": 3, "plot": False})
        assert not result.is_error
        assert "descriptive_only" in result.content[0].text
        assert "Missing Information" in result.content[0].text
        details = session.get("decoding_details")
        assert details["interpretation"]["status"] == "descriptive_only"
        scores = session.get("decoding")
        assert f"{scores.mean():.4g}" in details["interpretation"]["draft"]
