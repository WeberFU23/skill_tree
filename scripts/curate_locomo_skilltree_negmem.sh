#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

INPUT_DIR="${NEGATIVE_MEMORY_DIR:-./negative_memories}"
OUTPUT_DIR="${CURATED_NEGATIVE_MEMORY_DIR:-./curated_negative_memories}"
REPORT="${CURATION_REPORT:-./results/negative_memory_curation_$(date +%Y%m%d_%H%M%S).md}"
SIMILARITY_THRESHOLD="${CURATION_SIMILARITY_THRESHOLD:-0.55}"
MIN_CLUSTER_SIZE="${CURATION_MIN_CLUSTER_SIZE:-1}"
MIN_QUALITY="${CURATION_MIN_QUALITY:-0}"
MAX_CURATED="${CURATION_MAX_CURATED:-30}"
MAX_EXAMPLES_PER_CLUSTER="${CURATION_MAX_EXAMPLES_PER_CLUSTER:-8}"

ARGS=(
    --dir "$INPUT_DIR"
    --out-dir "$OUTPUT_DIR"
    --report "$REPORT"
    --similarity-threshold "$SIMILARITY_THRESHOLD"
    --min-cluster-size "$MIN_CLUSTER_SIZE"
    --min-quality "$MIN_QUALITY"
    --max-curated "$MAX_CURATED"
    --max-examples-per-cluster "$MAX_EXAMPLES_PER_CLUSTER"
    --write-curated
)

if [[ "${CURATION_OVERWRITE:-1}" == "1" ]]; then
    ARGS+=(--overwrite)
fi

python -B curate_negative_memories.py "${ARGS[@]}"
