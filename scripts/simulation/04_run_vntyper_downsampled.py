#!/usr/bin/env python3
"""
04_run_vntyper_downsampled.py — Run VNtyper on all downsampled BAMs.

Usage:
    python scripts/simulation/04_run_vntyper_downsampled.py [--test] [--workers 16] [--experiment {1,2,all}]
"""

from concurrent.futures import ProcessPoolExecutor, as_completed

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
    parser = build_common_parser("Run VNtyper on downsampled BAMs")
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
    fractions = cfg["experiment3"]["fractions"]
    exp3_dir_name = cfg["experiment3"]["dir_name"]

    logger = setup_logging("04_run_vntyper_downsampled")
    logger.info(f"Mode: {'TEST' if test_mode else 'PRODUCTION'}, workers={workers}")
    if use_docker:
        logger.info(f"Using Docker: {docker_image}")

    tasks = []
    for exp_num in experiments:
        pairs = get_experiment_pairs(cfg, exp_num, test_mode)
        ds_dir = results_base / exp3_dir_name / "downsampled"
        vntyper_dir = results_base / exp3_dir_name / "vntyper"

        for pair in pairs:
            seed = pair["seed"]
            pair_name = f"pair_{seed}"
            for condition in ["normal", "mut"]:
                cond_label = "normal" if condition == "normal" else "mutated"
                for frac in fractions:
                    bam = (
                        ds_dir / pair_name /
                        f"{pair_name}.001.{condition}.{frac['label']}.bam"
                    )
                    out = vntyper_dir / pair_name / cond_label / frac["label"]
                    tasks.append((bam, out))

    logger.info(f"Total VNtyper tasks: {len(tasks)}")

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
            if res["status"] in ("success", "skipped"):
                if completed % 50 == 0 or completed == len(tasks):
                    logger.info(f"[{completed}/{len(tasks)}] progress...")
            else:
                logger.error(f"[{completed}/{len(tasks)}] {futures[fut]} FAILED")
                failed.append(res)

    logger.info(f"VNtyper downsampled done: {completed - len(failed)}/{len(tasks)} succeeded")


if __name__ == "__main__":
    main()
