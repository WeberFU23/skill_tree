#!/bin/bash
set -euo pipefail

: "${DEEPSEEK_API_KEY:?Set DEEPSEEK_API_KEY before running this script}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

RUN_DIR="${RUN_DIR:-./results/skill_tree_evolution_pruned_bad3_$(date +%Y%m%d_%H%M%S)}"
SOURCE_SKILL_TREE_DIR="${SOURCE_SKILL_TREE_DIR:-./skills_memory}"
EVOLVED_SKILL_TREE_DIR="${EVOLVED_SKILL_TREE_DIR:-$RUN_DIR/skills_memory}"
PRUNED_NEGATIVE_MEMORY_DIR="${PRUNED_NEGATIVE_MEMORY_DIR:-./curated_negative_memories_agg055_pruned_bad3}"
SAVE_DIR="${SAVE_DIR:-./checkpoints/locomo_skill_tree_evolved_bad3}"
WANDB_RUN_NAME="${WANDB_RUN_NAME:-locomo-skill-tree-evolve-bad3}"

if [[ -e "$EVOLVED_SKILL_TREE_DIR" ]]; then
    echo "[ERROR] Evolved skill-tree dir already exists: $EVOLVED_SKILL_TREE_DIR" >&2
    exit 1
fi

mkdir -p "$RUN_DIR"
cp -a "$SOURCE_SKILL_TREE_DIR" "$EVOLVED_SKILL_TREE_DIR"

OUTPUT_DIR="$PRUNED_NEGATIVE_MEMORY_DIR" bash "$SCRIPT_DIR/make_locomo_curated_agg055_pruned_bad3.sh"

echo "================================================================================"
echo "Training isolated skill-tree evolution run"
echo "RUN_DIR=$RUN_DIR"
echo "EVOLVED_SKILL_TREE_DIR=$EVOLVED_SKILL_TREE_DIR"
echo "PRUNED_NEGATIVE_MEMORY_DIR=$PRUNED_NEGATIVE_MEMORY_DIR"
echo "SAVE_DIR=$SAVE_DIR"
echo "WANDB_RUN_NAME=$WANDB_RUN_NAME"
echo "================================================================================"

SKILL_TREE_DIR="$EVOLVED_SKILL_TREE_DIR" \
NEGATIVE_MEMORY_DIR="$PRUNED_NEGATIVE_MEMORY_DIR" \
NEGATIVE_MEMORY_TOP_K="${NEGATIVE_MEMORY_TOP_K:-1}" \
NEGATIVE_MEMORY_MAX_CHARS="${NEGATIVE_MEMORY_MAX_CHARS:-1200}" \
SKILL_TREE_EVOLUTION_MIN_CASES="${SKILL_TREE_EVOLUTION_MIN_CASES:-2}" \
SKILL_TREE_EVOLUTION_MAX_BUCKETS="${SKILL_TREE_EVOLUTION_MAX_BUCKETS:-1}" \
AUTO_RECORD_NEGATIVE_MEMORY="${AUTO_RECORD_NEGATIVE_MEMORY:-0}" \
SAVE_DIR="$SAVE_DIR" \
OUT_FILE="${OUT_FILE:-$RUN_DIR/train.json}" \
WANDB_RUN_NAME="$WANDB_RUN_NAME" \
    bash "$SCRIPT_DIR/train_locomo_skilltree_negmem_autoevolve.sh"

cat > "$RUN_DIR/EVAL_COMMANDS.txt" <<EOF
Evaluate this evolved skill tree with:

SKILL_TREE_DIR="$EVOLVED_SKILL_TREE_DIR" \\
LOAD_CHECKPOINT="$SAVE_DIR/${WANDB_RUN_NAME}_epoch_final.pt" \\
NEGATIVE_MEMORY_DIR="$PRUNED_NEGATIVE_MEMORY_DIR" \\
NEGATIVE_MEMORY_TOP_K=1 \\
NEGATIVE_MEMORY_MAX_CHARS=1200 \\
MEMORY_CACHE_SUFFIX="evolved_bad3_eval" \\
OUT_FILE="$RUN_DIR/eval.json" \\
WANDB_RUN_NAME="locomo-skill-tree-evolve-bad3-eval" \\
  bash scripts/eval_locomo_skilltree_negmem.sh

If that single eval is promising, repeat it with:

RUN_DIR="$RUN_DIR" \\
REPEATS=3 \\
  bash scripts/repeat_locomo_skilltree_pruned_bad3_evolved_checkpoint.sh
EOF

cat "$RUN_DIR/EVAL_COMMANDS.txt"
