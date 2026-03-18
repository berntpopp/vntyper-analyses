# Downsampling Scripts

Two scripts for evaluating VNtyper sensitivity at different sequencing depths.

## Workflow

```
Original BAMs ──> downsample.py ──> downsampled BAMs ──> VNtyper ──> processing.py ──> CSV summary
```

---

## 1. `downsample.py` — BAM Downsampling

Creates downsampled copies of BAM files at configurable fractions using `samtools`.

### Usage

```bash
# Default: 10% to 90% in 10% steps
python downsample.py /path/to/bam_folder

# Custom percentages
python downsample.py /path/to/bam_folder -p 5 25 50 75

# With options
python downsample.py /path/to/bam_folder -p 10 20 30 -o /output/dir -t 8 --seed 42
```

### Arguments

| Argument | Description | Default |
|---|---|---|
| `input_dir` | Folder containing `.bam` and `.bai` files | required |
| `-p`, `--percentages` | Downsampling percentages (1–99) | `10 20 30 40 50 60 70 80 90` |
| `-o`, `--output-dir` | Output folder | `<input_dir>/../downsampled_bams` |
| `-t`, `--threads` | samtools threads | `4` |
| `--seed` | Random seed for reproducibility | `42` |

### Output

Each input BAM produces one downsampled BAM per percentage inside `downsampled_bams/`:

```
downsampled_bams/
├── sampleA_downsampled_10pct.bam
├── sampleA_downsampled_10pct.bam.bai
├── sampleA_downsampled_20pct.bam
├── sampleA_downsampled_20pct.bam.bai
├── ...
└── sampleA_downsampled_90pct.bam
```

Each BAM is sorted and indexed automatically.

---

## 2. `processing.py` — Aggregate VNtyper Results (run suing apptainer or docker container and slurm scripts are available)

Reads VNtyper output folders (one per sample) and produces a single CSV summarizing variant calls and coverage across all samples.

### Usage

```bash
python processing.py /path/to/vntyper_output
python processing.py /path/to/vntyper_output -o results.csv
```

### Expected input structure

```
vntyper_output/
├── sampleA_downsampled_10pct/
│   ├── kestrel/
│   │   └── Kestrel_result.tsv
│   └── coverage/
│       └── coverage_summary.tsv
├── sampleA_downsampled_20pct/
│   ├── kestrel/
│   │   └── Kestrel_result.tsv
│   └── coverage/
│       └── coverage_summary.tsv
└── ...
```

### Output

A single `downsample_results.csv` with one row per sample:

| Column | Description |
|---|---|
| `Sample_Folder` | Name of the sample subfolder |
| `Status` | **POS** (variant detected) or **NEG** (no variant / "Negative" in TSV) |
| `Fraction` | Downsampling percentage extracted from folder name (e.g. `50` from `*_50pct`) |
| `Motifs` | VNTR motif |
| `POS` | Genomic position |
| `REF` | Reference allele |
| `ALT` | Alternate allele |
| `Sample` | Sample identifier from VNtyper |
| `Motif_sequence` | Motif sequence |
| `Estimated_Depth_AlternateVariant` | Estimated depth of alternate variant |
| `Estimated_Depth_Variant_ActiveRegion` | Estimated depth across the active region |
| `Depth_Score` | Depth-based quality score |
| `Confidence` | VNtyper confidence level |
| `mean` | Mean coverage (from `coverage_summary.tsv`) |
| `median` | Median coverage |
| `stdev` | Standard deviation of coverage |
| `min` | Minimum coverage |
| `max` | Maximum coverage |
| `region_length` | Length of the target region |
| `uncovered_bases` | Number of bases with zero coverage |
| `percent_uncovered` | Percentage of bases with zero coverage |

### Interpreting the results

- **POS** rows contain variant details from VNtyper; all Kestrel columns are populated.
- **NEG** rows have `None` for all Kestrel columns; only coverage information is present.
- The **Fraction** column lets you group results by sequencing depth to evaluate at which depth VNtyper can still detect the variant.
- A sample that is POS at 90% but NEG at 10% indicates the variant requires higher depth to be detected.
- Coverage columns help verify that downsampling achieved the expected depth reduction.

---

## Requirements

- Python 3.10+
- `samtools` 1.21+ (for `downsample.py`)
