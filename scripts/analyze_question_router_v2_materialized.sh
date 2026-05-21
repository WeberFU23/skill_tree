#!/bin/bash
set -euo pipefail

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

REPEAT_DIR="${REPEAT_DIR:-}"
if [[ -z "$REPEAT_DIR" ]]; then
    REPEAT_DIR="$(ls -td "$RUN_DIR"/repeat_eval_* 2>/dev/null | head -n 1 || true)"
fi
if [[ -z "$REPEAT_DIR" || ! -d "$REPEAT_DIR" ]]; then
    echo "[ERROR] Set REPEAT_DIR to an evolved-checkpoint repeat_eval_* directory." >&2
    exit 1
fi

BASELINE_SUMMARY="${BASELINE_SUMMARY:-}"
if [[ -z "$BASELINE_SUMMARY" ]]; then
    BASELINE_SUMMARY="$(ls -td ./results/repeat_locomo_skilltree_curated_agg055_pruned_bad3_*/summary.tsv 2>/dev/null | head -n 1 || true)"
fi
if [[ -z "$BASELINE_SUMMARY" || ! -f "$BASELINE_SUMMARY" ]]; then
    echo "[ERROR] Set BASELINE_SUMMARY to the pruned-bad3 repeat summary.tsv." >&2
    exit 1
fi

EVOLVED_SUMMARY="${EVOLVED_SUMMARY:-$REPEAT_DIR/summary.tsv}"
if [[ ! -f "$EVOLVED_SUMMARY" ]]; then
    echo "[ERROR] Missing evolved checkpoint summary: $EVOLVED_SUMMARY" >&2
    exit 1
fi

summarize_repeat_config() {
    local label="$1"
    local summary_file="$2"
    local wanted_config="$3"
    awk -F '\t' -v label="$label" -v wanted_config="$wanted_config" '
    NR == 1 {
        for (i = 1; i <= NF; i++) {
            col[$i] = i
        }
        next
    }
    {
        if (wanted_config != "" && col["config"] && $(col["config"]) != wanted_config) {
            next
        }
        f1 = $(col["f1"])
        judge = $(col["llm_judge"])
        if (f1 == "" || f1 == "NA" || judge == "" || judge == "NA") {
            next
        }
        n += 1
        f1_sum += f1
        f1_sq += f1 * f1
        judge_sum += judge
        judge_sq += judge * judge
    }
    END {
        if (n == 0) {
            printf "%s\t0\tNA\tNA\tNA\tNA\t%s\n", label, wanted_config
            exit
        }
        f1_mean = f1_sum / n
        judge_mean = judge_sum / n
        f1_std = sqrt((f1_sq / n) - (f1_mean * f1_mean))
        judge_std = sqrt((judge_sq / n) - (judge_mean * judge_mean))
        printf "%s\t%d\t%.4f\t%.4f\t%.4f\t%.4f\t%s\n", label, n, f1_mean, f1_std, judge_mean, judge_std, wanted_config
    }' "$summary_file"
}

BASELINE_CONFIG="${BASELINE_CONFIG:-curated_agg055_pruned_bad3_top1_chars1200}"
EVOLVED_CONFIG="${EVOLVED_CONFIG:-evolved_checkpoint_pruned_bad3_top1_chars1200}"
ROUTER_CONFIG="${ROUTER_CONFIG:-question_router_risk_profile_baseline_v2}"
ROUTER_MODE="${ROUTER_MODE:-risk_profile_baseline_v2}"
QUESTION_COMPARE_ALL="${QUESTION_COMPARE_ALL:-$REPEAT_DIR/question_compare_evolved_checkpoint_vs_pruned_bad3_all.tsv}"
ROUTER_SUMMARY="${ROUTER_SUMMARY:-$REPEAT_DIR/question_compare_evolved_checkpoint_vs_pruned_bad3_all_question_router_${ROUTER_MODE}_repeat_summary.tsv}"

if [[ ! -f "$QUESTION_COMPARE_ALL" ]]; then
    python -B scripts/compare_locomo_repeat_questions.py \
        --summary-tsv "$BASELINE_SUMMARY" "$EVOLVED_SUMMARY" \
        --baseline-config "$BASELINE_CONFIG" \
        --candidate-config "$EVOLVED_CONFIG" \
        --out "$QUESTION_COMPARE_ALL"
fi

if [[ ! -f "$ROUTER_SUMMARY" ]]; then
    python -B scripts/evaluate_question_compare_question_router.py \
        "$QUESTION_COMPARE_ALL" \
        --mode "$ROUTER_MODE" \
        --config-name "$ROUTER_CONFIG"
fi

ROUTER_CATEGORY_SUMMARY="$REPEAT_DIR/question_router_${ROUTER_MODE}_category_summary.tsv"
ROUTER_VS_BASELINE="$REPEAT_DIR/question_compare_${ROUTER_CONFIG}_vs_pruned_bad3_all.tsv"
ROUTER_VS_EVOLVED="$REPEAT_DIR/question_compare_${ROUTER_CONFIG}_vs_evolved_checkpoint_all.tsv"
ROUTER_VS_BASELINE_CATEGORY_SUMMARY="${ROUTER_VS_BASELINE%.tsv}_category_summary.tsv"
ROUTER_VS_EVOLVED_CATEGORY_SUMMARY="${ROUTER_VS_EVOLVED%.tsv}_category_summary.tsv"
OVERALL_SUMMARY="$REPEAT_DIR/question_router_${ROUTER_MODE}_overall_summary.tsv"
REPORT_FILE="$REPEAT_DIR/question_router_${ROUTER_MODE}_report.md"
ROUTER_REPEAT_DIR="${ROUTER_REPEAT_DIR:-$REPEAT_DIR/question_router_${ROUTER_MODE}_repeat}"
ROUTER_MATERIALIZED_DIR="${ROUTER_SUMMARY%_repeat_summary.tsv}_materialized"

