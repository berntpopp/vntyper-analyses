# Simulation Experiment Plan

Plan for generating two synthetic cohorts with MucOneUp to benchmark VNtyper 2 sensitivity and specificity for the manuscript.

## Overview

Three experiments: two simulation cohorts (200 matched pairs, 400 BAMs) plus a coverage titration analysis on all simulated BAMs. All samples simulated with MucOneUp using the Twist Bioscience v2 exome enrichment profile and biologically grounded VNTR length distributions informed by Vrbacka et al. 2025 long-read data.

| Experiment | Pairs | Mutation types | Coverage levels | VNtyper runs |
|------------|-------|---------------|-----------------|-------------|
| 1: Canonical dupC | 100 | dupC only | 1 (full) | 200 |
| 2: Atypical frameshifts | 100 | 10 published types | 1 (full) | 200 |
| 3: Coverage titration | 200 (reuses Exp 1+2 BAMs) | All from Exp 1+2 | 4 (50%, 25%, 12.5%, 6.25%) | 1,600 |
| **Total VNtyper runs** | | | | **2,000** |

## VNTR length parameters

Based on Vrbacka et al. 2025 (bioRxiv 10.1101/2025.09.06.673538), who characterized 598 alleles across 300 individuals via PacBio long-read sequencing:

- Wild-type alleles: median 37-57 repeats (varies by progression group)
- Mutation-bearing alleles: median 59-69 repeats
- Each repeat unit = 60 bp

### Chosen distribution

| Parameter | Value | Justification |
|-----------|-------|---------------|
| Distribution | Normal (truncated) | Standard for population simulation |
| Mean | 60 repeats | Centre of mutant allele range; consistent with manuscript Methods text |
| SD | 15 repeats | Covers wild-type and mutant ranges within ~1 SD |
| Min | 20 repeats | Biological lower bound (Vrbacka shortest alleles) |
| Max | 130 repeats | Biological upper bound; avoids known Kestrel failure zone >165 combined |

Both haplotypes drawn independently from this distribution. The mutation is applied to haplotype 1 in positive samples. The mutation target repeat is randomized per sample.

**Note:** The manuscript Methods section already states "VNTR haplotype lengths followed a normal distribution (mean 60 repeats, SD 15)". These parameters are consistent with Vrbacka et al. 2025 and do not need updating.

## Paired simulation mode

MucOneUp's dual simulation mode (`--mutation-name normal,dupC`) generates a matched pair from the same VNTR haplotype structure in one call. This produces two FASTAs per seed:
- `{out_base}.001.normal.simulated.fa` (wild-type control)
- `{out_base}.001.mut.simulated.fa` (mutated sample)

Each FASTA is then passed to `muconeup reads illumina` to generate a BAM file. This ensures positive and negative samples share identical VNTR lengths and structure, differing only by the presence of the mutation. One seed = one matched pair = one positive BAM + one negative BAM.

## Experiment 1: Canonical dupC

### Design

- 100 matched pairs: each pair shares VNTR structure, one mutated (dupC), one wild-type
- Seeds: 3000-3099 (100 pairs)

### Parameters

| Parameter | Value |
|-----------|-------|
| Mutation | `dupC` (c.27dupC, ins C at position 27 of repeat X) |
| Mutation target | Random repeat position per sample (auto-selected from allowed repeats) |
| Enrichment profile | Twist Bioscience v2 (`data/twist_v2_hg38.bam`) |
| Read simulation | Illumina, 10,000 fixed read pairs |
| Coverage | 150x (post-hoc downsampling via `non_vntr` mode) |
| Fragment size | 250 bp mean, 35 bp SD |
| Reference assembly | hg38 |
| Flanking regions | 10 kb upstream + downstream |

### Expected outcomes

Based on muconeup-manuscript (50 pairs, similar parameters):
- Kestrel normal mode: ~94-96% sensitivity, ~100% specificity
- False negatives expected in samples with very long combined VNTR (>165 repeats)

## Experiment 2: Atypical frameshifts

### Design

- 100 matched pairs: 10 published atypical mutations, 10 pairs each, random repeat positions
- Seeds: 4000-4099 (100 pairs, 10 consecutive seeds per mutation type)

### Mutation allocation

All mutations are published and citable. Equal allocation (10 samples each) ensures each mutation type is tested with sufficient power to detect gross failures.

