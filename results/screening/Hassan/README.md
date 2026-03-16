# Hassan - French Exome Screening Cohort

## Status: Complete (coverage + genotyping)

| Field | Value |
|-------|-------|
| **Cohort** | French Exome |
| **Analysis type** | Screening |
| **Contributor** | Hassan |
| **Samples** | 40 |
| **VNtyper version** | 2.0.0 |
| **Reference assembly** | hg38 |
| **Pipeline** | BWA |
| **Coverage region** | 4,501 bp |
| **Capture kit** | Not specified |
| **Upload date** | 2026-03-16 |

## Genotyping Results (Kestrel)

| Classification | Count |
|----------------|-------|
| High_Precision | 31 |
| Low_Precision | 2 |
| Negative | 7 |

## Files

| File | Description |
|------|-------------|
| `260310_exome_France_coverage.csv` | Coverage metrics for 40 samples |
| `260310_cohort_exome_kestrel.tsv` | Kestrel variant calling results (40 samples) |
| `260310_exome_France.html` | Cohort summary HTML report |
| `french_cohorts_260311_HS.xlsx` | Additional metadata and analysis |

## Notes

- Sample naming: LB26-XXXX format plus TEST_EXOME-NTI test samples
- Contains both Dragen and BWA pipeline entries in coverage file
- Uses hg38 assembly (differs from validation cohort which uses hg19)
