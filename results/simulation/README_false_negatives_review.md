# VNtyper 2 False Negatives — Review Package

This archive contains the complete simulation and VNtyper 2 data for all 27 false negative samples from the simulation benchmark, prepared for manual review.

## Simulation settings

| Parameter | Value |
|-----------|-------|
| Tool | MucOneUp v0.28.1 |
| VNTR length distribution | Normal, mean=60, min=20, max=130 repeats |
| SD (derived) | (max-min)/4 = 27.5 repeats |
| Read simulator | Illumina (ReSeq/WeSSim) |
| Coverage | 150x (non-VNTR downsampling mode) |
| Fragment size | 250 bp mean, 35 bp SD |
| Read pairs | 10,000 per sample |
| Enrichment profile | Twist Bioscience v2 exome |
| Reference assembly | hg38 |

## VNtyper 2 settings

| Parameter | Value |
|-----------|-------|
| Tool | VNtyper 2.0.1 (Docker: saei/vntyper:latest) |
| Mode | Normal (Kestrel genotyping, no --fast-mode) |
| Reference | hg38 |

## False negative summary

27 false negatives out of 200 mutated samples (173 TP, 0 FP across 200 matched pairs).

| Mutation | FN count | Total samples | Sensitivity |
|----------|----------|---------------|-------------|
| dupC | 6 | 100 | 94% |
| insA_pos54 | 6 | 10 | 40% |
| dupA | 4 | 10 | 60% |
| delGCCCA | 3 | 10 | 70% |
| insC_pos23 | 3 | 10 | 70% |
| delinsAT | 2 | 10 | 80% |
| ins25bp | 1 | 10 | 90% |
| insG | 1 | 10 | 90% |
| insG_pos58 | 1 | 10 | 90% |

FN total VNTR length: median 142 repeats (range 90-195).
FN mutated allele length: median 82 repeats (range 52-111).
Longer alleles are significantly associated with FN (Mann-Whitney U p=0.002 total, p=1.2e-04 mutated allele).

## Archive structure

```
results/simulation/
├── experiment{1,2}_*/
│   ├── muconeup/pair_XXXX/         # Per FN pair: simulation data
│   │   ├── *.simulated.bam(.bai)   # Simulated BAMs (mutated + normal)
│   │   ├── *.simulated.fa          # VNTR haplotype FASTAs
│   │   ├── *_R1.fastq.gz           # Simulated reads
│   │   ├── *_R2.fastq.gz
│   │   ├── *.simulation_stats.json # Simulation parameters & haplotype details
│   │   └── *.vntr_structure.txt    # Repeat unit chain per haplotype
│   └── vntyper/pair_XXXX/mutated/  # VNtyper 2 output for mutated sample
│       ├── kestrel/
│       │   ├── kestrel_result.tsv  # Genotyping result (Negative for FNs)
│       │   ├── output.vcf          # Raw Kestrel VCF
│       │   └── output.bam(.bai)    # Kestrel alignment
│       ├── pipeline_summary.json   # Pipeline metadata & timing
│       ├── pipeline.log            # Full execution log
│       └── summary_report.html     # Visual HTML report
├── tables/
│   ├── comprehensive_all_samples.* # All 400 samples with full metadata
│   ├── supp_table_false_negatives.*# FN detail table
│   ├── main_table_performance.*    # Overall performance metrics
│   └── supp_table_per_mutation.*   # Per-mutation sensitivity
└── figures/
    ├── fig_per_mutation_sensitivity.png
    └── fig_vntr_length_vs_detection.png
```

## How to review a false negative

1. Open `tables/supp_table_false_negatives.xlsx` for the summary
2. For a specific pair (e.g., pair_3002):
   - Check haplotype structure: `muconeup/pair_3002/*.simulation_stats.json`
   - View the simulated VNTR: `muconeup/pair_3002/*.vntr_structure.txt`
   - Inspect VNtyper result: `vntyper/pair_3002/mutated/kestrel/kestrel_result.tsv`
   - Check coverage: `vntyper/pair_3002/mutated/pipeline_summary.json` (Coverage Calculation step)
   - Full log: `vntyper/pair_3002/mutated/pipeline.log`
   - Load BAM in IGV: `muconeup/pair_3002/pair_3002.001.mut.simulated.bam`
