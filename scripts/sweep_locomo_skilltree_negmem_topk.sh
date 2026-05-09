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

SWEEP_DIR="${SWEEP_DIR:-./results/negative_memory_sweep_$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$SWEEP_DIR/logs"

SUMMARY_FILE="$SWEEP_DIR/summary.tsv"
printf "case\tnegative_top_k\tnegative_min_score\tf1\tllm_judge\tlog\n" > "$SUMMARY_FILE"

extract_metric() {
    local label="$1"
    local log_file="$2"
    grep -E "^${label}:" "$log_file" | tail -n 1 | awk '{print $NF}' || true
}

record_summary() {
    local name="$1"
    local top_k="$2"
    local min_score="$3"
    local log_file="$4"
    local f1
    local judge
    f1="$(extract_metric "F1" "$log_file")"
    judge="$(extract_metric "LLM Judge" "$log_file")"
    printf "%s\t%s\t%s\t%s\t%s\t%s\n" \
        "$name" "$top_k" "${min_score:-none}" "${f1:-NA}" "${judge:-NA}" "$log_file" \
        | tee -a "$SUMMARY_FILE"
}

run_no_negative() {
    local name="no_negative"
    local log_file="$SWEEP_DIR/logs/${name}.log"
    echo
    echo "================================================================================"
    echo "Running sweep case: ${name}"
    echo "================================================================================"
    MEMORY_CACHE_SUFFIX="sweep_${name}" \
    OUT_FILE="$SWEEP_DIR/${name}.json" \
    WANDB_RUN_NAME="locomo-sweep-${name}" \
        bash "$SCRIPT_DIR/eval_locomo_skilltree_nonegmem.sh" 2>&1 | tee "$log_file"
    record_summary "$name" "0" "" "$log_file"
}

run_negative_case() {
    local name="$1"
    local top_k="$2"
    local min_score="${3:-}"
    local log_file="$SWEEP_DIR/logs/${name}.log"
    echo
    echo "================================================================================"
    echo "Running sweep case: ${name}"
    echo "NEGATIVE_MEMORY_TOP_K=${top_k} NEGATIVE_MEMORY_MIN_SCORE=${min_score:-unset}"
    echo "================================================================================"
    if [[ -n "$min_score" ]]; then
        NEGATIVE_MEMORY_TOP_K="$top_k" \
        NEGATIVE_MEMORY_MIN_SCORE="$min_score" \
        MEMORY_CACHE_SUFFIX="sweep_${name}" \
        OUT_FILE="$SWEEP_DIR/${name}.json" \
        WANDB_RUN_NAME="locomo-sweep-${name}" \
            bash "$SCRIPT_DIR/eval_locomo_skilltree_negmem.sh" 2>&1 | tee "$log_file"
    else
        NEGATIVE_MEMORY_TOP_K="$top_k" \
        MEMORY_CACHE_SUFFIX="sweep_${name}" \
        OUT_FILE="$SWEEP_DIR/${name}.json" \
        WANDB_RUN_NAME="locomo-sweep-${name}" \
            bash "$SCRIPT_DIR/eval_locomo_skilltree_negmem.sh" 2>&1 | tee "$log_file"
    fi
    record_summary "$name" "$top_k" "$min_score" "$log_file"
}

run_no_negative
run_negative_case "top1" "1"
run_negative_case "top2" "2"
run_negative_case "top3" "3"
run_negative_case "top3_score035" "3" "0.35"

echo
echo "================================================================================"
echo "Sweep summary: $SUMMARY_FILE"
echo "================================================================================"
column -t -s $'\t' "$SUMMARY_FILE" || cat "$SUMMARY_FILE"
