#!/usr/bin/env python3
"""
Aggregate VNtyper Kestrel results from multiple sample folders into a single CSV.

Expects a root folder containing one subfolder per sample. Each subfolder should
contain a ``Kestrel_result.tsv`` produced by VNtyper. The script reads each TSV,
determines whether the sample is positive (POS) or negative (NEG), and writes a
combined ``downsample_results.csv``.

Usage
-----
    python processing.py /path/to/vntyper_output
    python processing.py /path/to/vntyper_output -o results.csv
"""

import argparse
import csv
import logging
import re
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

KESTREL_FILENAME = "Kestrel_result.tsv"
COVERAGE_FILENAME = "coverage_summary.tsv"
FRACTION_PATTERN = re.compile(r"(\d+)pct")

KEEP_COLUMNS = [
    "Motifs",
    "POS",
    "REF",
    "ALT",
    "Sample",
    "Motif_sequence",
    "Estimated_Depth_AlternateVariant",
    "Estimated_Depth_Variant_ActiveRegion",
    "Depth_Score",
    "Confidence",
]


def extract_fraction(folder_name: str) -> str:
    """Extract the number before 'pct' in a folder name, or '' if absent."""
    m = FRACTION_PATTERN.search(folder_name)
    return m.group(1) if m else ""


def read_kestrel_tsv(tsv_path: Path) -> tuple[list[str], list[list[str]]]:
    """
    Parse a VNtyper Kestrel TSV.

    - Lines starting with ``##`` are skipped (metadata).
    - The first non-``##`` line is the header.
    - Only columns listed in KEEP_COLUMNS are retained.
    - Data rows containing the word "Negative" are treated as no-variant.
    - Blank / whitespace-only rows are skipped.

    Returns (kept_header, data_rows).
    """
    with open(tsv_path) as fh:
        lines = fh.readlines()

    content_lines = [
        ln.rstrip("\n\r") for ln in lines if not ln.startswith("##")
    ]

    if not content_lines:
        return list(KEEP_COLUMNS), []

    raw_header = content_lines[0].split("\t")
    col_map = {col.strip(): i for i, col in enumerate(raw_header)}

    keep_idx: list[int | None] = []
    for col in KEEP_COLUMNS:
        keep_idx.append(col_map.get(col))

    rows: list[list[str]] = []
    for line in content_lines[1:]:
        if not line.strip():
            continue
        if "negative" in line.lower():
            continue
        raw_cells = line.split("\t")
        row = [
            raw_cells[idx].strip() if idx is not None and idx < len(raw_cells) else ""
            for idx in keep_idx
        ]
        if any(cell for cell in row):
            rows.append(row)

    return list(KEEP_COLUMNS), rows


def read_coverage_summary(tsv_path: Path) -> tuple[list[str], list[str]]:
    """
    Parse a coverage_summary.tsv (single header + single data row).

    Returns (header_columns, data_values).  Both empty if file is missing
    or malformed.
    """
    header: list[str] = []
    values: list[str] = []

    if not tsv_path.exists():
        return header, values

    with open(tsv_path, newline="") as fh:
        reader = csv.reader(fh, delimiter="\t")
        try:
            header = next(reader)
            values = next(reader)
        except StopIteration:
            pass

    return header, values


def collect_results(root_dir: Path) -> tuple[list[str], list[list[str]]]:
    """
    Walk every immediate subfolder of *root_dir*, look for Kestrel TSVs,
    and return a combined (header, rows) ready for CSV output.

    Uses a two-pass approach: first collect all data, then build rows with
    a consistent column count. NEG samples get "None" for Kestrel columns.
    """
    sample_dirs = sorted(
        d for d in root_dir.iterdir() if d.is_dir()
    )
    if not sample_dirs:
        log.error("No sample subdirectories found in %s", root_dir)
        sys.exit(1)

    log.info("Found %d sample folder(s)", len(sample_dirs))

    cov_header: list[str] = []
    samples: list[dict] = []
    n_kestrel = len(KEEP_COLUMNS)

    for sample_dir in sample_dirs:
        folder_name = sample_dir.name
        tsv_path = sample_dir / "kestrel" / KESTREL_FILENAME
        cov_path = sample_dir / "coverage" / COVERAGE_FILENAME

        if not tsv_path.exists():
            log.warning("  %s — %s not found, skipping", folder_name, KESTREL_FILENAME)
            continue

        _, data_rows = read_kestrel_tsv(tsv_path)
        ch, cv = read_coverage_summary(cov_path)

        if not cov_header and ch:
            cov_header = ch

        fraction = extract_fraction(folder_name)
        is_positive = len(data_rows) > 0
        status = "POS" if is_positive else "NEG"
        log.info("  %s — %s%s", folder_name, status,
                 f" ({len(data_rows)} variant(s))" if is_positive else "")

        if not cv:
            log.warning("  %s — %s not found or empty", folder_name, COVERAGE_FILENAME)

        samples.append({
            "folder": folder_name,
            "fraction": fraction,
            "status": status,
            "kestrel_rows": data_rows,
            "cov_values": cv,
        })

    n_cov = len(cov_header)
    combined_header = (
        ["Sample_Folder", "Status", "Fraction"]
        + list(KEEP_COLUMNS) + cov_header
    )
    combined_rows: list[list[str]] = []

    for s in samples:
        prefix = [s["folder"], s["status"], s["fraction"]]
        cov_values = s["cov_values"] if s["cov_values"] else ["None"] * n_cov

        if s["status"] == "POS":
            for row in s["kestrel_rows"]:
                combined_rows.append(prefix + row + cov_values)
        else:
            combined_rows.append(
                prefix + ["None"] * n_kestrel + cov_values
            )

    return combined_header, combined_rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aggregate VNtyper Kestrel results into a single CSV.",
    )
    parser.add_argument(
        "input_dir",
        type=Path,
        help="Root directory containing one subfolder per sample.",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Output CSV path (default: <input_dir>/downsample_results.csv).",
    )
    args = parser.parse_args()

    root_dir = args.input_dir.resolve()
    if not root_dir.is_dir():
        log.error("Input directory does not exist: %s", root_dir)
        sys.exit(1)

    output_csv = (
        args.output.resolve() if args.output
        else root_dir / "downsample_results.csv"
    )

    header, rows = collect_results(root_dir)

    with open(output_csv, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(header)
        writer.writerows(rows)

    log.info("Wrote %d row(s) to %s", len(rows), output_csv)


if __name__ == "__main__":
    main()
