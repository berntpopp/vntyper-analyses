#!/usr/bin/env python3
"""
07_calculate_metrics.py — Calculate performance metrics for all experiments.

Joins ground truth with parsed VNtyper results and computes:
- Per-sample classification (TP/TN/FP/FN)
- Aggregate sensitivity, specificity, PPV, NPV, F1
- Wilson 95% confidence intervals
- Per-mutation-type breakdown (experiment 2)
- Per-coverage-fraction breakdown (experiment 3)

Usage:
    python scripts/simulation/07_calculate_metrics.py [--test]
"""

import math
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple

from _common import (
    build_common_parser,
    get_experiment_dir,
    get_experiments_to_run,
    get_results_base,
    load_config,
    setup_logging,
)


def classify_sample(row: Dict) -> str:
    """
    Classify a sample as TP, TN, FP, or FN.

    Rules:
    - TP: mutated sample, unflagged frameshift call with non-Negative confidence
    - TN: normal sample, no positive call
    - FP: normal sample, unflagged positive call
    - FN: mutated sample, no call or only flagged calls
    """
    is_mutated = row["condition"] == "mutated"
    has_call = bool(row.get("kestrel_call")) and row.get("confidence", "Negative") != "Negative"
    is_flagged = "False_Positive" in str(row.get("flag", ""))

    # A call only counts as positive if it's unflagged
    called_positive = has_call and not is_flagged

    if is_mutated:
        return "TP" if called_positive else "FN"
    else:
        return "FP" if called_positive else "TN"


def wilson_ci(successes: int, total: int, z: float = 1.96) -> Tuple[float, float]:
    """
    Wilson score confidence interval for a proportion.

    Args:
        successes: Number of successes.
        total: Total trials.
        z: Z-score for confidence level (1.96 = 95%).

    Returns:
        (lower, upper) bounds.
    """
    if total == 0:
        return 0.0, 0.0

    p = successes / total
    denominator = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total) / denominator

    lower = max(0.0, centre - margin)
    upper = min(1.0, centre + margin)
    return lower, upper


def calculate_metrics(classifications: List[str]) -> Dict:
    """Calculate aggregate metrics from a list of classifications."""
    tp = classifications.count("TP")
    tn = classifications.count("TN")
    fp = classifications.count("FP")
    fn = classifications.count("FN")

    n_positive = tp + fn
    n_negative = tn + fp

    sensitivity = tp / n_positive if n_positive > 0 else 0.0
    specificity = tn / n_negative if n_negative > 0 else 0.0
    ppv = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    npv = tn / (tn + fn) if (tn + fn) > 0 else 0.0
    f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) > 0 else 0.0

    sens_ci_low, sens_ci_high = wilson_ci(tp, n_positive)
    spec_ci_low, spec_ci_high = wilson_ci(tn, n_negative)

    return {
        "n_positive": n_positive,
        "n_negative": n_negative,
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "sensitivity": sensitivity,
        "sensitivity_ci_low": sens_ci_low,
        "sensitivity_ci_high": sens_ci_high,
        "specificity": specificity,
        "specificity_ci_low": spec_ci_low,
        "specificity_ci_high": spec_ci_high,
        "ppv": ppv, "npv": npv, "f1_score": f1,
    }


