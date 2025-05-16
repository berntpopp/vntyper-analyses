#!/bin/bash
#SBATCH --job-name=vntyper2
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=100
#SBATCH --output=./vntyper2.%j.out
#SBATCH --error=./vntyper2.%j.err

# INPUTS
INPUT_DIR_NAME="$1"     # e.g., my_sample_folder
OUTPUT_DIR="$2"         # full output path
MODE="$3"               # fast or slow
THREADS_PER_BAM=10
MAX_PARALLEL=$((SLURM_CPUS_PER_TASK / THREADS_PER_BAM))

# CONSTANTS
INPUT_DIR="${INPUT_DIR_NAME}"
CONTAINER="/data-master/workspace/labss/hsaei/images/vntyper/vntyper_2.0.0-beta.sif"
REF="hg19"

# MODE CHECK
if [[ "$MODE" == "fast" ]]; then
    MODE_FLAG="--fast-mode"
    echo "Running in FAST mode"
else
    MODE_FLAG=""  # default is slow mode (no flag)
    echo "Running in standard (default) mode"
fi

# INPUT CHECK
if [ ! -d "$INPUT_DIR" ]; then
    echo "Input directory does not exist: $INPUT_DIR"
    exit 1
fi
if [ ! -d "$OUTPUT_DIR" ]; then
    echo "Output directory does not exist: $OUTPUT_DIR"
    exit 1
fi
if [ ! -f "$CONTAINER" ]; then
    echo "Container file does not exist: $CONTAINER"
    exit 1
fi
if ! compgen -G "${INPUT_DIR}/*.bam" > /dev/null; then
    echo "No BAM files found in ${INPUT_DIR}"
    exit 1
fi


# FUNCTION TO PROCESS BAM
CMD_FILE="vntyper2_cmds_${SLURM_JOB_ID}.txt"

for BAM in "${INPUT_DIR}"/*.bam; do
    BAM_NAME=$(basename "$BAM" .bam)
    echo "apptainer run --pwd /opt/vntyper -B ${INPUT_DIR}:/opt/vntyper/input -B ${OUTPUT_DIR}:/opt/vntyper/output ${CONTAINER} vntyper pipeline --threads ${THREADS_PER_BAM} --reference-assembly ${REF} --bam /opt/vntyper/input/${BAM_NAME}.bam -o /opt/vntyper/output/${BAM_NAME} -n ${BAM_NAME} ${MODE_FLAG}" >> "$CMD_FILE"
done

# Run commands in parallel with xargs
cat "$CMD_FILE" | xargs -I {} -P ${MAX_PARALLEL} bash -c "{}"
trap "rm -f $CMD_FILE" EXIT

echo "All BAMs processed."
