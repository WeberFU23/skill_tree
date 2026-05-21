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

BASE_ROUTER_MODE="${BASE_ROUTER_MODE:-risk_profile_baseline_v2}"
CANDIDATE_ROUTER_MODE="${CANDIDATE_ROUTER_MODE:-risk_profile_baseline_v3}"
BASE_ROUTER_CONFIG="${BASE_ROUTER_CONFIG:-question_router_${BASE_ROUTER_MODE}_end2end}"
CANDIDATE_ROUTER_CONFIG="${CANDIDATE_ROUTER_CONFIG:-question_router_${CANDIDATE_ROUTER_MODE}_end2end}"

BASE_SUMMARY="${BASE_SUMMARY:-}"
if [[ -z "$BASE_SUMMARY" ]]; then
    BASE_SUMMARY="$(ls -td "$RUN_DIR"/question_router_"$BASE_ROUTER_MODE"_end2end_repeat_*/summary.tsv 2>/dev/null | head -n 1 || true)"
fi
if [[ -z "$BASE_SUMMARY" || ! -f "$BASE_SUMMARY" ]]; then
    echo "[ERROR] Set BASE_SUMMARY to the baseline router end-to-end summary.tsv." >&2
    exit 1
fi

CANDIDATE_SUMMARY="${CANDIDATE_SUMMARY:-}"
if [[ -z "$CANDIDATE_SUMMARY" ]]; then
    CANDIDATE_SUMMARY="$(ls -td "$RUN_DIR"/question_router_"$CANDIDATE_ROUTER_MODE"_end2end_repeat_*/summary.tsv 2>/dev/null | head -n 1 || true)"
fi
if [[ -z "$CANDIDATE_SUMMARY" || ! -f "$CANDIDATE_SUMMARY" ]]; then
    echo "[ERROR] Set CANDIDATE_SUMMARY to the candidate router end-to-end summary.tsv." >&2
    exit 1
fi

OUT_DIR="${OUT_DIR:-}"
if [[ -z "$OUT_DIR" ]]; then
    OUT_DIR="$(cd "$(dirname "$CANDIDATE_SUMMARY")" && pwd)"
fi
mkdir -p "$OUT_DIR"

COMPARE_TSV="${COMPARE_TSV:-$OUT_DIR/question_compare_${CANDIDATE_ROUTER_CONFIG}_vs_${BASE_ROUTER_CONFIG}_all.tsv}"
CATEGORY_SUMMARY="${COMPARE_TSV%.tsv}_category_summary.tsv"
BASE_REASON_SUMMARY="${COMPARE_TSV%.tsv}_baseline_router_category_reason_summary.tsv"
CANDIDATE_REASON_SUMMARY="${COMPARE_TSV%.tsv}_candidate_router_category_reason_summary.tsv"
VERSION_SUMMARY="${VERSION_SUMMARY:-$OUT_DIR/question_router_end2end_version_summary.tsv}"

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
        baseline_rows = col["selected_baseline_rows"] ? $(col["selected_baseline_rows"]) : 0
        candidate_rows = col["selected_candidate_rows"] ? $(col["selected_candidate_rows"]) : 0
        if (f1 == "" || f1 == "NA" || judge == "" || judge == "NA") {
            next
        }
        n += 1
        f1_sum += f1
        f1_sq += f1 * f1
        judge_sum += judge
        judge_sq += judge * judge
        baseline_sum += baseline_rows
        candidate_sum += candidate_rows
    }
    END {
        if (n == 0) {
            printf "%s\t0\tNA\tNA\tNA\tNA\tNA\tNA\t%s\n", label, wanted_config
            exit
        }
        f1_mean = f1_sum / n
        judge_mean = judge_sum / n
        f1_std = sqrt((f1_sq / n) - (f1_mean * f1_mean))
        judge_std = sqrt((judge_sq / n) - (judge_mean * judge_mean))
        printf "%s\t%d\t%.4f\t%.4f\t%.4f\t%.4f\t%.1f\t%.1f\t%s\n",
            label, n, f1_mean, f1_std, judge_mean, judge_std,
            baseline_sum / n, candidate_sum / n, wanted_config
    }' "$summary_file"
}

python -B scripts/compare_locomo_repeat_questions.py \
    --summary-tsv "$BASE_SUMMARY" "$CANDIDATE_SUMMARY" \
    --baseline-config "$BASE_ROUTER_CONFIG" \
    --candidate-config "$CANDIDATE_ROUTER_CONFIG" \
    --out "$COMPARE_TSV"

python -B scripts/summarize_question_compare_deltas.py "$COMPARE_TSV"
python -B scripts/summarize_question_compare_deltas.py \
    "$COMPARE_TSV" \
    --group-by baseline_router_category_reason \
    --out "$BASE_REASON_SUMMARY"
python -B scripts/summarize_question_compare_deltas.py \
    "$COMPARE_TSV" \
    --group-by candidate_router_category_reason \
    --out "$CANDIDATE_REASON_SUMMARY"

{
    printf "label\tn\tf1_mean\tf1_std\tllm_judge_mean\tllm_judge_std\tselected_baseline_rows_mean\tselected_candidate_rows_mean\tconfig\n"
    summarize_repeat_config "$BASE_ROUTER_CONFIG" "$BASE_SUMMARY" "$BASE_ROUTER_CONFIG"
    summarize_repeat_config "$CANDIDATE_ROUTER_CONFIG" "$CANDIDATE_SUMMARY" "$CANDIDATE_ROUTER_CONFIG"
} > "$VERSION_SUMMARY"

echo
echo "================================================================================"
echo "Question-router end-to-end version comparison"
echo "================================================================================"
echo "base_summary=$BASE_SUMMARY"
echo "candidate_summary=$CANDIDATE_SUMMARY"
echo "version_summary=$VERSION_SUMMARY"
echo "question_compare=$COMPARE_TSV"
echo "category_summary=$CATEGORY_SUMMARY"
echo "baseline_reason_summary=$BASE_REASON_SUMMARY"
echo "candidate_reason_summary=$CANDIDATE_REASON_SUMMARY"
echo

echo "Overall version summary"
column -t -s $'\t' "$VERSION_SUMMARY" || cat "$VERSION_SUMMARY"

echo
echo "Candidate minus baseline category deltas"
column -t -s $'\t' "$CATEGORY_SUMMARY" || cat "$CATEGORY_SUMMARY"

echo
echo "Candidate minus baseline deltas by baseline route reason"
column -t -s $'\t' "$BASE_REASON_SUMMARY" || cat "$BASE_REASON_SUMMARY"

echo
echo "Candidate minus baseline deltas by candidate route reason"
column -t -s $'\t' "$CANDIDATE_REASON_SUMMARY" || cat "$CANDIDATE_REASON_SUMMARY"
