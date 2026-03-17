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
