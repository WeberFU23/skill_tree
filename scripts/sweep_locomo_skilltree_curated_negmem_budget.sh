#!/bin/bash
set -euo pipefail

: "${DEEPSEEK_API_KEY:?Set DEEPSEEK_API_KEY before running this script}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-0}"
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
export WANDB_MODE="${WANDB_MODE:-offline}"
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"

NEGATIVE_MEMORY_DIR="${NEGATIVE_MEMORY_DIR:-./curated_negative_memories_agg055}"
SWEEP_DIR="${SWEEP_DIR:-./results/curated_negative_memory_budget_sweep_$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$SWEEP_DIR/logs"

SUMMARY_FILE="$SWEEP_DIR/summary.tsv"
printf "case\tnegative_dir\tnegative_top_k\tnegative_max_chars\tf1\tllm_judge\tlog\n" > "$SUMMARY_FILE"

extract_metric() {
    local label="$1"
    local log_file="$2"
    grep -E "^${label}:" "$log_file" | tail -n 1 | awk '{print $NF}' || true
}

record_summary() {
    local name="$1"
    local top_k="$2"
    local max_chars="$3"
    local log_file="$4"
    local f1
    local judge
    f1="$(extract_metric "F1" "$log_file")"
    judge="$(extract_metric "LLM Judge" "$log_file")"
    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
        "$name" "$NEGATIVE_MEMORY_DIR" "$top_k" "$max_chars" \
        "${f1:-NA}" "${judge:-NA}" "$log_file" | tee -a "$SUMMARY_FILE"
}

run_case() {
    local top_k="$1"
    local max_chars="$2"
    local name="curated_top${top_k}_chars${max_chars}"
    local log_file="$SWEEP_DIR/logs/${name}.log"

    echo
    echo "================================================================================"
    echo "Running curated negative-memory budget case: ${name}"
    echo "NEGATIVE_MEMORY_DIR=${NEGATIVE_MEMORY_DIR}"
    echo "NEGATIVE_MEMORY_TOP_K=${top_k} NEGATIVE_MEMORY_MAX_CHARS=${max_chars}"
    echo "================================================================================"

    NEGATIVE_MEMORY_DIR="$NEGATIVE_MEMORY_DIR" \
    NEGATIVE_MEMORY_TOP_K="$top_k" \
    NEGATIVE_MEMORY_MAX_CHARS="$max_chars" \
    MEMORY_CACHE_SUFFIX="sweep_${name}" \
    OUT_FILE="$SWEEP_DIR/${name}.json" \
    WANDB_RUN_NAME="locomo-sweep-${name}" \
        bash "$SCRIPT_DIR/eval_locomo_skilltree_negmem_curated.sh" 2>&1 | tee "$log_file"

    record_summary "$name" "$top_k" "$max_chars" "$log_file"
}

run_case 1 900
run_case 1 1200
run_case 1 1800
run_case 2 900
run_case 2 1200
run_case 2 1800
run_case 3 1200
run_case 3 1800

echo
echo "================================================================================"
echo "Curated budget sweep summary: $SUMMARY_FILE"
echo "================================================================================"
column -t -s $'\t' "$SUMMARY_FILE" || cat "$SUMMARY_FILE"
