#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

NEGATIVE_MEMORY_MATCH_CATEGORIES="${NEGATIVE_MEMORY_MATCH_CATEGORIES:-3}" \
CONFIG_NAME="${CONFIG_NAME:-curated_agg055_cat3match_top${NEGATIVE_MEMORY_TOP_K:-1}_chars${NEGATIVE_MEMORY_MAX_CHARS:-1200}}" \
REPEAT_DIR="${REPEAT_DIR:-./results/repeat_locomo_skilltree_curated_agg055_cat3match_$(date +%Y%m%d_%H%M%S)}" \
    bash "$SCRIPT_DIR/repeat_locomo_skilltree_negmem_curated_agg055.sh" "$@"
