# Bernt Cohort (CerKiD Exome) Screening Plan

Plan for running VNtyper 2 on the CerKiD exome cohort and generating cohort-level summary reports.

## Cohort overview

| Parameter | Value |
|-----------|-------|
| Cohort name | CerKiD Exome (Labor Berlin) |
| Total samples | 1,059 |
| Downloadable (Twist exome) | 1,051 |
| Excluded (no Twist exome) | 8 |
| BAM type | Pre-sliced to chr1:155184000-155194000 (MUC1 VNTR region, ~10 kb) |
| BAM size | ~4-5 MB per sample |
| Reference assembly | hg38 (UCSC, bwa 0.7.17) |
| Enrichment kits | TwistExomev0.2 (647), TwistExomev2 (404) |
| Sequencing platform | Illumina |
| Sample metadata | `data/cerkid-exome-chr1/cerkid_exome_overview.tsv` |
| Data location | `results/screening/Bernt/data/cerkid-exome-chr1/` |

## Key observations

1. **BAMs are pre-sliced** to the MUC1 VNTR region only (~4.5 MB each, not full exomes). VNtyper's read extraction step will be fast since all reads are already from the region of interest.
2. **Two enrichment kits** are used across the cohort. TwistExomev0.2 and TwistExomev2 may have different capture performance over the VNTR. Coverage should be compared between kits.
3. **Orphan BAI files** exist for the original whole-exome BAMs (the `.bam.bai` without `chr1_155184000` in the name). These are index files for BAMs not present in this dataset — ignore them.
4. **Sample naming**: LB number (e.g., `LB24-0824`) is the primary identifier, extracted from the BAM filename or the metadata TSV.

## Pipeline

### Step 1: Run VNtyper 2 on all 1,051 samples

Run VNtyper 2 normal mode (Kestrel) via Docker on all downloaded BAMs.

**Input**: 1,051 pre-sliced BAMs from `data/cerkid-exome-chr1/`
**Output**: Per-sample VNtyper results in `results/screening/Bernt/vntyper/{sample_id}/`

```bash
python scripts/screening/run_vntyper_cohort.py \
  --cohort Bernt \
  --workers 4
```

Docker invocation per sample (same pattern as simulation pipeline):
```bash
docker run --rm -w /opt/vntyper \
  -v {bam_dir}:/opt/vntyper/input \
  -v {output_dir}:/opt/vntyper/output \
  --user {uid}:{gid} \
  saei/vntyper:latest \
  vntyper pipeline \
    --bam /opt/vntyper/input/{bam_filename} \
    -o /opt/vntyper/output \
    --reference-assembly hg38
```

**Workers**: 4 Docker containers (same as simulation — memory-safe).
**Skip logic**: Check for `kestrel/kestrel_result.tsv` to skip completed samples.
**Estimated runtime**: ~10s per sample x 1,051 / 4 workers = ~44 min.

### Step 2: Generate cohort summary report

Use VNtyper's built-in `cohort` command to aggregate all per-sample results into a single HTML + TSV summary.

**Input**: All per-sample output directories from step 1
**Output**: `results/screening/Bernt/cohort_summary/`

```bash
docker run --rm \
  -v {vntyper_results_dir}:/opt/vntyper/input \
  -v {cohort_output_dir}:/opt/vntyper/output \
  --user {uid}:{gid} \
  saei/vntyper:latest \
  vntyper cohort \
    --input-file /opt/vntyper/input/sample_dirs.txt \
    -o /opt/vntyper/output \
    --summary-formats csv,tsv,json \
    --pseudonymize-samples
```

### Step 3: Parse and enrich results

Join VNtyper results with sample metadata (enrichment kit, sample IDs) from the overview TSV. Produce:

1. **Enriched results table** (`results/screening/Bernt/tables/screening_results.tsv/.xlsx`):
   - Sample ID (LB number), enrichment kit
   - Kestrel call, confidence, depth score, flag
   - VNTR coverage (mean, median)
   - VNtyper runtime

2. **Summary statistics** (`results/screening/Bernt/tables/screening_summary.tsv/.xlsx`):
   - Total samples screened
   - Positive calls (by confidence tier)
   - Coverage statistics (by enrichment kit)
   - Flagged samples

3. **Coverage comparison by kit** — compare VNTR coverage between TwistExomev0.2 and TwistExomev2.

## Scripts

| Script | Responsibility |
|--------|---------------|
| `scripts/screening/run_vntyper_cohort.py` | Run VNtyper on all BAMs via Docker (parallel) |
| `scripts/screening/generate_cohort_report.py` | Run VNtyper `cohort` command for HTML/TSV summary |
| `scripts/screening/parse_screening_results.py` | Parse results, join with metadata, produce tables |
| `scripts/screening/config.yml` | Cohort-specific parameters |

## Configuration

```yaml
# scripts/screening/config.yml
cohorts:
  Bernt:
    name: "CerKiD Exome"
    data_dir: "results/screening/Bernt/data/cerkid-exome-chr1"
    metadata_tsv: "results/screening/Bernt/data/cerkid-exome-chr1/cerkid_exome_overview.tsv"
    results_dir: "results/screening/Bernt/vntyper"
    cohort_dir: "results/screening/Bernt/cohort_summary"
    tables_dir: "results/screening/Bernt/tables"
    reference_assembly: hg38
    bam_column: "bam_file"
    sample_id_column: "lb_number"
    filter_column: "download_status"
    filter_value: "downloaded"

vntyper:
  use_docker: true
  docker_image: "saei/vntyper:latest"
  timeout_seconds: 300
  workers: 4
```

## Output structure

```
results/screening/Bernt/
├── data/                           # Input (gitignored)
│   └── cerkid-exome-chr1/
│       ├── *.bam, *.bam.bai
│       └── cerkid_exome_overview.tsv
├── vntyper/                        # Per-sample VNtyper output (gitignored)
│   ├── LB24-0824/
│   │   ├── kestrel/kestrel_result.tsv
│   │   ├── pipeline_summary.json
│   │   └── ...
│   └── ...
├── cohort_summary/                 # VNtyper cohort aggregate report
│   ├── cohort_summary.html
│   ├── cohort_summary.tsv
│   └── cohort_summary.json
├── tables/
│   ├── screening_results.tsv/.xlsx     # All samples with metadata
│   └── screening_summary.tsv/.xlsx     # Aggregate statistics
└── README.md
```

## Considerations

- **Pre-sliced BAMs**: Since these are already limited to the MUC1 region, VNtyper's BAM-to-FASTQ extraction will process all reads. This is effectively equivalent to the simulation BAMs and should run very fast (~10s per sample).
- **No fast mode**: Use normal mode (Kestrel) for consistency with the simulation benchmark results.
- **Pseudonymization**: Use VNtyper's `--pseudonymize-samples` for the cohort report if sharing externally. The enriched results table keeps real LB numbers for internal use.
- **Enrichment kit comparison**: The two Twist kit versions may have different VNTR capture efficiency. Flag any systematic coverage differences.
- **Reusability**: The script structure mirrors the simulation pipeline (`_common.py` shared utilities, Docker support, parallel execution). The same scripts should work for other cohorts by adding entries to `config.yml`.
