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


def _fmt_ci(val, ci_low, ci_high):
    """Format value with 95% CI as 'XX.X% (XX.X%-XX.X%)'."""
    return f"{val*100:.1f}% ({ci_low*100:.1f}%-{ci_high*100:.1f}%)"


def _fmt_pct(val):
    """Format as percentage."""
    return f"{val*100:.1f}%"


def _save(df: pd.DataFrame, path: Path, logger):
    """Save as both TSV and XLSX."""
    df.to_csv(path.with_suffix(".tsv"), sep="\t", index=False)
    df.to_excel(path.with_suffix(".xlsx"), index=False)
    logger.info(f"  {path.stem} (.tsv, .xlsx)")


def generate_tables(results_base: Path, cfg: dict, logger):
    """Generate manuscript-ready tables in TSV and XLSX."""
    tables_dir = results_base / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    exp1_metrics_path = results_base / cfg["experiment1"]["dir_name"] / "performance_metrics.csv"
    exp2_metrics_path = results_base / cfg["experiment2"]["dir_name"] / "performance_metrics.csv"
    exp3_metrics_path = results_base / cfg["experiment3"]["dir_name"] / "performance_metrics.csv"

    # ── Main Table: Performance overview (dupC + atypical) ──
    rows = []
    for label, exp_dir_name in [("dupC", cfg["experiment1"]["dir_name"]),
                                 ("Atypical", cfg["experiment2"]["dir_name"])]:
        metrics_path = results_base / exp_dir_name / "performance_metrics.csv"
        parsed_path = results_base / exp_dir_name / "vntyper_parsed.csv"
        if not metrics_path.exists():
            continue
        df = pd.read_csv(metrics_path)
        o = df[df["subset"] == "all"].iloc[0]

        rows.append({
            "Experiment": label,
            "N pairs": int(o["n_positive"]),
            "TP": int(o["tp"]), "TN": int(o["tn"]),
            "FP": int(o["fp"]), "FN": int(o["fn"]),
            "Sensitivity": _fmt_ci(o["sensitivity"], o["sensitivity_ci_low"], o["sensitivity_ci_high"]),
            "Specificity": _fmt_ci(o["specificity"], o["specificity_ci_low"], o["specificity_ci_high"]),
            "PPV": _fmt_pct(o["ppv"]),
            "NPV": _fmt_pct(o["npv"]),
            "F1": f"{o['f1_score']:.3f}",
        })
    if rows:
        _save(pd.DataFrame(rows), tables_dir / "main_table_performance", logger)

    # ── Supplementary Table 1: Per-mutation sensitivity ──
    if exp2_metrics_path.exists():
        df2 = pd.read_csv(exp2_metrics_path)
        per_mut = df2[df2["subset"] != "all"].sort_values("sensitivity", ascending=False)

        # Add dupC from exp1
        if exp1_metrics_path.exists():
            df1 = pd.read_csv(exp1_metrics_path)
            dupc = df1[df1["subset"] == "all"].iloc[0]
            dupc_row = {
                "Mutation": "dupC",
                "N": int(dupc["n_positive"]),
                "TP": int(dupc["tp"]), "FN": int(dupc["fn"]),
                "Sensitivity": _fmt_ci(dupc["sensitivity"], dupc["sensitivity_ci_low"], dupc["sensitivity_ci_high"]),
            }
        else:
            dupc_row = None

        sup_rows = []
        if dupc_row:
            sup_rows.append(dupc_row)
        for _, r in per_mut.iterrows():
            sup_rows.append({
                "Mutation": r["subset"],
                "N": int(r["n_positive"]),
                "TP": int(r["tp"]), "FN": int(r["fn"]),
                "Sensitivity": _fmt_ci(r["sensitivity"], r["sensitivity_ci_low"], r["sensitivity_ci_high"]),
            })
        _save(pd.DataFrame(sup_rows), tables_dir / "supp_table_per_mutation", logger)

    # ── Supplementary Table 2: Coverage titration ──
    if exp3_metrics_path.exists():
        df3 = pd.read_csv(exp3_metrics_path)
        cov = df3[df3["subset"].str.match(r"^(dupC|atypical)_ds\d+$")].copy()
        cov["source"] = cov["subset"].str.extract(r"^(\w+)_ds")[0]
        cov["fraction"] = cov["subset"].str.extract(r"_ds(\d+)$")[0].astype(int)

        # Add 100% baseline
        baseline_rows = []
        if exp1_metrics_path.exists():
            o1 = pd.read_csv(exp1_metrics_path)
            o1 = o1[o1["subset"] == "all"].iloc[0]
            baseline_rows.append({"source": "dupC", "fraction": 100, **o1.to_dict()})
        if exp2_metrics_path.exists():
            o2 = pd.read_csv(exp2_metrics_path)
            o2 = o2[o2["subset"] == "all"].iloc[0]
            baseline_rows.append({"source": "atypical", "fraction": 100, **o2.to_dict()})
        if baseline_rows:
            cov = pd.concat([cov, pd.DataFrame(baseline_rows)], ignore_index=True)

        # Deduplicate: keep one row per (source, fraction)
        cov = cov.drop_duplicates(subset=["source", "fraction"], keep="first")
        cov_rows = []
        for _, r in cov.sort_values(["source", "fraction"], ascending=[True, False]).iterrows():
            cov_rows.append({
                "Experiment": r["source"],
                "Coverage (%)": int(r["fraction"]),
                "N positive": int(r["n_positive"]),
                "N negative": int(r["n_negative"]),
                "Sensitivity": _fmt_ci(r["sensitivity"], r["sensitivity_ci_low"], r["sensitivity_ci_high"]),
                "Specificity": _fmt_ci(r["specificity"], r["specificity_ci_low"], r["specificity_ci_high"]),
            })
        _save(pd.DataFrame(cov_rows), tables_dir / "supp_table_coverage_titration", logger)

    # ── Supplementary Table 3: Per-mutation x coverage heatmap data ──
    if exp3_metrics_path.exists():
        df3 = pd.read_csv(exp3_metrics_path)
        mut_cov = df3[~df3["subset"].str.match(r"^(atypical_ds|all)")].copy()

        # Add 100% baselines
        baseline_rows = []
        if exp1_metrics_path.exists():
            df1 = pd.read_csv(exp1_metrics_path)
            r100 = df1[df1["subset"] == "all"].iloc[0].to_dict()
            r100["subset"] = "dupC_ds100"
            baseline_rows.append(r100)
        if exp2_metrics_path.exists():
            df2 = pd.read_csv(exp2_metrics_path)
            for _, r in df2[df2["subset"] != "all"].iterrows():
                r100 = r.to_dict()
                r100["subset"] = f"{r['subset']}_ds100"
                baseline_rows.append(r100)
        if baseline_rows:
            mut_cov = pd.concat([mut_cov, pd.DataFrame(baseline_rows)], ignore_index=True)

        mut_cov["Mutation"] = mut_cov["subset"].str.extract(r"^(.+?)_ds")[0]
        mut_cov["Coverage (%)"] = mut_cov["subset"].str.extract(r"_ds(\d+)$")[0].astype(int)

        pivot = mut_cov.pivot_table(values="sensitivity", index="Mutation", columns="Coverage (%)")
        if not pivot.empty:
            pivot = pivot[sorted(pivot.columns, reverse=True)]
            row_order = ["dupC"] + sorted([m for m in pivot.index if m != "dupC"])
            pivot = pivot.reindex([m for m in row_order if m in pivot.index])
            # Format as percentages
            pivot_fmt = pivot.map(lambda x: f"{x*100:.0f}%" if pd.notna(x) else "")
            _save(pivot_fmt.reset_index(), tables_dir / "supp_table_mutation_coverage_matrix", logger)

    # ── Supplementary Table 4: False negatives detail ──
    fn_frames = []
    for exp_num in [1, 2]:
        exp_dir_name = get_experiment_dir(cfg, exp_num)
        sl_file = results_base / exp_dir_name / "sample_level_results.csv"
        if sl_file.exists():
            df = pd.read_csv(sl_file)
            fn_df = df[df["classification"] == "FN"]
            if len(fn_df) > 0:
                fn_frames.append(fn_df)

    if fn_frames:
        fn_all = pd.concat(fn_frames, ignore_index=True)
        fn_clean = fn_all[[
            "pair_id", "mutation", "hap1_length", "hap2_length",
            "total_length", "mutated_allele_length",
            "vntr_coverage_mean", "confidence",
        ]].copy()
        fn_clean.columns = [
            "Pair", "Mutation", "Hap1 length", "Hap2 length",
            "Total length", "Mutated allele length",
            "VNTR coverage", "VNtyper confidence",
        ]
        fn_clean = fn_clean.sort_values(["Mutation", "Total length"])
        _save(fn_clean, tables_dir / "supp_table_false_negatives", logger)

    # ── Supplementary Table 5: False positives detail ──
    fp_frames = []
    for exp_num in [1, 2]:
        exp_dir_name = get_experiment_dir(cfg, exp_num)
        sl_file = results_base / exp_dir_name / "sample_level_results.csv"
        if sl_file.exists():
            df = pd.read_csv(sl_file)
            fp_df = df[df["classification"] == "FP"]
            if len(fp_df) > 0:
                fp_frames.append(fp_df)

    if fp_frames:
        fp_all = pd.concat(fp_frames, ignore_index=True)
        _save(fp_all, tables_dir / "supp_table_false_positives", logger)
    else:
        logger.info("  No false positives (table not generated)")


