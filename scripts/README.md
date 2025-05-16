# Script Folder Overview

This folder contains SLURM batch scripts and analysis utilities related to running the VNTyper pipeline and generating cohort-level summary reports. These scripts support both Apptainer (`.sif`) and Docker container environments.

## 🔧 SLURM Scripts for VNTyper

### 1. Run VNTyper Pipeline on Multiple BAMs

You can run the VNTyper pipeline in parallel on all BAM files in a directory using either Apptainer or Docker.

#### Apptainer version:
The script can run is standard and fast mode (skipping unaligned reads)

```bash
sbatch pipeline_apptainer_sbatch_parallel.sh /path/to/bams /path/to/output slow/fast

```

#### Docker version:
The script can run is standard and fast mode (skipping unaligned reads)

```bash
sbatch pipeline_docker_sbatch_parallel.sh /path/to/bams /path/to/output slow/fast

```

- Arguments:
  - `/path/to/bams`: Folder containing input `.bam` files (e.g all BAM files from a cohort)
  - `/path/to/output`: Output directory
  - `fast` or `slow`: Mode flag for VNTyper

### 2. Generate Cohort Summary Report

After genotyping is completed, generate a cohort summary from the output directory. This directory contains one subfolder per sample (BAM file), each with all the necessary outputs. Among these, the .json and .html files are particularly important for further analysis.

#### Apptainer version:

```bash
sbatch cohort_apptainer_sbatch.sh /path/to/output /path/to/summary_output cohort_summary_name
```

#### Docker version:
```bash
sbatch vntyper2_cohort_docker_sbatch.sh /path/to/output /path/to/summary_output cohort_summary_name
```

- Arguments:
  - `/path/to/output`: The directory with per-sample VNTyper outputs
  - `/path/to/summary_output`: Where to write the summary files
  - `cohort_summary_name`: Base name for the generated `.html`

## 📊 Additional Scripts

This folder will also include analysis and plotting scripts to generate publication-ready figures from VNTyper outputs (e.g., merged cohort tables, variant distributions, summary plots).

Stay tuned!