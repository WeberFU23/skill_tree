#!/bin/bash
set -euo pipefail

: "${DEEPSEEK_API_KEY:?Set DEEPSEEK_API_KEY before running this script}"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export WANDB_MODE="${WANDB_MODE:-offline}"
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"

NEGATIVE_MEMORY_TOP_K="${NEGATIVE_MEMORY_TOP_K:-2}"
NEGATIVE_MEMORY_ARGS=()
if [[ -n "${NEGATIVE_MEMORY_MIN_SCORE:-}" ]]; then
    NEGATIVE_MEMORY_ARGS+=(--negative-memory-min-score "$NEGATIVE_MEMORY_MIN_SCORE")
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
    --skill-tree-dir ./skills_memory \
    --skill-tree-top-k 3 \
    --skill-tree-max-depth 4 \
    --enable-skill-tree-evolution \
    --skill-tree-evolution-min-cases 5 \
    --skill-tree-evolution-max-buckets 1 \
    --enable-negative-memory \
    --negative-memory-dir ./negative_memories \
    --negative-memory-top-k "$NEGATIVE_MEMORY_TOP_K" \
    "${NEGATIVE_MEMORY_ARGS[@]}" \
    --auto-record-negative-memory \
    --negative-memory-write-limit 20 \
    --wandb-run-name locomo-skill-tree-train \
    --save-dir ./checkpoints/locomo_skill_tree \
    --out-file ./results/locomo_skill_tree_train.json