| Mutation | N | Operation | Repeat | Citation |
|----------|---|-----------|--------|----------|
| `insG` | 10 | ins G | Various | Olinger 2020 |
| `dupA` | 10 | ins A | Various | Olinger 2020 |
| `delinsAT` | 10 | del+ins AT | Various | Olinger 2020 |
| `insCCCC` | 10 | ins CCCC | Various | Vrbacka 2025 |
| `insC_pos23` | 10 | ins C @pos23 | Various | Vrbacka 2025 |
| `insG_pos58` | 10 | ins G @pos58 | Various | Vrbacka 2025 |
| `insG_pos54` | 10 | ins G @pos54 | Various | Vrbacka 2025 |
| `insA_pos54` | 10 | ins A @pos54 | Various | Vrbacka 2025 |
| `delGCCCA` | 10 | del GCCC | Various | Saei 2023 |
| `ins25bp` | 10 | ins 25bp | Various | Saei 2023 |

### Seed allocation

Each mutation subgroup uses consecutive seeds within its block:

| Mutation | Seeds (paired) |
|----------|---------------|
| `insG` | 4000-4009 |
| `dupA` | 4010-4019 |
| `delinsAT` | 4020-4029 |
| `insCCCC` | 4030-4039 |
| `insC_pos23` | 4040-4049 |
| `insG_pos58` | 4050-4059 |
| `insG_pos54` | 4060-4069 |
| `insA_pos54` | 4070-4079 |
| `delGCCCA` | 4080-4089 |
| `ins25bp` | 4090-4099 |

### Expected outcomes

- Sensitivity will likely vary by mutation type (some mutations produce stronger k-mer signals than others)
- Per-mutation-type sensitivity breakdown is a key manuscript result
- Atypical mutations not detectable by SNaPshot, highlighting VNtyper's unique value

## Experiment 3: Coverage titration

### Design

Downsample all 400 BAMs from experiments 1 and 2 to relative fractions of their original VNTR coverage, then rerun VNtyper to measure sensitivity and specificity as a function of coverage depth.

- **Input**: All 400 BAMs from experiments 1 and 2 (200 mutated + 200 normal)
- **Downsampling fractions**: 50%, 25%, 12.5%, 6.25% of original VNTR coverage
- **Downsampling method**: `samtools view -s {seed}.{fraction}` (seeded for reproducibility, seed=42)
- **VNtyper runs**: 400 BAMs x 4 fractions = 1,600 additional runs

### Downsampling levels

With a baseline of ~150x non-VNTR coverage, approximate resulting VNTR coverages:

| Fraction | Approx. VNTR coverage | Purpose |
|----------|----------------------|---------|
| 100% | ~150x (baseline) | Already run in Exp 1+2 |
| 50% | ~75x | Standard exome |
| 25% | ~37x | Low-coverage exome |
| 12.5% | ~19x | Minimal coverage |
| 6.25% | ~9x | Near detection limit |

Actual per-sample VNTR coverage varies with VNTR length and capture efficiency; fractions are relative to each sample's own baseline.

### Implementation

Uses VNtyper's existing downsampling infrastructure (`samtools view -s` with seed-based sampling). Per BAM:

```bash
# Downsample to 50% of reads
samtools view -b -s 42.500 \
  input.bam \
  -o input.ds50.bam
samtools index input.ds50.bam

# Run VNtyper on downsampled BAM
vntyper pipeline \
  --bam-file input.ds50.bam \
  --reference-assembly hg38 \
  --output-dir vntyper/pair_3000/mutated/ds50
```

### Expected outcomes

- Sensitivity should decrease monotonically with coverage
- Specificity should remain high (few false positives even at low coverage)
- Establishes minimum coverage recommendation for clinical use
- Atypical mutations may show steeper sensitivity drop than dupC (weaker k-mer signal)

### Analysis

- Sensitivity and specificity at each coverage fraction, for dupC and atypical separately
- Coverage-sensitivity curve (key supplementary figure)
- Per-mutation-type sensitivity at each fraction (experiment 2 subset)
- Identify inflection point: coverage below which sensitivity drops below 90%

## Shared configuration

### MucOneUp config overrides

The base config is at `../MucOneUp/config.json`. The following overrides apply to both experiments:

