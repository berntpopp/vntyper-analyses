# Simulation Pipeline Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 8 Python scripts + config to simulate MUC1 VNTR samples with MucOneUp, genotype them with VNtyper 2, and compute performance metrics for the manuscript.

**Architecture:** CLI orchestration scripts that invoke MucOneUp and VNtyper via subprocess, with `concurrent.futures.ProcessPoolExecutor` for parallelism. A shared config.yml centralizes all experiment parameters. A small shared utilities module (`_common.py`) provides logging, config loading, and argument parsing to avoid duplication across the 8 scripts.

**Tech Stack:** Python 3.8+, PyYAML, pandas, numpy, scipy (Wilson CI), matplotlib, seaborn, subprocess, concurrent.futures, samtools CLI, muconeup CLI, vntyper CLI.

**Key assumption:** MucOneUp's `config.json` (`../MucOneUp/config.json`) already contains the correct simulation parameters (VNTR distribution: normal, mean=60, min=20, max=130; read simulation: 10000 read pairs, 250bp fragments, 35bp SD, 150x coverage, non_vntr downsample mode, Twist v2 enrichment). These are NOT CLI flags — they are config-file-only settings. A validation step (Task 1a) verifies this before any simulation runs. Note: MucOneUp derives SD from `(max-min)/4 = 27.5`, not the 15 stated in the manuscript Methods text.

---

## File Structure

| File | Responsibility |
|------|---------------|
| `scripts/simulation/config.yml` | All experiment parameters in one file |
| `scripts/simulation/_common.py` | Shared utilities: config loading, logging, CLI args, path helpers |
| `scripts/simulation/01_simulate.py` | MucOneUp paired simulation for both experiments |
| `scripts/simulation/02_run_vntyper.py` | VNtyper normal mode on all 400 full-coverage BAMs |
| `scripts/simulation/03_downsample.py` | Downsample all 400 BAMs to 4 coverage fractions |
| `scripts/simulation/04_run_vntyper_downsampled.py` | VNtyper on all 1,600 downsampled BAMs |
| `scripts/simulation/05_create_ground_truth.py` | Extract ground truth from simulation metadata |
| `scripts/simulation/06_parse_vntyper_results.py` | Parse all VNtyper outputs into structured tables |
| `scripts/simulation/07_calculate_metrics.py` | Sensitivity, specificity, Wilson CIs for all experiments |
| `scripts/simulation/08_generate_summary.py` | Summary tables, figures, YAML fragment for manuscript |
| `tests/simulation/test_common.py` | Unit tests for shared utilities |
| `tests/simulation/test_ground_truth.py` | Unit tests for ground truth extraction |
| `tests/simulation/test_parse_vntyper.py` | Unit tests for VNtyper output parsing |
| `tests/simulation/test_metrics.py` | Unit tests for performance metric calculations |

---

## Chunk 1: Project Setup, Config, and Shared Utilities

### Task 1a: Validate MucOneUp config.json

**Files:**
- Read: `../MucOneUp/config.json`

- [ ] **Step 1: Verify MucOneUp config.json has expected values**

```bash
cd /home/bernt-popp/development/vntyper-analyses
python -c "
import json
with open('../MucOneUp/config.json') as f:
    cfg = json.load(f)
lm = cfg['length_model']
rs = cfg['read_simulation']
checks = [
    ('length_model.distribution', lm['distribution'], 'normal'),
    ('length_model.mean_repeats', lm['mean_repeats'], 60),
    ('length_model.min_repeats', lm['min_repeats'], 20),
    ('length_model.max_repeats', lm['max_repeats'], 130),
    ('read_simulation.read_number', rs['read_number'], 10000),
    ('read_simulation.fragment_size', rs['fragment_size'], 250),
    ('read_simulation.fragment_sd', rs['fragment_sd'], 35),
    ('read_simulation.coverage', rs['coverage'], 150),
    ('read_simulation.downsample_mode', rs['downsample_mode'], 'non_vntr'),
    ('read_simulation.sample_bam_hg38', 'twist_v2' in rs.get('sample_bam_hg38',''), True),
]
ok = True
for name, actual, expected in checks:
    status = 'OK' if actual == expected else 'MISMATCH'
    if status == 'MISMATCH': ok = False
    print(f'  {status}: {name} = {actual} (expected {expected})')
assert ok, 'MucOneUp config.json has unexpected values — update before proceeding'
print('All checks passed.')
"
```

Expected: All checks pass. If any fail, update `../MucOneUp/config.json` before proceeding.

### Task 1: Create directory structure

**Files:**
- Create: `scripts/simulation/` directory
- Create: `tests/simulation/` directory

- [ ] **Step 1: Create directories**

```bash
mkdir -p scripts/simulation
mkdir -p tests/simulation
touch tests/__init__.py
touch tests/simulation/__init__.py
```

- [ ] **Step 2: Commit**

```bash
git add scripts/simulation tests/
git commit -m "chore: create simulation scripts and tests directories"
```

### Task 2: Create config.yml

**Files:**
- Create: `scripts/simulation/config.yml`

- [ ] **Step 1: Write config.yml with all experiment parameters**

```yaml
# Simulation experiment configuration
# All parameters for the 3-experiment MUC1 VNTR simulation benchmark

# Paths (relative to vntyper-analyses working directory)
paths:
  muconeup_config: "../MucOneUp/config.json"
  results_base: "results/simulation"
  results_test_base: "results/simulation_test"

# VNTR length distribution (Vrbacka et al. 2025)
vntr:
  distribution: normal
  mean_repeats: 60
  sd_repeats: 15
  min_repeats: 20
  max_repeats: 130

# Read simulation parameters
read_simulation:
  simulator: illumina
  coverage: 150
  read_number: 10000
  fragment_size: 250
  fragment_sd: 35
  downsample_mode: non_vntr
  reference_assembly: hg38

# Experiment 1: Canonical dupC
experiment1:
  name: "dupC"
  dir_name: "experiment1_dupC"
  mutation: "dupC"
  seed_start: 3000
  seed_end: 3099
  n_pairs: 100

# Experiment 2: Atypical frameshifts
experiment2:
  name: "atypical"
  dir_name: "experiment2_atypical"
  mutations:
    # seeds: [start_inclusive, end_inclusive] — range generates start..end
    - name: "insG"
      seeds: [4000, 4009]
    - name: "dupA"
      seeds: [4010, 4019]
    - name: "delinsAT"
      seeds: [4020, 4029]
    - name: "insCCCC"
      seeds: [4030, 4039]
    - name: "insC_pos23"
      seeds: [4040, 4049]
    - name: "insG_pos58"
      seeds: [4050, 4059]
    - name: "insG_pos54"
      seeds: [4060, 4069]
    - name: "insA_pos54"
      seeds: [4070, 4079]
    - name: "delGCCCA"
      seeds: [4080, 4089]
    - name: "ins25bp"
      seeds: [4090, 4099]
  n_pairs: 100

# Experiment 3: Coverage titration
experiment3:
  name: "coverage"
  dir_name: "experiment3_coverage"
  fractions:
    - label: "ds50"
      value: 0.5000
      samtools_arg: "42.5000"
    - label: "ds25"
      value: 0.2500
      samtools_arg: "42.2500"
    - label: "ds12"
      value: 0.1250
      samtools_arg: "42.1250"
    - label: "ds6"
      value: 0.0625
      samtools_arg: "42.0625"

# Smoke test subset
test:
  experiment1:
    seed_start: 3000
    seed_end: 3004
    n_pairs: 5
  experiment2:
    # First 5 mutations, 1 pair each
    seeds: [4000, 4010, 4020, 4030, 4040]
    n_pairs: 5

# Parallelism
workers:
  default: 16
  test: 4
  threads_per_job: 2

# VNtyper settings
vntyper:
  reference_assembly: hg38
  timeout_seconds: 1200
```

