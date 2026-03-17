#!/usr/bin/env python3
"""
08_generate_summary.py — Generate manuscript-ready outputs.

Produces:
1. YAML fragment for manuscript variables
2. Summary CSV tables
3. Supplementary figures (PNG + SVG)

Usage:
    python scripts/simulation/08_generate_summary.py [--test]
"""

import pandas as pd
import yaml
from pathlib import Path

from _common import (
    build_common_parser,
    get_experiment_dir,
    get_results_base,
    load_config,
    setup_logging,
)


def generate_yaml_fragment(results_base: Path, cfg: dict) -> dict:
    """Build the YAML variables structure from metrics CSVs."""
    fragment = {"results": {}}

    # Experiment 1: dupC
    exp1_metrics = results_base / cfg["experiment1"]["dir_name"] / "performance_metrics.csv"
    if exp1_metrics.exists():
        df = pd.read_csv(exp1_metrics)
        overall = df[df["subset"] == "all"].iloc[0]
        fragment["results"]["simulation_dupC"] = {
            "n_pairs": cfg["experiment1"]["n_pairs"],
            **{k: _yaml_val(overall[k]) for k in [
                "tp", "tn", "fp", "fn",
                "sensitivity", "sensitivity_ci_low", "sensitivity_ci_high",
                "specificity", "specificity_ci_low", "specificity_ci_high",
                "ppv", "npv", "f1_score",
            ]},
        }

    # Experiment 2: atypical
    exp2_metrics = results_base / cfg["experiment2"]["dir_name"] / "performance_metrics.csv"
    if exp2_metrics.exists():
        df = pd.read_csv(exp2_metrics)
        overall = df[df["subset"] == "all"].iloc[0]
        per_mut = {}
        for _, row in df[df["subset"] != "all"].iterrows():
            per_mut[row["subset"]] = {
                "n": int(row["n_positive"]),
                "tp": int(row["tp"]), "fn": int(row["fn"]),
                "sensitivity": round(row["sensitivity"], 4),
                "sensitivity_ci_low": round(row["sensitivity_ci_low"], 4),
                "sensitivity_ci_high": round(row["sensitivity_ci_high"], 4),
            }
        fragment["results"]["simulation_atypical"] = {
            "n_pairs": cfg["experiment2"]["n_pairs"],
            **{k: _yaml_val(overall[k]) for k in [
                "tp", "tn", "fp", "fn",
                "sensitivity", "sensitivity_ci_low", "sensitivity_ci_high",
                "specificity", "specificity_ci_low", "specificity_ci_high",
                "ppv", "npv", "f1_score",
            ]},
            "per_mutation": per_mut,
        }

    # Experiment 3: coverage
    exp3_metrics = results_base / cfg["experiment3"]["dir_name"] / "performance_metrics.csv"
    if exp3_metrics.exists():
        df = pd.read_csv(exp3_metrics)
        cov_data = {"fractions": [100, 50, 25, 12.5, 6.25]}

        for src in ["dupC", "atypical"]:
            src_data = {}
            for _, row in df[df["subset"].str.startswith(f"{src}_ds")].iterrows():
                label = row["subset"].replace(f"{src}_", "")
                src_data[label] = {
                    "sensitivity": round(row["sensitivity"], 4),
                    "specificity": round(row["specificity"], 4),
                }
            cov_data[src] = src_data

        fragment["results"]["simulation_coverage"] = cov_data

    return fragment


def _yaml_val(v):
    """Convert numpy/pandas types to Python native for YAML serialization."""
    if pd.isna(v):
        return None
    if isinstance(v, (int, float)):
        return round(float(v), 4) if isinstance(v, float) else int(v)
    try:
        return round(float(v), 4)
    except (ValueError, TypeError):
        return v