```yaml
read_simulation:
  simulator: illumina
  coverage: 150
  read_number: 10000
  fragment_size: 250
  fragment_sd: 35
  downsample_mode: non_vntr
  reference_assembly: hg38

vntr:
  distribution: normal
  mean_repeats: 60
  sd_repeats: 15
  min_repeats: 20
  max_repeats: 130
```

### VNtyper analysis

| Mode | Purpose | Run for |
|------|---------|---------|
| Normal (Kestrel) | Primary genotyping | All 400 samples + 1,600 downsampled |

Normal mode (default, no `--fast-mode` flag). Includes filtering for unmapped and partially mapped reads. No adVNTR cross-validation.

## Repository and tool locations

All paths are relative to this manuscript repository (`vntyper-manuscript/`). The sibling repositories share a common parent directory:

```
~/development/
├── vntyper-manuscript/          # This repo (plan lives here)
├── vntyper-analyses/            # Scripts and results (submodule of this repo)
├── MucOneUp/                    # Simulation tool (v0.28.1)
├── VNtyper/                     # Genotyping pipeline (v2.0.0-alpha.16)
└── muconeup-manuscript/         # Reference only (not used at runtime)
```

| Tool | Repo path (from manuscript) | Invocation |
|------|----------------------------|------------|
| MucOneUp v0.28.1 | `../MucOneUp/` | `muconeup` CLI (installed in base conda env) |
| MucOneUp config | `../MucOneUp/config.json` | Passed via `--config` flag |
| VNtyper 2 (v2.0.0-alpha.16) | `../VNtyper/` | `vntyper` CLI via subprocess (needs `pip install -e ../VNtyper`) |
| vntyper-analyses | `../vntyper-analyses/` | Working directory for scripts and results |
| VNtyper benchmark | `../VNtyper/tests/benchmark/benchamrk_downsample.py` | Reference for downsampling approach |

### Prerequisites

Before running, ensure both CLIs are available:

```bash
# MucOneUp (already installed in base env)
muconeup --version   # should show 0.28.1

# VNtyper (not installed by default; install in editable mode)
pip install -e ../VNtyper
vntyper --version    # should show 2.0.0-alpha.16

# samtools (needed for downsampling in Experiment 3)
samtools --version
```

### Working directory

When running scripts, the working directory is `../vntyper-analyses/`. Paths in `config.yml` and scripts use paths relative to that directory:
- MucOneUp config: `../MucOneUp/config.json`
- VNtyper CLI: `vntyper` (on PATH after pip install)
- Simulation results: `results/simulation/`

## Directory structure (in vntyper-analyses)

Scripts and results are organized within the `vntyper-analyses` repository, following its existing `results/{type}/` and `scripts/` conventions. Simulation data goes under a new `results/simulation/` top-level category.

