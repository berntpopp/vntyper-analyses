# MUC1 VNTR Simulation Benchmark

Simulation pipeline for benchmarking VNtyper 2 sensitivity and specificity across 11 MUC1-VNTR frameshift mutation types and 5 coverage levels.

## Overview

Three experiments using MucOneUp-simulated paired samples (matched wild-type + mutated from identical VNTR haplotypes):

| Experiment | Pairs | Mutations | Coverage levels | VNtyper runs |
|------------|-------|-----------|-----------------|--------------|
| 1: Canonical dupC | 100 | dupC only | 1 (full) | 200 |
| 2: Atypical frameshifts | 100 | 10 published types | 1 (full) | 200 |
| 3: Coverage titration | 200 (reuses 1+2) | All from 1+2 | 5 (75%-6.25%) | 2,000 |
| **Total** | | | | **2,400** |

## Prerequisites

- **MucOneUp** v0.28.1 (`muconeup` CLI, installed in conda base env)
- **VNtyper** 2.0.1 via Docker (`saei/vntyper:latest`)
- **Python** 3.8+ with: `pandas`, `numpy`, `scipy`, `matplotlib`, `seaborn`, `pyyaml`, `openpyxl`

```bash
muconeup --version          # 0.28.1
docker run --rm saei/vntyper:latest vntyper --version  # 2.0.1
```

## Configuration

All parameters are in [`config.yml`](config.yml):

- **VNTR lengths**: Normal distribution, mean=60, min=20, max=130 repeats (Vrbacka et al. 2025)
- **Read simulation**: Illumina, 150x coverage, 250 bp fragments, Twist v2 enrichment
- **Seeds**: 3000-3099 (dupC), 4000-4099 (atypical, 10 consecutive per mutation type)
- **Workers**: 8 for MucOneUp (BWA-MEM ~5 GB/instance), 4 for VNtyper Docker, 16 for samtools

MucOneUp's `config.json` (`../MucOneUp/config.json`) provides read simulation parameters. The pipeline runs MucOneUp from its own directory to resolve relative paths.

## Pipeline

Run sequentially (each step depends on the previous):

```bash
cd /path/to/vntyper-analyses

# Step 1: Simulate 200 matched pairs (~50 min/experiment, 8 workers)
python scripts/simulation/01_simulate.py --experiment 1
python scripts/simulation/01_simulate.py --experiment 2

# Step 2: VNtyper on 400 full-coverage BAMs (~12 min, 4 Docker workers)
python scripts/simulation/02_run_vntyper.py

# Step 3: Downsample 400 BAMs to 5 fractions (~6 min, 16 workers)
python scripts/simulation/03_downsample.py

# Step 4: VNtyper on 2,000 downsampled BAMs (~48 min, 4 Docker workers)
python scripts/simulation/04_run_vntyper_downsampled.py

# Steps 5-8: Analysis (seconds each)
python scripts/simulation/05_create_ground_truth.py
python scripts/simulation/06_parse_vntyper_results.py
python scripts/simulation/07_calculate_metrics.py
python scripts/simulation/08_generate_summary.py
```

**Smoke test** (5+5 pairs, ~10 min): add `--test` to all commands.

### Common flags

| Flag | Description |
|------|-------------|
| `--test` | Run on 10-pair subset (5 dupC + 5 atypical) |
| `--workers N` | Override parallel worker count |
| `--experiment {1,2,all}` | Run one experiment only |
| `--force` | Re-simulate even if BAMs exist (01_simulate only) |

### Resource requirements

| Step | CPU | RAM | Disk |
|------|-----|-----|------|
| Simulation (8 workers) | 16 cores | ~40 GB | 430 MB |
| VNtyper (4 Docker workers) | 4 cores | ~8 GB | 6 GB |
| Downsampling (16 workers) | 16 cores | ~2 GB | 530 MB |
| **Total** | | | **~7 GB** |

## Output

Production results go to `results/simulation/`, smoke test to `results/simulation_test/`.

### Tables (`results/simulation/tables/`)

| File | Description |
|------|-------------|
| `main_table_performance.*` | dupC + atypical: Sens, Spec, PPV, NPV, F1 with 95% Wilson CIs |
| `supp_table_per_mutation.*` | Sensitivity per mutation type (11 rows) |
| `supp_table_coverage_titration.*` | Sensitivity/specificity at 6 coverage fractions |
| `supp_table_mutation_coverage_matrix.*` | Mutation x coverage sensitivity grid |
| `supp_table_false_negatives.*` | FN detail: VNTR lengths, coverage, mutation info |
| `comprehensive_all_samples.*` | All 400 samples, 34 columns (simulation + VNtyper data) |

All tables are generated as both `.tsv` and `.xlsx`.

### Figures (`results/simulation/figures/`)

| File | Description |
|------|-------------|
| `fig_coverage_sensitivity_curve` | Sensitivity vs coverage fraction (dupC + atypical) |
| `fig_per_mutation_sensitivity` | Bar chart: sensitivity by mutation type (dupC highlighted) |
| `fig_per_mutation_coverage_heatmap` | Heatmap: mutation x coverage sensitivity |
| `fig_vntr_length_vs_detection` | 2x3 panel: VNTR length vs TP/FN (box + strip + Mann-Whitney) |

All figures are generated as both `.png` (300 dpi) and `.svg`.

### YAML fragment

`results/simulation/variables_fragment.yml` contains all metrics formatted for merging into the manuscript's `_variables.yml`.

## Scripts

| Script | Responsibility |
|--------|---------------|
| `_common.py` | Shared utilities: config, logging, CLI, VNtyper/samtools Docker wrappers |
| `01_simulate.py` | MucOneUp paired simulation (FASTA + Illumina reads) |
| `02_run_vntyper.py` | VNtyper normal mode on full-coverage BAMs |
| `03_downsample.py` | `samtools view -s` downsampling to coverage fractions |
| `04_run_vntyper_downsampled.py` | VNtyper on downsampled BAMs |
| `05_create_ground_truth.py` | Extract haplotype lengths and mutation info from simulation metadata |
| `06_parse_vntyper_results.py` | Parse Kestrel TSV and pipeline_summary.json into structured tables |
| `07_calculate_metrics.py` | Classify samples (TP/TN/FP/FN), compute metrics with Wilson CIs |
| `08_generate_summary.py` | Generate manuscript tables (TSV + XLSX), figures, and YAML |

## Tests

```bash
python -m pytest tests/simulation/ -v    # 31 tests
```

Unit tests cover config loading, experiment pair generation, ground truth parsing, Kestrel result parsing, sample classification, Wilson CI calculation, and aggregate metric computation.
