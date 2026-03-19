#!/usr/bin/env python3
"""
parse_screening_results.py — Parse VNtyper results and join with sample metadata.

Produces enriched results tables (TSV + XLSX) with Kestrel calls, coverage,
runtime, and sample metadata (enrichment kit, sample IDs).

Usage:
    python scripts/screening/parse_screening_results.py --cohort Bernt
"""

import argparse
import json
import logging
import sys
import yaml
from datetime import datetime
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = SCRIPT_DIR / "config.yml"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def setup_logging(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger


def parse_sample(sample_dir: Path) -> dict:
    """Parse VNtyper output for a single sample."""
    result = {"sample_dir": sample_dir.name}

    # Find kestrel result
    kestrel_tsv = sample_dir / "kestrel" / "kestrel_result.tsv"
    if not kestrel_tsv.exists():
        kestrel_tsv = sample_dir / "vntyper_output" / "kestrel" / "kestrel_result.tsv"
    if kestrel_tsv.exists():
        df = pd.read_csv(kestrel_tsv, sep="\t", comment="#")
        if len(df) > 0:
            row = df.iloc[0]
            confidence = str(row.get("Confidence", "Negative"))
            variant = str(row.get("Variant", ""))
            if confidence != "Negative" and variant != "None":
                result["kestrel_call"] = variant
                result["confidence"] = confidence
                result["depth_score"] = row.get("Depth_Score")
                result["haplo_count"] = row.get("haplo_count")
                result["frame_score"] = row.get("Frame_Score")
                result["is_frameshift"] = (
                    str(row.get("is_frameshift", "")).strip().lower() == "true"
                )
                result["flag"] = str(row.get("Flag", ""))
                result["motif"] = str(row.get("Motif", ""))
            else:
                result["kestrel_call"] = ""
                result["confidence"] = "Negative"
        else:
            result["kestrel_call"] = ""
            result["confidence"] = "Negative"
    else:
        result["kestrel_call"] = ""
        result["confidence"] = "Missing"

    # Coverage from pipeline_summary.json
    ps_file = sample_dir / "pipeline_summary.json"
    if not ps_file.exists():
        ps_file = sample_dir / "vntyper_output" / "pipeline_summary.json"
    if ps_file.exists():
        with open(ps_file) as f:
            ps = json.load(f)

        for step in ps.get("steps", []):
            if step.get("step") == "Coverage Calculation":
                cov_data = step.get("parsed_result", {}).get("data", [])
                if cov_data:
                    c = cov_data[0]
                    result["vntr_coverage_mean"] = float(c.get("mean", 0))
                    result["vntr_coverage_median"] = float(c.get("median", 0))
                    result["vntr_coverage_stdev"] = float(c.get("stdev", 0))
                    result["vntr_percent_uncovered"] = float(
                        c.get("percent_uncovered", 0)
                    )

        # Runtime
        t_start = ps.get("pipeline_start")
        t_end = ps.get("pipeline_end")
        if t_start and t_end:
            try:
                result["runtime_seconds"] = (
                    datetime.fromisoformat(t_end)
                    - datetime.fromisoformat(t_start)
                ).total_seconds()
            except (ValueError, TypeError):
                pass

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Parse VNtyper screening results and join with metadata"
    )
    parser.add_argument("--cohort", required=True, help="Cohort name")
    args = parser.parse_args()

    cfg = load_config()
    cohort_cfg = cfg["cohorts"][args.cohort]

    logger = setup_logging("parse_screening_results")

    results_dir = Path(cohort_cfg["results_dir"])
    tables_dir = Path(cohort_cfg["tables_dir"])
    tables_dir.mkdir(parents=True, exist_ok=True)

    # Load metadata
    metadata = pd.read_csv(cohort_cfg["metadata_tsv"], sep="\t")
    metadata = metadata[
        metadata[cohort_cfg["filter_column"]] == cohort_cfg["filter_value"]
    ].copy()

    logger.info(f"Cohort: {cohort_cfg['name']}")
    logger.info(f"Metadata: {len(metadata)} samples")

    # Parse all VNtyper results
    rows = []
    if results_dir.exists():
        for sample_dir in sorted(results_dir.iterdir()):
            if not sample_dir.is_dir():
                continue
            result = parse_sample(sample_dir)
            result["sample_id"] = sample_dir.name
            rows.append(result)

    logger.info(f"Parsed: {len(rows)} VNtyper results")

    if not rows:
        logger.error("No results found. Run step 1 first.")
        sys.exit(1)

    results_df = pd.DataFrame(rows)

    # Join with metadata
    sample_col = cohort_cfg["sample_id_column"]
    results_df = results_df.merge(
        metadata[[sample_col, "enrichment_kit", "analysis_id", "server"]],
        left_on="sample_id",
        right_on=sample_col,
        how="left",
    )

    # Classify call status
    results_df["is_positive"] = (
        results_df["kestrel_call"].fillna("").astype(str).str.len() > 0
    ) & (~results_df["flag"].fillna("").str.contains("False_Positive", na=False))

    # Sort: positives first, then by confidence
    conf_order = {"High_Precision": 0, "High_Precision*": 1, "Low_Precision": 2,
                  "Negative": 3, "Missing": 4}
    results_df["_conf_order"] = results_df["confidence"].map(conf_order).fillna(5)
    results_df = results_df.sort_values(
        ["is_positive", "_conf_order", "sample_id"],
        ascending=[False, True, True],
    ).drop(columns=["_conf_order", "sample_dir"])

    # Save enriched results
    results_df.to_csv(tables_dir / "screening_results.tsv", sep="\t", index=False)
    results_df.to_excel(tables_dir / "screening_results.xlsx", index=False)
    logger.info(f"Results table: {tables_dir / 'screening_results.tsv'}")

    # Summary statistics
    total = len(results_df)
    positives = results_df[results_df["is_positive"]]
    n_positive = len(positives)

    summary_rows = [
        {"Metric": "Total samples", "Value": total},
        {"Metric": "Positive calls", "Value": n_positive},
        {"Metric": "Negative calls", "Value": total - n_positive},
        {"Metric": "Positive rate", "Value": f"{n_positive/total*100:.1f}%"},
    ]

    # Breakdown by confidence
    for conf in ["High_Precision", "High_Precision*", "Low_Precision"]:
        n = len(positives[positives["confidence"] == conf])
        if n > 0:
            summary_rows.append(
                {"Metric": f"  {conf}", "Value": n}
            )

    # Flagged
    n_flagged = len(results_df[
        results_df["flag"].fillna("").str.contains("False_Positive", na=False)
    ])
    if n_flagged > 0:
        summary_rows.append({"Metric": "Flagged (artifact)", "Value": n_flagged})

    # Coverage by enrichment kit
    for kit in sorted(results_df["enrichment_kit"].dropna().unique()):
        kit_data = results_df[results_df["enrichment_kit"] == kit]
        cov = kit_data["vntr_coverage_mean"].dropna()
        if len(cov) > 0:
            summary_rows.append({
                "Metric": f"Coverage mean ({kit})",
                "Value": f"{cov.median():.1f} (IQR {cov.quantile(0.25):.1f}-{cov.quantile(0.75):.1f})",
            })

    # Runtime
    rt = results_df["runtime_seconds"].dropna()
    if len(rt) > 0:
        summary_rows.append({
            "Metric": "Runtime per sample",
            "Value": f"{rt.median():.1f}s median (range {rt.min():.1f}-{rt.max():.1f}s)",
        })

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(tables_dir / "screening_summary.tsv", sep="\t", index=False)
    summary_df.to_excel(tables_dir / "screening_summary.xlsx", index=False)
    logger.info(f"Summary: {tables_dir / 'screening_summary.tsv'}")

    # Print summary
    logger.info("")
    for _, row in summary_df.iterrows():
        logger.info(f"  {row['Metric']}: {row['Value']}")

    # List positives
    if n_positive > 0:
        logger.info(f"\nPositive samples ({n_positive}):")
        for _, row in positives.iterrows():
            logger.info(
                f"  {row['sample_id']}: {row['confidence']} "
                f"(depth={row.get('depth_score', 'N/A')}, "
                f"flag={row.get('flag', 'N/A')})"
            )

    logger.info("\nDone.")


if __name__ == "__main__":
    main()