```
vntyper-analyses/
├── results/
│   ├── screening/          # (existing clinical cohorts)
│   ├── validation/         # (existing clinical cohorts)
│   └── simulation/         # NEW
│       ├── README.md
│       ├── experiment1_dupC/
│       │   ├── README.md
│       │   ├── muconeup/
│       │   │   └── pair_3000/              # One dir per matched pair
│       │   │       ├── pair_3000.001.normal.simulated.fa
│       │   │       ├── pair_3000.001.mut.simulated.fa
│       │   │       ├── pair_3000.001.normal.simulated_reads.bam
│       │   │       ├── pair_3000.001.normal.simulated_reads.bam.bai
│       │   │       ├── pair_3000.001.mut.simulated_reads.bam
│       │   │       ├── pair_3000.001.mut.simulated_reads.bam.bai
│       │   │       ├── pair_3000.001.normal.simulation_stats.json
│       │   │       ├── pair_3000.001.mut.simulation_stats.json
│       │   │       └── pair_3000.001.vntr_structure.txt
│       │   │   # ... pair_3001/ through pair_3099/
│       │   ├── vntyper/
│       │   │   └── pair_3000/
│       │   │       ├── normal/             # VNtyper results for wild-type
│       │   │       └── mutated/            # VNtyper results for mutated
│       │   │   # ... pair_3001/ through pair_3099/
│       │   ├── ground_truth.csv
│       │   └── performance_metrics.csv
│       │
│       ├── experiment2_atypical/
│       │   ├── README.md
│       │   ├── muconeup/
│       │   │   └── pair_4000/              # insG (seeds 4000-4009)
│       │   │   # ... pair_4001/ through pair_4099/
│       │   ├── vntyper/
│       │   │   └── pair_4000/
│       │   │       ├── normal/
│       │   │       └── mutated/
│       │   │   # ... pair_4001/ through pair_4099/
│       │   ├── ground_truth.csv
│       │   └── performance_metrics.csv
│       │
│       └── experiment3_coverage/
│           ├── README.md
│           ├── downsampled/                # Downsampled BAMs
│           │   └── pair_3000/
│           │       ├── pair_3000.001.normal.ds50.bam
│           │       ├── pair_3000.001.normal.ds25.bam
│           │       ├── pair_3000.001.normal.ds12.bam
│           │       ├── pair_3000.001.normal.ds6.bam
│           │       ├── pair_3000.001.mut.ds50.bam
│           │       ├── pair_3000.001.mut.ds25.bam
│           │       ├── pair_3000.001.mut.ds12.bam
│           │       └── pair_3000.001.mut.ds6.bam
│           │   # ... all pairs from exp1 + exp2
│           ├── vntyper/
│           │   └── pair_3000/
│           │       ├── normal/
│           │       │   ├── ds50/
│           │       │   ├── ds25/
│           │       │   ├── ds12/
│           │       │   └── ds6/
│           │       └── mutated/
│           │           ├── ds50/
│           │           ├── ds25/
│           │           ├── ds12/
│           │           └── ds6/
│           │   # ... all pairs from exp1 + exp2
│           └── performance_metrics.csv
│
│       # Shared outputs (generated by scripts 05-08)
│       ├── tables/
│       │   ├── table_exp1_performance.csv
│       │   ├── table_exp2_performance.csv
│       │   ├── table_exp2_per_mutation.csv
│       │   ├── table_exp3_coverage_curve.csv
│       │   ├── table_exp3_per_mutation_coverage.csv
│       │   ├── table_false_negatives.csv
│       │   ├── table_false_positives.csv
│       │   └── table_combined_overview.csv
│       ├── figures/
│       │   ├── fig_coverage_sensitivity_curve.png
│       │   ├── fig_per_mutation_sensitivity.png
│       │   ├── fig_per_mutation_coverage_heatmap.png
│       │   └── fig_vntr_length_vs_detection.png
│       └── variables_fragment.yml
│
└── scripts/
    └── simulation/         # NEW
        ├── README.md
        ├── 01_simulate.py              # MucOneUp paired simulation (both experiments)
        ├── 02_run_vntyper.py           # VNtyper normal mode on all BAMs
        ├── 03_downsample.py            # Downsample BAMs to coverage fractions
        ├── 04_run_vntyper_downsampled.py  # VNtyper on downsampled BAMs
        ├── 05_create_ground_truth.py   # Extract ground truth from simulation metadata
        ├── 06_parse_vntyper_results.py # Parse all VNtyper outputs into structured tables
        ├── 07_calculate_metrics.py     # Sensitivity, specificity, CIs (all experiments)
        ├── 08_generate_summary.py      # Summary tables, figures, YAML for manuscript
        └── config.yml                  # All experiment parameters in one file
```

### Naming conventions

- Pair directories named by seed: `pair_{seed}` (e.g., `pair_3000`, `pair_4057`)
- Normal/mutated separation by MucOneUp filename convention (`.normal.` vs `.mut.`)
- Per-pair subdirectories contain both BAMs, FASTAs, metadata, and VNTR structure
- Ground truth and metrics as flat CSVs at experiment level

## Implementation: Python scripts

All scripts use Python with `concurrent.futures.ProcessPoolExecutor` for parallelism on 32-core workstation. Both MucOneUp and VNtyper are invoked via their CLIs using `subprocess`.

### Script 1: `01_simulate.py`

Generates all 400 samples across both experiments.

```
Usage: python scripts/simulation/01_simulate.py [--workers 16] [--experiment {1,2,all}]
```

Per pair, three CLI calls (one simulate, two reads):

