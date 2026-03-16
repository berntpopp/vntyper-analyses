# VNtyper-Analyses: Cohort Summary

> Auto-generated: 2026-03-16

## Overview

This repository contains pseudonymized results from multi-center cohort analyses using **VNtyper 2.0** for MUC1-VNTR genotyping in Autosomal Dominant Tubulointerstitial Kidney Disease (ADTKD-MUC1).

| Metric | Value |
|--------|-------|
| **Total unique samples** | ~7,608 |
| **Cohorts** | 4 (3 screening + 1 validation) |
| **Contributing centers** | 3 (Hassan, Omri, Vaclav) |
| **VNtyper versions used** | 2.0.0, 2.0.0-beta.3 |
| **Reference assemblies** | hg19, hg38 |
| **Repository active since** | 2025-05-07 |
| **Latest data upload** | 2026-03-16 |

---

## Cohort Breakdown

### Screening Cohorts

#### 1. Hassan - French Exome Cohort
| Field | Value |
|-------|-------|
| **Samples** | 40 |
| **VNtyper version** | 2.0.0 |
| **Reference assembly** | hg38 |
| **Pipeline** | BWA |
| **Coverage region** | 4,501 bp |
| **Processing mode** | Mixed (Fast/Slow) |
| **Capture kit** | Not specified |

**Files:**
- `260310_exome_France_coverage.csv` - Coverage metrics (40 samples)
- `260310_cohort_exome_kestrel.tsv` - Kestrel genotyping results (40 samples, 40 rows)
- `260310_exome_France.html` - Cohort summary report (4.4 MB)
- `french_cohorts_260311_HS.xlsx` - Additional metadata/analysis (565 KB)

**Genotyping results (Kestrel):**
| Classification | Count |
|----------------|-------|
| High_Precision | 31 |
| Low_Precision | 2 |
| Negative | 7 |

---

#### 2. Omri - Irish Cohort
| Field | Value |
|-------|-------|
| **Samples** | 954 |
| **VNtyper version** | 2.0.0-beta.3 |
| **Reference assembly** | hg38 |
| **Pipeline** | BWA |
| **Coverage region** | 4,501 bp |
| **Processing modes** | Both Fast and Slow (same 954 samples run in both modes) |
| **Capture kit** | Not specified |

**Files:**
- `summary_coverage_FastMode.csv` - Coverage metrics, fast mode (954 samples)
- `summary_coverage_SlowMode.csv` - Coverage metrics, slow mode (954 samples)
- `summary_reults_vntyper_2.0.0-beta.3_fast_mode_Irish_cohort.html` - Fast mode report (5.2 MB)
- `summary_reults_vntyper_2.0.0-beta.3_slow_mode_Irish_cohort.html` - Slow mode report (5.2 MB)

**Genotyping results:** Only available in HTML reports (no TSV/CSV with variant calls).

---

#### 3. Vaclav - Czech Cohort
| Field | Value |
|-------|-------|
| **Samples** | 263 |
| **VNtyper version** | 2.0.0-beta.3 |
| **Reference assembly** | hg19 |
| **Pipeline** | BWA |
| **Coverage region** | 1,501 bp |
| **Processing mode** | Slow |
| **Capture kit** | Not specified |
| **Run date** | 2025-12-22 |

**Files:**
- `cohort_vaclav_coverage_SlowMode.csv` - Coverage metrics (263 samples)
- `cohort_kestrel-deanonymised-slow-bwa-final-22122025.tsv` - Kestrel genotyping results (263 samples, 263 rows)
- `vntyper-run-slow-22122025.html` - Cohort summary report (4.5 MB)

**Genotyping results (Kestrel):**
| Classification | Count |
|----------------|-------|
| High_Precision | 31 |
| High_Precision_flagged | 1 |
| Low_Precision | 14 |
| Low_Precision_flagged | 4 |
| Negative | 213 |

---

### Validation Cohorts

#### 4. Hassan - Renome France Cohort
| Field | Value |
|-------|-------|
| **Samples** | 6,351 |
| **VNtyper version** | 2.0.0 |
| **Reference assembly** | hg19 |
| **Pipeline** | BWA |
| **Coverage region** | 1,501 bp |
| **Processing mode** | Not specified |
| **Capture kit** | Not specified |

**Files:**
- `260310_renome_France_coverage.csv` - Coverage metrics (6,351 samples)
- `260310_renome_France.html` - Cohort summary report (8.2 MB)

**Sample naming convention:** `{DiseasePrefix}{ID}_NGS{Year}_{Number}.MUC1`
- Prefixes observed: PK, ALP, HYP, NCR, NTI, NPH, REN (likely disease phenotype codes)
- NGS years: 2020, 2022 (and potentially others)

**Genotyping results:** Only available in HTML report (no TSV/CSV with variant calls).

---

## Data Completeness & Gaps

### Available data per cohort

| Cohort | Coverage CSV | Kestrel TSV | HTML Report | Excel | Capture Kit |
|--------|:-----------:|:-----------:|:-----------:|:-----:|:-----------:|
| Hassan Screening | Yes | Yes | Yes | Yes | No |
| Omri Screening | Yes (x2) | No | Yes (x2) | No | No |
| Vaclav Screening | Yes | Yes | Yes | No | No |
| Hassan Validation | Yes | No | Yes | No | No |

### Notable gaps
1. **No capture kit information** in any cohort - required per repository guidelines (Twist, Kapa, Agilent, etc.)
2. **Missing Kestrel genotyping TSV** for Omri (Irish, 954 samples) and Hassan validation (Renome, 6,351 samples)
3. **Aggregated results directory is empty** - no cross-cohort meta-analysis results yet
4. **No workflow implementations** - both Nextflow and Snakemake directories are empty
5. **No documentation/SOPs** - `docs/` directory is empty

---

## VNtyper Version & Assembly Consistency

| Cohort | Version | Assembly | Region (bp) |
|--------|---------|----------|-------------|
| Hassan Screening | 2.0.0 | hg38 | 4,501 |
| Omri Screening | 2.0.0-beta.3 | hg38 | 4,501 |
| Vaclav Screening | 2.0.0-beta.3 | hg19 | 1,501 |
| Hassan Validation | 2.0.0 | hg19 | 1,501 |

**Warning:** Mixed reference assemblies (hg19 vs hg38) and VNtyper versions across cohorts may impact cross-cohort comparability. The coverage region length also differs (4,501 bp vs 1,501 bp), likely reflecting different reference region definitions between versions/assemblies.

---

## Git History & Upload Timeline

| Date | Event |
|------|-------|
| 2025-05-07 | Repository initialized with README and project structure |
| 2025-05-16 | SLURM scripts and extract_additional_stats.py added |
| 2025-06-19 | Renome (validation) cohort results from Paris uploaded |
| 2025-06-23 | Results README updated with folder structure guidelines |
| 2025-07-02 | Gitignore updated |
| 2026-03-16 | Screening cohort results uploaded (Hassan, Omri, Vaclav) |

---

## Container & Infrastructure

| Component | Details |
|-----------|---------|
| **Apptainer image** | `vntyper_2.0.0-beta.sif` at `/data-master/workspace/labss/hsaei/images/vntyper/` |
| **Docker image** | `vntyper:latest` |
| **SLURM defaults** | 100 CPUs, 10 threads/BAM, xargs parallelization |
| **Python deps** | beautifulsoup4, pandas |
