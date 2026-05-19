#!/bin/bash
set -euo pipefail

: "${DEEPSEEK_API_KEY:?Set DEEPSEEK_API_KEY before running this script}"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export WANDB_MODE="${WANDB_MODE:-offline}"
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"

NEGATIVE_MEMORY_TOP_K="${NEGATIVE_MEMORY_TOP_K:-2}"
NEGATIVE_MEMORY_DIR="${NEGATIVE_MEMORY_DIR:-./negative_memories}"
NEGATIVE_MEMORY_MAX_CHARS="${NEGATIVE_MEMORY_MAX_CHARS:-1200}"
SKILL_TREE_DIR="${SKILL_TREE_DIR:-./skills_memory}"
SAVE_DIR="${SAVE_DIR:-./checkpoints/locomo_skill_tree}"
OUT_FILE="${OUT_FILE:-./results/locomo_skill_tree_train.json}"
WANDB_RUN_NAME="${WANDB_RUN_NAME:-locomo-skill-tree-train}"
SKILL_TREE_EVOLUTION_MIN_CASES="${SKILL_TREE_EVOLUTION_MIN_CASES:-5}"
SKILL_TREE_EVOLUTION_MAX_BUCKETS="${SKILL_TREE_EVOLUTION_MAX_BUCKETS:-1}"
AUTO_RECORD_NEGATIVE_MEMORY="${AUTO_RECORD_NEGATIVE_MEMORY:-1}"
NEGATIVE_MEMORY_WRITE_LIMIT="${NEGATIVE_MEMORY_WRITE_LIMIT:-20}"
NEGATIVE_MEMORY_ARGS=()
if [[ -n "${NEGATIVE_MEMORY_MIN_SCORE:-}" ]]; then
    NEGATIVE_MEMORY_ARGS+=(--negative-memory-min-score "$NEGATIVE_MEMORY_MIN_SCORE")
fi
AUTO_RECORD_ARGS=()
if [[ "$AUTO_RECORD_NEGATIVE_MEMORY" == "1" ]]; then
    AUTO_RECORD_ARGS+=(--auto-record-negative-memory --negative-memory-write-limit "$NEGATIVE_MEMORY_WRITE_LIMIT")
fi

python -B main.py \
    --disable-flash-attn \
    --dataset locomo \
    --data-file "./data/locomo10.json" \
    --model "deepseek-chat" \
    --designer-model "deepseek-chat" \
    --api \
    --api-base "https://api.deepseek.com" \
    --retriever contriever \
    --state-encoder sentence-transformers/all-MiniLM-L6-v2 \
    --op-encoder sentence-transformers/all-MiniLM-L6-v2 \
    --designer-freq 1 \
    --inner-epochs 1 \
    --outer-epochs 1 \
    --batch-size 1 \
    --encode-batch-size 8 \
    --session-mode full-session \
    --ppo-epochs 1 \
    --action-top-k 1 \
    --mem-top-k 1 \
    --mem-top-k-eval 1 \
    --reward-metric f1 \
    --device cuda \
    --enable-skill-tree \
    --skill-tree-dir "$SKILL_TREE_DIR" \
    --skill-tree-top-k 3 \
    --skill-tree-max-depth 4 \
    --enable-skill-tree-evolution \
    --skill-tree-evolution-min-cases "$SKILL_TREE_EVOLUTION_MIN_CASES" \
    --skill-tree-evolution-max-buckets "$SKILL_TREE_EVOLUTION_MAX_BUCKETS" \
    --enable-negative-memory \
    --negative-memory-dir "$NEGATIVE_MEMORY_DIR" \
    --negative-memory-top-k "$NEGATIVE_MEMORY_TOP_K" \
    --negative-memory-max-chars "$NEGATIVE_MEMORY_MAX_CHARS" \
    "${NEGATIVE_MEMORY_ARGS[@]}" \
    "${AUTO_RECORD_ARGS[@]}" \
    --wandb-run-name "$WANDB_RUN_NAME" \
    --save-dir "$SAVE_DIR" \
    --out-file "$OUT_FILE"
