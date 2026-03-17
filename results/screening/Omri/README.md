# Omri - Irish Screening Cohort

## Status: Complete (coverage + extracted Kestrel results)

| Field | Value |
|-------|-------|
| **Cohort** | Irish Cohort |
| **Analysis type** | Screening |
| **Contributor** | Omri |
| **Samples** | 954 |
| **VNtyper version** | 2.0.0-beta.3 |
| **Reference assembly** | hg38 |
| **Pipeline** | BWA |
| **Coverage region** | 4,501 bp |
| **Processing modes** | Fast and Slow (same samples, both modes) |
| **Capture kit** | Not specified |
| **Upload date** | 2026-03-16 |

## Genotyping Results

Genotyping results were extracted from the HTML reports using `scripts/extract_kestrel_from_html.py` in the manuscript repository.

## Files

| File | Description |
|------|-------------|
| `summary_coverage_FastMode.csv` | Coverage metrics, fast mode (954 samples) |
| `summary_coverage_SlowMode.csv` | Coverage metrics, slow mode (954 samples) |
| `summary_reults_vntyper_2.0.0-beta.3_fast_mode_Irish_cohort.html` | Fast mode cohort summary report |
| `summary_reults_vntyper_2.0.0-beta.3_slow_mode_Irish_cohort.html` | Slow mode cohort summary report |
| `kestrel_results_fast_mode_irish.csv` | **Generated:** Kestrel results extracted from fast mode HTML (954 samples) |

## Missing Data

- Capture kit information

## Notes

- Largest screening cohort (954 samples)
- Both fast and slow mode results available, enabling direct comparison of processing modes
- Uses beta version of VNtyper (2.0.0-beta.3)
