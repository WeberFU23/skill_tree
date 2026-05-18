#!/bin/bash
set -euo pipefail

: "${DEEPSEEK_API_KEY:?Set DEEPSEEK_API_KEY before running this script}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

REPEATS="${REPEATS:-3}"
NEGATIVE_MEMORY_DIR="${NEGATIVE_MEMORY_DIR:-./curated_negative_memories_agg055}"
NEGATIVE_MEMORY_TOP_K="${NEGATIVE_MEMORY_TOP_K:-1}"
NEGATIVE_MEMORY_MAX_CHARS="${NEGATIVE_MEMORY_MAX_CHARS:-1200}"
CONFIG_NAME="${CONFIG_NAME:-curated_agg055_top${NEGATIVE_MEMORY_TOP_K}_chars${NEGATIVE_MEMORY_MAX_CHARS}}"
REPEAT_DIR="${REPEAT_DIR:-./results/repeat_locomo_skilltree_curated_agg055_$(date +%Y%m%d_%H%M%S)}"

mkdir -p "$REPEAT_DIR/logs"

SUMMARY_FILE="$REPEAT_DIR/summary.tsv"
printf "config\trun\tnegative_dir\tnegative_top_k\tnegative_max_chars\tf1\tllm_judge\tlog\tout_file\n" > "$SUMMARY_FILE"

extract_metric() {
    local label="$1"
    local log_file="$2"
    grep -E "^${label}:" "$log_file" | tail -n 1 | awk '{print $NF}' || true
}

record_summary() {
    local run_id="$1"
    local log_file="$2"
    local out_file="$3"
    local f1
    local judge
    f1="$(extract_metric "F1" "$log_file")"
    judge="$(extract_metric "LLM Judge" "$log_file")"
    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
        "$CONFIG_NAME" "$run_id" "$NEGATIVE_MEMORY_DIR" "$NEGATIVE_MEMORY_TOP_K" "$NEGATIVE_MEMORY_MAX_CHARS" \
        "${f1:-NA}" "${judge:-NA}" "$log_file" "$out_file" | tee -a "$SUMMARY_FILE"
}

for run_id in $(seq 1 "$REPEATS"); do
    name="${CONFIG_NAME}_r${run_id}"
    log_file="$REPEAT_DIR/logs/${name}.log"
    out_file="$REPEAT_DIR/${name}.json"

    echo
    echo "================================================================================"
    echo "Running repeat ${run_id}/${REPEATS}: ${name}"
    echo "NEGATIVE_MEMORY_DIR=${NEGATIVE_MEMORY_DIR}"
    echo "NEGATIVE_MEMORY_TOP_K=${NEGATIVE_MEMORY_TOP_K} NEGATIVE_MEMORY_MAX_CHARS=${NEGATIVE_MEMORY_MAX_CHARS}"
    echo "================================================================================"

    NEGATIVE_MEMORY_DIR="$NEGATIVE_MEMORY_DIR" \
    NEGATIVE_MEMORY_TOP_K="$NEGATIVE_MEMORY_TOP_K" \
    NEGATIVE_MEMORY_MAX_CHARS="$NEGATIVE_MEMORY_MAX_CHARS" \
    MEMORY_CACHE_SUFFIX="repeat_${name}" \
    OUT_FILE="$out_file" \
    WANDB_RUN_NAME="locomo-repeat-${name}" \
        bash "$SCRIPT_DIR/eval_locomo_skilltree_negmem_curated_agg055.sh" 2>&1 | tee "$log_file"

    record_summary "$run_id" "$log_file" "$out_file"
done

echo
echo "================================================================================"
echo "Repeat summary: $SUMMARY_FILE"
echo "================================================================================"
column -t -s $'\t' "$SUMMARY_FILE" || cat "$SUMMARY_FILE"

awk -F '\t' '
NR > 1 && $6 != "NA" && $7 != "NA" {
    n += 1
    f1 += $6
    f1_sq += $6 * $6
    judge += $7
    judge_sq += $7 * $7
}
END {
    if (n == 0) {
        print "No numeric metrics found."
        exit 0
    }
    f1_mean = f1 / n
    judge_mean = judge / n
    f1_std = sqrt((f1_sq / n) - (f1_mean * f1_mean))
    judge_std = sqrt((judge_sq / n) - (judge_mean * judge_mean))
    printf "Mean over %d runs: F1=%.4f +/- %.4f, LLM Judge=%.4f +/- %.4f\n", n, f1_mean, f1_std, judge_mean, judge_std
}' "$SUMMARY_FILE"