python -B scripts/summarize_locomo_repeat_categories.py \
    "$ROUTER_SUMMARY" \
    --config-name "$ROUTER_CONFIG" \
    --out "$ROUTER_CATEGORY_SUMMARY"

python -B scripts/compare_locomo_repeat_questions.py \
    --summary-tsv "$BASELINE_SUMMARY" "$ROUTER_SUMMARY" \
    --baseline-config "$BASELINE_CONFIG" \
    --candidate-config "$ROUTER_CONFIG" \
    --out "$ROUTER_VS_BASELINE"

python -B scripts/summarize_question_compare_deltas.py "$ROUTER_VS_BASELINE"

python -B scripts/compare_locomo_repeat_questions.py \
    --summary-tsv "$EVOLVED_SUMMARY" "$ROUTER_SUMMARY" \
    --baseline-config "$EVOLVED_CONFIG" \
    --candidate-config "$ROUTER_CONFIG" \
    --out "$ROUTER_VS_EVOLVED"

python -B scripts/summarize_question_compare_deltas.py "$ROUTER_VS_EVOLVED"

{
    printf "label\tn\tf1_mean\tf1_std\tllm_judge_mean\tllm_judge_std\tconfig\n"
    summarize_repeat_config "pruned_bad3" "$BASELINE_SUMMARY" "$BASELINE_CONFIG"
    summarize_repeat_config "evolved_checkpoint" "$EVOLVED_SUMMARY" "$EVOLVED_CONFIG"
    summarize_repeat_config "$ROUTER_CONFIG" "$ROUTER_SUMMARY" "$ROUTER_CONFIG"
} > "$OVERALL_SUMMARY"

python -B scripts/write_question_router_report.py \
    --repeat-dir "$REPEAT_DIR" \
    --router-mode "$ROUTER_MODE" \
    --router-config "$ROUTER_CONFIG" \
    --out "$REPORT_FILE"

if [[ -d "$ROUTER_MATERIALIZED_DIR" ]]; then
    mkdir -p "$ROUTER_REPEAT_DIR/logs"
    find "$ROUTER_MATERIALIZED_DIR" -maxdepth 1 -type f -name '*.json' \
        -exec cp {} "$ROUTER_REPEAT_DIR/" \;
    if [[ -d "$ROUTER_MATERIALIZED_DIR/logs" ]]; then
        find "$ROUTER_MATERIALIZED_DIR/logs" -maxdepth 1 -type f -name '*.log' \
            -exec cp {} "$ROUTER_REPEAT_DIR/logs/" \;
    fi
    awk -F '\t' -v OFS='\t' -v repeat_dir="$ROUTER_REPEAT_DIR" '
    NR == 1 {
        for (i = 1; i <= NF; i++) {
            if ($i == "log") {
                log_col = i
            }
            if ($i == "out_file") {
                out_col = i
            }
        }
        print
        next
    }
    {
        if (log_col) {
            n = split($log_col, log_parts, "/")
            $log_col = repeat_dir "/logs/" log_parts[n]
        }
        if (out_col) {
            n = split($out_col, out_parts, "/")
            $out_col = repeat_dir "/" out_parts[n]
        }
        print
    }' "$ROUTER_SUMMARY" > "$ROUTER_REPEAT_DIR/summary.tsv"
    cp "$OVERALL_SUMMARY" "$ROUTER_REPEAT_DIR/overall_summary.tsv"
    cp "$ROUTER_CATEGORY_SUMMARY" "$ROUTER_REPEAT_DIR/category_summary.tsv"
    cp "$REPORT_FILE" "$ROUTER_REPEAT_DIR/report.md"
fi

echo
echo "================================================================================"
echo "Router v2 materialized analysis outputs"
echo "================================================================================"
echo "router_summary=$ROUTER_SUMMARY"
echo "router_category_summary=$ROUTER_CATEGORY_SUMMARY"
echo "router_vs_pruned_bad3=$ROUTER_VS_BASELINE"
echo "router_vs_pruned_bad3_category_summary=$ROUTER_VS_BASELINE_CATEGORY_SUMMARY"
echo "router_vs_evolved_checkpoint=$ROUTER_VS_EVOLVED"
echo "router_vs_evolved_checkpoint_category_summary=$ROUTER_VS_EVOLVED_CATEGORY_SUMMARY"
echo "overall_summary=$OVERALL_SUMMARY"
echo "report=$REPORT_FILE"
echo "canonical_repeat_dir=$ROUTER_REPEAT_DIR"
echo "canonical_repeat_summary=$ROUTER_REPEAT_DIR/summary.tsv"
echo "canonical_report=$ROUTER_REPEAT_DIR/report.md"
echo

echo "Overall repeat summary"
column -t -s $'\t' "$OVERALL_SUMMARY" || cat "$OVERALL_SUMMARY"

echo
echo "Router category summary"
column -t -s $'\t' "$ROUTER_CATEGORY_SUMMARY" || cat "$ROUTER_CATEGORY_SUMMARY"

echo
echo "Router vs pruned bad3 category deltas"
column -t -s $'\t' "$ROUTER_VS_BASELINE_CATEGORY_SUMMARY" || cat "$ROUTER_VS_BASELINE_CATEGORY_SUMMARY"

echo
echo "Router vs evolved checkpoint category deltas"
column -t -s $'\t' "$ROUTER_VS_EVOLVED_CATEGORY_SUMMARY" || cat "$ROUTER_VS_EVOLVED_CATEGORY_SUMMARY"
