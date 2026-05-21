#!/bin/bash
set -euo pipefail

: "${DEEPSEEK_API_KEY:?Set DEEPSEEK_API_KEY before running this script}"

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

REPEATS="${REPEATS:-3}"
QUESTION_ROUTER_MODE="${QUESTION_ROUTER_MODE:-risk_profile_baseline_v2}"
CONFIG_NAME="${CONFIG_NAME:-question_router_${QUESTION_ROUTER_MODE}_end2end}"
REPEAT_DIR="${REPEAT_DIR:-$RUN_DIR/question_router_${QUESTION_ROUTER_MODE}_end2end_repeat_$(date +%Y%m%d_%H%M%S)}"

mkdir -p "$REPEAT_DIR/logs"
SUMMARY_FILE="$REPEAT_DIR/summary.tsv"
printf "config\trun\trouter_mode\tselected_baseline_rows\tselected_candidate_rows\tf1\tllm_judge\tlog\tout_file\n" > "$SUMMARY_FILE"

extract_metric() {
    local label="$1"
    local log_file="$2"
    grep -E "^${label}:" "$log_file" | tail -n 1 | awk '{print $NF}' || true
}

extract_selected() {
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
    local selected_baseline
    local selected_candidate
    f1="$(extract_metric "F1" "$log_file")"
    judge="$(extract_metric "LLM Judge" "$log_file")"
    selected_baseline="$(extract_selected "Selected baseline rows" "$log_file")"
    selected_candidate="$(extract_selected "Selected candidate rows" "$log_file")"
    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
        "$CONFIG_NAME" "$run_id" "$QUESTION_ROUTER_MODE" \
        "${selected_baseline:-NA}" "${selected_candidate:-NA}" \
        "${f1:-NA}" "${judge:-NA}" "$log_file" "$out_file" | tee -a "$SUMMARY_FILE"
}

for run_id in $(seq 1 "$REPEATS"); do
    name="${CONFIG_NAME}_r${run_id}"
    log_file="$REPEAT_DIR/logs/${name}.log"
    out_file="$REPEAT_DIR/${name}.json"
    echo
    echo "================================================================================"
    echo "Running end-to-end question-router repeat ${run_id}/${REPEATS}: $name"
    echo "RUN_DIR=$RUN_DIR"
    echo "OUT_FILE=$out_file"
    echo "================================================================================"
    RUN_DIR="$RUN_DIR" \
    QUESTION_ROUTER_MODE="$QUESTION_ROUTER_MODE" \
    MEMORY_CACHE_SUFFIX="repeat_${name}" \
    OUT_FILE="$out_file" \
    WANDB_RUN_NAME="locomo-repeat-${name}" \
        bash "$SCRIPT_DIR/eval_locomo_question_router_v2_end2end.sh" 2>&1 | tee "$log_file"
    record_summary "$run_id" "$log_file" "$out_file"
done

echo
echo "================================================================================"
echo "End-to-end question-router repeat summary: $SUMMARY_FILE"
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
