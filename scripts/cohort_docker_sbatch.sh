#!/bin/bash
#SBATCH --job-name=vntyper_cohort
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --output=./vntyper2_cohort.%j.out
#SBATCH --error=./vntyper2_cohort.%j.err

# ARGUMENTS 
INPUT_DIR="$1"      # Path to genotyping output from VNTyper
OUTPUT_DIR="$2"     # Path where summary will be written
SUMMARY_NAME="$3"    # Required: Base name for summary files (no extension)

# CONSTANTS
DOCKER_IMAGE="vntyper:latest"

# CHECKS
if [ -z "$INPUT_DIR" ] || [ -z "$OUTPUT_DIR" ] || [ -z "$SUMMARY_NAME" ]; then
    echo "Usage: sbatch $0 <input_folder> <output_folder> <summary_filename_base>"
    echo "Example: sbatch $0 /data/cohort1 /results/cohort1_summary cohort_paris"
    exit 1
fi

if [ ! -d "$INPUT_DIR" ]; then
    echo "Error: Input folder does not exist: $INPUT_DIR"
    exit 1
fi

if [ ! -f "$SIF_IMAGE" ]; then
    echo "Error: Apptainer image not found: $SIF_IMAGE"
    exit 1
fi

# RUN
docker run --rm \
    -w /opt/vntyper \
    -v "${INPUT_DIR}":/opt/vntyper/input \
    -v "${OUTPUT_DIR}":/opt/vntyper/output \
    "$DOCKER_IMAGE" \
    vntyper cohort \
    -i /opt/vntyper/input \
    -o /opt/vntyper/output \
    --summary-file "${SUMMARY_NAME}.html" \
    --summary-formats json,tsv \
    --pseudonymize-samples

echo "Cohort summary generated in: $OUTPUT_DIR"
