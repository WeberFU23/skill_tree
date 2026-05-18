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
MEMORY_CACHE_SUFFIX="${MEMORY_CACHE_SUFFIX:-locomo_skill_tree_eval}"
OUT_FILE="${OUT_FILE:-./results/locomo_skill_tree_eval.json}"
WANDB_RUN_NAME="${WANDB_RUN_NAME:-locomo-skill-tree-eval}"
NEGATIVE_MEMORY_ARGS=()
if [[ -n "${NEGATIVE_MEMORY_MIN_SCORE:-}" ]]; then
    NEGATIVE_MEMORY_ARGS+=(--negative-memory-min-score "$NEGATIVE_MEMORY_MIN_SCORE")
fi
if [[ "${NEGATIVE_MEMORY_MATCH_CATEGORY:-0}" == "1" ]]; then
    NEGATIVE_MEMORY_ARGS+=(--negative-memory-match-category)
fi
if [[ -n "${NEGATIVE_MEMORY_MATCH_CATEGORIES:-}" ]]; then
    read -r -a MATCH_CATEGORIES <<< "$NEGATIVE_MEMORY_MATCH_CATEGORIES"
    NEGATIVE_MEMORY_ARGS+=(--negative-memory-match-categories "${MATCH_CATEGORIES[@]}")
fi

python -B main.py \
    --disable-flash-attn \
    --memory-cache-suffix "$MEMORY_CACHE_SUFFIX" \
    --overwrite \
    --eval-only \
    --inference-workers 1 \
    --inference-session-workers 1 \
    --action-top-k 1 \
    --mem-top-k-eval 1 \
    --session-mode fixed-length \
    --chunk-size 512 \
    --chunk-overlap 64 \
    --load-checkpoint "./checkpoints/locomo_skill_tree/locomo-skill-tree-train_epoch_final.pt" \
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
    --skill-tree-dir ./skills_memory \
    --skill-tree-top-k 3 \
    --skill-tree-max-depth 4 \
    --enable-negative-memory \
    --negative-memory-dir "$NEGATIVE_MEMORY_DIR" \
    --negative-memory-top-k "$NEGATIVE_MEMORY_TOP_K" \
    --negative-memory-max-chars "$NEGATIVE_MEMORY_MAX_CHARS" \
    "${NEGATIVE_MEMORY_ARGS[@]}" \
    --skip-load-snapshot-manager \
    --wandb-run-name "$WANDB_RUN_NAME" \
    --save-dir ./checkpoints/locomo_skill_tree \
    --out-file "$OUT_FILE"
