#!/usr/bin/env python3
"""
01_simulate.py — MucOneUp paired simulation for experiments 1 and 2.

Generates matched pairs (one wild-type + one mutated) using MucOneUp's
dual simulation mode, then simulates Illumina reads for each FASTA.

Usage:
    python scripts/simulation/01_simulate.py [--test] [--workers 16] [--experiment {1,2,all}]
"""

import subprocess
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from _common import (
    build_common_parser,
    get_experiment_dir,
    get_experiment_pairs,
    get_experiments_to_run,
    get_results_base,
    get_workers,
    load_config,
    setup_logging,
)


def simulate_pair(seed: int, mutation: str, pair_dir: Path,
                  muconeup_config: str, threads: int,
                  reference_assembly: str) -> dict:
    """
    Run MucOneUp simulate + reads for one matched pair.

    Returns dict with status info.
    """
    pair_name = f"pair_{seed}"
    pair_dir.mkdir(parents=True, exist_ok=True)

    # Check if already completed (both BAMs exist)
    normal_bam = pair_dir / f"{pair_name}.001.normal.simulated_reads.bam"
    mut_bam = pair_dir / f"{pair_name}.001.mut.simulated_reads.bam"
    if normal_bam.exists() and mut_bam.exists():
        return {"seed": seed, "status": "skipped", "time": 0.0}

    start = time.time()

    # 1. Generate matched pair FASTAs
    sim_cmd = [
        "muconeup", "--config", muconeup_config,
        "simulate",
        "--out-dir", str(pair_dir),
        "--out-base", pair_name,
        "--seed", str(seed),
        "--mutation-name", f"normal,{mutation}",
        "--reference-assembly", reference_assembly,
        "--output-structure",
    ]
    result = subprocess.run(sim_cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        return {"seed": seed, "status": "fail_simulate",
                "error": result.stderr, "time": time.time() - start}

    # 2. Simulate reads for wild-type FASTA
    normal_fa = pair_dir / f"{pair_name}.001.normal.simulated.fa"
    reads_normal_cmd = [
        "muconeup", "--config", muconeup_config,
        "reads", "illumina",
        str(normal_fa),
        "--out-dir", str(pair_dir),
        "--coverage", "150",
        "--threads", str(threads),
    ]
    result = subprocess.run(reads_normal_cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        return {"seed": seed, "status": "fail_reads_normal",
                "error": result.stderr, "time": time.time() - start}

    # 3. Simulate reads for mutated FASTA
    mut_fa = pair_dir / f"{pair_name}.001.mut.simulated.fa"
    reads_mut_cmd = [
        "muconeup", "--config", muconeup_config,
        "reads", "illumina",
        str(mut_fa),
        "--out-dir", str(pair_dir),
        "--coverage", "150",
        "--threads", str(threads),
    ]
    result = subprocess.run(reads_mut_cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        return {"seed": seed, "status": "fail_reads_mut",
                "error": result.stderr, "time": time.time() - start}

    return {"seed": seed, "status": "success", "time": time.time() - start}


def main():
    parser = build_common_parser("MucOneUp paired simulation")
    args = parser.parse_args()
    cfg = load_config()

    test_mode = args.test
    workers = get_workers(cfg, args)
    results_base = get_results_base(cfg, test_mode)
    experiments = get_experiments_to_run(args)
    muconeup_config = cfg["paths"]["muconeup_config"]
    threads = cfg["workers"]["threads_per_job"]
    ref = cfg["read_simulation"]["reference_assembly"]

    logger = setup_logging("01_simulate")
    logger.info(f"Mode: {'TEST' if test_mode else 'PRODUCTION'}, workers={workers}")

    for exp_num in experiments:
        exp_dir_name = get_experiment_dir(cfg, exp_num)
        pairs = get_experiment_pairs(cfg, exp_num, test_mode)
        logger.info(f"Experiment {exp_num}: {len(pairs)} pairs")

        muconeup_dir = results_base / exp_dir_name / "muconeup"
        completed = 0
        failed = []

        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {}
            for pair in pairs:
                seed = pair["seed"]
                mutation = pair["mutation"]
                pair_dir = muconeup_dir / f"pair_{seed}"
                fut = executor.submit(
                    simulate_pair, seed, mutation, pair_dir,
                    muconeup_config, threads, ref
                )
                futures[fut] = seed

            for fut in as_completed(futures):
                res = fut.result()
                completed += 1
                if res["status"] == "success":
                    logger.info(
                        f"[{completed}/{len(pairs)}] pair_{res['seed']} "
                        f"OK ({res['time']:.1f}s)"
                    )
                elif res["status"] == "skipped":
                    logger.info(
                        f"[{completed}/{len(pairs)}] pair_{res['seed']} skipped"
                    )
                else:
                    logger.error(
                        f"[{completed}/{len(pairs)}] pair_{res['seed']} "
                        f"FAILED: {res['status']}"
                    )
                    failed.append(res)

        logger.info(
            f"Experiment {exp_num} done: "
            f"{completed - len(failed)}/{len(pairs)} succeeded"
        )
        if failed:
            for f in failed:
                logger.error(f"  pair_{f['seed']}: {f.get('error', '')[:200]}")

    logger.info("Simulation complete.")


if __name__ == "__main__":
    main()
