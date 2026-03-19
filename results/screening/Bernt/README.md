# Bernt Cohort — CerKiD Exome Screening

VNtyper 2.0.2 screening of 1,051 exome samples from the Labor Berlin CerKiD (Certification of Kidney Diseases) cohort.

## Cohort

| Parameter | Value |
|-----------|-------|
| Source | Labor Berlin, CerKiD exome panel |
| Total samples | 1,059 (1,051 with Twist exome, 8 excluded) |
| BAM type | Pre-sliced to chr1:155184000-155194000 (~10 kb MUC1 VNTR region) |
| Reference | hg38 (bwa 0.7.17) |
| Enrichment kits | TwistExomev0.2 (647), TwistExomev2 (404) |
| VNtyper version | 2.0.2 (Docker: saei/vntyper:latest) |
| VNtyper mode | Normal (Kestrel) |
| Analysis date | 2026-03-19 |

## Results

| Metric | Value |
|--------|-------|
| Samples analyzed | 1,049 (2 failed) |
| Positive calls | 22 (2.1%) |
| High_Precision | 9 |
| High_Precision* | 4 |
| Low_Precision | 9 |
| Flagged artifacts | 23 (excluded from positives) |
| Median VNTR coverage | 153x (TwistExomev0.2), 197x (TwistExomev2) |
| Runtime per sample | 4.2s median |

Most positive calls (19/22) show G→GG at position 67, consistent with the canonical MUC1-VNTR dupC frameshift. One sample (LB24-3313) shows a larger insertion (G→GGGTGGAGCCCGGGGCCGGC), suggesting an atypical variant.

## Directory structure

```
results/screening/Bernt/
├── README.md                       # This file
├── data/                           # Input BAMs and metadata (gitignored)
│   └── cerkid-exome-chr1/
│       ├── *.bam, *.bam.bai        # 1,051 pre-sliced BAMs
│       └── cerkid_exome_overview.tsv
├── vntyper/                        # Per-sample VNtyper output (gitignored)
│   └── {sample_id}/
│       ├── kestrel/kestrel_result.tsv
│       └── pipeline_summary.json
├── positive_bams/                  # BAMs for all 22 positive samples
│   └── *.bam, *.bam.bai
├── cohort_summary/                 # VNtyper cohort aggregate report
│   ├── cohort_summary.html         # Interactive HTML report
│   ├── cohort_kestrel.tsv          # All Kestrel calls
│   └── plots/kestrel_summary_plot.png
└── tables/
    ├── screening_results.tsv/.xlsx # All samples with calls + metadata
    └── screening_summary.tsv/.xlsx # Aggregate statistics
```

## Positive BAMs

The `positive_bams/` directory contains the pre-sliced BAM files (chr1:155184000-155194000) for all 22 positive samples. These can be loaded directly in IGV for manual review.

## Reproducibility

```bash
python scripts/screening/run_vntyper_cohort.py --cohort Bernt
python scripts/screening/generate_cohort_report.py --cohort Bernt
python scripts/screening/parse_screening_results.py --cohort Bernt
```

See [`scripts/screening/README.md`](../../scripts/screening/README.md) for details.
