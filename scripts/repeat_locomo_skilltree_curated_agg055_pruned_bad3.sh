#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

PRUNED_NEGATIVE_MEMORY_DIR="${PRUNED_NEGATIVE_MEMORY_DIR:-./curated_negative_memories_agg055_pruned_bad3}"
OUTPUT_DIR="$PRUNED_NEGATIVE_MEMORY_DIR" bash "$SCRIPT_DIR/make_locomo_curated_agg055_pruned_bad3.sh"

NEGATIVE_MEMORY_DIR="$PRUNED_NEGATIVE_MEMORY_DIR" \
CONFIG_NAME="${CONFIG_NAME:-curated_agg055_pruned_bad3_top${NEGATIVE_MEMORY_TOP_K:-1}_chars${NEGATIVE_MEMORY_MAX_CHARS:-1200}}" \
REPEAT_DIR="${REPEAT_DIR:-./results/repeat_locomo_skilltree_curated_agg055_pruned_bad3_$(date +%Y%m%d_%H%M%S)}" \
    bash "$SCRIPT_DIR/repeat_locomo_skilltree_negmem_curated_agg055.sh" "$@"