- [ ] **Step 2: Commit**

```bash
git add scripts/simulation/config.yml
git commit -m "feat: add simulation experiment config.yml"
```

### Task 3: Create shared utilities module

**Files:**
- Create: `scripts/simulation/_common.py`
- Test: `tests/simulation/test_common.py`

- [ ] **Step 1: Write failing tests for config loading and path helpers**

```python
# tests/simulation/test_common.py
"""Tests for shared simulation utilities."""

import pytest
import yaml
from pathlib import Path
from unittest.mock import patch


# Determine paths
TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts" / "simulation"

# Add scripts dir to path for imports
import sys
sys.path.insert(0, str(SCRIPTS_DIR))


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_returns_dict(self):
        from _common import load_config
        cfg = load_config()
        assert isinstance(cfg, dict)

    def test_load_config_has_required_keys(self):
        from _common import load_config
        cfg = load_config()
        assert "experiment1" in cfg
        assert "experiment2" in cfg
        assert "experiment3" in cfg
        assert "vntr" in cfg
        assert "read_simulation" in cfg
        assert "paths" in cfg

    def test_experiment1_seeds(self):
        from _common import load_config
        cfg = load_config()
        assert cfg["experiment1"]["seed_start"] == 3000
        assert cfg["experiment1"]["seed_end"] == 3099

    def test_experiment2_mutations_count(self):
        from _common import load_config
        cfg = load_config()
        assert len(cfg["experiment2"]["mutations"]) == 10


class TestGetExperimentPairs:
    """Tests for get_experiment_pairs function."""

    def test_exp1_full_returns_100_pairs(self):
        from _common import load_config, get_experiment_pairs
        cfg = load_config()
        pairs = get_experiment_pairs(cfg, experiment=1, test_mode=False)
        assert len(pairs) == 100
        assert pairs[0] == {"seed": 3000, "mutation": "dupC"}
        assert pairs[99] == {"seed": 3099, "mutation": "dupC"}

    def test_exp1_test_returns_5_pairs(self):
        from _common import load_config, get_experiment_pairs
        cfg = load_config()
        pairs = get_experiment_pairs(cfg, experiment=1, test_mode=True)
        assert len(pairs) == 5

    def test_exp2_full_returns_100_pairs(self):
        from _common import load_config, get_experiment_pairs
        cfg = load_config()
        pairs = get_experiment_pairs(cfg, experiment=2, test_mode=False)
        assert len(pairs) == 100
        # First 10 pairs are insG
        assert all(p["mutation"] == "insG" for p in pairs[:10])

    def test_exp2_test_returns_5_pairs(self):
        from _common import load_config, get_experiment_pairs
        cfg = load_config()
        pairs = get_experiment_pairs(cfg, experiment=2, test_mode=True)
        assert len(pairs) == 5
        mutations = [p["mutation"] for p in pairs]
        assert mutations == ["insG", "dupA", "delinsAT", "insCCCC", "insC_pos23"]


class TestGetResultsBase:
    """Tests for get_results_base function."""

    def test_production_path(self):
        from _common import load_config, get_results_base
        cfg = load_config()
        base = get_results_base(cfg, test_mode=False)
        assert base == Path("results/simulation")

    def test_test_path(self):
        from _common import load_config, get_results_base
        cfg = load_config()
        base = get_results_base(cfg, test_mode=True)
        assert base == Path("results/simulation_test")


class TestBuildParser:
    """Tests for build_common_parser function."""

    def test_parser_has_test_flag(self):
        from _common import build_common_parser
        parser = build_common_parser("test script")
        args = parser.parse_args(["--test"])
        assert args.test is True

    def test_parser_has_workers_flag(self):
        from _common import build_common_parser
        parser = build_common_parser("test script")
        args = parser.parse_args(["--workers", "8"])
        assert args.workers == 8

    def test_parser_has_experiment_flag(self):
        from _common import build_common_parser
        parser = build_common_parser("test script")
        args = parser.parse_args(["--experiment", "1"])
        assert args.experiment == "1"

    def test_parser_defaults(self):
        from _common import build_common_parser
        parser = build_common_parser("test script")
        args = parser.parse_args([])
        assert args.test is False
        assert args.experiment == "all"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/bernt-popp/development/vntyper-analyses && python -m pytest tests/simulation/test_common.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named '_common'`

- [ ] **Step 3: Implement _common.py**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/bernt-popp/development/vntyper-analyses && python -m pytest tests/simulation/test_common.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/simulation/_common.py tests/simulation/test_common.py
git commit -m "feat: add shared simulation utilities with config loading and CLI helpers"
```

---

## Chunk 2: Script 01 — MucOneUp Paired Simulation

### Task 4: Implement 01_simulate.py

**Files:**
- Create: `scripts/simulation/01_simulate.py`

- [ ] **Step 1: Write 01_simulate.py**

```python
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
```

- [ ] **Step 2: Verify script loads without errors**

Run: `cd /home/bernt-popp/development/vntyper-analyses && python -c "import sys; sys.path.insert(0, 'scripts/simulation'); import importlib; importlib.import_module('01_simulate')"`
Expected: No errors (actual execution requires MucOneUp installed)

- [ ] **Step 3: Commit**

```bash
git add scripts/simulation/01_simulate.py
git commit -m "feat: add 01_simulate.py for MucOneUp paired simulation"
```

---

## Chunk 3: Scripts 02-04 — VNtyper and Downsampling

### Task 5: Implement 02_run_vntyper.py

**Files:**
- Create: `scripts/simulation/02_run_vntyper.py`

- [ ] **Step 1: Write 02_run_vntyper.py**

```python
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
    workers = get_workers(cfg, args)
    results_base = get_results_base(cfg, test_mode)
    experiments = get_experiments_to_run(args)
    reference = cfg["vntyper"]["reference_assembly"]
    timeout = cfg["vntyper"]["timeout_seconds"]

    logger = setup_logging("02_run_vntyper")
    logger.info(f"Mode: {'TEST' if test_mode else 'PRODUCTION'}, workers={workers}")

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
                bam = muconeup_dir / pair_name / f"{pair_name}.001.{condition}.simulated_reads.bam"
                out = vntyper_dir / pair_name / ("normal" if condition == "normal" else "mutated")
                tasks.append((bam, out))

        completed = 0
        failed = []

        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {}
            for bam, out in tasks:
                fut = executor.submit(run_vntyper_on_bam, bam, out, reference, timeout)
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
```

- [ ] **Step 2: Commit**

```bash
git add scripts/simulation/02_run_vntyper.py
git commit -m "feat: add 02_run_vntyper.py for VNtyper on full-coverage BAMs"
```

### Task 6: Implement 03_downsample.py

**Files:**
- Create: `scripts/simulation/03_downsample.py`

- [ ] **Step 1: Write 03_downsample.py**

```python
#!/usr/bin/env python3
"""
03_downsample.py — Downsample all BAMs from experiments 1+2 to coverage fractions.

Uses samtools view -s with seed-based sampling for reproducibility.
Input BAMs are read from experiment{1,2}/muconeup/pair_*/.
Output goes to experiment3_coverage/downsampled/pair_*/.

Usage:
    python scripts/simulation/03_downsample.py [--test] [--workers 16] [--experiment {1,2,all}]
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


def downsample_bam(input_bam: Path, output_bam: Path,
                   samtools_arg: str) -> dict:
    """Downsample a single BAM to a fraction using samtools."""
    if output_bam.exists():
        return {"bam": output_bam.name, "status": "skipped", "time": 0.0}

    if not input_bam.exists():
        return {"bam": output_bam.name, "status": "missing_input", "time": 0.0}

    output_bam.parent.mkdir(parents=True, exist_ok=True)
    start = time.time()

    # samtools view -b -s {seed}.{fraction}
    cmd_view = [
        "samtools", "view", "-b", "-s", samtools_arg,
        str(input_bam), "-o", str(output_bam),
    ]
    result = subprocess.run(cmd_view, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        return {"bam": output_bam.name, "status": "fail_view",
                "error": result.stderr[:300], "time": time.time() - start}

    # Index
    cmd_index = ["samtools", "index", str(output_bam)]
    result = subprocess.run(cmd_index, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        return {"bam": output_bam.name, "status": "fail_index",
                "error": result.stderr[:300], "time": time.time() - start}

    return {"bam": output_bam.name, "status": "success",
            "time": time.time() - start}


def main():
    parser = build_common_parser("Downsample BAMs for coverage titration")
    args = parser.parse_args()
    cfg = load_config()

    test_mode = args.test
    workers = get_workers(cfg, args)
    results_base = get_results_base(cfg, test_mode)
    experiments = get_experiments_to_run(args)
    fractions = cfg["experiment3"]["fractions"]
    exp3_dir_name = cfg["experiment3"]["dir_name"]

    logger = setup_logging("03_downsample")
    logger.info(f"Mode: {'TEST' if test_mode else 'PRODUCTION'}, workers={workers}")

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
                    f"{pair_name}.001.{condition}.simulated_reads.bam"
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
            fut = executor.submit(downsample_bam, input_bam, output_bam, samtools_arg)
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
```

- [ ] **Step 2: Commit**

```bash
git add scripts/simulation/03_downsample.py
git commit -m "feat: add 03_downsample.py for coverage titration downsampling"
```

### Task 7: Implement 04_run_vntyper_downsampled.py

**Files:**
- Create: `scripts/simulation/04_run_vntyper_downsampled.py`

- [ ] **Step 1: Write 04_run_vntyper_downsampled.py**

```python
#!/usr/bin/env python3
"""
04_run_vntyper_downsampled.py — Run VNtyper on all downsampled BAMs.

