#!/bin/bash
set -euo pipefail

: "${DEEPSEEK_API_KEY:?Set DEEPSEEK_API_KEY before running this script}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

REPEATS="${REPEATS:-3}"
REPEAT_DIR="${REPEAT_DIR:-./results/repeat_locomo_skilltree_core_configs_$(date +%Y%m%d_%H%M%S)}"
RAW_NEGATIVE_MEMORY_DIR="${RAW_NEGATIVE_MEMORY_DIR:-./negative_memories}"
CURATED_NEGATIVE_MEMORY_DIR="${CURATED_NEGATIVE_MEMORY_DIR:-./curated_negative_memories_agg055}"
RAW_NEGATIVE_MEMORY_TOP_K="${RAW_NEGATIVE_MEMORY_TOP_K:-2}"
CURATED_NEGATIVE_MEMORY_TOP_K="${CURATED_NEGATIVE_MEMORY_TOP_K:-1}"
NEGATIVE_MEMORY_MAX_CHARS="${NEGATIVE_MEMORY_MAX_CHARS:-1200}"

mkdir -p "$REPEAT_DIR/logs"

SUMMARY_FILE="$REPEAT_DIR/summary.tsv"
printf "config\trun\tnegative_dir\tnegative_top_k\tnegative_max_chars\tf1\tllm_judge\tlog\tout_file\n" > "$SUMMARY_FILE"

extract_metric() {
    local label="$1"
    local log_file="$2"
    grep -E "^${label}:" "$log_file" | tail -n 1 | awk '{print $NF}' || true
}

record_summary() {
    local config="$1"
    local run_id="$2"
    local negative_dir="$3"
    local negative_top_k="$4"
    local negative_max_chars="$5"
    local log_file="$6"
    local out_file="$7"
    local f1
    local judge
    f1="$(extract_metric "F1" "$log_file")"
    judge="$(extract_metric "LLM Judge" "$log_file")"
    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
        "$config" "$run_id" "$negative_dir" "$negative_top_k" "$negative_max_chars" \
        "${f1:-NA}" "${judge:-NA}" "$log_file" "$out_file" | tee -a "$SUMMARY_FILE"
}

run_case() {
    local config="$1"
    local run_id="$2"
    local script_path="$3"
    local negative_dir="$4"
    local negative_top_k="$5"
    local negative_max_chars="$6"

    local name="${config}_r${run_id}"
    local log_file="$REPEAT_DIR/logs/${name}.log"
    local out_file="$REPEAT_DIR/${name}.json"

    echo
    echo "================================================================================"
    echo "Running ${config}, repeat ${run_id}/${REPEATS}"
    echo "negative_dir=${negative_dir}"
    echo "negative_top_k=${negative_top_k} negative_max_chars=${negative_max_chars}"
    echo "================================================================================"

    if [[ "$config" == "no_negative" ]]; then
        MEMORY_CACHE_SUFFIX="repeat_${name}" \
        OUT_FILE="$out_file" \
        WANDB_RUN_NAME="locomo-repeat-${name}" \
            bash "$script_path" 2>&1 | tee "$log_file"
    else
        NEGATIVE_MEMORY_DIR="$negative_dir" \
        NEGATIVE_MEMORY_TOP_K="$negative_top_k" \
        NEGATIVE_MEMORY_MAX_CHARS="$negative_max_chars" \
        MEMORY_CACHE_SUFFIX="repeat_${name}" \
        OUT_FILE="$out_file" \
        WANDB_RUN_NAME="locomo-repeat-${name}" \
            bash "$script_path" 2>&1 | tee "$log_file"
    fi

    record_summary "$config" "$run_id" "$negative_dir" "$negative_top_k" "$negative_max_chars" "$log_file" "$out_file"
}

if [[ ! -d "$CURATED_NEGATIVE_MEMORY_DIR" ]]; then
    echo "[WARN] Curated negative-memory directory not found: $CURATED_NEGATIVE_MEMORY_DIR"
    echo "[WARN] The curated config will still run, but the store may be empty unless this directory exists on the run machine."
fi

for run_id in $(seq 1 "$REPEATS"); do
    run_case \
        "no_negative" \
        "$run_id" \
        "$SCRIPT_DIR/eval_locomo_skilltree_nonegmem.sh" \
        "none" \
        "0" \
        "0"

    run_case \
        "raw_top${RAW_NEGATIVE_MEMORY_TOP_K}" \
        "$run_id" \
        "$SCRIPT_DIR/eval_locomo_skilltree_negmem.sh" \
        "$RAW_NEGATIVE_MEMORY_DIR" \
        "$RAW_NEGATIVE_MEMORY_TOP_K" \
        "$NEGATIVE_MEMORY_MAX_CHARS"

    run_case \
        "curated_agg055_top${CURATED_NEGATIVE_MEMORY_TOP_K}_chars${NEGATIVE_MEMORY_MAX_CHARS}" \
        "$run_id" \
        "$SCRIPT_DIR/eval_locomo_skilltree_negmem_curated_agg055.sh" \
        "$CURATED_NEGATIVE_MEMORY_DIR" \
        "$CURATED_NEGATIVE_MEMORY_TOP_K" \
        "$NEGATIVE_MEMORY_MAX_CHARS"
done

echo
echo "================================================================================"
echo "Core-config repeat summary: $SUMMARY_FILE"
echo "================================================================================"
column -t -s $'\t' "$SUMMARY_FILE" || cat "$SUMMARY_FILE"

echo
echo "================================================================================"
echo "Mean/std by config"
echo "================================================================================"
awk -F '\t' '
NR > 1 && $6 != "NA" && $7 != "NA" {
    cfg = $1
    n[cfg] += 1
    f1[cfg] += $6
    f1_sq[cfg] += $6 * $6
    judge[cfg] += $7
    judge_sq[cfg] += $7 * $7
}
END {
    printf "%-42s %5s %16s %20s\n", "config", "n", "F1 mean +/- std", "LLM Judge mean +/- std"
    for (cfg in n) {
        f1_mean = f1[cfg] / n[cfg]
        judge_mean = judge[cfg] / n[cfg]
        f1_var = (f1_sq[cfg] / n[cfg]) - (f1_mean * f1_mean)
        judge_var = (judge_sq[cfg] / n[cfg]) - (judge_mean * judge_mean)
        if (f1_var < 0) f1_var = 0
        if (judge_var < 0) judge_var = 0
        printf "%-42s %5d %7.4f +/- %-7.4f %9.4f +/- %-7.4f\n", \
            cfg, n[cfg], f1_mean, sqrt(f1_var), judge_mean, sqrt(judge_var)
    }
}
' "$SUMMARY_FILE"
