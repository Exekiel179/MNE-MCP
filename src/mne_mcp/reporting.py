"""Evidence-bound result narratives; no inferred biology or invented statistics."""


def render_interpretation(report: dict) -> str:
    sections = [
        ("Evidence", "evidence"),
        ("Methods", "methods"),
        ("Interpretation", "interpretation"),
        ("Limitations", "limitations"),
        ("Missing Information", "missing"),
        ("Results Draft (Needs Review)", "draft"),
    ]
    parts = [f"Reporting status: `{report['status']}`"]
    for title, key in sections:
        value = report.get(key)
        if value:
            text = (
                "\n".join(f"- {item}" for item in value)
                if isinstance(value, list)
                else value
            )
            parts.append(f"### {title}\n\n{text}")
    return "\n\n".join(parts)


def decoding_interpretation(name, scores, details) -> dict:
    import numpy as np

    peak = np.unravel_index(np.argmax(scores), scores.shape)
    coordinates = ", ".join(
        f"{axis}={details['times'][index]:.4g} s"
        for axis, index in zip(details["score_axes"], peak)
    )
    evidence = (
        f"Mean cross-validation {details['scoring']} across the supplied grid was {scores.mean():.4g}; "
        f"the descriptive maximum was {scores[peak]:.4g} ({coordinates})."
    )
    return {
        "status": "descriptive_only",
        "evidence": [
            evidence,
            f"Source: `{name}`, `{name}_folds`, `{name}_details`; no significance test was run by mne_decode.",
        ],
        "methods": [
            f"{details['method']} decoding; {details['n_folds']} {details['cv_strategy']} folds; "
            f"class counts={details['class_counts']}; positive event code={details['positive_class_code']}.",
            "Scaling and logistic regression were fit within training folds.",
        ],
        "interpretation": [
            "Scores describe predictive discrimination under the specified cross-validation design, not a neural mechanism."
        ],
        "limitations": [
            "The maximum is selected across the tested grid; it is not a corrected inference or precise onset estimate.",
            "Folds are not independent subjects; a theoretical reference line is not a significance threshold.",
        ]
        + details["warnings"],
        "missing": [
            "Study question, participant independence, condition semantics and preprocessing quality require review.",
            "Corrected statistical inference and confidence intervals were not computed in this decoding call.",
        ],
        "draft": evidence
        + " These descriptive scores alone do not establish above-chance statistical significance.",
    }


def group_interpretation(name: str, result: dict) -> dict:
    import numpy as np

    params = result["parameters"]
    cluster_test = params["correction"] == "cluster"
    p = result["cluster_p_values"] if cluster_test else result["p_values"]
    significant = p <= params["alpha"]
    n_significant = int(np.sum(significant))
    unit = "clusters" if cluster_test else "tested points"
    p_summary = (
        f"Minimum corrected p={float(np.min(p)):.6g}."
        if p.size
        else "No clusters crossed the forming threshold; no cluster p values were computed."
    )
    methods = (
        f"Across {result['n_subjects']} independently declared subjects, {result['scoring']} "
        f"was tested against {params['null_value']:g} using {params['correction']} sign-flip inference "
        f"(tail={params['tail']}, alpha={params['alpha']:g}, family={result['family_size']} points; "
        f"requested permutations={params['n_permutations']}, actual null samples={result['null_samples']}, seed={params['seed']})."
    )
    if cluster_test:
        threshold = params.get("threshold")
        methods += (
            " Cluster-forming threshold="
            + (
                "MNE's default p=0.05 t threshold"
                if threshold is None
                else f"t={threshold:g}"
            )
            + "."
        )
    finding = (
        f"{n_significant} {unit} met the family-wise corrected threshold. {p_summary}"
    )
    if n_significant:
        interpretation = "The test provides evidence against the specified null within the tested family, conditional on the design assumptions."
    else:
        interpretation = "The test did not detect a corrected effect; this is not evidence of equivalence or absence of an effect."
    report = {
        "status": "requires_design_review",
        "evidence": [
            finding,
            f"Mean score-reference differences range from {float(np.min(result['mean_effect'])):.6g} to {float(np.max(result['mean_effect'])):.6g} across the full grid (descriptive range, not a confidence interval).",
            f"Source: `{name}` fields statistic, p_values/cluster_p_values, mean_effect, H0 and parameters.",
        ],
        "methods": [methods],
        "interpretation": [interpretation],
        "limitations": list(result["warnings"]),
        "missing": [
            "Confidence intervals and standardized effect sizes were not computed; mean_effect contains unstandardized score differences.",
            "Condition meaning, preprocessing provenance, preregistration and any other tested contrasts must be reviewed before a scientific conclusion.",
            "Software citations and mechanistic literature must be verified separately; this draft is not publication-ready.",
        ],
        "draft": methods + " " + finding,
        "cluster_extents": [],
    }
    if cluster_test:
        report["limitations"].append(
            "Cluster p values apply to clusters, not to every cell or to precise onset/offset. Extents below are bounding ranges, not filled rectangular effects."
        )
        for index in np.flatnonzero(significant):
            coordinates = np.unravel_index(
                result["clusters"][index], result["statistic"].shape
            )
            extent = {
                "cluster": int(index),
                "p_corrected": float(p[index]),
                "size": len(result["clusters"][index]),
                "bounds_seconds": {
                    axis: [
                        float(result["times"][idx.min()]),
                        float(result["times"][idx.max()]),
                    ]
                    for axis, idx in zip(result["score_axes"], coordinates)
                },
            }
            report["cluster_extents"].append(extent)
        for extent in report["cluster_extents"][:10]:
            report["evidence"].append(
                f"Cluster {extent['cluster']}: p={extent['p_corrected']:.6g}, {extent['size']} cells; bounding ranges (s)={extent['bounds_seconds']}."
            )
        if len(report["cluster_extents"]) > 10:
            report["evidence"].append(
                "Only the first 10 significant clusters are displayed; interpretation.cluster_extents stores all extents."
            )
    return report