Usage:
    python scripts/simulation/04_run_vntyper_downsampled.py [--test] [--workers 16] [--experiment {1,2,all}]
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
    parser = build_common_parser("Run VNtyper on downsampled BAMs")
    args = parser.parse_args()
    cfg = load_config()

    test_mode = args.test
    workers = get_workers(cfg, args)
    results_base = get_results_base(cfg, test_mode)
    experiments = get_experiments_to_run(args)
    reference = cfg["vntyper"]["reference_assembly"]
    timeout = cfg["vntyper"]["timeout_seconds"]
    fractions = cfg["experiment3"]["fractions"]
    exp3_dir_name = cfg["experiment3"]["dir_name"]

    logger = setup_logging("04_run_vntyper_downsampled")
    logger.info(f"Mode: {'TEST' if test_mode else 'PRODUCTION'}, workers={workers}")

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
            fut = executor.submit(run_vntyper_on_bam, bam, out, reference, timeout)
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
```

- [ ] **Step 2: Commit**

```bash
git add scripts/simulation/04_run_vntyper_downsampled.py
git commit -m "feat: add 04_run_vntyper_downsampled.py for VNtyper on downsampled BAMs"
```

---

## Chunk 4: Scripts 05-06 — Ground Truth and VNtyper Parsing

### Task 8: Implement 05_create_ground_truth.py

**Files:**
- Create: `scripts/simulation/05_create_ground_truth.py`
- Test: `tests/simulation/test_ground_truth.py`

- [ ] **Step 1: Write failing tests for ground truth parsing**

```python
# tests/simulation/test_ground_truth.py
"""Tests for ground truth extraction logic."""

import pytest
import json
import tempfile
from pathlib import Path

import sys
SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts" / "simulation"
sys.path.insert(0, str(SCRIPTS_DIR))


class TestParseSimulationStats:
    """Tests for parsing simulation_stats.json files."""

    def test_parse_normal_sample(self, tmp_path):
        from importlib import import_module
        mod = import_module("05_create_ground_truth")

        stats = {
            "seed": 3000,
            "mutation_name": "normal",
            "haplotype_1": {
                "length": 55,
                "chain": "1-2-3-4-5-A-B-C-D-E-6p-7-8-9"
            },
            "haplotype_2": {
                "length": 62,
                "chain": "1-2-3-4-5-F-G-H-I-J-K-6p-7-8-9"
            },
        }
        stats_file = tmp_path / "pair_3000.001.normal.simulation_stats.json"
        stats_file.write_text(json.dumps(stats))

        row = mod.parse_simulation_stats(stats_file)
        assert row["seed"] == 3000
        assert row["mutation"] == "normal"
        assert row["hap1_length"] == 55
        assert row["hap2_length"] == 62

    def test_parse_mutated_sample(self, tmp_path):
        from importlib import import_module
        mod = import_module("05_create_ground_truth")

        stats = {
            "seed": 3000,
            "mutation_name": "dupC",
            "haplotype_1": {
                "length": 55,
                "chain": "1-2-3-4-5-A-B-C-D-E-6p-7-8-9"
            },
            "haplotype_2": {
                "length": 62,
                "chain": "1-2-3-4-5-F-G-H-I-J-K-6p-7-8-9"
            },
            "mutation_repeat_position": 3,
            "mutation_repeat_type": "X",
        }
        stats_file = tmp_path / "pair_3000.001.mut.simulation_stats.json"
        stats_file.write_text(json.dumps(stats))

        row = mod.parse_simulation_stats(stats_file)
        assert row["mutation"] == "dupC"
        assert row["mutation_repeat_position"] == 3
        assert row["mutation_repeat_type"] == "X"


class TestParseVntrStructure:
    """Tests for parsing vntr_structure.txt files."""

    def test_parse_structure_file(self, tmp_path):
        from importlib import import_module
        mod = import_module("05_create_ground_truth")

        content = "haplotype_1\t1-2-3-4-5-A-B-C-6p-7-8-9\nhaplotype_2\t1-2-3-4-5-D-E-F-G-6p-7-8-9\n"
        struct_file = tmp_path / "pair_3000.001.vntr_structure.txt"
        struct_file.write_text(content)

        hap1_chain, hap2_chain = mod.parse_vntr_structure(struct_file)
        assert "A-B-C" in hap1_chain
        assert "D-E-F-G" in hap2_chain
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/bernt-popp/development/vntyper-analyses && python -m pytest tests/simulation/test_ground_truth.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Implement 05_create_ground_truth.py**

```python
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
    """Parse a simulation_stats.json file into a ground truth row."""
    with open(stats_file) as f:
        stats = json.load(f)

    row = {
        "seed": stats.get("seed"),
        "mutation": stats.get("mutation_name", "normal"),
        "hap1_length": stats.get("haplotype_1", {}).get("length"),
        "hap2_length": stats.get("haplotype_2", {}).get("length"),
        "hap1_chain": stats.get("haplotype_1", {}).get("chain"),
        "hap2_chain": stats.get("haplotype_2", {}).get("chain"),
        "mutation_repeat_position": stats.get("mutation_repeat_position"),
        "mutation_repeat_type": stats.get("mutation_repeat_type"),
    }
    if row["hap1_length"] is not None and row["hap2_length"] is not None:
        row["total_length"] = row["hap1_length"] + row["hap2_length"]
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/bernt-popp/development/vntyper-analyses && python -m pytest tests/simulation/test_ground_truth.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/simulation/05_create_ground_truth.py tests/simulation/test_ground_truth.py
git commit -m "feat: add 05_create_ground_truth.py with ground truth extraction from simulation metadata"
```

### Task 9: Implement 06_parse_vntyper_results.py

**Files:**
- Create: `scripts/simulation/06_parse_vntyper_results.py`
- Test: `tests/simulation/test_parse_vntyper.py`

- [ ] **Step 1: Write failing tests for VNtyper output parsing**

