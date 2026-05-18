#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

INPUT_DIR="${INPUT_DIR:-./curated_negative_memories_agg055}"
OUTPUT_DIR="${OUTPUT_DIR:-./curated_negative_memories_agg055_pruned_bad3}"

python -B scripts/prune_curated_negative_memories.py \
    --dir "$INPUT_DIR" \
    --out-dir "$OUTPUT_DIR" \
    --overwrite \
    --exclude-key "curated auto failure locomo conv-42 37" \
    --exclude-key "curated auto failure locomo conv-42 43" \
    --exclude-key "curated auto failure locomo conv-42 9"
