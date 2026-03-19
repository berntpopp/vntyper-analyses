# Screening Pipeline

Scripts for running VNtyper 2 on clinical screening cohorts and generating cohort reports.

## Prerequisites

- Docker with `saei/vntyper:latest` image
- Python 3.8+ with: `pandas`, `pyyaml`, `openpyxl`

## Usage

```bash
cd /path/to/vntyper-analyses

# Step 1: Run VNtyper on all samples (4 Docker workers, ~44 min for 1,051 samples)
python scripts/screening/run_vntyper_cohort.py --cohort Bernt

# Step 2: Generate cohort summary report (HTML + TSV)
python scripts/screening/generate_cohort_report.py --cohort Bernt

# Step 3: Parse results and produce enriched tables
python scripts/screening/parse_screening_results.py --cohort Bernt
```

## Configuration

All cohort parameters are in [`config.yml`](config.yml). To add a new cohort, add an entry under `cohorts:` with the data directory, metadata TSV path, and column mappings.

## Options

| Flag | Script | Description |
|------|--------|-------------|
| `--cohort NAME` | All | Cohort key from config.yml |
| `--workers N` | run_vntyper | Override worker count |
| `--test N` | run_vntyper | Process only first N samples |
| `--pseudonymize` | generate_cohort_report | Anonymize sample names in report |