```python
# tests/simulation/test_parse_vntyper.py
"""Tests for VNtyper result parsing logic."""

import pytest
import json
import tempfile
from pathlib import Path

import sys
SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts" / "simulation"
sys.path.insert(0, str(SCRIPTS_DIR))


class TestParseKestrelResult:
    """Tests for parsing kestrel_result.tsv."""

    def test_parse_positive_result(self, tmp_path):
        from importlib import import_module
        mod = import_module("06_parse_vntyper_results")

        # Create a minimal kestrel_result.tsv with a positive call
        tsv_content = (
            "CHROM\tPOS\tREF\tALT\tVariant_Type\tAllele_Change\t"
            "Confidence\tDepth_Score\tHaplo_Count\tFlag\n"
            "chr1\t155192276\tG\tGC\tFrameshift\tc.27dupC\t"
            "High_Precision\t0.95\t2\tNot flagged\n"
        )
        tsv_file = tmp_path / "kestrel_result.tsv"
        tsv_file.write_text(tsv_content)

        result = mod.parse_kestrel_result(tsv_file)
        assert result["kestrel_call"] == "c.27dupC"
        assert result["confidence"] == "High_Precision"
        assert result["is_frameshift"] is True

    def test_parse_negative_result(self, tmp_path):
        from importlib import import_module
        mod = import_module("06_parse_vntyper_results")

        # Empty result (header only)
        tsv_content = (
            "CHROM\tPOS\tREF\tALT\tVariant_Type\tAllele_Change\t"
            "Confidence\tDepth_Score\tHaplo_Count\tFlag\n"
        )
        tsv_file = tmp_path / "kestrel_result.tsv"
        tsv_file.write_text(tsv_content)

        result = mod.parse_kestrel_result(tsv_file)
        assert result["kestrel_call"] == ""
        assert result["confidence"] == "Negative"

    def test_parse_flagged_result(self, tmp_path):
        from importlib import import_module
        mod = import_module("06_parse_vntyper_results")

        tsv_content = (
            "CHROM\tPOS\tREF\tALT\tVariant_Type\tAllele_Change\t"
            "Confidence\tDepth_Score\tHaplo_Count\tFlag\n"
            "chr1\t155192276\tG\tGCCCC\tInsertion\tc.27_28insCCCC\t"
            "Low_Precision\t0.3\t1\tFalse_Positive_4bp_Insertion\n"
        )
        tsv_file = tmp_path / "kestrel_result.tsv"
        tsv_file.write_text(tsv_content)

        result = mod.parse_kestrel_result(tsv_file)
        assert "False_Positive" in result["flag"]


class TestParsePipelineSummary:
    """Tests for parsing pipeline_summary.json."""

    def test_extract_coverage_from_summary(self, tmp_path):
        from importlib import import_module
        mod = import_module("06_parse_vntyper_results")

        summary = {
            "steps": [
                {
                    "step": "Coverage Calculation",
                    "parsed_result": {
                        "data": [{"mean": 145.2, "median": 142.0, "stdev": 20.1}]
                    }
                }
            ]
        }
        summary_file = tmp_path / "pipeline_summary.json"
        summary_file.write_text(json.dumps(summary))

        cov = mod.extract_coverage(summary_file)
        assert cov["vntr_coverage_mean"] == pytest.approx(145.2)
        assert cov["vntr_coverage_median"] == pytest.approx(142.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/bernt-popp/development/vntyper-analyses && python -m pytest tests/simulation/test_parse_vntyper.py -v`
Expected: FAIL

- [ ] **Step 3: Implement 06_parse_vntyper_results.py**

```python
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
    """Parse kestrel_result.tsv and return structured result dict."""
    df = pd.read_csv(tsv_file, sep="\t")

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
    variant_type = str(row.get("Variant_Type", ""))
    allele_change = str(row.get("Allele_Change", ""))

    return {
        "kestrel_call": allele_change,
        "confidence": str(row.get("Confidence", "Negative")),
        "depth_score": row.get("Depth_Score"),
        "haplo_count": row.get("Haplo_Count"),
        "flag": str(row.get("Flag", "")),
        "is_frameshift": "Frameshift" in variant_type or "frameshift" in variant_type.lower(),
    }


def extract_coverage(summary_file: Path) -> Dict:
    """Extract VNTR coverage stats from pipeline_summary.json."""
    with open(summary_file) as f:
        summary = json.load(f)

    for step in summary.get("steps", []):
        if step["step"] == "Coverage Calculation":
            data = step.get("parsed_result", {}).get("data", [])
            if data:
                cov = data[0]
                return {
                    "vntr_coverage_mean": float(cov.get("mean", 0)),
                    "vntr_coverage_median": float(cov.get("median", 0)),
                }
    return {"vntr_coverage_mean": None, "vntr_coverage_median": None}


def extract_analysis_time(summary_file: Path) -> float:
    """Extract total analysis time from pipeline_summary.json."""
    with open(summary_file) as f:
        summary = json.load(f)
    return summary.get("total_time_seconds", None)


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
                    result["coverage_fraction"] = int(frac["value"] * 100)
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/bernt-popp/development/vntyper-analyses && python -m pytest tests/simulation/test_parse_vntyper.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/simulation/06_parse_vntyper_results.py tests/simulation/test_parse_vntyper.py
git commit -m "feat: add 06_parse_vntyper_results.py for VNtyper output parsing"
```

---

## Chunk 5: Script 07 — Performance Metrics

### Task 10: Implement 07_calculate_metrics.py

**Files:**
- Create: `scripts/simulation/07_calculate_metrics.py`
- Test: `tests/simulation/test_metrics.py`

- [ ] **Step 1: Write failing tests for metrics calculation**

```python
# tests/simulation/test_metrics.py
"""Tests for performance metric calculations."""

import pytest
import pandas as pd
from pathlib import Path

import sys
SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts" / "simulation"
sys.path.insert(0, str(SCRIPTS_DIR))


class TestClassifySample:
    """Tests for sample classification (TP/TN/FP/FN)."""

    def test_true_positive(self):
        from importlib import import_module
        mod = import_module("07_calculate_metrics")

        row = {
            "condition": "mutated",
            "kestrel_call": "c.27dupC",
            "confidence": "High_Precision",
            "flag": "Not flagged",
            "is_frameshift": True,
        }
        assert mod.classify_sample(row) == "TP"

    def test_true_negative(self):
        from importlib import import_module
        mod = import_module("07_calculate_metrics")

        row = {
            "condition": "normal",
            "kestrel_call": "",
            "confidence": "Negative",
            "flag": "",
            "is_frameshift": False,
        }
        assert mod.classify_sample(row) == "TN"

    def test_false_positive(self):
        from importlib import import_module
        mod = import_module("07_calculate_metrics")

        row = {
            "condition": "normal",
            "kestrel_call": "c.27dupC",
            "confidence": "High_Precision",
            "flag": "Not flagged",
            "is_frameshift": True,
        }
        assert mod.classify_sample(row) == "FP"

    def test_false_negative(self):
        from importlib import import_module
        mod = import_module("07_calculate_metrics")

        row = {
            "condition": "mutated",
            "kestrel_call": "",
            "confidence": "Negative",
            "flag": "",
            "is_frameshift": False,
        }
        assert mod.classify_sample(row) == "FN"

    def test_flagged_positive_is_fn(self):
        """A mutated sample with only a flagged call should be FN."""
        from importlib import import_module
        mod = import_module("07_calculate_metrics")

        row = {
            "condition": "mutated",
            "kestrel_call": "c.27_28insCCCC",
            "confidence": "Low_Precision",
            "flag": "False_Positive_4bp_Insertion",
            "is_frameshift": False,
        }
        assert mod.classify_sample(row) == "FN"


class TestWilsonCI:
    """Tests for Wilson confidence interval calculation."""

    def test_perfect_sensitivity(self):
        from importlib import import_module
        mod = import_module("07_calculate_metrics")

        low, high = mod.wilson_ci(50, 50)
        assert low > 0.90
        assert high == 1.0

    def test_zero_sensitivity(self):
        from importlib import import_module
        mod = import_module("07_calculate_metrics")

        low, high = mod.wilson_ci(0, 50)
        assert low == 0.0
        assert high < 0.10

    def test_fifty_percent(self):
        from importlib import import_module
        mod = import_module("07_calculate_metrics")

        low, high = mod.wilson_ci(50, 100)
        assert low < 0.5
        assert high > 0.5

    def test_zero_total(self):
        from importlib import import_module
        mod = import_module("07_calculate_metrics")

        low, high = mod.wilson_ci(0, 0)
        assert low == 0.0
        assert high == 0.0


class TestCalculateMetrics:
    """Tests for aggregate metric calculation."""

    def test_basic_metrics(self):
        from importlib import import_module
        mod = import_module("07_calculate_metrics")

        classifications = ["TP"] * 45 + ["FN"] * 5 + ["TN"] * 50
        metrics = mod.calculate_metrics(classifications)

        assert metrics["tp"] == 45
        assert metrics["fn"] == 5
        assert metrics["tn"] == 50
        assert metrics["fp"] == 0
        assert metrics["sensitivity"] == pytest.approx(0.90)
        assert metrics["specificity"] == pytest.approx(1.0)
        assert metrics["sensitivity_ci_low"] < 0.90
        assert metrics["sensitivity_ci_high"] > 0.90
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/bernt-popp/development/vntyper-analyses && python -m pytest tests/simulation/test_metrics.py -v`
Expected: FAIL

