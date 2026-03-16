# Vaclav - Czech Screening Cohort

## Status: Complete (coverage + genotyping)

| Field | Value |
|-------|-------|
| **Cohort** | Czech Cohort |
| **Analysis type** | Screening |
| **Contributor** | Vaclav |
| **Samples** | 263 |
| **VNtyper version** | 2.0.0-beta.3 |
| **Reference assembly** | hg19 |
| **Pipeline** | BWA |
| **Coverage region** | 1,501 bp |
| **Processing mode** | Slow |
| **Capture kit** | Not specified |
| **VNtyper run date** | 2025-12-22 |
| **Upload date** | 2026-03-16 |

## Genotyping Results (Kestrel)

| Classification | Count |
|----------------|-------|
| High_Precision | 31 |
| High_Precision_flagged | 1 |
| Low_Precision | 14 |
| Low_Precision_flagged | 4 |
| Negative | 213 |

## Files

| File | Description |
|------|-------------|
| `cohort_vaclav_coverage_SlowMode.csv` | Coverage metrics (263 samples) |
| `cohort_kestrel-deanonymised-slow-bwa-final-22122025.tsv` | Kestrel variant calling results (263 samples) |
| `vntyper-run-slow-22122025.html` | Cohort summary HTML report |

## Missing Data

- Capture kit information

## Notes

- Pseudonymized sample IDs (sample_XXXXX format)
- Uses hg19 assembly (differs from Hassan and Omri screening which use hg38)
- Coverage region is 1,501 bp (vs 4,501 bp in hg38 cohorts)
- Uses beta version of VNtyper (2.0.0-beta.3)
- 5 flagged samples may require manual review
