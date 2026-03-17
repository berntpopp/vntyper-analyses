# VNtyper 2 False Negatives Review Package

Complete simulation and VNtyper 2 data for all 27 false negative samples plus 27 length-matched true positive controls, for manual review.

## Simulation parameters

| Parameter | Value |
|-----------|-------|
| Simulation tool | MucOneUp v0.28.1 |
| VNTR length distribution | Normal(mean=60, SD=27.5, min=20, max=130 repeats) |
| Read simulation | Illumina (ReSeq/WeSSim), 150x coverage |
| Fragment size | 250 bp mean, 35 bp SD |
| Read pairs per sample | 10,000 |
| Enrichment profile | Twist Bioscience v2 exome |
| Reference assembly | hg38 |
| Genotyping tool | VNtyper 2.0.1 (Docker: saei/vntyper:latest) |
| Genotyping mode | Normal (Kestrel, no --fast-mode) |

## False negative summary

27 FN out of 200 mutated samples (0 FP out of 200 wild-type controls).

| Mutation | FN | N | Sensitivity | Citation |
|----------|----|----|-------------|----------|
| dupC | 6 | 100 | 94.0% | canonical |
| insA_pos54 | 6 | 10 | 40.0% | Vrbacka 2025 |
| dupA | 4 | 10 | 60.0% | Olinger 2020 |
| delGCCCA | 3 | 10 | 70.0% | Saei 2023 |
| insC_pos23 | 3 | 10 | 70.0% | Vrbacka 2025 |
| delinsAT | 2 | 10 | 80.0% | Olinger 2020 |
| ins25bp | 1 | 10 | 90.0% | Saei 2023 |
| insG | 1 | 10 | 90.0% | Olinger 2020 |
| insG_pos58 | 1 | 10 | 90.0% | Vrbacka 2025 |

VNTR length is significantly longer in FN samples (Mann-Whitney U p = 0.002 total length, p = 1.2e-04 mutated allele length).

## Matched true positive controls

For each mutation type, 3 TP samples with the closest total VNTR length to the FN median are included for side-by-side comparison.

| Mutation | FN pairs | Matched TP pairs |
|----------|----------|------------------|
| dupC | 3002, 3014, 3041, 3068, 3081, 3090 | 3063, 3060, 3012 |
| insA_pos54 | 4070, 4073, 4074, 4075, 4076, 4078 | 4072, 4079, 4077 |
| dupA | 4013, 4014, 4016, 4019 | 4010, 4018, 4017 |
| delGCCCA | 4080, 4081, 4086 | 4087, 4088, 4082 |
| insC_pos23 | 4040, 4045, 4046 | 4043, 4042, 4041 |
| delinsAT | 4020, 4022 | 4024, 4029, 4027 |
| ins25bp | 4091 | 4097, 4093, 4094 |
| insG | 4005 | 4006, 4007, 4003 |
| insG_pos58 | 4058 | 4054, 4059, 4056 |

## Archive contents

Per sample pair directory:

```
muconeup/pair_XXXX/
  *.simulated.bam(.bai)          Simulated BAMs (mutated + normal)
  *.simulated.fa                 VNTR haplotype FASTAs
  *_R1.fastq.gz, *_R2.fastq.gz  Simulated reads
  *.simulation_stats.json        Haplotype lengths, mutation details, GC content
  *.vntr_structure.txt           Repeat unit chain per haplotype

vntyper/pair_XXXX/mutated/
  kestrel/kestrel_result.tsv     Genotyping result
  kestrel/output.vcf             Kestrel VCF
  kestrel/output.bam(.bai)       Kestrel alignment
  pipeline_summary.json          Step timing, coverage stats
  pipeline.log                   Full execution log
  summary_report.html            Visual report
```

Summary files included: `comprehensive_all_samples.xlsx`, `supp_table_false_negatives.xlsx`, `main_table_performance.tsv`, `supp_table_per_mutation.tsv`, figures.

## How to review

1. Open `tables/supp_table_false_negatives.xlsx` for the FN overview
2. Compare an FN with its matched TP (same mutation, similar VNTR length):
   - Haplotype structure: `*.simulation_stats.json` and `*.vntr_structure.txt`
   - Kestrel result: `kestrel/kestrel_result.tsv`
   - Coverage: `pipeline_summary.json` (Coverage Calculation step)
   - BAM in IGV: `muconeup/pair_XXXX/*.simulated.bam`