- [ ] **Step 3: Implement 07_calculate_metrics.py**

```python
#!/usr/bin/env python3
"""
07_calculate_metrics.py — Calculate performance metrics for all experiments.

Joins ground truth with parsed VNtyper results and computes:
- Per-sample classification (TP/TN/FP/FN)
- Aggregate sensitivity, specificity, PPV, NPV, F1
- Wilson 95% confidence intervals
- Per-mutation-type breakdown (experiment 2)
- Per-coverage-fraction breakdown (experiment 3)

Usage:
    python scripts/simulation/07_calculate_metrics.py [--test]
"""

import math
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple

from _common import (
    build_common_parser,
    get_experiment_dir,
    get_experiments_to_run,
    get_results_base,
    load_config,
    setup_logging,
)


def classify_sample(row: Dict) -> str:
    """
    Classify a sample as TP, TN, FP, or FN.

    Rules:
    - TP: mutated sample, unflagged frameshift call with non-Negative confidence
    - TN: normal sample, no positive call
    - FP: normal sample, unflagged positive call
    - FN: mutated sample, no call or only flagged calls
    """
    is_mutated = row["condition"] == "mutated"
    has_call = bool(row.get("kestrel_call")) and row.get("confidence", "Negative") != "Negative"
    is_flagged = "False_Positive" in str(row.get("flag", ""))

    # A call only counts as positive if it's unflagged
    called_positive = has_call and not is_flagged

    if is_mutated:
        return "TP" if called_positive else "FN"
    else:
        return "FP" if called_positive else "TN"


def wilson_ci(successes: int, total: int, z: float = 1.96) -> Tuple[float, float]:
    """
    Wilson score confidence interval for a proportion.

    Args:
        successes: Number of successes.
        total: Total trials.
        z: Z-score for confidence level (1.96 = 95%).

    Returns:
        (lower, upper) bounds.
    """
    if total == 0:
        return 0.0, 0.0

    p = successes / total
    denominator = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total) / denominator

    lower = max(0.0, centre - margin)
    upper = min(1.0, centre + margin)
    return lower, upper


def calculate_metrics(classifications: List[str]) -> Dict:
    """Calculate aggregate metrics from a list of classifications."""
    tp = classifications.count("TP")
    tn = classifications.count("TN")
    fp = classifications.count("FP")
    fn = classifications.count("FN")

    n_positive = tp + fn
    n_negative = tn + fp

    sensitivity = tp / n_positive if n_positive > 0 else 0.0
    specificity = tn / n_negative if n_negative > 0 else 0.0
    ppv = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    npv = tn / (tn + fn) if (tn + fn) > 0 else 0.0
    f1 = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) > 0 else 0.0

    sens_ci_low, sens_ci_high = wilson_ci(tp, n_positive)
    spec_ci_low, spec_ci_high = wilson_ci(tn, n_negative)

    return {
        "n_positive": n_positive,
        "n_negative": n_negative,
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "sensitivity": sensitivity,
        "sensitivity_ci_low": sens_ci_low,
        "sensitivity_ci_high": sens_ci_high,
        "specificity": specificity,
        "specificity_ci_low": spec_ci_low,
        "specificity_ci_high": spec_ci_high,
        "ppv": ppv, "npv": npv, "f1_score": f1,
    }


def main():
    parser = build_common_parser("Calculate performance metrics")
    args = parser.parse_args()
    cfg = load_config()

    test_mode = args.test
    results_base = get_results_base(cfg, test_mode)
    experiments = get_experiments_to_run(args)
    exp3_dir_name = cfg["experiment3"]["dir_name"]

    logger = setup_logging("07_metrics")

    for exp_num in experiments:
        exp_dir_name = get_experiment_dir(cfg, exp_num)
        exp_name = cfg[f"experiment{exp_num}"]["name"]

        # Load ground truth and parsed VNtyper results
        gt_file = results_base / exp_dir_name / "ground_truth.csv"
        parsed_file = results_base / exp_dir_name / "vntyper_parsed.csv"

        if not gt_file.exists() or not parsed_file.exists():
            logger.warning(f"Missing data for experiment {exp_num}, skipping")
            continue

        gt = pd.read_csv(gt_file)
        parsed = pd.read_csv(parsed_file)

        # Join on pair_id + condition
        df = pd.merge(
            parsed, gt[["pair_id", "condition", "mutation", "hap1_length", "hap2_length", "total_length"]],
            on=["pair_id", "condition"], how="left"
        )

        # Classify each sample
        df["classification"] = df.apply(
            lambda r: classify_sample(r.to_dict()), axis=1
        )

        # Save sample-level results
        sample_output = results_base / exp_dir_name / "sample_level_results.csv"
        df.to_csv(sample_output, index=False)
        logger.info(f"Experiment {exp_num}: sample-level -> {sample_output}")

        # Aggregate metrics
        metrics_rows = []

        # Overall
        overall = calculate_metrics(df["classification"].tolist())
        overall["experiment"] = exp_name
        overall["subset"] = "all"
        metrics_rows.append(overall)

        # Per mutation type (experiment 2)
        if exp_num == 2:
            for mut_name, grp in df[df["condition"] == "mutated"].groupby("mutation"):
                # Get corresponding normals (use all normals for specificity)
                normals = df[df["condition"] == "normal"]
                combined = pd.concat([grp, normals])
                m = calculate_metrics(combined["classification"].tolist())
                # Override with mutation-specific counts
                mut_tp = grp[grp["classification"] == "TP"].shape[0]
                mut_fn = grp[grp["classification"] == "FN"].shape[0]
                m["tp"] = mut_tp
                m["fn"] = mut_fn
                m["n_positive"] = mut_tp + mut_fn
                m["sensitivity"] = mut_tp / (mut_tp + mut_fn) if (mut_tp + mut_fn) > 0 else 0.0
                m["sensitivity_ci_low"], m["sensitivity_ci_high"] = wilson_ci(mut_tp, mut_tp + mut_fn)
                m["experiment"] = exp_name
                m["subset"] = mut_name
                metrics_rows.append(m)

        metrics_df = pd.DataFrame(metrics_rows)
        metrics_output = results_base / exp_dir_name / "performance_metrics.csv"
        metrics_df.to_csv(metrics_output, index=False)
        logger.info(f"Experiment {exp_num}: metrics -> {metrics_output}")

        # Print summary
        o = overall
        logger.info(
            f"  Sensitivity: {o['sensitivity']:.1%} "
            f"({o['sensitivity_ci_low']:.1%}-{o['sensitivity_ci_high']:.1%}), "
            f"Specificity: {o['specificity']:.1%} "
            f"({o['specificity_ci_low']:.1%}-{o['specificity_ci_high']:.1%})"
        )

    # Experiment 3: coverage titration metrics
    exp3_parsed = results_base / exp3_dir_name / "vntyper_parsed.csv"
    if exp3_parsed.exists():
        df3 = pd.read_csv(exp3_parsed)

        # Need ground truth from exp 1+2
        gt_frames = []
        for exp_num in [1, 2]:
            gt_file = results_base / get_experiment_dir(cfg, exp_num) / "ground_truth.csv"
            if gt_file.exists():
                gt_frames.append(pd.read_csv(gt_file))
        if gt_frames:
            gt_all = pd.concat(gt_frames, ignore_index=True)
            df3 = pd.merge(
                df3, gt_all[["pair_id", "condition", "mutation", "hap1_length", "hap2_length"]],
                on=["pair_id", "condition"], how="left"
            )
            df3["classification"] = df3.apply(
                lambda r: classify_sample(r.to_dict()), axis=1
            )

            # Save sample-level
            df3.to_csv(results_base / exp3_dir_name / "sample_level_results.csv", index=False)

            # Metrics per source_experiment x coverage_fraction
            metrics_rows_3 = []
            for (src, frac), grp in df3.groupby(["source_experiment", "coverage_fraction"]):
                m = calculate_metrics(grp["classification"].tolist())
                m["experiment"] = "coverage"
                m["subset"] = f"{src}_ds{int(frac)}"
                metrics_rows_3.append(m)

            # Per mutation type at each fraction
            for (mut, frac), grp in df3[df3["condition"] == "mutated"].groupby(["mutation", "coverage_fraction"]):
                normals_frac = df3[(df3["condition"] == "normal") & (df3["coverage_fraction"] == frac)]
                combined = pd.concat([grp, normals_frac])
                m = calculate_metrics(combined["classification"].tolist())
                mut_tp = grp[grp["classification"] == "TP"].shape[0]
                mut_fn = grp[grp["classification"] == "FN"].shape[0]
                m["tp"] = mut_tp
                m["fn"] = mut_fn
                m["n_positive"] = mut_tp + mut_fn
                m["sensitivity"] = mut_tp / (mut_tp + mut_fn) if (mut_tp + mut_fn) > 0 else 0.0
                m["sensitivity_ci_low"], m["sensitivity_ci_high"] = wilson_ci(mut_tp, mut_tp + mut_fn)
                m["experiment"] = "coverage"
                m["subset"] = f"{mut}_ds{int(frac)}"
                metrics_rows_3.append(m)

            metrics_df_3 = pd.DataFrame(metrics_rows_3)
            metrics_output_3 = results_base / exp3_dir_name / "performance_metrics.csv"
            metrics_df_3.to_csv(metrics_output_3, index=False)
            logger.info(f"Experiment 3: metrics -> {metrics_output_3}")

    logger.info("Metrics calculation complete.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/bernt-popp/development/vntyper-analyses && python -m pytest tests/simulation/test_metrics.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/simulation/07_calculate_metrics.py tests/simulation/test_metrics.py
git commit -m "feat: add 07_calculate_metrics.py with Wilson CI and per-mutation breakdown"
```

