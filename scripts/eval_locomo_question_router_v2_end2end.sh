#!/bin/bash
set -euo pipefail

: "${DEEPSEEK_API_KEY:?Set DEEPSEEK_API_KEY before running this script}"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export WANDB_MODE="${WANDB_MODE:-offline}"
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

RUN_DIR="${RUN_DIR:-}"
if [[ -z "$RUN_DIR" ]]; then
    RUN_DIR="$(ls -td ./results/skill_tree_evolution_pruned_bad3_* 2>/dev/null | head -n 1 || true)"
fi
if [[ -z "$RUN_DIR" || ! -d "$RUN_DIR" ]]; then
    echo "[ERROR] Set RUN_DIR to a skill_tree_evolution_pruned_bad3_* result directory." >&2
    exit 1
fi

BASELINE_SKILL_TREE_DIR="${BASELINE_SKILL_TREE_DIR:-./skills_memory}"
CANDIDATE_SKILL_TREE_DIR="${CANDIDATE_SKILL_TREE_DIR:-$RUN_DIR/skills_memory}"
BASELINE_SAVE_DIR="${BASELINE_SAVE_DIR:-./checkpoints/locomo_skill_tree}"
CANDIDATE_SAVE_DIR="${CANDIDATE_SAVE_DIR:-./checkpoints/locomo_skill_tree_evolved_bad3}"
BASELINE_CHECKPOINT="${BASELINE_CHECKPOINT:-$BASELINE_SAVE_DIR/locomo-skill-tree-train_epoch_final.pt}"
CANDIDATE_CHECKPOINT="${CANDIDATE_CHECKPOINT:-$CANDIDATE_SAVE_DIR/locomo-skill-tree-evolve-bad3_epoch_final.pt}"
NEGATIVE_MEMORY_DIR="${NEGATIVE_MEMORY_DIR:-./curated_negative_memories_agg055_pruned_bad3}"
NEGATIVE_MEMORY_TOP_K="${NEGATIVE_MEMORY_TOP_K:-1}"
NEGATIVE_MEMORY_MAX_CHARS="${NEGATIVE_MEMORY_MAX_CHARS:-1200}"
QUESTION_ROUTER_MODE="${QUESTION_ROUTER_MODE:-risk_profile_baseline_v2}"
MEMORY_CACHE_SUFFIX="${MEMORY_CACHE_SUFFIX:-question_router_v2_end2end}"
OUT_FILE="${OUT_FILE:-./results/locomo_question_router_v2_end2end_eval.json}"
WANDB_RUN_NAME="${WANDB_RUN_NAME:-locomo-question-router-v2-end2end-eval}"
SAVE_DIR="${SAVE_DIR:-./checkpoints/locomo_skill_tree_router_v2}"

if [[ ! -f "$BASELINE_CHECKPOINT" ]]; then
    echo "[ERROR] Missing baseline checkpoint: $BASELINE_CHECKPOINT" >&2
    exit 1
fi
if [[ ! -f "$CANDIDATE_CHECKPOINT" ]]; then
    echo "[ERROR] Missing candidate checkpoint: $CANDIDATE_CHECKPOINT" >&2
    exit 1
fi

OUTPUT_DIR="$NEGATIVE_MEMORY_DIR" bash "$SCRIPT_DIR/make_locomo_curated_agg055_pruned_bad3.sh"

python -B main.py \
    --disable-flash-attn \
    --memory-cache-suffix "$MEMORY_CACHE_SUFFIX" \
    --overwrite \
    --eval-only \
    --enable-question-router-eval \
    --question-router-mode "$QUESTION_ROUTER_MODE" \
    --router-baseline-checkpoint "$BASELINE_CHECKPOINT" \
    --router-candidate-checkpoint "$CANDIDATE_CHECKPOINT" \
    --router-baseline-skill-tree-dir "$BASELINE_SKILL_TREE_DIR" \
    --router-candidate-skill-tree-dir "$CANDIDATE_SKILL_TREE_DIR" \
    --router-baseline-save-dir "$BASELINE_SAVE_DIR" \
    --router-candidate-save-dir "$CANDIDATE_SAVE_DIR" \
    --router-baseline-memory-cache-suffix "${MEMORY_CACHE_SUFFIX}_baseline" \
    --router-candidate-memory-cache-suffix "${MEMORY_CACHE_SUFFIX}_candidate" \
    --inference-workers 1 \
    --inference-session-workers 1 \
    --action-top-k 1 \
    --mem-top-k-eval 1 \
    --session-mode fixed-length \
    --chunk-size 512 \
    --chunk-overlap 64 \
    --dataset locomo \
    --data-file "./data/locomo10.json" \
    --model "deepseek-chat" \
    --designer-model "deepseek-chat" \
    --llm-judge-model "deepseek-chat" \
    --api \
    --api-base "https://api.deepseek.com" \
    --retriever contriever \
    --state-encoder sentence-transformers/all-MiniLM-L6-v2 \
    --op-encoder sentence-transformers/all-MiniLM-L6-v2 \
    --encode-batch-size 8 \
    --reward-metric f1 \
    --device cuda \
    --enable-skill-tree \
    --skill-tree-dir "$CANDIDATE_SKILL_TREE_DIR" \
    --skill-tree-top-k 3 \
    --skill-tree-max-depth 4 \
    --enable-negative-memory \
    --negative-memory-dir "$NEGATIVE_MEMORY_DIR" \
    --negative-memory-top-k "$NEGATIVE_MEMORY_TOP_K" \
    --negative-memory-max-chars "$NEGATIVE_MEMORY_MAX_CHARS" \
    --skip-load-snapshot-manager \
    --wandb-run-name "$WANDB_RUN_NAME" \
    --save-dir "$SAVE_DIR" \
    --out-file "$OUT_FILE"