def main():
    parser = build_common_parser("Calculate performance metrics")
    args = parser.parse_args()
    cfg = load_config()

    test_mode = args.test
    results_base = get_results_base(cfg, test_mode)
    experiments = get_experiments_to_run(args)
    exp3_dir_name = cfg["experiment3"]["dir_name"]

    logger = setup_logging("07_metrics")

    for exp_num in experiments:
        exp_dir_name = get_experiment_dir(cfg, exp_num)
        exp_name = cfg[f"experiment{exp_num}"]["name"]

        # Load ground truth and parsed VNtyper results
        gt_file = results_base / exp_dir_name / "ground_truth.csv"
        parsed_file = results_base / exp_dir_name / "vntyper_parsed.csv"

        if not gt_file.exists() or not parsed_file.exists():
            logger.warning(f"Missing data for experiment {exp_num}, skipping")
            continue

        gt = pd.read_csv(gt_file)
        parsed = pd.read_csv(parsed_file)

        # Join on pair_id + condition
        df = pd.merge(
            parsed, gt[["pair_id", "condition", "mutation", "hap1_length", "hap2_length", "total_length", "mutated_allele_length"]],
            on=["pair_id", "condition"], how="left"
        )

        # Classify each sample
        df["classification"] = df.apply(
            lambda r: classify_sample(r.to_dict()), axis=1
        )

        # Save sample-level results
        sample_output = results_base / exp_dir_name / "sample_level_results.csv"
        df.to_csv(sample_output, index=False)
        logger.info(f"Experiment {exp_num}: sample-level -> {sample_output}")

        # Aggregate metrics
        metrics_rows = []

        # Overall
        overall = calculate_metrics(df["classification"].tolist())
        overall["experiment"] = exp_name
        overall["subset"] = "all"
        metrics_rows.append(overall)

        # Per mutation type (experiment 2)
        if exp_num == 2:
            for mut_name, grp in df[df["condition"] == "mutated"].groupby("mutation"):
                # Get corresponding normals (use all normals for specificity)
                normals = df[df["condition"] == "normal"]
                combined = pd.concat([grp, normals])
                m = calculate_metrics(combined["classification"].tolist())
                # Override with mutation-specific counts
                mut_tp = grp[grp["classification"] == "TP"].shape[0]
                mut_fn = grp[grp["classification"] == "FN"].shape[0]
                m["tp"] = mut_tp
                m["fn"] = mut_fn
                m["n_positive"] = mut_tp + mut_fn
                m["sensitivity"] = mut_tp / (mut_tp + mut_fn) if (mut_tp + mut_fn) > 0 else 0.0
                m["sensitivity_ci_low"], m["sensitivity_ci_high"] = wilson_ci(mut_tp, mut_tp + mut_fn)
                m["experiment"] = exp_name
                m["subset"] = mut_name
                metrics_rows.append(m)

        metrics_df = pd.DataFrame(metrics_rows)
        metrics_output = results_base / exp_dir_name / "performance_metrics.csv"
        metrics_df.to_csv(metrics_output, index=False)
        logger.info(f"Experiment {exp_num}: metrics -> {metrics_output}")

        # Print summary
        o = overall
        logger.info(
            f"  Sensitivity: {o['sensitivity']:.1%} "
            f"({o['sensitivity_ci_low']:.1%}-{o['sensitivity_ci_high']:.1%}), "
            f"Specificity: {o['specificity']:.1%} "
            f"({o['specificity_ci_low']:.1%}-{o['specificity_ci_high']:.1%})"
        )

    # Experiment 3: coverage titration metrics
    exp3_parsed = results_base / exp3_dir_name / "vntyper_parsed.csv"
    if exp3_parsed.exists():
        df3 = pd.read_csv(exp3_parsed)

        # Need ground truth from exp 1+2
        gt_frames = []
        for exp_num in [1, 2]:
            gt_file = results_base / get_experiment_dir(cfg, exp_num) / "ground_truth.csv"
            if gt_file.exists():
                gt_frames.append(pd.read_csv(gt_file))
        if gt_frames:
            gt_all = pd.concat(gt_frames, ignore_index=True)
            df3 = pd.merge(
                df3, gt_all[["pair_id", "condition", "mutation", "hap1_length", "hap2_length", "mutated_allele_length"]],
                on=["pair_id", "condition"], how="left"
            )
            df3["classification"] = df3.apply(
                lambda r: classify_sample(r.to_dict()), axis=1
            )

            # Save sample-level
            df3.to_csv(results_base / exp3_dir_name / "sample_level_results.csv", index=False)

            # Metrics per source_experiment x coverage_fraction
            metrics_rows_3 = []
            for (src, frac), grp in df3.groupby(["source_experiment", "coverage_fraction"]):
                m = calculate_metrics(grp["classification"].tolist())
                m["experiment"] = "coverage"
                m["subset"] = f"{src}_ds{int(frac)}"
                metrics_rows_3.append(m)

            # Per mutation type at each fraction
            for (mut, frac), grp in df3[df3["condition"] == "mutated"].groupby(["mutation", "coverage_fraction"]):
                normals_frac = df3[(df3["condition"] == "normal") & (df3["coverage_fraction"] == frac)]
                combined = pd.concat([grp, normals_frac])
                m = calculate_metrics(combined["classification"].tolist())
                mut_tp = grp[grp["classification"] == "TP"].shape[0]
                mut_fn = grp[grp["classification"] == "FN"].shape[0]
                m["tp"] = mut_tp
                m["fn"] = mut_fn
                m["n_positive"] = mut_tp + mut_fn
                m["sensitivity"] = mut_tp / (mut_tp + mut_fn) if (mut_tp + mut_fn) > 0 else 0.0
                m["sensitivity_ci_low"], m["sensitivity_ci_high"] = wilson_ci(mut_tp, mut_tp + mut_fn)
                m["experiment"] = "coverage"
                m["subset"] = f"{mut}_ds{int(frac)}"
                metrics_rows_3.append(m)

            metrics_df_3 = pd.DataFrame(metrics_rows_3)
            metrics_output_3 = results_base / exp3_dir_name / "performance_metrics.csv"
            metrics_df_3.to_csv(metrics_output_3, index=False)
            logger.info(f"Experiment 3: metrics -> {metrics_output_3}")

    logger.info("Metrics calculation complete.")


if __name__ == "__main__":
    main()