---

## Chunk 6: Script 08 — Summary Generation

### Task 11: Implement 08_generate_summary.py

**Files:**
- Create: `scripts/simulation/08_generate_summary.py`

- [ ] **Step 1: Write 08_generate_summary.py**

```python
#!/usr/bin/env python3
"""
08_generate_summary.py — Generate manuscript-ready outputs.

Produces:
1. YAML fragment for manuscript variables
2. Summary CSV tables
3. Supplementary figures (PNG + SVG)

Usage:
    python scripts/simulation/08_generate_summary.py [--test]
"""

import pandas as pd
import yaml
from pathlib import Path

from _common import (
    build_common_parser,
    get_experiment_dir,
    get_results_base,
    load_config,
    setup_logging,
)


def generate_yaml_fragment(results_base: Path, cfg: dict) -> dict:
    """Build the YAML variables structure from metrics CSVs."""
    fragment = {"results": {}}

    # Experiment 1: dupC
    exp1_metrics = results_base / cfg["experiment1"]["dir_name"] / "performance_metrics.csv"
    if exp1_metrics.exists():
        df = pd.read_csv(exp1_metrics)
        overall = df[df["subset"] == "all"].iloc[0]
        fragment["results"]["simulation_dupC"] = {
            "n_pairs": cfg["experiment1"]["n_pairs"],
            **{k: _yaml_val(overall[k]) for k in [
                "tp", "tn", "fp", "fn",
                "sensitivity", "sensitivity_ci_low", "sensitivity_ci_high",
                "specificity", "specificity_ci_low", "specificity_ci_high",
                "ppv", "npv", "f1_score",
            ]},
        }

    # Experiment 2: atypical
    exp2_metrics = results_base / cfg["experiment2"]["dir_name"] / "performance_metrics.csv"
    if exp2_metrics.exists():
        df = pd.read_csv(exp2_metrics)
        overall = df[df["subset"] == "all"].iloc[0]
        per_mut = {}
        for _, row in df[df["subset"] != "all"].iterrows():
            per_mut[row["subset"]] = {
                "n": int(row["n_positive"]),
                "tp": int(row["tp"]), "fn": int(row["fn"]),
                "sensitivity": round(row["sensitivity"], 4),
                "sensitivity_ci_low": round(row["sensitivity_ci_low"], 4),
                "sensitivity_ci_high": round(row["sensitivity_ci_high"], 4),
            }
        fragment["results"]["simulation_atypical"] = {
            "n_pairs": cfg["experiment2"]["n_pairs"],
            **{k: _yaml_val(overall[k]) for k in [
                "tp", "tn", "fp", "fn",
                "sensitivity", "sensitivity_ci_low", "sensitivity_ci_high",
                "specificity", "specificity_ci_low", "specificity_ci_high",
                "ppv", "npv", "f1_score",
            ]},
            "per_mutation": per_mut,
        }

    # Experiment 3: coverage
    exp3_metrics = results_base / cfg["experiment3"]["dir_name"] / "performance_metrics.csv"
    if exp3_metrics.exists():
        df = pd.read_csv(exp3_metrics)
        cov_data = {"fractions": [100, 50, 25, 12.5, 6.25]}

        for src in ["dupC", "atypical"]:
            src_data = {}
            for _, row in df[df["subset"].str.startswith(f"{src}_ds")].iterrows():
                label = row["subset"].replace(f"{src}_", "")
                src_data[label] = {
                    "sensitivity": round(row["sensitivity"], 4),
                    "specificity": round(row["specificity"], 4),
                }
            cov_data[src] = src_data

        fragment["results"]["simulation_coverage"] = cov_data

    return fragment


def _yaml_val(v):
    """Convert numpy/pandas types to Python native for YAML serialization."""
    if pd.isna(v):
        return None
    if isinstance(v, (int, float)):
        return round(float(v), 4) if isinstance(v, float) else int(v)
    try:
        return round(float(v), 4)
    except (ValueError, TypeError):
        return v


def generate_tables(results_base: Path, cfg: dict, logger):
    """Generate summary CSV tables."""
    tables_dir = results_base / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    # Table: Exp 1 performance
    exp1_metrics = results_base / cfg["experiment1"]["dir_name"] / "performance_metrics.csv"
    if exp1_metrics.exists():
        df = pd.read_csv(exp1_metrics)
        df[df["subset"] == "all"].to_csv(tables_dir / "table_exp1_performance.csv", index=False)
        logger.info(f"  table_exp1_performance.csv")

    # Table: Exp 2 performance + per-mutation
    exp2_metrics = results_base / cfg["experiment2"]["dir_name"] / "performance_metrics.csv"
    if exp2_metrics.exists():
        df = pd.read_csv(exp2_metrics)
        df[df["subset"] == "all"].to_csv(tables_dir / "table_exp2_performance.csv", index=False)
        df[df["subset"] != "all"].to_csv(tables_dir / "table_exp2_per_mutation.csv", index=False)
        logger.info(f"  table_exp2_performance.csv, table_exp2_per_mutation.csv")

    # Table: Exp 3 coverage curve + per-mutation coverage
    exp3_metrics = results_base / cfg["experiment3"]["dir_name"] / "performance_metrics.csv"
    if exp3_metrics.exists():
        df = pd.read_csv(exp3_metrics)
        # Coverage curve: rows like dupC_ds50, atypical_ds25
        cov_rows = df[df["subset"].str.match(r"^(dupC|atypical)_ds\d+$")]
        cov_rows.to_csv(tables_dir / "table_exp3_coverage_curve.csv", index=False)
        # Per-mutation coverage: rows like insG_ds50
        mut_cov_rows = df[~df["subset"].str.match(r"^(dupC|atypical)_ds\d+$")]
        if len(mut_cov_rows) > 0:
            mut_cov_rows.to_csv(tables_dir / "table_exp3_per_mutation_coverage.csv", index=False)
        logger.info(f"  table_exp3_coverage_curve.csv")

    # Table: False negatives and false positives
    fn_frames = []
    fp_frames = []
    for exp_num in [1, 2]:
        exp_dir_name = get_experiment_dir(cfg, exp_num)
        sl_file = results_base / exp_dir_name / "sample_level_results.csv"
        if sl_file.exists():
            df = pd.read_csv(sl_file)
            fn_df = df[df["classification"] == "FN"]
            if len(fn_df) > 0:
                fn_frames.append(fn_df)
            fp_df = df[df["classification"] == "FP"]
            if len(fp_df) > 0:
                fp_frames.append(fp_df)

    if fn_frames:
        fn_all = pd.concat(fn_frames, ignore_index=True)
        fn_all.to_csv(tables_dir / "table_false_negatives.csv", index=False)
        logger.info(f"  table_false_negatives.csv ({len(fn_all)} FNs)")

    if fp_frames:
        fp_all = pd.concat(fp_frames, ignore_index=True)
        fp_all.to_csv(tables_dir / "table_false_positives.csv", index=False)
        logger.info(f"  table_false_positives.csv ({len(fp_all)} FPs)")

    # Combined overview table
    all_metrics = []
    for exp_num in [1, 2]:
        exp_dir_name = get_experiment_dir(cfg, exp_num)
        mf = results_base / exp_dir_name / "performance_metrics.csv"
        if mf.exists():
            all_metrics.append(pd.read_csv(mf))
    exp3_mf = results_base / cfg["experiment3"]["dir_name"] / "performance_metrics.csv"
    if exp3_mf.exists():
        all_metrics.append(pd.read_csv(exp3_mf))
    if all_metrics:
        combined = pd.concat(all_metrics, ignore_index=True)
        combined.to_csv(tables_dir / "table_combined_overview.csv", index=False)
        logger.info(f"  table_combined_overview.csv")


def generate_figures(results_base: Path, cfg: dict, logger):
    """Generate supplementary figures."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    figures_dir = results_base / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)

    # Figure 1: Coverage-sensitivity curve
    exp3_metrics = results_base / cfg["experiment3"]["dir_name"] / "performance_metrics.csv"
    if exp3_metrics.exists():
        df = pd.read_csv(exp3_metrics)
        cov_df = df[df["subset"].str.match(r"^(dupC|atypical)_ds\d+$")].copy()
        if len(cov_df) > 0:
            cov_df["source"] = cov_df["subset"].str.extract(r"^(\w+)_ds")[0]
            cov_df["fraction"] = cov_df["subset"].str.extract(r"_ds(\d+)$")[0].astype(int)

            fig, ax = plt.subplots(figsize=(8, 5))
            for src, grp in cov_df.groupby("source"):
                grp = grp.sort_values("fraction", ascending=False)
                ax.plot(grp["fraction"], grp["sensitivity"], "o-", label=src, linewidth=2)
                ax.fill_between(
                    grp["fraction"],
                    grp["sensitivity_ci_low"],
                    grp["sensitivity_ci_high"],
                    alpha=0.2,
                )
            ax.set_xlabel("Coverage fraction (%)")
            ax.set_ylabel("Sensitivity")
            ax.set_title("VNtyper Sensitivity vs Coverage Depth")
            ax.legend()
            ax.set_ylim(0, 1.05)
            ax.invert_xaxis()
            plt.tight_layout()
            for ext in ["png", "svg"]:
                fig.savefig(figures_dir / f"fig_coverage_sensitivity_curve.{ext}", dpi=300)
            plt.close(fig)
            logger.info("  fig_coverage_sensitivity_curve")

    # Figure 2: Per-mutation sensitivity bar chart
    exp2_metrics = results_base / cfg["experiment2"]["dir_name"] / "performance_metrics.csv"
    if exp2_metrics.exists():
        df = pd.read_csv(exp2_metrics)
        per_mut = df[df["subset"] != "all"].copy()
        if len(per_mut) > 0:
            fig, ax = plt.subplots(figsize=(10, 5))
            per_mut = per_mut.sort_values("sensitivity", ascending=False)
            bars = ax.bar(per_mut["subset"], per_mut["sensitivity"], color="steelblue")
            ax.errorbar(
                per_mut["subset"], per_mut["sensitivity"],
                yerr=[
                    per_mut["sensitivity"] - per_mut["sensitivity_ci_low"],
                    per_mut["sensitivity_ci_high"] - per_mut["sensitivity"],
                ],
                fmt="none", color="black", capsize=3,
            )
            ax.set_ylabel("Sensitivity")
            ax.set_title("VNtyper Sensitivity by Mutation Type (Full Coverage)")
            ax.set_ylim(0, 1.05)
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            for ext in ["png", "svg"]:
                fig.savefig(figures_dir / f"fig_per_mutation_sensitivity.{ext}", dpi=300)
            plt.close(fig)
            logger.info("  fig_per_mutation_sensitivity")

    # Figure 3: Per-mutation x coverage heatmap
    if exp3_metrics.exists():
        df = pd.read_csv(exp3_metrics)
        # Filter mutation-specific rows (not dupC_ds* or atypical_ds*)
        mut_cov = df[~df["subset"].str.match(r"^(dupC|atypical|all)")].copy()
        if len(mut_cov) > 0:
            mut_cov["mutation"] = mut_cov["subset"].str.extract(r"^(.+?)_ds")[0]
            mut_cov["fraction"] = mut_cov["subset"].str.extract(r"_ds(\d+)$")[0].astype(int)
            pivot = mut_cov.pivot_table(
                values="sensitivity", index="mutation", columns="fraction"
            )
            if not pivot.empty:
                # Sort columns descending
                pivot = pivot[sorted(pivot.columns, reverse=True)]
                fig, ax = plt.subplots(figsize=(8, 6))
                sns.heatmap(
                    pivot, annot=True, fmt=".2f", cmap="YlOrRd_r",
                    vmin=0, vmax=1, ax=ax
                )
                ax.set_title("Sensitivity: Mutation Type x Coverage Fraction")
                ax.set_xlabel("Coverage fraction (%)")
                plt.tight_layout()
                for ext in ["png", "svg"]:
                    fig.savefig(figures_dir / f"fig_per_mutation_coverage_heatmap.{ext}", dpi=300)
                plt.close(fig)
                logger.info("  fig_per_mutation_coverage_heatmap")

    # Figure 4: VNTR length vs detection
    for exp_num in [1, 2]:
        exp_dir_name = get_experiment_dir(cfg, exp_num)
        sl_file = results_base / exp_dir_name / "sample_level_results.csv"
        if sl_file.exists():
            df = pd.read_csv(sl_file)
            mutated = df[df["condition"] == "mutated"].copy()
            if len(mutated) > 0 and "total_length" in mutated.columns:
                fig, ax = plt.subplots(figsize=(8, 5))
                colors = {"TP": "green", "FN": "red"}
                for cls in ["TP", "FN"]:
                    subset = mutated[mutated["classification"] == cls]
                    if len(subset) > 0:
                        ax.scatter(
                            subset["total_length"], [1 if cls == "TP" else 0] * len(subset),
                            label=cls, alpha=0.6, color=colors[cls], s=30,
                        )
                ax.set_xlabel("Total VNTR length (repeats)")
                ax.set_ylabel("Detection outcome")
                ax.set_yticks([0, 1])
                ax.set_yticklabels(["FN", "TP"])
                ax.set_title(f"VNTR Length vs Detection (Experiment {exp_num})")
                ax.legend()
                plt.tight_layout()
                exp_label = cfg[f"experiment{exp_num}"]["name"]
                for ext in ["png", "svg"]:
                    fig.savefig(
                        figures_dir / f"fig_vntr_length_vs_detection_{exp_label}.{ext}",
                        dpi=300,
                    )
                plt.close(fig)
                logger.info(f"  fig_vntr_length_vs_detection_{exp_label}")


def main():
    parser = build_common_parser("Generate summary tables, figures, and YAML")
    args = parser.parse_args()
    cfg = load_config()

    test_mode = args.test
    results_base = get_results_base(cfg, test_mode)

    logger = setup_logging("08_summary")

    # 1. YAML fragment
    logger.info("Generating YAML fragment...")
    fragment = generate_yaml_fragment(results_base, cfg)
    yaml_output = results_base / "variables_fragment.yml"
    yaml_output.parent.mkdir(parents=True, exist_ok=True)
    with open(yaml_output, "w") as f:
        yaml.dump(fragment, f, default_flow_style=False, sort_keys=False)
    logger.info(f"  -> {yaml_output}")

    # 2. Summary tables
    logger.info("Generating summary tables...")
    generate_tables(results_base, cfg, logger)

    # 3. Figures
    logger.info("Generating figures...")
    generate_figures(results_base, cfg, logger)

    logger.info("Summary generation complete.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify script loads without errors**

Run: `cd /home/bernt-popp/development/vntyper-analyses && python -c "import sys; sys.path.insert(0, 'scripts/simulation'); import importlib; importlib.import_module('08_generate_summary')"`
Expected: No import errors

- [ ] **Step 3: Commit**

```bash
git add scripts/simulation/08_generate_summary.py
git commit -m "feat: add 08_generate_summary.py for manuscript tables, figures, and YAML"
```

---

## Chunk 7: Integration and Smoke Test Validation

### Task 12: Add scripts/simulation/README.md

**Files:**
- Create: `scripts/simulation/README.md`

- [ ] **Step 1: Write README documenting the pipeline**

```markdown
# Simulation Pipeline

