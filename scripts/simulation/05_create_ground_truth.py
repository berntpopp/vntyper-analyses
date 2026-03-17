#!/usr/bin/env python3
"""
05_create_ground_truth.py — Extract ground truth from simulation metadata.

Reads simulation_stats.json and vntr_structure.txt files from MucOneUp output.
Produces one ground_truth.csv per experiment.

Usage:
    python scripts/simulation/05_create_ground_truth.py [--test]
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Tuple

from _common import (
    build_common_parser,
    get_experiment_dir,
    get_experiment_pairs,
    get_experiments_to_run,
    get_results_base,
    load_config,
    setup_logging,
)


def parse_simulation_stats(stats_file: Path) -> Dict:
    """Parse a simulation_stats.json file into a ground truth row.

    MucOneUp 0.28.x JSON structure:
    - mutation_info.mutation_name: mutation name (e.g. "dupC", "insG")
    - provenance.seed: random seed used
    - haplotype_statistics[0/1].repeat_count: repeat count per haplotype
    - haplotype_statistics[i].mutation_details: list of {position, repeat} dicts
    """
    with open(stats_file) as f:
        stats = json.load(f)

    # Mutation name
    mutation = stats.get("mutation_info", {}).get("mutation_name", "normal")

    # Seed from provenance
    seed = stats.get("provenance", {}).get("seed")

    # Haplotype lengths from haplotype_statistics array
    hap_stats = stats.get("haplotype_statistics", [])
    hap1_length = hap_stats[0].get("repeat_count") if len(hap_stats) > 0 else None
    hap2_length = hap_stats[1].get("repeat_count") if len(hap_stats) > 1 else None

    # Mutation details (position and repeat type) from the haplotype that has them
    mutation_repeat_position = None
    mutation_repeat_type = None
    for hap in hap_stats:
        details = hap.get("mutation_details", [])
        if details:
            mutation_repeat_position = details[0].get("position")
            mutation_repeat_type = details[0].get("repeat")
            break

    row = {
        "seed": seed,
        "mutation": mutation,
        "hap1_length": hap1_length,
        "hap2_length": hap2_length,
        "hap1_chain": None,  # Chain info from vntr_structure.txt, not stats JSON
        "hap2_chain": None,
        "mutation_repeat_position": mutation_repeat_position,
        "mutation_repeat_type": mutation_repeat_type,
    }
    if hap1_length is not None and hap2_length is not None:
        row["total_length"] = hap1_length + hap2_length
    else:
        row["total_length"] = None
    return row


def parse_vntr_structure(struct_file: Path) -> Tuple[Optional[str], Optional[str]]:
    """Parse vntr_structure.txt to extract haplotype chain strings."""
    hap1 = hap2 = None
    with open(struct_file) as f:
        for line in f:
            line = line.strip()
            if line.startswith("haplotype_1"):
                hap1 = line.split("\t")[1]
            elif line.startswith("haplotype_2"):
                hap2 = line.split("\t")[1]
    return hap1, hap2


def main():
    parser = build_common_parser("Create ground truth CSVs from simulation metadata")
    args = parser.parse_args()
    cfg = load_config()

    test_mode = args.test
    results_base = get_results_base(cfg, test_mode)
    experiments = get_experiments_to_run(args)

    logger = setup_logging("05_ground_truth")

    for exp_num in experiments:
        exp_dir_name = get_experiment_dir(cfg, exp_num)
        pairs = get_experiment_pairs(cfg, exp_num, test_mode)
        muconeup_dir = results_base / exp_dir_name / "muconeup"

        rows = []
        for pair in pairs:
            seed = pair["seed"]
            pair_name = f"pair_{seed}"
            pair_dir = muconeup_dir / pair_name

            for condition in ["normal", "mut"]:
                # Try simulation_stats.json first
                stats_file = pair_dir / f"{pair_name}.001.{condition}.simulation_stats.json"
                if stats_file.exists():
                    row = parse_simulation_stats(stats_file)
                else:
                    logger.warning(f"Missing stats: {stats_file}")
                    row = {"seed": seed, "mutation": pair["mutation"] if condition == "mut" else "normal"}

                row["pair_id"] = pair_name
                row["condition"] = "normal" if condition == "normal" else "mutated"
                row["experiment"] = cfg[f"experiment{exp_num}"]["name"]

                # Try vntr_structure.txt for chain info if not in stats
                struct_file = pair_dir / f"{pair_name}.001.vntr_structure.txt"
                if struct_file.exists() and row.get("hap1_chain") is None:
                    hap1_chain, hap2_chain = parse_vntr_structure(struct_file)
                    row["hap1_chain"] = hap1_chain
                    row["hap2_chain"] = hap2_chain

                rows.append(row)

        df = pd.DataFrame(rows)
        output_csv = results_base / exp_dir_name / "ground_truth.csv"
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_csv, index=False)
        logger.info(f"Experiment {exp_num}: wrote {len(df)} rows to {output_csv}")

    logger.info("Ground truth extraction complete.")


if __name__ == "__main__":
    main()