```bash
PAIR_DIR=results/simulation/experiment1_dupC/muconeup/pair_3000
CONFIG=../MucOneUp/config.json

# 1. Generate matched pair (one wild-type + one mutated FASTA)
muconeup --config $CONFIG simulate \
  --out-dir $PAIR_DIR \
  --out-base pair_3000 \
  --seed 3000 \
  --mutation-name normal,dupC \
  --reference-assembly hg38 \
  --output-structure

# 2. Simulate Illumina reads for wild-type
muconeup --config $CONFIG reads illumina \
  $PAIR_DIR/pair_3000.001.normal.simulated.fa \
  --out-dir $PAIR_DIR \
  --coverage 150 \
  --threads 2

# 3. Simulate Illumina reads for mutated
muconeup --config $CONFIG reads illumina \
  $PAIR_DIR/pair_3000.001.mut.simulated.fa \
  --out-dir $PAIR_DIR \
  --coverage 150 \
  --threads 2
```

For atypical mutations, replace `dupC` with the appropriate mutation name (e.g., `normal,insG`).

Parallelism: `ProcessPoolExecutor(max_workers=16)` (each MucOneUp `reads` call uses `--threads 2` for BWA-MEM).

Estimated runtime: ~4 hours with 16 workers.

### Script 2: `02_run_vntyper.py`

Runs VNtyper 2 normal mode on all 400 BAMs.

```
Usage: python scripts/simulation/02_run_vntyper.py [--workers 16] [--experiment {1,2,all}]
```

Per pair, two VNtyper calls (one for each BAM):

```bash
PAIR_DIR=results/simulation/experiment1_dupC
SEED=3000

# Wild-type BAM
vntyper pipeline \
  --bam-file $PAIR_DIR/muconeup/pair_$SEED/pair_$SEED.001.normal.simulated_reads.bam \
  --reference-assembly hg38 \
  --output-dir $PAIR_DIR/vntyper/pair_$SEED/normal

# Mutated BAM
vntyper pipeline \
  --bam-file $PAIR_DIR/muconeup/pair_$SEED/pair_$SEED.001.mut.simulated_reads.bam \
  --reference-assembly hg38 \
  --output-dir $PAIR_DIR/vntyper/pair_$SEED/mutated
```

Estimated runtime: ~2 hours with 16 workers.

### Script 3: `03_downsample.py`

Downsamples all 400 BAMs from experiments 1 and 2 to four relative coverage fractions.

```
Usage: python scripts/simulation/03_downsample.py [--workers 16] [--experiment {1,2,all}]
```

Per BAM, four `samtools view -s` calls:

```bash
# Fraction labels: ds50 (50%), ds25 (25%), ds12 (12.5%), ds6 (6.25%)
samtools view -b -s 42.5000 input.bam -o input.ds50.bam && samtools index input.ds50.bam
samtools view -b -s 42.2500 input.bam -o input.ds25.bam && samtools index input.ds25.bam
samtools view -b -s 42.1250 input.bam -o input.ds12.bam && samtools index input.ds12.bam
samtools view -b -s 42.0625 input.bam -o input.ds6.bam  && samtools index input.ds6.bam
```

Input BAMs are read from `experiment{1,2}/muconeup/pair_*/`. Output goes to `experiment3_coverage/downsampled/pair_*/`.

Estimated runtime: ~30 min with 16 workers (samtools is fast).

### Script 4: `04_run_vntyper_downsampled.py`

Runs VNtyper normal mode on all 1,600 downsampled BAMs.

```
Usage: python scripts/simulation/04_run_vntyper_downsampled.py [--workers 16] [--experiment {1,2,all}]
```

Estimated runtime: ~8 hours with 16 workers.

### Script 5: `05_create_ground_truth.py`

Collects metadata from all `simulation_stats.json` files into structured ground truth CSVs.

```
Usage: python scripts/simulation/05_create_ground_truth.py
```

Output: one CSV per experiment in `results/simulation/experiment{N}/ground_truth.csv`

| Column | Description |
|--------|-------------|
| `pair_id` | Pair identifier (e.g., `pair_3000`) |
| `seed` | Random seed used |
| `experiment` | `dupC` or `atypical` |
| `mutation` | Mutation name (e.g., `dupC`, `insG`) or `normal` |
| `hap1_length` | Haplotype 1 repeat count |
| `hap2_length` | Haplotype 2 repeat count |
| `total_length` | Sum of both haplotypes |
| `hap1_chain` | Repeat unit chain for haplotype 1 |
| `hap2_chain` | Repeat unit chain for haplotype 2 |
| `mutation_repeat_position` | 1-based index of mutated repeat (positives only) |
| `mutation_repeat_type` | Repeat unit symbol at mutation site (e.g., `X`) |

