#!/usr/bin/env python3
"""
02_run_vntyper.py — Run VNtyper 2 normal mode on all full-coverage BAMs.

Usage:
    python scripts/simulation/02_run_vntyper.py [--test] [--workers 16] [--experiment {1,2,all}]
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
    run_vntyper_on_bam,
    setup_logging,
)


def main():
    parser = build_common_parser("Run VNtyper on full-coverage BAMs")
    args = parser.parse_args()
    cfg = load_config()

    test_mode = args.test
    workers = get_workers(cfg, args, step="vntyper")
    results_base = get_results_base(cfg, test_mode)
    experiments = get_experiments_to_run(args)
    reference = cfg["vntyper"]["reference_assembly"]
    timeout = cfg["vntyper"]["timeout_seconds"]
    use_docker = cfg["vntyper"].get("use_docker", False)
    docker_image = cfg["vntyper"].get("docker_image", "")

    logger = setup_logging("02_run_vntyper")
    logger.info(f"Mode: {'TEST' if test_mode else 'PRODUCTION'}, workers={workers}")
    if use_docker:
        logger.info(f"Using Docker: {docker_image}")

    for exp_num in experiments:
        exp_dir_name = get_experiment_dir(cfg, exp_num)
        pairs = get_experiment_pairs(cfg, exp_num, test_mode)
        logger.info(f"Experiment {exp_num}: {len(pairs)} pairs = {len(pairs) * 2} BAMs")

        muconeup_dir = results_base / exp_dir_name / "muconeup"
        vntyper_dir = results_base / exp_dir_name / "vntyper"

        # Build task list: 2 BAMs per pair (normal + mutated)
        tasks = []
        for pair in pairs:
            seed = pair["seed"]
            pair_name = f"pair_{seed}"
            for condition in ["normal", "mut"]:
                bam = muconeup_dir / pair_name / f"{pair_name}.001.{condition}.simulated.bam"
                out = vntyper_dir / pair_name / ("normal" if condition == "normal" else "mutated")
                tasks.append((bam, out))

        completed = 0
        failed = []

        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {}
            for bam, out in tasks:
                fut = executor.submit(run_vntyper_on_bam, bam, out, reference, timeout,
                                     use_docker, docker_image)
                futures[fut] = bam.name

            for fut in as_completed(futures):
                res = fut.result()
                completed += 1
                name = futures[fut]
                if res["status"] in ("success", "skipped"):
                    logger.info(f"[{completed}/{len(tasks)}] {name} {res['status']} ({res['time']:.1f}s)")
                else:
                    logger.error(f"[{completed}/{len(tasks)}] {name} FAILED: {res['status']}")
                    failed.append(res)

        logger.info(f"Experiment {exp_num}: {completed - len(failed)}/{len(tasks)} succeeded")

    logger.info("VNtyper runs complete.")


if __name__ == "__main__":
    main()
