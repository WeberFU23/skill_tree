#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

NEGATIVE_MEMORY_DIR="${NEGATIVE_MEMORY_DIR:-./curated_negative_memories_agg055}" \
NEGATIVE_MEMORY_TOP_K="${NEGATIVE_MEMORY_TOP_K:-1}" \
NEGATIVE_MEMORY_MAX_CHARS="${NEGATIVE_MEMORY_MAX_CHARS:-1200}" \
MEMORY_CACHE_SUFFIX="${MEMORY_CACHE_SUFFIX:-locomo_skilltree_curated_agg055_top1_chars1200_eval}" \
OUT_FILE="${OUT_FILE:-./results/locomo_skilltree_curated_agg055_top1_chars1200_eval.json}" \
WANDB_RUN_NAME="${WANDB_RUN_NAME:-locomo-skilltree-curated-agg055-top1-chars1200-eval}" \
    bash "$SCRIPT_DIR/eval_locomo_skilltree_negmem.sh" "$@"