### Script 6: `06_parse_vntyper_results.py`

Parses all VNtyper Kestrel output files (`kestrel_result.tsv`) and coverage summaries into a single structured table per experiment. Handles both full-coverage (Exp 1+2) and downsampled (Exp 3) results.

```
Usage: python scripts/simulation/06_parse_vntyper_results.py
```

Output: one CSV per experiment in `results/simulation/experiment{N}/vntyper_parsed.csv`

| Column | Description |
|--------|-------------|
| `pair_id` | Pair identifier |
| `condition` | `normal` or `mutated` |
| `coverage_fraction` | `100` (full) or `50`, `25`, `12`, `6` |
| `kestrel_call` | VNtyper genotype call (variant string or empty) |
| `confidence` | Confidence label (`High_Precision`, `High_Precision*`, `Low_Precision`, `Negative`) |
| `depth_score` | Kestrel depth score |
| `haplo_count` | Haplotype count metric |
| `flag` | Flag annotation (if any) |
| `is_frameshift` | Boolean |
| `vntr_coverage_mean` | Mean VNTR coverage from VNtyper summary |
| `vntr_coverage_median` | Median VNTR coverage |
| `analysis_time_seconds` | Runtime from pipeline log |

### Script 7: `07_calculate_metrics.py`

Joins ground truth with parsed VNtyper results and computes performance metrics.

```
Usage: python scripts/simulation/07_calculate_metrics.py
```

Classification logic:
- **TP**: mutated sample called positive (any unflagged frameshift call)
- **TN**: normal sample called negative
- **FP**: normal sample called positive
- **FN**: mutated sample called negative or only flagged calls

Output files per experiment:

**`results/simulation/experiment{N}/sample_level_results.csv`** -- per-sample classification:

| Column | Description |
|--------|-------------|
| `pair_id` | Pair identifier |
| `condition` | `normal` or `mutated` |
| `coverage_fraction` | Coverage level |
| `mutation` | Ground truth mutation |
| `hap1_length`, `hap2_length` | VNTR lengths |
| `kestrel_call` | VNtyper call |
| `confidence` | Confidence tier |
| `classification` | `TP`, `TN`, `FP`, or `FN` |
| `vntr_coverage_mean` | Observed VNTR coverage |

**`results/simulation/experiment{N}/performance_metrics.csv`** -- aggregated metrics:

| Column | Description |
|--------|-------------|
| `experiment` | Experiment name |
| `subset` | `all`, mutation type, or coverage fraction |
| `n_positive` | Number of positive samples |
| `n_negative` | Number of negative samples |
| `tp`, `tn`, `fp`, `fn` | Counts |
| `sensitivity` | TP / (TP + FN) |
| `sensitivity_ci_low`, `sensitivity_ci_high` | 95% Wilson CI |
| `specificity` | TN / (TN + FP) |
| `specificity_ci_low`, `specificity_ci_high` | 95% Wilson CI |
| `ppv`, `npv` | Predictive values |
| `f1_score` | Harmonic mean of precision and recall |

Rows in `performance_metrics.csv`:
- Experiment 1: one row for `all`
- Experiment 2: one row for `all` + one row per mutation type (10 rows)
- Experiment 3: one row per coverage fraction per experiment source (dupC x 4 + atypical x 4 = 8 rows), plus per-mutation-type at each fraction

### Script 8: `08_generate_summary.py`

Generates manuscript-ready outputs from the metrics and parsed results.

```
Usage: python scripts/simulation/08_generate_summary.py
```

Output:

**1. YAML fragment** (`results/simulation/variables_fragment.yml`):
Ready to merge into `manuscript/_variables.yml` via `scripts/generate_variables.py`.