Scripts for running the MUC1 VNTR simulation benchmark (3 experiments, 2,000 VNtyper runs).

## Prerequisites

```bash
muconeup --version   # 0.28.1
vntyper --version    # 2.0.0-alpha.16
samtools --version
pip install pandas numpy scipy matplotlib seaborn pyyaml
```

## Quick start (smoke test)

```bash
cd /path/to/vntyper-analyses
python scripts/simulation/01_simulate.py --test --workers 4
python scripts/simulation/02_run_vntyper.py --test --workers 4
python scripts/simulation/03_downsample.py --test --workers 4
python scripts/simulation/04_run_vntyper_downsampled.py --test --workers 4
python scripts/simulation/05_create_ground_truth.py --test
python scripts/simulation/06_parse_vntyper_results.py --test
python scripts/simulation/07_calculate_metrics.py --test
python scripts/simulation/08_generate_summary.py --test
```

## Production run

```bash
python scripts/simulation/01_simulate.py --workers 16        # ~4h
python scripts/simulation/02_run_vntyper.py --workers 16     # ~3h
python scripts/simulation/03_downsample.py --workers 16      # ~30min
python scripts/simulation/04_run_vntyper_downsampled.py --workers 16  # ~12h
python scripts/simulation/05_create_ground_truth.py          # seconds
python scripts/simulation/06_parse_vntyper_results.py        # seconds
python scripts/simulation/07_calculate_metrics.py            # seconds
python scripts/simulation/08_generate_summary.py             # seconds
```

