#!/bin/bash
#SBATCH --job-name=vntyper2
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=100
#SBATCH --output=./vntyper2.%j.out
#SBATCH --error=./vntyper2.%j.err

# === INPUTS ===
INPUT_DIR_NAME="$1"     # e.g., bam_files/
OUTPUT_DIR="$2"         # e.g., /path/to/output
MODE="$3"               # fast or slow
THREADS_PER_BAM=10
MAX_PARALLEL=$((SLURM_CPUS_PER_TASK / THREADS_PER_BAM))

# === PRECHECK ===
INPUT_DIR="${INPUT_DIR_NAME}"
LOG_DIR="${OUTPUT_DIR}/logs"
mkdir -p "$LOG_DIR"

if [ ! -d "$INPUT_DIR" ]; then
    echo "Input directory does not exist: $INPUT_DIR"
    exit 1
fi
if [ ! -d "$OUTPUT_DIR" ]; then
    echo "Output directory does not exist: $OUTPUT_DIR"
    exit 1
fi
if ! compgen -G "${INPUT_DIR}/*.bam" > /dev/null; then
    echo "No BAM files found in ${INPUT_DIR}"
    exit 1
fi

# === MODE CHECK ===
if [[ "$MODE" == "fast" ]]; then
    MODE_FLAG="--fast-mode"
    echo "Running in FAST mode"
else
    MODE_FLAG=""
    echo "Running in standard (default) mode"
fi

# === CREATE CMD FILE ===
CMD_FILE="vntyper2_docker_cmds_${SLURM_JOB_ID}.txt"

for BAM in "${INPUT_DIR}"/*.bam; do
    BAM_NAME=$(basename "$BAM" .bam)
    echo "docker run -w /opt/vntyper --rm \
        -v ${INPUT_DIR}:/opt/vntyper/input \
        -v ${OUTPUT_DIR}:/opt/vntyper/output \
        vntyper:latest \
        vntyper pipeline --bam /opt/vntyper/input/${BAM_NAME}.bam \
        -o /opt/vntyper/output/${BAM_NAME} ${MODE_FLAG}" >> "$CMD_FILE"
done

# === RUN IN PARALLEL ===
cat "$CMD_FILE" | xargs -I {} -P ${MAX_PARALLEL} bash -c "{}"
trap "rm -f $CMD_FILE" EXIT

echo "All BAMs processed"