```yaml
results:
  simulation_dupC:
    n_pairs: 100
    tp: <value>
    tn: <value>
    fp: <value>
    fn: <value>
    sensitivity: <value>
    sensitivity_ci_low: <value>
    sensitivity_ci_high: <value>
    specificity: <value>
    specificity_ci_low: <value>
    specificity_ci_high: <value>
    ppv: <value>
    npv: <value>
    f1_score: <value>

  simulation_atypical:
    n_pairs: 100
    # aggregate metrics same as above
    per_mutation:
      insG: { n: 10, tp: <>, fn: <>, sensitivity: <>, sensitivity_ci_low: <>, sensitivity_ci_high: <> }
      dupA: { ... }
      # ... all 10 mutation types

  simulation_coverage:
    fractions: [100, 50, 25, 12.5, 6.25]
    dupC:
      ds100: { sensitivity: <>, specificity: <> }
      ds50:  { sensitivity: <>, specificity: <> }
      ds25:  { sensitivity: <>, specificity: <> }
      ds12:  { sensitivity: <>, specificity: <> }
      ds6:   { sensitivity: <>, specificity: <> }
    atypical:
      ds100: { sensitivity: <>, specificity: <> }
      # ...
```

**2. Summary tables** (`results/simulation/tables/`):

| File | Contents |
|------|----------|
| `table_exp1_performance.csv` | Exp 1 aggregate metrics (one row) |
| `table_exp2_performance.csv` | Exp 2 aggregate + per-mutation metrics |
| `table_exp2_per_mutation.csv` | Per-mutation-type breakdown (10 rows) |
| `table_exp3_coverage_curve.csv` | Sensitivity/specificity at each fraction, by experiment |
| `table_exp3_per_mutation_coverage.csv` | Per-mutation sensitivity at each fraction |
| `table_false_negatives.csv` | All FN samples with VNTR lengths, coverage, mutation details |
| `table_false_positives.csv` | All FP samples (if any) with details |
| `table_combined_overview.csv` | Single overview table: all experiments, all fractions |

**3. Supplementary figures** (`results/simulation/figures/`):

| File | Contents |
|------|----------|
| `fig_coverage_sensitivity_curve.png/svg` | Sensitivity vs coverage fraction (dupC + atypical lines) |
| `fig_per_mutation_sensitivity.png/svg` | Bar chart of sensitivity by mutation type at full coverage |
| `fig_per_mutation_coverage_heatmap.png/svg` | Heatmap: mutation type x coverage fraction -> sensitivity |
| `fig_vntr_length_vs_detection.png/svg` | Scatter: total VNTR length vs detection outcome |

## Smoke test (dry run)

Before committing to the full ~20 hour run, validate the entire pipeline end-to-end with a small subset: 5 dupC pairs + 5 atypical pairs (1 per mutation type for the first 5 mutations). This exercises every script and catches config errors, path issues, or tool incompatibilities early.

All scripts accept a `--test` flag that limits to this small subset:

```
cd ../vntyper-analyses

# Smoke test: 5 dupC pairs (seeds 3000-3004) + 5 atypical pairs (seeds 4000-4004)
python scripts/simulation/01_simulate.py --test --workers 4
python scripts/simulation/02_run_vntyper.py --test --workers 4
python scripts/simulation/03_downsample.py --test --workers 4
python scripts/simulation/04_run_vntyper_downsampled.py --test --workers 4
python scripts/simulation/05_create_ground_truth.py --test
python scripts/simulation/06_parse_vntyper_results.py --test
python scripts/simulation/07_calculate_metrics.py --test
python scripts/simulation/08_generate_summary.py --test
```

### Test subset definition

| Experiment | Pairs | Seeds | Mutations |
|------------|-------|-------|-----------|
| dupC | 5 | 3000-3004 | dupC only |
| Atypical | 5 | 4000-4004 | insG, dupA, delinsAT, insCCCC, insC_pos23 (1 each) |

This produces:
- 10 pairs = 20 BAMs (simulate)
- 20 VNtyper runs (full coverage)
- 80 downsampled BAMs + 80 VNtyper runs (4 fractions x 20 BAMs)
- Ground truth, parsed results, metrics, and summary outputs

### Test output location

Test outputs go to `results/simulation_test/` (separate from production `results/simulation/`) to avoid mixing test and final data. Same directory structure as production, just under a different root.

### What to verify

