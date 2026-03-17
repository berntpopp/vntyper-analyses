#!/usr/bin/env python3
"""
03_downsample.py — Downsample all BAMs from experiments 1+2 to coverage fractions.

Uses samtools view -s with seed-based sampling for reproducibility.
Input BAMs are read from experiment{1,2}/muconeup/pair_*/.
Output goes to experiment3_coverage/downsampled/pair_*/.

Usage:
    python scripts/simulation/03_downsample.py [--test] [--workers 16] [--experiment {1,2,all}]
"""

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
    run_samtools_downsample,
    setup_logging,
)


def main():
    parser = build_common_parser("Downsample BAMs for coverage titration")
    args = parser.parse_args()
    cfg = load_config()

    test_mode = args.test
    workers = get_workers(cfg, args, step="downsample")
    results_base = get_results_base(cfg, test_mode)
    experiments = get_experiments_to_run(args)
    fractions = cfg["experiment3"]["fractions"]
    exp3_dir_name = cfg["experiment3"]["dir_name"]
    use_docker = cfg["vntyper"].get("use_docker", False)
    docker_image = cfg["vntyper"].get("docker_image", "")

    logger = setup_logging("03_downsample")
    logger.info(f"Mode: {'TEST' if test_mode else 'PRODUCTION'}, workers={workers}")
    if use_docker:
        logger.info(f"Using Docker for samtools: {docker_image}")

    tasks = []
    for exp_num in experiments:
        exp_dir_name = get_experiment_dir(cfg, exp_num)
        pairs = get_experiment_pairs(cfg, exp_num, test_mode)

        muconeup_dir = results_base / exp_dir_name / "muconeup"
        ds_dir = results_base / exp3_dir_name / "downsampled"

        for pair in pairs:
            seed = pair["seed"]
            pair_name = f"pair_{seed}"
            for condition in ["normal", "mut"]:
                input_bam = (
                    muconeup_dir / pair_name /
                    f"{pair_name}.001.{condition}.simulated.bam"
                )
                for frac in fractions:
                    output_bam = (
                        ds_dir / pair_name /
                        f"{pair_name}.001.{condition}.{frac['label']}.bam"
                    )
                    tasks.append((input_bam, output_bam, frac["samtools_arg"]))

    logger.info(f"Total downsampling tasks: {len(tasks)}")

    completed = 0
    failed = []

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for input_bam, output_bam, samtools_arg in tasks:
            fut = executor.submit(run_samtools_downsample, input_bam, output_bam,
                                 samtools_arg, use_docker, docker_image)
            futures[fut] = output_bam.name

        for fut in as_completed(futures):
            res = fut.result()
            completed += 1
            if res["status"] in ("success", "skipped"):
                if completed % 50 == 0 or completed == len(tasks):
                    logger.info(f"[{completed}/{len(tasks)}] progress...")
            else:
                logger.error(f"[{completed}/{len(tasks)}] {res['bam']} FAILED: {res['status']}")
                failed.append(res)

    logger.info(f"Downsampling done: {completed - len(failed)}/{len(tasks)} succeeded")


if __name__ == "__main__":
    main()