def generate_tables(results_base: Path, cfg: dict, logger):
    """Generate summary CSV tables."""
    tables_dir = results_base / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    # Table: Exp 1 performance
    exp1_metrics = results_base / cfg["experiment1"]["dir_name"] / "performance_metrics.csv"
    if exp1_metrics.exists():
        df = pd.read_csv(exp1_metrics)
        df[df["subset"] == "all"].to_csv(tables_dir / "table_exp1_performance.csv", index=False)
        logger.info("  table_exp1_performance.csv")

    # Table: Exp 2 performance + per-mutation
    exp2_metrics = results_base / cfg["experiment2"]["dir_name"] / "performance_metrics.csv"
    if exp2_metrics.exists():
        df = pd.read_csv(exp2_metrics)
        df[df["subset"] == "all"].to_csv(tables_dir / "table_exp2_performance.csv", index=False)
        df[df["subset"] != "all"].to_csv(tables_dir / "table_exp2_per_mutation.csv", index=False)
        logger.info("  table_exp2_performance.csv, table_exp2_per_mutation.csv")

    # Table: Exp 3 coverage curve + per-mutation coverage
    exp3_metrics = results_base / cfg["experiment3"]["dir_name"] / "performance_metrics.csv"
    if exp3_metrics.exists():
        df = pd.read_csv(exp3_metrics)
        # Coverage curve: rows like dupC_ds50, atypical_ds25
        cov_rows = df[df["subset"].str.match(r"^(dupC|atypical)_ds\d+$")]
        cov_rows.to_csv(tables_dir / "table_exp3_coverage_curve.csv", index=False)
        # Per-mutation coverage: rows like insG_ds50
        mut_cov_rows = df[~df["subset"].str.match(r"^(dupC|atypical)_ds\d+$")]
        if len(mut_cov_rows) > 0:
            mut_cov_rows.to_csv(tables_dir / "table_exp3_per_mutation_coverage.csv", index=False)
        logger.info("  table_exp3_coverage_curve.csv")

    # Table: False negatives and false positives
    fn_frames = []
    fp_frames = []
    for exp_num in [1, 2]:
        exp_dir_name = get_experiment_dir(cfg, exp_num)
        sl_file = results_base / exp_dir_name / "sample_level_results.csv"
        if sl_file.exists():
            df = pd.read_csv(sl_file)
            fn_df = df[df["classification"] == "FN"]
            if len(fn_df) > 0:
                fn_frames.append(fn_df)
            fp_df = df[df["classification"] == "FP"]
            if len(fp_df) > 0:
                fp_frames.append(fp_df)

    if fn_frames:
        fn_all = pd.concat(fn_frames, ignore_index=True)
        fn_all.to_csv(tables_dir / "table_false_negatives.csv", index=False)
        logger.info(f"  table_false_negatives.csv ({len(fn_all)} FNs)")

    if fp_frames:
        fp_all = pd.concat(fp_frames, ignore_index=True)
        fp_all.to_csv(tables_dir / "table_false_positives.csv", index=False)
        logger.info(f"  table_false_positives.csv ({len(fp_all)} FPs)")

    # Combined overview table
    all_metrics = []
    for exp_num in [1, 2]:
        exp_dir_name = get_experiment_dir(cfg, exp_num)
        mf = results_base / exp_dir_name / "performance_metrics.csv"
        if mf.exists():
            all_metrics.append(pd.read_csv(mf))
    exp3_mf = results_base / cfg["experiment3"]["dir_name"] / "performance_metrics.csv"
    if exp3_mf.exists():
        all_metrics.append(pd.read_csv(exp3_mf))
    if all_metrics:
        combined = pd.concat(all_metrics, ignore_index=True)
        combined.to_csv(tables_dir / "table_combined_overview.csv", index=False)
        logger.info("  table_combined_overview.csv")


