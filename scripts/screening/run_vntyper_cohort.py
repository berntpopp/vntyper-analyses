#!/usr/bin/env python3
"""
run_vntyper_cohort.py — Run VNtyper 2 on all BAMs in a screening cohort.

Reads sample metadata from the cohort's overview TSV, filters to downloaded
samples, and runs VNtyper normal mode via Docker in parallel.

Usage:
    python scripts/screening/run_vntyper_cohort.py --cohort Bernt [--workers 4]
"""

import argparse
import logging
import os
import subprocess
import sys
import time
import yaml
from concurrent.futures import ProcessPoolExecutor, as_completed
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


def run_vntyper_docker(bam_path: Path, output_dir: Path,
                       reference: str, docker_image: str,
                       timeout: int) -> dict:
    """Run VNtyper pipeline on a single BAM via Docker."""
    # Skip if already completed
    for check in [
        output_dir / "kestrel" / "kestrel_result.tsv",
        output_dir / "vntyper_output" / "kestrel" / "kestrel_result.tsv",
    ]:
        if check.exists():
            return {"sample": bam_path.name, "status": "skipped", "time": 0.0}

    if not bam_path.exists():
        return {"sample": bam_path.name, "status": "missing_bam", "time": 0.0}

    output_dir.mkdir(parents=True, exist_ok=True)

    uid = os.getuid()
    gid = os.getgid()
    bam_abs = bam_path.resolve()
    out_abs = output_dir.resolve()

    cmd = [
        "docker", "run", "--rm",
        "-w", "/opt/vntyper",
        "-v", f"{bam_abs.parent}:/opt/vntyper/input",
        "-v", f"{out_abs}:/opt/vntyper/output",
        "--user", f"{uid}:{gid}",
        docker_image,
        "vntyper", "pipeline",
        "--bam", f"/opt/vntyper/input/{bam_abs.name}",
        "-o", "/opt/vntyper/output",
        "--reference-assembly", reference,
    ]

    start = time.time()
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        elapsed = time.time() - start
        if result.returncode != 0:
            return {"sample": bam_path.name, "status": "fail",
                    "error": result.stderr[:500], "time": elapsed}
        return {"sample": bam_path.name, "status": "success", "time": elapsed}
    except subprocess.TimeoutExpired:
        return {"sample": bam_path.name, "status": "timeout",
                "time": time.time() - start}


def main():
    parser = argparse.ArgumentParser(description="Run VNtyper on screening cohort")
    parser.add_argument("--cohort", required=True, help="Cohort name (key in config.yml)")
    parser.add_argument("--workers", type=int, default=None, help="Parallel workers")
    parser.add_argument("--test", type=int, default=None, metavar="N",
                        help="Process only first N samples")
    args = parser.parse_args()

    cfg = load_config()
    cohort_cfg = cfg["cohorts"][args.cohort]
    vntyper_cfg = cfg["vntyper"]

    workers = args.workers or vntyper_cfg["workers"]
    docker_image = vntyper_cfg["docker_image"]
    timeout = vntyper_cfg["timeout_seconds"]
    reference = cohort_cfg["reference_assembly"]

    logger = setup_logging("run_vntyper_cohort")

    # Load sample metadata
    metadata = pd.read_csv(cohort_cfg["metadata_tsv"], sep="\t")
    samples = metadata[
        metadata[cohort_cfg["filter_column"]] == cohort_cfg["filter_value"]
    ].copy()
    samples = samples.dropna(subset=[cohort_cfg["bam_column"]])

    if args.test:
        samples = samples.head(args.test)

    data_dir = Path(cohort_cfg["data_dir"])
    results_dir = Path(cohort_cfg["results_dir"])

    logger.info(f"Cohort: {cohort_cfg['name']}")
    logger.info(f"Samples: {len(samples)}, Workers: {workers}")
    logger.info(f"Docker: {docker_image}")

    # Build task list
    tasks = []
    for _, row in samples.iterrows():
        sample_id = str(row[cohort_cfg["sample_id_column"]])
        bam_file = str(row[cohort_cfg["bam_column"]])
        bam_path = data_dir / bam_file
        output_dir = results_dir / sample_id
        tasks.append((bam_path, output_dir, sample_id))

    completed = 0
    failed = []

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for bam_path, output_dir, sample_id in tasks:
            fut = executor.submit(
                run_vntyper_docker, bam_path, output_dir,
                reference, docker_image, timeout
            )
            futures[fut] = sample_id

        for fut in as_completed(futures):
            res = fut.result()
            completed += 1
            sample_id = futures[fut]
            if res["status"] in ("success", "skipped"):
                if completed % 50 == 0 or completed == len(tasks):
                    logger.info(f"[{completed}/{len(tasks)}] {sample_id} "
                                f"{res['status']} ({res['time']:.1f}s)")
            else:
                logger.error(f"[{completed}/{len(tasks)}] {sample_id} "
                             f"FAILED: {res['status']}")
                failed.append((sample_id, res))

    logger.info(f"Done: {completed - len(failed)}/{len(tasks)} succeeded, "
                f"{len(failed)} failed")
    if failed:
        for sid, res in failed:
            logger.error(f"  {sid}: {res.get('error', '')[:200]}")


if __name__ == "__main__":
    main()