## Common flags

| Flag | Description |
|------|-------------|
| `--test` | Smoke-test mode (5+5 pairs) |
| `--workers N` | Parallel workers (default: 16 production, 4 test) |
| `--experiment {1,2,all}` | Run specific experiment only |

## Configuration

All parameters are in `config.yml`. Edit this file to change seeds, coverage, VNTR distributions, etc.

## Output

Results go to `results/simulation/` (production) or `results/simulation_test/` (smoke test).
```

- [ ] **Step 2: Commit**

```bash
git add scripts/simulation/README.md
git commit -m "docs: add simulation pipeline README"
```

### Task 13: Run all unit tests

- [ ] **Step 1: Run the full test suite**

Run: `cd /home/bernt-popp/development/vntyper-analyses && python -m pytest tests/simulation/ -v`
Expected: All tests PASS

- [ ] **Step 2: Fix any failures, re-run, and commit fixes if needed**

### Task 14: Validate end-to-end (dry import check)

- [ ] **Step 1: Verify all scripts import cleanly**

```bash
cd /home/bernt-popp/development/vntyper-analyses
for script in scripts/simulation/0*.py; do
    echo "Checking $script..."
    python -c "
import sys, importlib
sys.path.insert(0, 'scripts/simulation')
name = '$(basename $script .py)'
importlib.import_module(name)
print(f'  OK: {name}')
"
done
```

Expected: All 8 scripts import without errors.

- [ ] **Step 2: Verify config.yml loads correctly**

```bash
cd /home/bernt-popp/development/vntyper-analyses
python -c "
import sys; sys.path.insert(0, 'scripts/simulation')
from _common import load_config, get_experiment_pairs
cfg = load_config()
p1 = get_experiment_pairs(cfg, 1, False)
p2 = get_experiment_pairs(cfg, 2, False)
print(f'Exp1: {len(p1)} pairs, seeds {p1[0][\"seed\"]}-{p1[-1][\"seed\"]}')
print(f'Exp2: {len(p2)} pairs, mutations: {set(p[\"mutation\"] for p in p2)}')
"
```

Expected:
```
Exp1: 100 pairs, seeds 3000-3099
Exp2: 100 pairs, mutations: {insG, dupA, delinsAT, insCCCC, insC_pos23, insG_pos58, insG_pos54, insA_pos54, delGCCCA, ins25bp}
```

- [ ] **Step 3: Final commit with all files**

```bash
git add -A
git status
# Verify only expected files are staged
git commit -m "feat: complete simulation pipeline (8 scripts + config + tests)

Implements the full simulation benchmark pipeline:
- 01_simulate.py: MucOneUp paired simulation
- 02_run_vntyper.py: VNtyper on full-coverage BAMs
- 03_downsample.py: Coverage titration downsampling
- 04_run_vntyper_downsampled.py: VNtyper on downsampled BAMs
- 05_create_ground_truth.py: Ground truth extraction
- 06_parse_vntyper_results.py: VNtyper output parsing
- 07_calculate_metrics.py: Performance metrics with Wilson CIs
- 08_generate_summary.py: Tables, figures, YAML for manuscript

All scripts support --test (smoke test) and --workers flags."
```
