#!/usr/bin/env python3
"""
06_parse_vntyper_results.py — Parse all VNtyper outputs into structured tables.

Reads kestrel_result.tsv and pipeline_summary.json from VNtyper output directories.
Produces one vntyper_parsed.csv per experiment (exp1, exp2, exp3).

Usage:
    python scripts/simulation/06_parse_vntyper_results.py [--test]
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict

from _common import (
    build_common_parser,
    get_experiment_dir,
    get_experiment_pairs,
    get_experiments_to_run,
    get_results_base,
    load_config,
    setup_logging,
)


def parse_kestrel_result(tsv_file: Path) -> Dict:
    """Parse kestrel_result.tsv and return structured result dict.

    VNtyper 2.x kestrel output has:
    - Comment lines starting with '##'
    - Different column sets for positive vs negative results
    - Key columns: Variant, Confidence, Depth_Score, Flag, is_frameshift, haplo_count
    """
    df = pd.read_csv(tsv_file, sep="\t", comment="#")

    if len(df) == 0:
        return {
            "kestrel_call": "",
            "confidence": "Negative",
            "depth_score": None,
            "haplo_count": None,
            "flag": "",
            "is_frameshift": False,
        }

    # Take best variant (first row)
    row = df.iloc[0]
    confidence = str(row.get("Confidence", "Negative"))

    # Check for negative result
    if confidence == "Negative" or str(row.get("Variant", "")) == "None":
        return {
            "kestrel_call": "",
            "confidence": "Negative",
            "depth_score": None,
            "haplo_count": None,
            "flag": "",
            "is_frameshift": False,
        }

    variant = str(row.get("Variant", ""))
    return {
        "kestrel_call": variant,
        "confidence": confidence,
        "depth_score": row.get("Depth_Score"),
        "haplo_count": row.get("haplo_count"),
        "flag": str(row.get("Flag", "")),
        "is_frameshift": str(row.get("is_frameshift", "")).strip().lower() == "true",
    }


def extract_coverage(summary_file: Path) -> Dict:
    """Extract VNTR coverage stats from pipeline_summary.json."""
    with open(summary_file) as f:
        summary = json.load(f)

    for step in summary.get("steps", []):
        if step.get("step") == "Coverage Calculation":
            data = step.get("parsed_result", {}).get("data", [])
            if data:
                cov = data[0]
                return {
                    "vntr_coverage_mean": float(cov.get("mean", 0)),
                    "vntr_coverage_median": float(cov.get("median", 0)),
                }
    return {"vntr_coverage_mean": None, "vntr_coverage_median": None}


def extract_analysis_time(summary_file: Path) -> float:
    """Extract total analysis time from pipeline_summary.json.

    VNtyper 2.x stores pipeline_start and pipeline_end as ISO timestamps.
    """
    from datetime import datetime

    with open(summary_file) as f:
        summary = json.load(f)

    # Try direct field first (future-proofing)
    if "total_time_seconds" in summary:
        return summary["total_time_seconds"]

    # Calculate from start/end timestamps
    start = summary.get("pipeline_start")
    end = summary.get("pipeline_end")
    if start and end:
        try:
            t_start = datetime.fromisoformat(start)
            t_end = datetime.fromisoformat(end)
            return (t_end - t_start).total_seconds()
        except (ValueError, TypeError):
            pass
    return None


def parse_vntyper_output(vntyper_dir: Path) -> Dict:
    """Parse a single VNtyper output directory."""
    result = {}

    # Check both possible locations for kestrel result
    kestrel_tsv = vntyper_dir / "vntyper_output" / "kestrel" / "kestrel_result.tsv"
    if not kestrel_tsv.exists():
        kestrel_tsv = vntyper_dir / "kestrel" / "kestrel_result.tsv"
    if kestrel_tsv.exists():
        result.update(parse_kestrel_result(kestrel_tsv))
    else:
        result.update({
            "kestrel_call": "", "confidence": "Missing",
            "depth_score": None, "haplo_count": None,
            "flag": "", "is_frameshift": False,
        })

    # Coverage and timing
    pipeline_json = vntyper_dir / "vntyper_output" / "pipeline_summary.json"
    if not pipeline_json.exists():
        pipeline_json = vntyper_dir / "pipeline_summary.json"
    if pipeline_json.exists():
        result.update(extract_coverage(pipeline_json))
        result["analysis_time_seconds"] = extract_analysis_time(pipeline_json)
    else:
        result["vntr_coverage_mean"] = None
        result["vntr_coverage_median"] = None
        result["analysis_time_seconds"] = None

    return result


def main():
    parser = build_common_parser("Parse VNtyper results into structured tables")
    args = parser.parse_args()
    cfg = load_config()

    test_mode = args.test
    results_base = get_results_base(cfg, test_mode)
    experiments = get_experiments_to_run(args)
    fractions = cfg["experiment3"]["fractions"]
    exp3_dir_name = cfg["experiment3"]["dir_name"]

    logger = setup_logging("06_parse_vntyper")

    # Parse full-coverage results (experiments 1 and 2)
    for exp_num in experiments:
        exp_dir_name = get_experiment_dir(cfg, exp_num)
        pairs = get_experiment_pairs(cfg, exp_num, test_mode)
        vntyper_dir = results_base / exp_dir_name / "vntyper"

        rows = []
        for pair in pairs:
            seed = pair["seed"]
            pair_name = f"pair_{seed}"
            for condition_dir, condition_label in [("normal", "normal"), ("mutated", "mutated")]:
                out_dir = vntyper_dir / pair_name / condition_dir
                result = parse_vntyper_output(out_dir)
                result["pair_id"] = pair_name
                result["condition"] = condition_label
                result["coverage_fraction"] = 100
                rows.append(result)

        df = pd.DataFrame(rows)
        output = results_base / exp_dir_name / "vntyper_parsed.csv"
        output.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output, index=False)
        logger.info(f"Experiment {exp_num}: {len(df)} rows -> {output}")

    # Parse downsampled results (experiment 3)
    all_ds_rows = []
    for exp_num in experiments:
        pairs = get_experiment_pairs(cfg, exp_num, test_mode)
        vntyper_dir = results_base / exp3_dir_name / "vntyper"

        for pair in pairs:
            seed = pair["seed"]
            pair_name = f"pair_{seed}"
            for condition_dir, condition_label in [("normal", "normal"), ("mutated", "mutated")]:
                for frac in fractions:
                    out_dir = vntyper_dir / pair_name / condition_dir / frac["label"]
                    result = parse_vntyper_output(out_dir)
                    result["pair_id"] = pair_name
                    result["condition"] = condition_label
                    result["coverage_fraction"] = frac["value"] * 100  # float: 12.5, 6.25
                    result["coverage_label"] = frac["label"]
                    result["source_experiment"] = cfg[f"experiment{exp_num}"]["name"]
                    all_ds_rows.append(result)

    if all_ds_rows:
        df_ds = pd.DataFrame(all_ds_rows)
        output_ds = results_base / exp3_dir_name / "vntyper_parsed.csv"
        output_ds.parent.mkdir(parents=True, exist_ok=True)
        df_ds.to_csv(output_ds, index=False)
        logger.info(f"Experiment 3: {len(df_ds)} rows -> {output_ds}")

    logger.info("VNtyper parsing complete.")


if __name__ == "__main__":
    main()
