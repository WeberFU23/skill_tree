#!/bin/bash
set -euo pipefail

: "${DEEPSEEK_API_KEY:?Set DEEPSEEK_API_KEY before running this script}"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export WANDB_MODE="${WANDB_MODE:-offline}"
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"

# Optional:
# export ZHIPU_API_KEY_1="your_first_key"
# export ZHIPU_API_KEY_2="your_second_key"
#
# Use conservative concurrency by default to reduce 429 rate-limit failures.
python main.py \
    --memory-cache-suffix "locomo_eval_lite" \
    --eval-only \
    --inference-workers 1 \
    --inference-session-workers 1 \
    --action-top-k 1 \
    --mem-top-k-eval 3 \
    --session-mode full-session \
    --load-checkpoint "./checkpoints/locomo_with_designer_lite/locomo-train-lite_epoch_final.pt" \
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
    --disable-flash-attn \
    --designer-freq 1 \
    --inner-epochs 2 \
    --outer-epochs 1 \
    --batch-size 1 \
    --encode-batch-size 2 \
    --ppo-epochs 2 \
    --mem-top-k 3 \
    --reward-metric f1 \
    --device cuda \
    --enable-designer \
    --wandb-run-name locomo-eval-lite \
    --save-dir ./checkpoints/locomo_with_designer_lite \
    --out-file ./results/locomo_with_designer_lite_eval.json
