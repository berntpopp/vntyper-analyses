# Hassan - Renome France Validation Cohort

## Status: Complete (coverage + extracted Kestrel results)

| Field | Value |
|-------|-------|
| **Cohort** | Renome France |
| **Analysis type** | Validation |
| **Contributor** | Hassan |
| **Samples** | 6,351 |
| **VNtyper version** | 2.0.0 |
| **Reference assembly** | hg19 |
| **Pipeline** | BWA |
| **Coverage region** | 1,501 bp |
| **Capture kit** | Not specified |
| **Upload date** | 2025-06-19 |

## Genotyping Results

Genotyping results were extracted from the HTML report using `scripts/extract_kestrel_from_html.py` in the manuscript repository.

## Files

| File | Description |
|------|-------------|
| `260310_renome_France_coverage.csv` | Coverage metrics (6,351 samples) |
| `260310_renome_France.html` | Cohort summary HTML report (8.2 MB) |
| `renome_kestrel_results.csv` | **Generated:** Kestrel results extracted from HTML (6,350 samples) |

## Missing Data

- Capture kit information

## Notes

- Largest cohort in the repository (6,351 samples)
- Sample naming convention: `{DiseasePrefix}{ID}_NGS{Year}_{Number}.MUC1`
- Disease prefix codes observed: PK, ALP, HYP, NCR, NTI, NPH, REN
- NGS years in sample IDs: 2020, 2022
- First cohort uploaded to the repository (2025-06-19)