def generate_comprehensive_table(results_base: Path, cfg: dict, logger):
    """Generate a comprehensive per-sample table merging all simulation and VNtyper data."""
    import json
    from datetime import datetime

    tables_dir = results_base / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    all_rows = []
    for exp_num in [1, 2]:
        exp_dir_name = get_experiment_dir(cfg, exp_num)
        exp_name = cfg[f"experiment{exp_num}"]["name"]
        muconeup_dir = results_base / exp_dir_name / "muconeup"
        vntyper_dir = results_base / exp_dir_name / "vntyper"

        from _common import get_experiment_pairs, load_config
        pairs = get_experiment_pairs(cfg, exp_num, test_mode=False)

        for pair in pairs:
            seed = pair["seed"]
            pair_name = f"pair_{seed}"

            for condition, cond_label, vnt_subdir in [
                ("normal", "normal", "normal"),
                ("mut", "mutated", "mutated"),
            ]:
                row = {
                    "experiment": exp_name,
                    "pair_id": pair_name,
                    "seed": seed,
                    "condition": cond_label,
                    "expected_mutation": pair["mutation"] if condition == "mut" else "none",
                }

                # ── Simulation metadata ──
                stats_file = muconeup_dir / pair_name / f"{pair_name}.001.{condition}.simulation_stats.json"
                if stats_file.exists():
                    with open(stats_file) as f:
                        stats = json.load(f)

                    hap_stats = stats.get("haplotype_statistics", [])
                    if len(hap_stats) >= 2:
                        row["hap1_repeat_count"] = hap_stats[0].get("repeat_count")
                        row["hap2_repeat_count"] = hap_stats[1].get("repeat_count")
                        row["hap1_vntr_length_bp"] = hap_stats[0].get("vntr_length")
                        row["hap2_vntr_length_bp"] = hap_stats[1].get("vntr_length")
                        row["total_repeat_count"] = (
                            (hap_stats[0].get("repeat_count") or 0) +
                            (hap_stats[1].get("repeat_count") or 0)
                        )

                        # Find mutated haplotype
                        for i, h in enumerate(hap_stats):
                            details = h.get("mutation_details", [])
                            if details:
                                row["mutated_haplotype"] = i + 1
                                row["mutated_allele_repeat_count"] = h.get("repeat_count")
                                row["mutation_position"] = details[0].get("position")
                                row["mutation_repeat_type"] = details[0].get("repeat")
                                break

                    overall = stats.get("overall_statistics", {})
                    row["avg_gc_content"] = overall.get("gc_content", {}).get("average")

                    mut_info = stats.get("mutation_info", {})
                    row["simulation_mutation"] = mut_info.get("mutation_name")

                # ── VNtyper results ──
                kestrel_tsv = vntyper_dir / pair_name / vnt_subdir / "kestrel" / "kestrel_result.tsv"
                if kestrel_tsv.exists():
                    kdf = pd.read_csv(kestrel_tsv, sep="\t", comment="#")
                    if len(kdf) > 0:
                        kr = kdf.iloc[0]
                        conf = str(kr.get("Confidence", ""))
                        if conf != "Negative" and str(kr.get("Variant", "")) != "None":
                            row["vntyper_call"] = str(kr.get("Variant", ""))
                            row["vntyper_confidence"] = conf
                            row["vntyper_depth_score"] = kr.get("Depth_Score")
                            row["vntyper_haplo_count"] = kr.get("haplo_count")
                            row["vntyper_frame_score"] = kr.get("Frame_Score")
                            row["vntyper_is_frameshift"] = kr.get("is_frameshift")
                            row["vntyper_flag"] = str(kr.get("Flag", ""))
                            row["vntyper_motif"] = str(kr.get("Motif", ""))
                            row["vntyper_alt_depth"] = kr.get("Estimated_Depth_AlternateVariant")
                            row["vntyper_region_depth"] = kr.get("Estimated_Depth_Variant_ActiveRegion")
                        else:
                            row["vntyper_call"] = ""
                            row["vntyper_confidence"] = "Negative"
                    else:
                        row["vntyper_call"] = ""
                        row["vntyper_confidence"] = "Negative"

                # ── Coverage from pipeline_summary ──
                ps_file = vntyper_dir / pair_name / vnt_subdir / "pipeline_summary.json"
                if ps_file.exists():
                    with open(ps_file) as f:
                        ps = json.load(f)

                    for step in ps.get("steps", []):
                        if step["step"] == "Coverage Calculation":
                            cov_data = step.get("parsed_result", {}).get("data", [])
                            if cov_data:
                                c = cov_data[0]
                                row["vntr_coverage_mean"] = float(c.get("mean", 0))
                                row["vntr_coverage_median"] = float(c.get("median", 0))
                                row["vntr_coverage_stdev"] = float(c.get("stdev", 0))
                                row["vntr_coverage_min"] = float(c.get("min", 0))
                                row["vntr_coverage_max"] = float(c.get("max", 0))
                                row["vntr_percent_uncovered"] = float(c.get("percent_uncovered", 0))

                    # Runtime
                    t_start = ps.get("pipeline_start")
                    t_end = ps.get("pipeline_end")
                    if t_start and t_end:
                        try:
                            row["vntyper_runtime_seconds"] = (
                                datetime.fromisoformat(t_end) -
                                datetime.fromisoformat(t_start)
                            ).total_seconds()
                        except (ValueError, TypeError):
                            pass

                # ── Classification ──
                is_mutated = condition == "mut"
                has_call = bool(row.get("vntyper_call"))
                is_flagged = "False_Positive" in str(row.get("vntyper_flag", ""))
                called_positive = has_call and not is_flagged
                if is_mutated:
                    row["classification"] = "TP" if called_positive else "FN"
                else:
                    row["classification"] = "FP" if called_positive else "TN"

                all_rows.append(row)

    if all_rows:
        df = pd.DataFrame(all_rows)
        # Order columns logically
        col_order = [
            "experiment", "pair_id", "seed", "condition", "expected_mutation",
            "simulation_mutation", "classification",
            # Simulation haplotype data
            "hap1_repeat_count", "hap2_repeat_count", "total_repeat_count",
            "hap1_vntr_length_bp", "hap2_vntr_length_bp",
            "mutated_haplotype", "mutated_allele_repeat_count",
            "mutation_position", "mutation_repeat_type", "avg_gc_content",
            # VNtyper results
            "vntyper_call", "vntyper_confidence", "vntyper_depth_score",
            "vntyper_haplo_count", "vntyper_frame_score", "vntyper_is_frameshift",
            "vntyper_flag", "vntyper_motif",
            "vntyper_alt_depth", "vntyper_region_depth",
            # Coverage
            "vntr_coverage_mean", "vntr_coverage_median", "vntr_coverage_stdev",
            "vntr_coverage_min", "vntr_coverage_max", "vntr_percent_uncovered",
            # Runtime
            "vntyper_runtime_seconds",
        ]
        # Only keep columns that exist
        col_order = [c for c in col_order if c in df.columns]
        df = df[col_order]
        _save(df, tables_dir / "comprehensive_all_samples", logger)