def generate_figures(results_base: Path, cfg: dict, logger):
    """Generate supplementary figures."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    figures_dir = results_base / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Figure 1: Coverage-sensitivity curve (includes 100% baseline from exp1/exp2)
    exp1_metrics = results_base / cfg["experiment1"]["dir_name"] / "performance_metrics.csv"
    exp2_metrics_path = results_base / cfg["experiment2"]["dir_name"] / "performance_metrics.csv"
    exp3_metrics = results_base / cfg["experiment3"]["dir_name"] / "performance_metrics.csv"
    if exp3_metrics.exists():
        df = pd.read_csv(exp3_metrics)
        cov_df = df[df["subset"].str.match(r"^(dupC|atypical)_ds\d+$")].copy()

        # Add 100% baseline from exp1 (dupC) and exp2 (atypical)
        baseline_rows = []
        if exp1_metrics.exists():
            df1 = pd.read_csv(exp1_metrics)
            row100 = df1[df1["subset"] == "all"].iloc[0].to_dict()
            row100["subset"] = "dupC_ds100"
            baseline_rows.append(row100)
        if exp2_metrics_path.exists():
            df2_m = pd.read_csv(exp2_metrics_path)
            row100 = df2_m[df2_m["subset"] == "all"].iloc[0].to_dict()
            row100["subset"] = "atypical_ds100"
            baseline_rows.append(row100)
        if baseline_rows:
            cov_df = pd.concat([cov_df, pd.DataFrame(baseline_rows)], ignore_index=True)

        if len(cov_df) > 0:
            cov_df["source"] = cov_df["subset"].str.extract(r"^(\w+)_ds")[0]
            cov_df["fraction"] = cov_df["subset"].str.extract(r"_ds(\d+)$")[0].astype(int)

            fig, ax = plt.subplots(figsize=(8, 5))
            for src, grp in cov_df.groupby("source"):
                grp = grp.sort_values("fraction", ascending=False)
                ax.plot(grp["fraction"], grp["sensitivity"], "o-", label=src, linewidth=2)
                ax.fill_between(
                    grp["fraction"],
                    grp["sensitivity_ci_low"],
                    grp["sensitivity_ci_high"],
                    alpha=0.2,
                )
            # Mark the 100% baseline with a vertical dashed line
            ax.axvline(x=100, color="grey", linestyle="--", alpha=0.5, linewidth=1)
            ax.text(99, 0.03, "full\ncoverage", ha="right", va="bottom",
                    fontsize=8, color="grey", style="italic")
            ax.set_xlabel("Coverage fraction (%)")
            ax.set_ylabel("Sensitivity")
            ax.set_title("VNtyper 2 Sensitivity vs Coverage Depth")
            ax.legend()
            ax.set_ylim(0, 1.05)
            ax.invert_xaxis()
            plt.tight_layout()
            for ext in ["png", "svg"]:
                fig.savefig(figures_dir / f"fig_coverage_sensitivity_curve.{ext}", dpi=300)
            plt.close(fig)
            logger.info("  fig_coverage_sensitivity_curve")

    # Figure 2: Per-mutation sensitivity bar chart (includes dupC from exp1)
    exp1_metrics = results_base / cfg["experiment1"]["dir_name"] / "performance_metrics.csv"
    exp2_metrics = results_base / cfg["experiment2"]["dir_name"] / "performance_metrics.csv"
    if exp2_metrics.exists():
        df2 = pd.read_csv(exp2_metrics)
        per_mut = df2[df2["subset"] != "all"].copy()

        # Add dupC from experiment 1 as first entry
        if exp1_metrics.exists():
            df1 = pd.read_csv(exp1_metrics)
            dupc_row = df1[df1["subset"] == "all"].copy()
            dupc_row["subset"] = "dupC"
            per_mut = pd.concat([dupc_row, per_mut], ignore_index=True)

        if len(per_mut) > 0:
            # Sort: dupC first, then descending sensitivity
            per_mut["_is_dupc"] = per_mut["subset"] == "dupC"
            per_mut = per_mut.sort_values(
                ["_is_dupc", "sensitivity"], ascending=[False, False]
            ).drop(columns=["_is_dupc"])

            fig, ax = plt.subplots(figsize=(10, 5))
            colors = ["#d62728" if m == "dupC" else "steelblue"
                      for m in per_mut["subset"]]
            ax.bar(per_mut["subset"], per_mut["sensitivity"], color=colors)
            ax.errorbar(
                per_mut["subset"], per_mut["sensitivity"],
                yerr=[
                    per_mut["sensitivity"] - per_mut["sensitivity_ci_low"],
                    per_mut["sensitivity_ci_high"] - per_mut["sensitivity"],
                ],
                fmt="none", color="black", capsize=3,
            )
            ax.set_ylabel("Sensitivity")
            ax.set_title("VNtyper 2 Sensitivity by Mutation Type (Full Coverage)")
            ax.set_ylim(0, 1.05)
            # Add legend for dupC highlight
            from matplotlib.patches import Patch
            ax.legend(handles=[
                Patch(color="#d62728", label="dupC (canonical)"),
                Patch(color="steelblue", label="Atypical frameshifts"),
            ])
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            for ext in ["png", "svg"]:
                fig.savefig(figures_dir / f"fig_per_mutation_sensitivity.{ext}", dpi=300)
            plt.close(fig)
            logger.info("  fig_per_mutation_sensitivity")

    # Figure 3: Per-mutation x coverage heatmap (includes dupC + 100% baseline)
    if exp3_metrics.exists():
        df = pd.read_csv(exp3_metrics)
        # Include dupC aggregate rows AND individual atypical mutation rows
        # Exclude only the "atypical_ds*" aggregate rows and "all"
        mut_cov = df[~df["subset"].str.match(r"^(atypical_ds|all)")].copy()

        # Add 100% baseline from exp1 (dupC) and exp2 per-mutation
        baseline_rows = []
        if exp1_metrics.exists():
            df1 = pd.read_csv(exp1_metrics)
            row100 = df1[df1["subset"] == "all"].iloc[0].to_dict()
            row100["subset"] = "dupC_ds100"
            baseline_rows.append(row100)
        if exp2_metrics_path.exists():
            df2_m = pd.read_csv(exp2_metrics_path)
            for _, r in df2_m[df2_m["subset"] != "all"].iterrows():
                row100 = r.to_dict()
                row100["subset"] = f"{r['subset']}_ds100"
                baseline_rows.append(row100)
        if baseline_rows:
            mut_cov = pd.concat([mut_cov, pd.DataFrame(baseline_rows)], ignore_index=True)

        if len(mut_cov) > 0:
            mut_cov["mutation"] = mut_cov["subset"].str.extract(r"^(.+?)_ds")[0]
            mut_cov["fraction"] = mut_cov["subset"].str.extract(r"_ds(\d+)$")[0].astype(int)
            pivot = mut_cov.pivot_table(
                values="sensitivity", index="mutation", columns="fraction"
            )
            if not pivot.empty:
                # Sort columns descending (100% first)
                pivot = pivot[sorted(pivot.columns, reverse=True)]
                # Sort rows: dupC first, then alphabetical
                row_order = ["dupC"] + sorted([m for m in pivot.index if m != "dupC"])
                pivot = pivot.reindex([m for m in row_order if m in pivot.index])

                fig, ax = plt.subplots(figsize=(9, 7))
                sns.heatmap(
                    pivot, annot=True, fmt=".2f", cmap="YlOrRd_r",
                    vmin=0, vmax=1, ax=ax
                )
                # Highlight dupC row with a box
                if "dupC" in pivot.index:
                    dupc_idx = list(pivot.index).index("dupC")
                    ax.add_patch(plt.Rectangle(
                        (0, dupc_idx), len(pivot.columns), 1,
                        fill=False, edgecolor="#d62728", linewidth=2.5
                    ))
                # Highlight 100% column with a box
                if 100 in pivot.columns:
                    col100_idx = list(pivot.columns).index(100)
                    ax.add_patch(plt.Rectangle(
                        (col100_idx, 0), 1, len(pivot.index),
                        fill=False, edgecolor="grey", linewidth=2, linestyle="--"
                    ))
                ax.set_title("Sensitivity: Mutation Type x Coverage Fraction")
                ax.set_xlabel("Coverage fraction (%)")
                ax.set_ylabel("")
                plt.tight_layout()
                for ext in ["png", "svg"]:
                    fig.savefig(figures_dir / f"fig_per_mutation_coverage_heatmap.{ext}", dpi=300)
                plt.close(fig)
                logger.info("  fig_per_mutation_coverage_heatmap")

    # Figure 4: VNTR length vs detection — 2x3 panel (rows: total/allele, cols: dupC/atypical/combined)
    from scipy.stats import mannwhitneyu

    all_mutated = []
    for exp_num in [1, 2]:
        exp_dir_name = get_experiment_dir(cfg, exp_num)
        sl_file = results_base / exp_dir_name / "sample_level_results.csv"
        if sl_file.exists():
            df = pd.read_csv(sl_file)
            mutated = df[df["condition"] == "mutated"].copy()
            mutated["experiment"] = cfg[f"experiment{exp_num}"]["name"]
            all_mutated.append(mutated)

    if all_mutated:
        combined = pd.concat(all_mutated, ignore_index=True)

        length_configs = [
            ("total_length", "Total VNTR length\n(both alleles, repeats)"),
            ("mutated_allele_length", "Mutated allele length\n(repeats)"),
        ]
        # Only keep metrics that exist in the data
        length_configs = [(c, l) for c, l in length_configs if c in combined.columns]

        exp_labels = list(combined["experiment"].unique()) + ["Combined"]

        if length_configs:
            fig, axes = plt.subplots(
                len(length_configs), len(exp_labels),
                figsize=(4 * len(exp_labels), 4.5 * len(length_configs)),
                squeeze=False,
            )

            for row, (length_col, length_label) in enumerate(length_configs):
                for col, exp_label in enumerate(exp_labels):
                    ax = axes[row, col]
                    if exp_label == "Combined":
                        plot_df = combined.dropna(subset=[length_col])
                    else:
                        plot_df = combined[combined["experiment"] == exp_label].dropna(subset=[length_col])

                    if len(plot_df) == 0:
                        ax.set_visible(False)
                        continue

                    sns.boxplot(
                        data=plot_df, x="classification", y=length_col,
                        order=["TP", "FN"],
                        hue="classification", hue_order=["TP", "FN"],
                        palette={"TP": "#2ca02c", "FN": "#d62728"},
                        width=0.5, ax=ax, showfliers=False, legend=False,
                    )
                    sns.stripplot(
                        data=plot_df, x="classification", y=length_col,
                        order=["TP", "FN"],
                        hue="classification", hue_order=["TP", "FN"],
                        palette={"TP": "#2ca02c", "FN": "#d62728"},
                        alpha=0.4, size=4, jitter=True, ax=ax, legend=False,
                    )

                    tp_vals = plot_df.loc[plot_df["classification"] == "TP", length_col]
                    fn_vals = plot_df.loc[plot_df["classification"] == "FN", length_col]
                    if len(tp_vals) > 0 and len(fn_vals) > 0:
                        _, pval = mannwhitneyu(tp_vals, fn_vals, alternative="two-sided")
                        p_text = f"p={pval:.2e}" if pval < 0.001 else f"p={pval:.3f}"
                        ax.text(
                            0.5, 0.97,
                            f"{p_text}\nn={len(tp_vals)}+{len(fn_vals)}",
                            transform=ax.transAxes, ha="center", va="top",
                            fontsize=9, style="italic",
                            bbox=dict(boxstyle="round,pad=0.2", facecolor="wheat", alpha=0.5),
                        )

                    ax.set_xlabel("")
                    ax.set_ylabel(length_label if col == 0 else "")
                    ax.set_title(exp_label if row == 0 else "")

            fig.suptitle("VNTR Length vs Detection Outcome", fontsize=14, y=1.01)
            plt.tight_layout()
            for ext in ["png", "svg"]:
                fig.savefig(
                    figures_dir / f"fig_vntr_length_vs_detection.{ext}",
                    dpi=300, bbox_inches="tight",
                )
            plt.close(fig)
            logger.info("  fig_vntr_length_vs_detection")


def main():
    parser = build_common_parser("Generate summary tables, figures, and YAML")
    args = parser.parse_args()
    cfg = load_config()

    test_mode = args.test
    results_base = get_results_base(cfg, test_mode)

    logger = setup_logging("08_summary")

    # 1. YAML fragment
    logger.info("Generating YAML fragment...")
    fragment = generate_yaml_fragment(results_base, cfg)
    yaml_output = results_base / "variables_fragment.yml"
    yaml_output.parent.mkdir(parents=True, exist_ok=True)
    with open(yaml_output, "w") as f:
        yaml.dump(fragment, f, default_flow_style=False, sort_keys=False)
    logger.info(f"  -> {yaml_output}")

    # 2. Summary tables
    logger.info("Generating summary tables...")
    generate_tables(results_base, cfg, logger)

    # 3. Figures
    logger.info("Generating figures...")
    generate_figures(results_base, cfg, logger)

    logger.info("Summary generation complete.")


if __name__ == "__main__":
    main()
