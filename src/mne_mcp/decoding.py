"""Binary sliding/generalizing decoding with explicit, auditable CV splits."""

import warnings

from mne_mcp import figures
from mne_mcp.config import get_results_dir
from mne_mcp.kernel import get_session
from mne_mcp.parameters import DecodingOptions, _session_name


def run_decoding(
    epochs_name: str,
    cond_a: str | None,
    cond_b: str | None,
    scoring: str,
    cv: int,
    name: str,
    *,
    cv_strategy: str,
    groups: list[str] | list[int] | None,
    picks: str | list | None,
    shuffle: bool,
    random_state: int,
    plot: bool,
    method: str = "sliding",
    tmin: float | None = None,
    tmax: float | None = None,
    C: float = 1.0,
    class_weight: str | None = None,
    max_iter: int = 1000,
) -> dict:
    import mne
    import numpy as np
    from mne.decoding import (
        GeneralizingEstimator,
        SlidingEstimator,
        cross_val_multiscore,
    )
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import get_scorer
    from sklearn.model_selection import (
        LeaveOneGroupOut,
        StratifiedGroupKFold,
        StratifiedKFold,
    )
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    options = DecodingOptions(
        method=method,
        tmin=tmin,
        tmax=tmax,
        C=C,
        class_weight=class_weight,
        max_iter=max_iter,
        cv=cv,
        shuffle=shuffle,
        random_state=random_state,
        plot=plot,
    )
    session = get_session()
    epochs = session.get(epochs_name)
    if not isinstance(epochs, mne.BaseEpochs):
        raise ValueError("Decoding requires an Epochs object.")
    _session_name(epochs_name)
    _session_name(name)
    if epochs_name in {name, name + "_folds", name + "_details"}:
        raise ValueError("Output names must not overwrite input epochs.")
    if (cond_a is None) != (cond_b is None) or (
        cond_a is not None and cond_a == cond_b
    ):
        raise ValueError("Provide two distinct conditions, or omit both.")
    if cv_strategy not in {"stratified", "stratified_group", "leave_one_group_out"}:
        raise ValueError("Unknown cv_strategy.")
    get_scorer(scoring)
    if cv_strategy == "stratified" and groups is not None:
        raise ValueError(
            "groups requires grouped CV; labels cannot be silently ignored."
        )
    if cv_strategy != "stratified" and groups is None:
        raise ValueError("Grouped CV requires one group per retained input epoch.")
    if cv_strategy == "leave_one_group_out" and shuffle:
        raise ValueError("shuffle does not apply to leave_one_group_out.")
    rows = np.arange(len(epochs))
    if cond_a is not None:
        a_rows, b_rows = epochs[cond_a].selection, epochs[cond_b].selection
        if np.intersect1d(a_rows, b_rows).size:
            raise ValueError("Conditions overlap; choose disjoint event selections.")
        rows = np.flatnonzero(
            np.isin(epochs.selection, np.concatenate([a_rows, b_rows]))
        )
    sub = (
        epochs[rows].copy().pick(picks if picks is not None else "data", exclude="bads")
    )
    for label, value in (("tmin", tmin), ("tmax", tmax)):
        if value is not None and not epochs.times[0] <= value <= epochs.times[-1]:
            raise ValueError(f"{label} must lie inside the input epoch time range.")
    if tmin is not None or tmax is not None:
        sub.crop(tmin=tmin, tmax=tmax)
    group_values = None
    if groups is not None:
        if len(groups) != len(epochs) or not groups:
            raise ValueError(
                "groups must align with all retained input epochs, before condition selection."
            )
        if not (
            all(type(g) is int for g in groups)
            or all(isinstance(g, str) and g.strip() for g in groups)
        ):
            raise ValueError(
                "groups must be homogeneous integers or nonempty strings, without missing values."
            )
        group_values = np.asarray(groups)[rows]
    X = sub.get_data(copy=False)
    classes, y = np.unique(sub.events[:, 2], return_inverse=True)
    if len(classes) != 2:
        raise ValueError(
            f"Decoding requires exactly 2 classes, got {classes.tolist()}."
        )
    if not np.isfinite(X).all():
        raise ValueError("Decoding data contains non-finite samples.")
    seed = random_state if shuffle else None
    if cv_strategy == "stratified":
        if np.bincount(y).min() < cv:
            raise ValueError("Each class needs at least cv trials.")
        splitter = StratifiedKFold(cv, shuffle=shuffle, random_state=seed)
    elif cv_strategy == "stratified_group":
        if len(np.unique(group_values)) < cv:
            raise ValueError("Grouped CV needs at least cv distinct groups.")
        splitter = StratifiedGroupKFold(cv, shuffle=shuffle, random_state=seed)
    else:
        if len(np.unique(group_values)) < 2:
            raise ValueError("Leave-one-group-out needs at least two groups.")
        splitter = LeaveOneGroupOut()
    splits = list(splitter.split(X, y, group_values))
    for train, test in splits:
        if len(np.unique(y[train])) != 2 or len(np.unique(y[test])) != 2:
            raise ValueError(
                "Every train/test fold must contain both classes. Change grouping or reduce folds."
            )
        if (
            group_values is not None
            and np.intersect1d(group_values[train], group_values[test]).size
        ):
            raise ValueError("A group overlaps train and test; refusing leaked CV.")
    classifier_options = dict(
        C=options.C,
        class_weight=class_weight,
        max_iter=max_iter,
        random_state=random_state,
    )
    clf = make_pipeline(StandardScaler(), LogisticRegression(**classifier_options))
    estimator_class = SlidingEstimator if method == "sliding" else GeneralizingEstimator
    estimator = estimator_class(clf, scoring=scoring, n_jobs=1, verbose="ERROR")
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        fold_scores = cross_val_multiscore(estimator, X, y, cv=splits, n_jobs=1)
    if not np.isfinite(fold_scores).all():
        raise ValueError(
            "Non-finite CV scores; inspect the metric, class counts and fit warnings."
        )
    scores = fold_scores.mean(axis=0)
    reference = 0.5 if scoring in {"roc_auc", "balanced_accuracy"} else None
    details = {
        "method": method,
        "classifier": classifier_options,
        "options": options.model_dump(),
        "score_axes": ["time"] if method == "sliding" else ["train_time", "test_time"],
        "cv_strategy": cv_strategy,
        "scoring": scoring,
        "n_folds": len(splits),
        "class_codes": classes.tolist(),
        "class_counts": np.bincount(y).tolist(),
        "positive_class_code": int(classes[1]),
        "times": sub.times.copy(),
        "channels": sub.ch_names,
        "input_rows": rows,
        "groups": group_values,
        "splits": splits,
        "reference_level": reference,
        "fold_class_counts": [
            {
                "train": np.bincount(y[train], minlength=2).tolist(),
                "test": np.bincount(y[test], minlength=2).tolist(),
            }
            for train, test in splits
        ],
        "reference_kind": (
            "theoretical, not a significance threshold"
            if reference is not None
            else None
        ),
        "warnings": list(dict.fromkeys(str(w.message) for w in captured)),
    }
    from mne_mcp.reporting import decoding_interpretation

    details["interpretation"] = decoding_interpretation(name, scores, details)
    figs = []
    if plot:
        import matplotlib.pyplot as plt

        before = figures.open_figure_numbers()
        fig, ax = plt.subplots()
        if method == "sliding":
            ax.plot(sub.times, scores, lw=2, label="mean CV score")
            if reference is not None:
                ax.axhline(
                    reference,
                    color="k",
                    linestyle="--",
                    label="theoretical reference (not significance)",
                )
            ax.set(xlabel="Time (s)", ylabel=scoring)
            ax.legend()
        else:
            image = ax.pcolormesh(
                sub.times, sub.times, scores, shading="nearest", cmap="viridis"
            )
            fig.colorbar(image, ax=ax, label=scoring)
            ax.set(xlabel="Test time (s)", ylabel="Train time (s)")
        ax.set_title(f"Decoding {classes.tolist()} ({cv_strategy}, {method})")
        fig.tight_layout()
        figs = figures.capture_new_figures(before, get_results_dir(), prefix="decode")
    session.set(name, scores)
    session.set(name + "_folds", fold_scores)
    session.set(name + "_details", details)
    peak = np.unravel_index(np.argmax(scores), scores.shape)
    peak_time = (
        f"{sub.times[peak[0]]:.3f}s"
        if method == "sliding"
        else f"train={sub.times[peak[0]]:.3f}s, test={sub.times[peak[1]]:.3f}s"
    )
    md = (
        f"Decoding ({method}, {scoring}, {cv_strategy}) on `{epochs_name}`: mean={scores.mean():.3f}, "
        f"peak={scores[peak]:.3f} at {peak_time}; {len(y)} trials, {len(splits)} folds. "
        f"Score shape={scores.shape}, axes={details['score_axes']}. "
        f"Class codes={classes.tolist()}, counts={np.bincount(y).tolist()}, positive code={classes[1]}. "
        f"Mean scores: `{name}`; per-fold scores: `{name}_folds`; split diagnostics: `{name}_details`. "
        "CV folds are not independent subjects; curves and reference lines are not significance tests."
    )
    if details["warnings"]:
        md += "\nWarnings:\n" + "\n".join(details["warnings"][:5])
    crop_code = ""
    if tmin is not None or tmax is not None:
        crop_code = f"sub.crop(tmin={tmin!r}, tmax={tmax!r})\n"
    code = (
        "import numpy as np\n"
        f"from mne.decoding import {estimator_class.__name__}, cross_val_multiscore\n"
        "from sklearn.pipeline import make_pipeline\n"
        "from sklearn.preprocessing import StandardScaler\n"
        "from sklearn.linear_model import LogisticRegression\n"
        f"sub = {epochs_name}[{rows.tolist()!r}].copy().pick({sub.ch_names!r}, exclude=[])\n"
        f"{crop_code}"
        "classes, y = np.unique(sub.events[:, 2], return_inverse=True)\n"
        f"splits = {[(a.tolist(), b.tolist()) for a, b in splits]!r}\n"
        f"clf = make_pipeline(StandardScaler(), LogisticRegression(**{classifier_options!r}))\n"
        f"sl = {estimator_class.__name__}(clf, scoring={scoring!r}, n_jobs=1)\n"
        f"{name}_folds = cross_val_multiscore(sl, sub.get_data(), y, cv=splits, n_jobs=1)\n"
        f"{name} = {name}_folds.mean(0)"
    )
    return {
        "markdown": md,
        "figures": figs,
        "code": code,
        "interpretation": details["interpretation"],
    }
