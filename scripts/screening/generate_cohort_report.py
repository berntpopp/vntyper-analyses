#!/usr/bin/env python3
"""
generate_cohort_report.py — Run VNtyper cohort command for HTML/TSV summary.

Generates a list of per-sample output directories, then runs VNtyper's
built-in cohort aggregation to produce HTML and tabular summaries.

Usage:
    python scripts/screening/generate_cohort_report.py --cohort Bernt [--pseudonymize]
"""

import argparse
import logging
import os
import subprocess
import sys
import tempfile
import yaml
from pathlib import Path

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


def main():
    parser = argparse.ArgumentParser(description="Generate VNtyper cohort report")
    parser.add_argument("--cohort", required=True, help="Cohort name")
    parser.add_argument("--pseudonymize", action="store_true",
                        help="Pseudonymize sample names in report")
    parser.add_argument("--summary-name", default=None,
                        help="Custom summary filename (default: cohort_summary)")
    args = parser.parse_args()

    cfg = load_config()
    cohort_cfg = cfg["cohorts"][args.cohort]
    vntyper_cfg = cfg["vntyper"]

    logger = setup_logging("generate_cohort_report")

    results_dir = Path(cohort_cfg["results_dir"]).resolve()
    cohort_dir = Path(cohort_cfg["cohort_dir"])
    cohort_dir.mkdir(parents=True, exist_ok=True)
    cohort_dir_abs = cohort_dir.resolve()

    # Find all completed sample directories (those with kestrel_result.tsv)
    sample_dirs = []
    if results_dir.exists():
        for d in sorted(results_dir.iterdir()):
            if d.is_dir():
                for check in [
                    d / "kestrel" / "kestrel_result.tsv",
                    d / "vntyper_output" / "kestrel" / "kestrel_result.tsv",
                ]:
                    if check.exists():
                        sample_dirs.append(d)
                        break

    logger.info(f"Cohort: {cohort_cfg['name']}")
    logger.info(f"Sample directories found: {len(sample_dirs)}")

    if not sample_dirs:
        logger.error("No completed VNtyper results found. Run step 1 first.")
        sys.exit(1)

    # Write sample directory list for --input-file
    # Paths must be relative to the Docker mount
    dir_list_path = cohort_dir_abs / "sample_dirs.txt"
    with open(dir_list_path, "w") as f:
        for d in sample_dirs:
            # Docker mount: results_dir -> /opt/vntyper/input
            rel = d.relative_to(results_dir)
            f.write(f"/opt/vntyper/input/{rel}\n")

    uid = os.getuid()
    gid = os.getgid()
    docker_image = vntyper_cfg["docker_image"]
    summary_name = args.summary_name or "cohort_summary"

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{results_dir}:/opt/vntyper/input:ro",
        "-v", f"{cohort_dir_abs}:/opt/vntyper/output",
        "--user", f"{uid}:{gid}",
        docker_image,
        "vntyper", "cohort",
        "--input-file", f"/opt/vntyper/output/sample_dirs.txt",
        "-o", "/opt/vntyper/output",
        "--summary-file", summary_name,
        "--summary-formats", "csv,tsv,json",
    ]

    if args.pseudonymize:
        cmd.append("--pseudonymize-samples")

    logger.info("Running VNtyper cohort aggregation...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        logger.error(f"Cohort report failed: {result.stderr[:500]}")
        sys.exit(1)

    # List generated files
    logger.info("Cohort report generated:")
    for f in sorted(cohort_dir.iterdir()):
        if f.name != "sample_dirs.txt":
            logger.info(f"  {f.name} ({f.stat().st_size / 1024:.1f} KB)")

    logger.info("Done.")


if __name__ == "__main__":
    main()
