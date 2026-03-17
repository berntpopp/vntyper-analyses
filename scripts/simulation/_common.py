#!/usr/bin/env python3
"""Shared utilities for simulation pipeline scripts."""

import argparse
import logging
import sys
import yaml
from pathlib import Path
from typing import Dict, List


SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = SCRIPT_DIR / "config.yml"


def load_config(config_path: Path = CONFIG_PATH) -> Dict:
    """Load experiment configuration from YAML file."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_experiment_pairs(cfg: Dict, experiment: int, test_mode: bool) -> List[Dict]:
    """
    Get list of {seed, mutation} dicts for an experiment.

    Args:
        cfg: Loaded config dict.
        experiment: 1 or 2.
        test_mode: If True, return smoke-test subset only.

    Returns:
        List of dicts with 'seed' and 'mutation' keys.
    """
    if experiment == 1:
        if test_mode:
            start = cfg["test"]["experiment1"]["seed_start"]
            end = cfg["test"]["experiment1"]["seed_end"]
        else:
            start = cfg["experiment1"]["seed_start"]
            end = cfg["experiment1"]["seed_end"]
        mutation = cfg["experiment1"]["mutation"]
        return [{"seed": s, "mutation": mutation} for s in range(start, end + 1)]

    elif experiment == 2:
        if test_mode:
            test_seeds = set(cfg["test"]["experiment2"]["seeds"])
            pairs = []
            for mut_cfg in cfg["experiment2"]["mutations"]:
                s_start, s_end = mut_cfg["seeds"]
                for s in range(s_start, s_end + 1):
                    if s in test_seeds:
                        pairs.append({"seed": s, "mutation": mut_cfg["name"]})
            return pairs
        else:
            pairs = []
            for mut_cfg in cfg["experiment2"]["mutations"]:
                s_start, s_end = mut_cfg["seeds"]
                for s in range(s_start, s_end + 1):
                    pairs.append({"seed": s, "mutation": mut_cfg["name"]})
            return pairs

    else:
        raise ValueError(f"Unknown experiment: {experiment}")


def get_results_base(cfg: Dict, test_mode: bool) -> Path:
    """Get results base directory (production or test)."""
    key = "results_test_base" if test_mode else "results_base"
    return Path(cfg["paths"][key])


def get_experiment_dir(cfg: Dict, experiment: int) -> str:
    """Get experiment directory name from config."""
    return cfg[f"experiment{experiment}"]["dir_name"]


def build_common_parser(description: str) -> argparse.ArgumentParser:
    """Build argument parser with common flags."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--test", action="store_true",
        help="Smoke-test mode: run on small subset only"
    )
    parser.add_argument(
        "--workers", type=int, default=None,
        help="Number of parallel workers (default: from config)"
    )
    parser.add_argument(
        "--experiment", type=str, default="all", choices=["1", "2", "all"],
        help="Which experiment to run (default: all)"
    )
    return parser


def get_workers(cfg: Dict, args) -> int:
    """Resolve worker count from args or config."""
    if args.workers is not None:
        return args.workers
    return cfg["workers"]["test"] if args.test else cfg["workers"]["default"]


def run_vntyper_on_bam(bam_path: Path, output_dir: Path,
                       reference: str, timeout: int) -> dict:
    """Run VNtyper pipeline on a single BAM file. Used by scripts 02 and 04."""
    import subprocess
    import time

    if not bam_path.exists():
        return {"bam": str(bam_path), "status": "missing_bam", "time": 0.0}

    # Check if already completed (kestrel_result.tsv is the canonical output)
    for check_path in [
        output_dir / "vntyper_output" / "kestrel" / "kestrel_result.tsv",
        output_dir / "kestrel" / "kestrel_result.tsv",
    ]:
        if check_path.exists():
            return {"bam": str(bam_path), "status": "skipped", "time": 0.0}

    output_dir.mkdir(parents=True, exist_ok=True)
    start = time.time()

    cmd = [
        "vntyper", "pipeline",
        "--bam-file", str(bam_path),
        "--reference-assembly", reference,
        "--output-dir", str(output_dir),
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        elapsed = time.time() - start
        if result.returncode != 0:
            return {"bam": str(bam_path), "status": "fail",
                    "error": result.stderr[:500], "time": elapsed}
        return {"bam": str(bam_path), "status": "success", "time": elapsed}
    except subprocess.TimeoutExpired:
        return {"bam": str(bam_path), "status": "timeout",
                "time": time.time() - start}


def setup_logging(name: str, log_file: Path = None) -> logging.Logger:
    """Configure logging to console and optionally to file."""
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

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, mode="w")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger


def get_experiments_to_run(args) -> List[int]:
    """Return list of experiment numbers based on --experiment flag."""
    if args.experiment == "all":
        return [1, 2]
    return [int(args.experiment)]
