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

    # Figure 1: Coverage-sensitivity curve
    exp3_metrics = results_base / cfg["experiment3"]["dir_name"] / "performance_metrics.csv"
    if exp3_metrics.exists():
        df = pd.read_csv(exp3_metrics)
        cov_df = df[df["subset"].str.match(r"^(dupC|atypical)_ds\d+$")].copy()
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
            ax.set_xlabel("Coverage fraction (%)")
            ax.set_ylabel("Sensitivity")
            ax.set_title("VNtyper Sensitivity vs Coverage Depth")
            ax.legend()
            ax.set_ylim(0, 1.05)
            ax.invert_xaxis()
            plt.tight_layout()
            for ext in ["png", "svg"]:
                fig.savefig(figures_dir / f"fig_coverage_sensitivity_curve.{ext}", dpi=300)
            plt.close(fig)
            logger.info("  fig_coverage_sensitivity_curve")

    # Figure 2: Per-mutation sensitivity bar chart
    exp2_metrics = results_base / cfg["experiment2"]["dir_name"] / "performance_metrics.csv"
    if exp2_metrics.exists():
        df = pd.read_csv(exp2_metrics)
        per_mut = df[df["subset"] != "all"].copy()
        if len(per_mut) > 0:
            fig, ax = plt.subplots(figsize=(10, 5))
            per_mut = per_mut.sort_values("sensitivity", ascending=False)
            ax.bar(per_mut["subset"], per_mut["sensitivity"], color="steelblue")
            ax.errorbar(
                per_mut["subset"], per_mut["sensitivity"],
                yerr=[
                    per_mut["sensitivity"] - per_mut["sensitivity_ci_low"],
                    per_mut["sensitivity_ci_high"] - per_mut["sensitivity"],
                ],
                fmt="none", color="black", capsize=3,
            )
            ax.set_ylabel("Sensitivity")
            ax.set_title("VNtyper Sensitivity by Mutation Type (Full Coverage)")
            ax.set_ylim(0, 1.05)
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            for ext in ["png", "svg"]:
                fig.savefig(figures_dir / f"fig_per_mutation_sensitivity.{ext}", dpi=300)
            plt.close(fig)
            logger.info("  fig_per_mutation_sensitivity")

    # Figure 3: Per-mutation x coverage heatmap
    if exp3_metrics.exists():
        df = pd.read_csv(exp3_metrics)
        # Filter mutation-specific rows (not dupC_ds* or atypical_ds*)
        mut_cov = df[~df["subset"].str.match(r"^(dupC|atypical|all)")].copy()
        if len(mut_cov) > 0:
            mut_cov["mutation"] = mut_cov["subset"].str.extract(r"^(.+?)_ds")[0]
            mut_cov["fraction"] = mut_cov["subset"].str.extract(r"_ds(\d+)$")[0].astype(int)
            pivot = mut_cov.pivot_table(
                values="sensitivity", index="mutation", columns="fraction"
            )
            if not pivot.empty:
                # Sort columns descending
                pivot = pivot[sorted(pivot.columns, reverse=True)]
                fig, ax = plt.subplots(figsize=(8, 6))
                sns.heatmap(
                    pivot, annot=True, fmt=".2f", cmap="YlOrRd_r",
                    vmin=0, vmax=1, ax=ax
                )
                ax.set_title("Sensitivity: Mutation Type x Coverage Fraction")
                ax.set_xlabel("Coverage fraction (%)")
                plt.tight_layout()
                for ext in ["png", "svg"]:
                    fig.savefig(figures_dir / f"fig_per_mutation_coverage_heatmap.{ext}", dpi=300)
                plt.close(fig)
                logger.info("  fig_per_mutation_coverage_heatmap")

    # Figure 4: VNTR length vs detection
    for exp_num in [1, 2]:
        exp_dir_name = get_experiment_dir(cfg, exp_num)
        sl_file = results_base / exp_dir_name / "sample_level_results.csv"
        if sl_file.exists():
            df = pd.read_csv(sl_file)
            mutated = df[df["condition"] == "mutated"].copy()
            if len(mutated) > 0 and "total_length" in mutated.columns:
                fig, ax = plt.subplots(figsize=(8, 5))
                colors = {"TP": "green", "FN": "red"}
                for cls in ["TP", "FN"]:
                    subset = mutated[mutated["classification"] == cls]
                    if len(subset) > 0:
                        ax.scatter(
                            subset["total_length"], [1 if cls == "TP" else 0] * len(subset),
                            label=cls, alpha=0.6, color=colors[cls], s=30,
                        )
                ax.set_xlabel("Total VNTR length (repeats)")
                ax.set_ylabel("Detection outcome")
                ax.set_yticks([0, 1])
                ax.set_yticklabels(["FN", "TP"])
                ax.set_title(f"VNTR Length vs Detection (Experiment {exp_num})")
                ax.legend()
                plt.tight_layout()
                exp_label = cfg[f"experiment{exp_num}"]["name"]
                for ext in ["png", "svg"]:
                    fig.savefig(
                        figures_dir / f"fig_vntr_length_vs_detection_{exp_label}.{ext}",
                        dpi=300,
                    )
                plt.close(fig)
                logger.info(f"  fig_vntr_length_vs_detection_{exp_label}")


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
