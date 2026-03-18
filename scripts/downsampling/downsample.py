#!/usr/bin/env python3
"""
Downsample BAM files using samtools (version 1.21).

For each BAM in the input folder, this script creates downsampled BAMs at the
requested percentages inside an output directory called ``downsampled_bams``
(created next to the input folder by default, or at a custom path).

Usage
-----
    python downsample.py /path/to/bam_folder -p 5 -o /custom/output -t 8 (default is 10-90%)
"""

import argparse
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

DEFAULT_PERCENTAGES = list(range(10, 100, 10))  # 10, 20, …, 90


def parse_percentages(values: list[int]) -> list[float]:
    """Convert user-supplied percentages to sorted fractions, with validation."""
    fractions = []
    for v in values:
        if not 1 <= v <= 99:
            log.error("Percentage must be between 1 and 99, got %d", v)
            sys.exit(1)
        fractions.append(round(v / 100, 2))
    return sorted(set(fractions))


def find_samtools() -> str:
    """Return the path to samtools, or exit if not found."""
    try:
        result = subprocess.run(
            ["samtools", "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        version_line = result.stdout.splitlines()[0]
        log.info("Found %s", version_line)
        return "samtools"
    except (FileNotFoundError, subprocess.CalledProcessError):
        log.error("samtools not found in PATH. Please install samtools first.")
        sys.exit(1)


def discover_bams(input_dir: Path) -> list[Path]:
    """Return sorted list of BAM files in *input_dir*."""
    bams = sorted(input_dir.glob("*.bam"))
    if not bams:
        log.error("No .bam files found in %s", input_dir)
        sys.exit(1)
    log.info("Discovered %d BAM file(s) in %s", len(bams), input_dir)
    return bams


def downsample(
    samtools: str,
    bam: Path,
    fraction: float,
    output_dir: Path,
    threads: int,
    seed: int,
) -> Path:
    """Downsample *bam* to *fraction* and write to *output_dir*. Returns output path."""
    pct = int(fraction * 100)
    stem = bam.stem  # e.g. "sample1" from "sample1.bam"
    out_bam = output_dir / f"{stem}_downsampled_{pct}pct.bam"

    cmd = [
        samtools,
        "view",
        "-b",
        "--subsample", str(fraction),
        "--subsample-seed", str(seed),
        "-@", str(threads),
        "-o", str(out_bam),
        str(bam),
    ]
    log.info("  %d%% → %s", pct, out_bam.name)
    subprocess.run(cmd, check=True)
    return out_bam


def index_bam(samtools: str, bam: Path, threads: int) -> None:
    """Create a .bai index for *bam*."""
    cmd = [samtools, "index", "-@", str(threads), str(bam)]
    subprocess.run(cmd, check=True)


def sort_bam(samtools: str, bam: Path, threads: int) -> None:
    """Sort a BAM in-place (required for indexing)."""
    sorted_tmp = bam.with_suffix(".sorted.bam")
    cmd = [
        samtools, "sort",
        "-@", str(threads),
        "-o", str(sorted_tmp),
        str(bam),
    ]
    subprocess.run(cmd, check=True)
    sorted_tmp.replace(bam)


def process_bam(
    samtools: str,
    bam: Path,
    fractions: list[float],
    output_dir: Path,
    threads: int,
    seed: int,
) -> None:
    """Downsample a single BAM at all fractions, sort, and index each output."""
    log.info("Processing %s", bam.name)
    for frac in fractions:
        out_bam = downsample(samtools, bam, frac, output_dir, threads, seed)
        sort_bam(samtools, out_bam, threads)
        index_bam(samtools, out_bam, threads)
    log.info("Finished %s\n", bam.name)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Downsample BAM files using samtools.",
    )
    parser.add_argument(
        "input_dir",
        type=Path,
        help="Directory containing .bam (and optionally .bai) files.",
    )
    parser.add_argument(
        "-p", "--percentages",
        type=int,
        nargs="+",
        default=DEFAULT_PERCENTAGES,
        metavar="PCT",
        help="Downsampling percentages to generate, 1–99 "
             "(default: 10 20 30 40 50 60 70 80 90).",
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: <input_dir>/../downsampled_bams).",
    )
    parser.add_argument(
        "-t", "--threads",
        type=int,
        default=4,
        help="Number of threads for samtools (default: 4).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible downsampling (default: 42).",
    )
    args = parser.parse_args()

    fractions = parse_percentages(args.percentages)
    log.info("Downsampling at: %s", ", ".join(f"{int(f*100)}%%" for f in fractions))

    input_dir = args.input_dir.resolve()
    if not input_dir.is_dir():
        log.error("Input directory does not exist: %s", input_dir)
        sys.exit(1)

    output_dir = (
        args.output_dir.resolve()
        if args.output_dir
        else input_dir.parent / "downsampled_bams"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    log.info("Output directory: %s", output_dir)

    samtools = find_samtools()
    bams = discover_bams(input_dir)

    for bam in bams:
        process_bam(samtools, bam, fractions, output_dir, args.threads, args.seed)

    log.info("All done — downsampled BAMs are in %s", output_dir)


if __name__ == "__main__":
    main()
