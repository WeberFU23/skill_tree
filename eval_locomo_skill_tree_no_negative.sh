#!/bin/bash
set -euo pipefail

: "${DEEPSEEK_API_KEY:?Set DEEPSEEK_API_KEY before running this script}"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export WANDB_MODE="${WANDB_MODE:-offline}"
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"

python -B main.py \
    --disable-flash-attn \
    --memory-cache-suffix "locomo_skill_tree_no_negative" \
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
    --skip-load-snapshot-manager \
    --wandb-run-name locomo-skill-tree-no-negative \
    --save-dir ./checkpoints/locomo_skill_tree \
    --out-file ./results/locomo_skill_tree_no_negative.json