After the smoke test completes, check:
1. **Simulation**: BAM files exist and are non-empty in `muconeup/pair_*/`
2. **VNtyper**: `kestrel_result.tsv` exists in each `vntyper/pair_*/` output dir
3. **Downsampling**: Downsampled BAMs are smaller than originals
4. **Ground truth**: CSV has correct columns and 10 rows (one per pair, two conditions each)
5. **Parsed results**: All VNtyper outputs parsed, no missing entries
6. **Metrics**: Sensitivity/specificity values are plausible (not all zero or NaN)
7. **Summary**: YAML fragment, tables, and figures all generated without errors

Estimated test runtime: ~30-45 min with 4 workers.

## Execution order (production)

After the smoke test passes, run the full pipeline:

```
cd ../vntyper-analyses

# Step 1: Simulate all 200 pairs (~4 hours)
python scripts/simulation/01_simulate.py --workers 16

# Step 2: Run VNtyper normal mode on all 400 BAMs (~3 hours)
python scripts/simulation/02_run_vntyper.py --workers 16

# Step 3: Downsample all 400 BAMs to 4 fractions (~30 min)
python scripts/simulation/03_downsample.py --workers 16

# Step 4: Run VNtyper normal mode on all 1,600 downsampled BAMs (~12 hours)
python scripts/simulation/04_run_vntyper_downsampled.py --workers 16

# Step 5: Collect ground truth from simulation metadata (~seconds)
python scripts/simulation/05_create_ground_truth.py

# Step 6: Parse all VNtyper outputs into structured tables (~seconds)
python scripts/simulation/06_parse_vntyper_results.py

# Step 7: Calculate performance metrics for all experiments (~seconds)
python scripts/simulation/07_calculate_metrics.py

# Step 8: Generate summary tables, figures, and YAML for manuscript (~seconds)
python scripts/simulation/08_generate_summary.py
```

Total estimated runtime: ~20 hours on 32-core workstation with 60 GB RAM.
Normal mode is slower than fast mode (~50% more per sample).

Dependency chain:
- Steps 1 -> 2 (need BAMs before VNtyper)
- Steps 2 -> 3 -> 4 (need full BAMs before downsampling, then VNtyper on downsampled)
- Steps 1 -> 5 (ground truth from simulation metadata, independent of VNtyper)
- Steps 2+4 -> 6 (parse all VNtyper outputs)
- Steps 5+6 -> 7 (join ground truth with parsed results)
- Step 7 -> 8 (summary from metrics)

## Manuscript integration

### Variables to generate

Script 08 generates `results/simulation/variables_fragment.yml`, ready to merge into `manuscript/_variables.yml`. See Script 8 description above for the full YAML structure.

### Figures

- Performance comparison table (Table 2 in manuscript)
- Coverage-sensitivity curve: sensitivity vs downsampling fraction for dupC and atypical (Supplementary)
- Per-mutation-type sensitivity bar chart (Supplementary)
- Optional: sensitivity vs VNTR length scatter (Supplementary)

### Text updates needed

1. Replace `simulation_interim` references with final `simulation_dupC` results
2. Add atypical simulation results paragraph in Results section
3. Add coverage titration results (1-2 sentences in Results, full data in Supplement)
4. Remove the TODO comment about full simulation results
5. Add Vrbacka et al. 2025 citation for VNTR length justification (run `make zotero-sync` first)

## Differences from muconeup-manuscript

| Aspect | muconeup-manuscript | This manuscript |
|--------|-------------------|-----------------|
| dupC sample size | 50 pairs | 100 pairs |
| Atypical variants | None | 100 pairs, 10 mutation types |
| Coverage titration | None | 4 fractions (50%, 25%, 12.5%, 6.25%) on all 400 BAMs |
| VNTR lengths | mean=60, SD=20 | mean=60, SD=15 |
| Coverage | 150x | 150x |
| VNtyper modes tested | Fast, Normal, Shark, adVNTR | Normal only |
| Mutation position | Fixed | Randomized per sample |
| Negative samples | Wild-type | Wild-type |
| Focus | MucOneUp tool validation | VNtyper 2 clinical pipeline validation |
| Seeds | 1000-1099 | 3000-3099, 4000-4099 (200 pairs) |
| Total VNtyper runs | ~300 | 2,000 |
| Scripts | Shell + Python analysis | Python orchestration, CLI execution via subprocess |
| Results location | `../muconeup-manuscript/experiments/` | `../vntyper-analyses/results/simulation/` |
