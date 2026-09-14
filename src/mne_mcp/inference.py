"""Group-level decoding inference using MNE sign-flip tests."""

import warnings

from mne_mcp import figures
from mne_mcp.config import get_results_dir
from mne_mcp.kernel import get_session
from mne_mcp.parameters import DecodingGroupTestParameters


def decoding_group_test(params: DecodingGroupTestParameters) -> dict:
    import mne
    import numpy as np

    params = DecodingGroupTestParameters.model_validate(params.model_dump())
    session = get_session()
    scores, metadata = [], []
    for name in params.score_names:
        value = session.get(name)
        if not session.has(name + "_details"):
            raise ValueError(
                f"{name} has no decoding diagnostics; pass mne_decode mean scores, never CV folds."
            )
        details = session.get(name + "_details")
        if not isinstance(details, dict):
            raise ValueError(f"{name}_details must contain decoding diagnostics.")
        method = details.get("method")
        axes = ["time"] if method == "sliding" else ["train_time", "test_time"]
        if (
            method not in {"sliding", "generalizing"}
            or details.get("score_axes") != axes
        ):
            raise ValueError("Unsupported decoding method or score axes.")
        if details.get("scoring") not in {"roc_auc", "balanced_accuracy"}:
            raise ValueError(
                "Group test supports roc_auc or balanced_accuracy only; raw accuracy has no universal chance reference."
            )
        if not isinstance(value, np.ndarray) or value.dtype.kind not in "fiu":
            raise ValueError("Mean scores must be real numerical arrays.")
        times = np.asarray(details.get("times"), dtype=float)
        if (
            times.ndim != 1
            or not times.size
            or not np.isfinite(times).all()
            or np.any(np.diff(times) <= 0)
        ):
            raise ValueError("Decoding times must be finite and strictly increasing.")
        if value.shape != (times.size,) * len(axes):
            raise ValueError(
                "Score shape does not match time axes; do not pass CV folds as subjects."
            )
        if not np.isfinite(value).all() or np.any((value < 0) | (value > 1)):
            raise ValueError("Scores must be finite and between zero and one.")
        if details.get("warnings"):
            raise ValueError(f"{name} has fit warnings. Resolve them before inference.")
        if metadata:
            first = metadata[0]
            for key in (
                "method",
                "scoring",
                "score_axes",
                "class_codes",
                "positive_class_code",
                "classifier",
            ):
                if details.get(key) != first.get(key):
                    raise ValueError(f"Decoding {key} must match across subjects.")
            if not np.array_equal(times, np.asarray(first["times"])):
                raise ValueError(
                    "Time grids must match exactly across subjects; align them before decoding."
                )
        scores.append(value)
        metadata.append(details)
    if len({id(value) for value in scores}) != len(scores):
        raise ValueError("Aliased score arrays are not independent subjects.")
    X = np.stack(scores).astype(float) - params.null_value
    flat = X.reshape(len(scores), -1)
    if np.any(np.var(flat, axis=0, ddof=1) <= np.finfo(float).eps ** 2):
        raise ValueError(
            "Zero between-subject variance at a tested point; t statistics are undefined. Inspect scores before testing."
        )
    shape = X.shape[1:]
    common = dict(
        n_permutations=params.n_permutations,
        tail=params.tail,
        seed=params.seed,
        n_jobs=1,
    )
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        if params.correction == "max_t":
            statistic, p_values, h0 = mne.stats.permutation_t_test(flat, **common)
            statistic, p_values = statistic.reshape(shape), p_values.reshape(shape)
            clusters, cluster_p = [], np.array([])
            significant = p_values <= params.alpha
        else:
            # Explicit lattice: both train and test time for generalization, not a flattened chain.
            adjacency = mne.stats.combine_adjacency(*shape)
            statistic, clusters, cluster_p, h0 = (
                mne.stats.permutation_cluster_1samp_test(
                    flat,
                    adjacency=adjacency,
                    threshold=params.threshold,
                    out_type="indices",
                    **common,
                )
            )
            statistic = statistic.reshape(shape)
            clusters = [np.asarray(cluster[0], dtype=int) for cluster in clusters]
            significant = np.zeros(flat.shape[1], dtype=bool)
            for indices, p_value in zip(clusters, cluster_p):
                if p_value <= params.alpha:
                    significant[indices] = True
            significant = significant.reshape(shape)
            p_values = (
                None  # Cluster p values must not masquerade as pointwise p values.
            )
    if not np.isfinite(statistic).all() or not np.isfinite(h0).all():
        raise ValueError(
            "Non-finite permutation statistics; inspect between-subject variance."
        )
    notes = list(dict.fromkeys(str(w.message) for w in captured))
    if len(h0) and 1 / len(h0) > params.alpha:
        notes.append(
            "Permutation resolution is coarser than alpha; more permutations cannot overcome a small exact sign-flip space."
        )
    notes.append(
        "Requires independent subjects and symmetry of subject effects about the null. Subject IDs are a design declaration, not proof of independence."
    )
    notes.append(
        "A group mean test against a reference is not single-subject label permutation or population-prevalence inference."
    )
    output = {
        "statistic": statistic,
        "p_values": p_values,
        "clusters": clusters,
        "cluster_p_values": cluster_p,
        "significant_mask": significant,
        "H0": h0,
        "mean_effect": X.mean(axis=0),
        "times": np.asarray(metadata[0]["times"]).copy(),
        "score_axes": metadata[0]["score_axes"],
        "scoring": metadata[0]["scoring"],
        "n_subjects": len(scores),
        "family_size": int(flat.shape[1]),
        "null_samples": len(h0),
        "parameters": params.model_dump(),
        "warnings": notes,
        "inference_level": (
            "pointwise FWER" if params.correction == "max_t" else "cluster-level FWER"
        ),
    }
    figs = []
    if params.plot:
        import matplotlib.pyplot as plt

        before = figures.open_figure_numbers()
        fig, ax = plt.subplots()
        times = output["times"]
        if len(shape) == 1:
            ax.plot(times, output["mean_effect"], label="mean score - reference")
            ax.axhline(0, color="black", linestyle="--")
            ax.scatter(
                times[significant],
                output["mean_effect"][significant],
                color="red",
                label="corrected mask",
            )
            ax.set(xlabel="Time (s)", ylabel="Score difference")
            ax.legend()
        else:
            limit = max(
                float(np.max(np.abs(output["mean_effect"]))), np.finfo(float).eps
            )
            mesh = ax.pcolormesh(
                times,
                times,
                output["mean_effect"],
                shading="nearest",
                cmap="RdBu_r",
                vmin=-limit,
                vmax=limit,
            )
            fig.colorbar(mesh, ax=ax, label="Mean score - reference")
            train, test = np.nonzero(significant)
            ax.scatter(times[test], times[train], s=8, color="black")
            ax.set(xlabel="Test time (s)", ylabel="Train time (s)")
        title = output["inference_level"]
        if params.correction == "cluster":
            title += "\nCluster masks do not localize effects"
        ax.set_title(title)
        fig.tight_layout()
        figs = figures.capture_new_figures(
            before, get_results_dir(), prefix="decoding_stats"
        )
    stack_code = ", ".join(params.score_names)
    code = (
        "import numpy as np\nimport mne\n"
        f"X = np.stack([{stack_code}]).astype(float) - {params.null_value!r}\n"
        "shape = X.shape[1:]\nflat = X.reshape(len(X), -1)\n"
    )
    if params.correction == "max_t":
        code += (
            f"T, p, H0 = mne.stats.permutation_t_test(flat, **{common!r})\n"
            f"{params.name} = dict(statistic=T.reshape(shape), p_values=p.reshape(shape), H0=H0)\n"
        )
    else:
        code += (
            "adjacency = mne.stats.combine_adjacency(*shape)\n"
            f"T, clusters, p, H0 = mne.stats.permutation_cluster_1samp_test(flat, adjacency=adjacency, threshold={params.threshold!r}, out_type='indices', **{common!r})\n"
            f"{params.name} = dict(statistic=T.reshape(shape), clusters=[c[0] for c in clusters], cluster_p_values=p, H0=H0)\n"
        )
    from mne_mcp.reporting import group_interpretation

    output["interpretation"] = group_interpretation(params.name, output)
    session.set(params.name, output)
    summary = (
        f"{output['inference_level']}: {len(scores)} subjects, {flat.shape[1]} tested points; "
        f"requested permutations={params.n_permutations}, actual null samples={len(h0)}. "
        f"Results: `{params.name}`. "
    )
    if params.correction == "cluster":
        summary += f"{int(np.sum(cluster_p <= params.alpha))} significant clusters. Cluster extent is not pointwise significance or precise onset. "
    else:
        summary += f"{int(significant.sum())} corrected significant points. "
    summary += "\n" + "\n".join(notes)
    return {
        "markdown": summary,
        "figures": figs,
        "code": code,
        "interpretation": output["interpretation"],
    }
