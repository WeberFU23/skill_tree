#!/bin/bash
set -euo pipefail

: "${DEEPSEEK_API_KEY:?Set DEEPSEEK_API_KEY before running this script}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

REPEATS="${REPEATS:-3}"
RUN_DIR="${RUN_DIR:-}"
if [[ -z "$RUN_DIR" ]]; then
    RUN_DIR="$(ls -td ./results/skill_tree_evolution_pruned_bad3_* 2>/dev/null | head -n 1 || true)"
fi
if [[ -z "$RUN_DIR" || ! -d "$RUN_DIR" ]]; then
    echo "[ERROR] Set RUN_DIR to a skill_tree_evolution_pruned_bad3_* result directory." >&2
    exit 1
fi

EVOLVED_SKILL_TREE_DIR="${EVOLVED_SKILL_TREE_DIR:-$RUN_DIR/skills_memory}"
PRUNED_NEGATIVE_MEMORY_DIR="${PRUNED_NEGATIVE_MEMORY_DIR:-./curated_negative_memories_agg055_pruned_bad3}"
SAVE_DIR="${SAVE_DIR:-./checkpoints/locomo_skill_tree_evolved_bad3}"
LOAD_CHECKPOINT="${LOAD_CHECKPOINT:-$SAVE_DIR/locomo-skill-tree-evolve-bad3_epoch_final.pt}"
NEGATIVE_MEMORY_TOP_K="${NEGATIVE_MEMORY_TOP_K:-1}"
NEGATIVE_MEMORY_MAX_CHARS="${NEGATIVE_MEMORY_MAX_CHARS:-1200}"
CONFIG_NAME="${CONFIG_NAME:-evolved_checkpoint_pruned_bad3_top${NEGATIVE_MEMORY_TOP_K}_chars${NEGATIVE_MEMORY_MAX_CHARS}}"
REPEAT_DIR="${REPEAT_DIR:-$RUN_DIR/repeat_eval_$(date +%Y%m%d_%H%M%S)}"

if [[ ! -d "$EVOLVED_SKILL_TREE_DIR" ]]; then
    echo "[ERROR] Missing skill-tree dir: $EVOLVED_SKILL_TREE_DIR" >&2
    exit 1
fi
if [[ ! -f "$LOAD_CHECKPOINT" ]]; then
    echo "[ERROR] Missing checkpoint: $LOAD_CHECKPOINT" >&2
    exit 1
fi

OUTPUT_DIR="$PRUNED_NEGATIVE_MEMORY_DIR" bash "$SCRIPT_DIR/make_locomo_curated_agg055_pruned_bad3.sh"

mkdir -p "$REPEAT_DIR/logs"

SUMMARY_FILE="$REPEAT_DIR/summary.tsv"
printf "config\trun\tskill_tree_dir\tload_checkpoint\tnegative_dir\tnegative_top_k\tnegative_max_chars\tf1\tllm_judge\tlog\tout_file\n" > "$SUMMARY_FILE"

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
    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
        "$CONFIG_NAME" "$run_id" "$EVOLVED_SKILL_TREE_DIR" "$LOAD_CHECKPOINT" \
        "$PRUNED_NEGATIVE_MEMORY_DIR" "$NEGATIVE_MEMORY_TOP_K" "$NEGATIVE_MEMORY_MAX_CHARS" \
        "${f1:-NA}" "${judge:-NA}" "$log_file" "$out_file" | tee -a "$SUMMARY_FILE"
}

for run_id in $(seq 1 "$REPEATS"); do
    name="${CONFIG_NAME}_r${run_id}"
    log_file="$REPEAT_DIR/logs/${name}.log"
    out_file="$REPEAT_DIR/${name}.json"

    echo
    echo "================================================================================"
    echo "Running repeat ${run_id}/${REPEATS}: ${name}"
    echo "RUN_DIR=${RUN_DIR}"
    echo "SKILL_TREE_DIR=${EVOLVED_SKILL_TREE_DIR}"
    echo "LOAD_CHECKPOINT=${LOAD_CHECKPOINT}"
    echo "NEGATIVE_MEMORY_DIR=${PRUNED_NEGATIVE_MEMORY_DIR}"
    echo "NEGATIVE_MEMORY_TOP_K=${NEGATIVE_MEMORY_TOP_K} NEGATIVE_MEMORY_MAX_CHARS=${NEGATIVE_MEMORY_MAX_CHARS}"
    echo "================================================================================"

    SKILL_TREE_DIR="$EVOLVED_SKILL_TREE_DIR" \
    SAVE_DIR="$SAVE_DIR" \
    LOAD_CHECKPOINT="$LOAD_CHECKPOINT" \
    NEGATIVE_MEMORY_DIR="$PRUNED_NEGATIVE_MEMORY_DIR" \
    NEGATIVE_MEMORY_TOP_K="$NEGATIVE_MEMORY_TOP_K" \
    NEGATIVE_MEMORY_MAX_CHARS="$NEGATIVE_MEMORY_MAX_CHARS" \
    MEMORY_CACHE_SUFFIX="repeat_${name}" \
    OUT_FILE="$out_file" \
    WANDB_RUN_NAME="locomo-repeat-${name}" \
        bash "$SCRIPT_DIR/eval_locomo_skilltree_negmem.sh" 2>&1 | tee "$log_file"

    record_summary "$run_id" "$log_file" "$out_file"
done

echo
echo "================================================================================"
echo "Repeat summary: $SUMMARY_FILE"
echo "================================================================================"
column -t -s $'\t' "$SUMMARY_FILE" || cat "$SUMMARY_FILE"

awk -F '\t' '
NR > 1 && $8 != "NA" && $9 != "NA" {
    n += 1
    f1 += $8
    f1_sq += $8 * $8
    judge += $9
    judge_sq += $9 * $9
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