def generate_figures(results_base: Path, cfg: dict, logger):
    """Generate supplementary figures."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    figures_dir = results_base / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Global style: despine (show only x and y axes, no top/right box)
    sns.set_style("ticks")

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
            ax.legend()
            ax.set_ylim(0, 1.05)
            ax.invert_xaxis()
            sns.despine(ax=ax)
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
            ax.set_ylim(0, 1.05)
            # Add legend for dupC highlight
            from matplotlib.patches import Patch
            ax.legend(handles=[
                Patch(color="#d62728", label="dupC (canonical)"),
                Patch(color="steelblue", label="Atypical frameshifts"),
            ])
            plt.xticks(rotation=45, ha="right")
            sns.despine(ax=ax)
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

                    sns.despine(ax=ax)
                    ax.set_xlabel("")
                    ax.set_ylabel(length_label if col == 0 else "")
                    # Column labels on first row only
                    if row == 0:
                        ax.text(0.5, 1.05, exp_label, transform=ax.transAxes,
                                ha="center", va="bottom", fontsize=11, fontweight="bold")

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

    # 3. Comprehensive per-sample table
    logger.info("Generating comprehensive sample table...")
    generate_comprehensive_table(results_base, cfg, logger)

    # 4. Figures
    logger.info("Generating figures...")
    generate_figures(results_base, cfg, logger)

    logger.info("Summary generation complete.")


if __name__ == "__main__":
    main()
