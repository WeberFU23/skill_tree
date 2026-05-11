#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

NEGATIVE_MEMORY_DIR="${NEGATIVE_MEMORY_DIR:-./curated_negative_memories}" \
NEGATIVE_MEMORY_MAX_CHARS="${NEGATIVE_MEMORY_MAX_CHARS:-1800}" \
MEMORY_CACHE_SUFFIX="${MEMORY_CACHE_SUFFIX:-locomo_skill_tree_eval_curated_negmem}" \
OUT_FILE="${OUT_FILE:-./results/locomo_skill_tree_eval_curated_negmem.json}" \
WANDB_RUN_NAME="${WANDB_RUN_NAME:-locomo-skill-tree-eval-curated-negmem}" \
    bash "$SCRIPT_DIR/eval_locomo_skilltree_negmem.sh" "$@"
