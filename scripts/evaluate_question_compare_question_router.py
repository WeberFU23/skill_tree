#!/usr/bin/env python3
"""Evaluate a text-only router over question comparison rows.

Input is the TSV written by ``compare_locomo_repeat_questions.py``. The router
chooses either the baseline or candidate prediction for each question using only
the question text. This is a diagnostic for whether an automatic route between
two checkpoints can approach an oracle category-routed hybrid.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.question_router import route_question as shared_route_question


Row = Dict[str, str]
RoutedRow = Tuple[Row, str, str]


def as_float(value: str) -> float:
    try:
        if value is None or value == "":
            return math.nan
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def format_float(value: float) -> str:
    if math.isnan(value):
        return ""
    return f"{value:.4f}"


def format_signed(value: float) -> str:
    if math.isnan(value):
        return ""
    return f"{value:+.4f}"


def mean_std(values: Iterable[float]) -> Tuple[float, float]:
    clean = [value for value in values if not math.isnan(value)]
    if not clean:
        return math.nan, math.nan
    mean = sum(clean) / len(clean)
    var = sum((value - mean) ** 2 for value in clean) / len(clean)
    return mean, math.sqrt(max(var, 0.0))


def read_rows(path: Path) -> List[Row]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_rows(path: Path, rows: List[Row], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def safe_filename(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return safe.strip("_") or "router"


def route_question(question: str, mode: str) -> Tuple[str, str]:
    return shared_route_question(question, mode)


def metric(row: Row, prefix: str, name: str) -> float:
    return as_float(row.get(f"{prefix}_{name}", ""))


def route_rows(rows: List[Row], mode: str) -> List[RoutedRow]:
    return [(row, *route_question(row.get("question", ""), mode)) for row in rows]


def summarize(routed_rows: List[RoutedRow]) -> Tuple[List[Row], List[Row], List[Row]]:
    grouped: Dict[str, List[RoutedRow]] = defaultdict(list)
    reason_groups: Dict[Tuple[str, str, str], List[RoutedRow]] = defaultdict(list)
    run_groups: Dict[str, List[RoutedRow]] = defaultdict(list)

    for row, prefix, reason in routed_rows:
        category = row.get("category", "") or "<missing>"
        run = row.get("run", "") or "<missing>"
        grouped[category].append((row, prefix, reason))
        grouped["ALL"].append((row, prefix, reason))
        reason_groups[(category, prefix, reason)].append((row, prefix, reason))
        reason_groups[("ALL", prefix, reason)].append((row, prefix, reason))
        run_groups[run].append((row, prefix, reason))

    summary_rows: List[Row] = []
    for category, items in sorted(grouped.items(), key=lambda pair: (pair[0] != "ALL", pair[0])):
        baseline_f1 = [metric(row, "baseline", "f1") for row, _, _ in items]
        candidate_f1 = [metric(row, "candidate", "f1") for row, _, _ in items]
        baseline_judge = [metric(row, "baseline", "llm_judge") for row, _, _ in items]
        candidate_judge = [metric(row, "candidate", "llm_judge") for row, _, _ in items]
        router_f1 = [metric(row, prefix, "f1") for row, prefix, _ in items]
        router_judge = [metric(row, prefix, "llm_judge") for row, prefix, _ in items]
        selected_counts = Counter(prefix for _, prefix, _ in items)

        base_f1_mean, base_f1_std = mean_std(baseline_f1)
        cand_f1_mean, cand_f1_std = mean_std(candidate_f1)
        router_f1_mean, router_f1_std = mean_std(router_f1)
        base_judge_mean, base_judge_std = mean_std(baseline_judge)
        cand_judge_mean, cand_judge_std = mean_std(candidate_judge)
        router_judge_mean, router_judge_std = mean_std(router_judge)

        summary_rows.append({
            "category": category,
            "rows": str(len(items)),
            "selected_baseline_rows": str(selected_counts["baseline"]),
            "selected_candidate_rows": str(selected_counts["candidate"]),
            "baseline_f1_mean": format_float(base_f1_mean),
            "baseline_f1_std": format_float(base_f1_std),
            "candidate_f1_mean": format_float(cand_f1_mean),
            "candidate_f1_std": format_float(cand_f1_std),
            "router_f1_mean": format_float(router_f1_mean),
            "router_f1_std": format_float(router_f1_std),
            "router_delta_vs_baseline_f1": format_signed(router_f1_mean - base_f1_mean),
            "router_delta_vs_candidate_f1": format_signed(router_f1_mean - cand_f1_mean),
            "baseline_llm_judge_mean": format_float(base_judge_mean),
            "baseline_llm_judge_std": format_float(base_judge_std),
            "candidate_llm_judge_mean": format_float(cand_judge_mean),
            "candidate_llm_judge_std": format_float(cand_judge_std),
            "router_llm_judge_mean": format_float(router_judge_mean),
            "router_llm_judge_std": format_float(router_judge_std),
            "router_delta_vs_baseline_llm_judge": format_signed(router_judge_mean - base_judge_mean),
            "router_delta_vs_candidate_llm_judge": format_signed(router_judge_mean - cand_judge_mean),
        })

    reason_rows: List[Row] = []
    for (category, selected, reason), items in sorted(reason_groups.items()):
        baseline_f1 = [metric(row, "baseline", "f1") for row, _, _ in items]
        candidate_f1 = [metric(row, "candidate", "f1") for row, _, _ in items]
        router_f1 = [metric(row, prefix, "f1") for row, prefix, _ in items]
        baseline_judge = [metric(row, "baseline", "llm_judge") for row, _, _ in items]
        candidate_judge = [metric(row, "candidate", "llm_judge") for row, _, _ in items]
        router_judge = [metric(row, prefix, "llm_judge") for row, prefix, _ in items]
        base_f1_mean, _ = mean_std(baseline_f1)
        cand_f1_mean, _ = mean_std(candidate_f1)
        router_f1_mean, _ = mean_std(router_f1)
        base_judge_mean, _ = mean_std(baseline_judge)
        cand_judge_mean, _ = mean_std(candidate_judge)
        router_judge_mean, _ = mean_std(router_judge)

        reason_rows.append({
            "category": category,
            "selected": selected,
            "reason": reason,
            "rows": str(len(items)),
            "baseline_f1_mean": format_float(base_f1_mean),
            "candidate_f1_mean": format_float(cand_f1_mean),
            "router_f1_mean": format_float(router_f1_mean),
            "router_delta_vs_baseline_f1": format_signed(router_f1_mean - base_f1_mean),
            "router_delta_vs_candidate_f1": format_signed(router_f1_mean - cand_f1_mean),
            "baseline_llm_judge_mean": format_float(base_judge_mean),
            "candidate_llm_judge_mean": format_float(cand_judge_mean),
            "router_llm_judge_mean": format_float(router_judge_mean),
            "router_delta_vs_baseline_llm_judge": format_signed(router_judge_mean - base_judge_mean),
            "router_delta_vs_candidate_llm_judge": format_signed(router_judge_mean - cand_judge_mean),
        })
    run_rows: List[Row] = []
    for run, items in sorted(run_groups.items(), key=lambda pair: int(pair[0]) if pair[0].isdigit() else pair[0]):
        baseline_f1 = [metric(row, "baseline", "f1") for row, _, _ in items]
        candidate_f1 = [metric(row, "candidate", "f1") for row, _, _ in items]
        router_f1 = [metric(row, prefix, "f1") for row, prefix, _ in items]
        baseline_judge = [metric(row, "baseline", "llm_judge") for row, _, _ in items]
        candidate_judge = [metric(row, "candidate", "llm_judge") for row, _, _ in items]
        router_judge = [metric(row, prefix, "llm_judge") for row, prefix, _ in items]
        selected_counts = Counter(prefix for _, prefix, _ in items)
        base_f1_mean, _ = mean_std(baseline_f1)
        cand_f1_mean, _ = mean_std(candidate_f1)
        router_f1_mean, _ = mean_std(router_f1)
        base_judge_mean, _ = mean_std(baseline_judge)
        cand_judge_mean, _ = mean_std(candidate_judge)
        router_judge_mean, _ = mean_std(router_judge)
        run_rows.append({
            "run": run,
            "rows": str(len(items)),
            "selected_baseline_rows": str(selected_counts["baseline"]),
            "selected_candidate_rows": str(selected_counts["candidate"]),
            "baseline_f1": format_float(base_f1_mean),
            "candidate_f1": format_float(cand_f1_mean),
            "router_f1": format_float(router_f1_mean),
            "baseline_llm_judge": format_float(base_judge_mean),
            "candidate_llm_judge": format_float(cand_judge_mean),
            "router_llm_judge": format_float(router_judge_mean),
        })
    return summary_rows, reason_rows, run_rows


def build_selected_rows(routed_rows: List[RoutedRow]) -> List[Row]:
    output_rows: List[Row] = []
    for row, prefix, reason in routed_rows:
        selected_f1 = metric(row, prefix, "f1")
        selected_judge = metric(row, prefix, "llm_judge")
        output_rows.append({
            "run": row.get("run", ""),
            "category": row.get("category", ""),
            "sample_id": row.get("sample_id", ""),
            "qa_idx": row.get("qa_idx", ""),
            "question": row.get("question", ""),
            "ground_truth": row.get("ground_truth", ""),
            "selected": prefix,
            "selected_reason": reason,
            "selected_prediction": row.get(f"{prefix}_prediction", ""),
            "selected_f1": format_float(selected_f1),
            "selected_llm_judge": format_float(selected_judge),
            "baseline_prediction": row.get("baseline_prediction", ""),
            "candidate_prediction": row.get("candidate_prediction", ""),
            "baseline_f1": row.get("baseline_f1", ""),
            "candidate_f1": row.get("candidate_f1", ""),
            "baseline_llm_judge": row.get("baseline_llm_judge", ""),
            "candidate_llm_judge": row.get("candidate_llm_judge", ""),
            "selected_negative_memories": row.get(f"{prefix}_negative_memories", ""),
            "selected_retrieved_memories": row.get(f"{prefix}_retrieved_memories", ""),
        })
    return output_rows


def json_float(value: float) -> Any:
    if math.isnan(value):
        return None
    return value


def compact_context_list(value: str) -> List[str]:
    return [value] if value else []


def materialized_record(row: Row, prefix: str, reason: str) -> Dict[str, Any]:
    selected_f1 = metric(row, prefix, "f1")
    selected_judge = metric(row, prefix, "llm_judge")
    return {
        "sample_id": row.get("sample_id", ""),
        "qa_idx": row.get("qa_idx", ""),
        "category": row.get("category", ""),
        "question": row.get("question", ""),
        "ground_truth": row.get("ground_truth", ""),
        "prediction": row.get(f"{prefix}_prediction", ""),
        "f1": json_float(selected_f1),
        "llm_judge": json_float(selected_judge),
        "router_selected": prefix,
        "router_reason": reason,
        "baseline_prediction": row.get("baseline_prediction", ""),
        "candidate_prediction": row.get("candidate_prediction", ""),
        "baseline_f1": json_float(metric(row, "baseline", "f1")),
        "candidate_f1": json_float(metric(row, "candidate", "f1")),
        "baseline_llm_judge": json_float(metric(row, "baseline", "llm_judge")),
        "candidate_llm_judge": json_float(metric(row, "candidate", "llm_judge")),
        "negative_memories": compact_context_list(row.get(f"{prefix}_negative_memories", "")),
        "retrieved_memories": compact_context_list(row.get(f"{prefix}_retrieved_memories", "")),
    }


def sort_key(value: str) -> Tuple[int, Any]:
    if str(value).isdigit():
        return (0, int(value))
    return (1, value)


def write_router_log(path: Path, items: List[RoutedRow], f1: float, judge: float) -> None:
    by_category: Dict[str, List[RoutedRow]] = defaultdict(list)
    for row, prefix, reason in items:
        by_category[row.get("category", "") or "<missing>"].append((row, prefix, reason))

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write("=" * 80 + "\n")
        handle.write("locomo Evaluation (question-router materialized output)\n")
        handle.write("=" * 80 + "\n")
        handle.write(f"Total queries: {len(items)}\n")
        handle.write(f"F1: {format_float(f1)}\n")
        handle.write(f"LLM Judge: {format_float(judge)}\n\n")
        handle.write("By category:\n")
        for category, category_items in sorted(by_category.items(), key=lambda pair: sort_key(pair[0])):
            cat_f1, _ = mean_std(metric(row, prefix, "f1") for row, prefix, _ in category_items)
            cat_judge, _ = mean_std(metric(row, prefix, "llm_judge") for row, prefix, _ in category_items)
            handle.write(
                f"Category {category}: F1={format_float(cat_f1)}, "
                f"LLM Judge={format_float(cat_judge)}\n"
            )


def materialize_repeat_outputs(
    routed_rows: List[RoutedRow],
    *,
    mode: str,
    config_name: str,
    output_dir: Path,
    summary_path: Path,
) -> List[Row]:
    run_groups: Dict[str, List[RoutedRow]] = defaultdict(list)
    for row, prefix, reason in routed_rows:
        run_groups[row.get("run", "") or "<missing>"].append((row, prefix, reason))

    output_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = output_dir / "logs"
    safe_config = safe_filename(config_name)
    summary_rows: List[Row] = []
    for run, items in sorted(run_groups.items(), key=lambda pair: sort_key(pair[0])):
        selected_counts = Counter(prefix for _, prefix, _ in items)
        f1, _ = mean_std(metric(row, prefix, "f1") for row, prefix, _ in items)
        judge, _ = mean_std(metric(row, prefix, "llm_judge") for row, prefix, _ in items)
        safe_run = safe_filename(f"r{run}")
        out_file = output_dir / f"{safe_config}_{safe_run}.json"
        log_file = logs_dir / f"{safe_config}_{safe_run}.log"
        records = [materialized_record(row, prefix, reason) for row, prefix, reason in items]
        with out_file.open("w", encoding="utf-8") as handle:
            json.dump(
                {
                    "config": config_name,
                    "router_mode": mode,
                    "run": run,
                    "metrics": {
                        "f1": json_float(f1),
                        "llm_judge": json_float(judge),
                        "total_queries": len(items),
                        "selected_baseline_rows": selected_counts["baseline"],
                        "selected_candidate_rows": selected_counts["candidate"],
                    },
                    "results": records,
                },
                handle,
                ensure_ascii=False,
                indent=2,
            )
            handle.write("\n")
        write_router_log(log_file, items, f1, judge)
        summary_rows.append({
            "config": config_name,
            "run": run,
            "router_mode": mode,
            "selected_baseline_rows": str(selected_counts["baseline"]),
            "selected_candidate_rows": str(selected_counts["candidate"]),
            "f1": format_float(f1),
            "llm_judge": format_float(judge),
            "log": str(log_file),
            "out_file": str(out_file),
        })

    summary_fields = [
        "config",
        "run",
        "router_mode",
        "selected_baseline_rows",
        "selected_candidate_rows",
        "f1",
        "llm_judge",
        "log",
        "out_file",
    ]
    write_rows(summary_path, summary_rows, summary_fields)
    return summary_rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question_compare_tsv", type=Path)
    parser.add_argument(
        "--mode",
        choices=[
            "risk_baseline_v1",
            "risk_profile_baseline_v1",
            "risk_profile_baseline_v2",
            "risk_profile_baseline_v3",
            "risk_profile_baseline_v4",
            "candidate_all",
            "baseline_all",
        ],
        default="risk_baseline_v1",
    )
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--reasons-out", type=Path, default=None)
    parser.add_argument("--runs-out", type=Path, default=None)
    parser.add_argument("--selected-out", type=Path, default=None)
    parser.add_argument("--repeat-summary-out", type=Path, default=None)
    parser.add_argument("--materialized-dir", type=Path, default=None)
    parser.add_argument("--config-name", default=None)
    parser.add_argument("--no-materialize", action="store_true")
    args = parser.parse_args()

    rows = read_rows(args.question_compare_tsv)
    if not rows:
        raise SystemExit("No rows found.")
    required = [
        "question",
        "category",
        "baseline_prediction",
        "candidate_prediction",
        "baseline_f1",
        "candidate_f1",
        "baseline_llm_judge",
        "candidate_llm_judge",
    ]
    missing = [column for column in required if column not in rows[0]]
    if missing:
        available = ", ".join(rows[0].keys())
        raise SystemExit(f"Missing required columns {missing}. Available columns: {available}")

    out_path = args.out or args.question_compare_tsv.with_name(
        args.question_compare_tsv.stem + f"_question_router_{args.mode}.tsv"
    )
    reasons_path = args.reasons_out or args.question_compare_tsv.with_name(
        args.question_compare_tsv.stem + f"_question_router_{args.mode}_reasons.tsv"
    )
    runs_path = args.runs_out or args.question_compare_tsv.with_name(
        args.question_compare_tsv.stem + f"_question_router_{args.mode}_runs.tsv"
    )
    selected_path = args.selected_out or args.question_compare_tsv.with_name(
        args.question_compare_tsv.stem + f"_question_router_{args.mode}_selected.tsv"
    )
    repeat_summary_path = args.repeat_summary_out or args.question_compare_tsv.with_name(
        args.question_compare_tsv.stem + f"_question_router_{args.mode}_repeat_summary.tsv"
    )
    materialized_dir = args.materialized_dir or args.question_compare_tsv.with_name(
        args.question_compare_tsv.stem + f"_question_router_{args.mode}_materialized"
    )
    config_name = args.config_name or f"question_router_{args.mode}"
    routed_rows = route_rows(rows, args.mode)
    summary_rows, reason_rows, run_rows = summarize(routed_rows)
    selected_rows = build_selected_rows(routed_rows)

    summary_fields = [
        "category",
        "rows",
        "selected_baseline_rows",
        "selected_candidate_rows",
        "baseline_f1_mean",
        "baseline_f1_std",
        "candidate_f1_mean",
        "candidate_f1_std",
        "router_f1_mean",
        "router_f1_std",
        "router_delta_vs_baseline_f1",
        "router_delta_vs_candidate_f1",
        "baseline_llm_judge_mean",
        "baseline_llm_judge_std",
        "candidate_llm_judge_mean",
        "candidate_llm_judge_std",
        "router_llm_judge_mean",
        "router_llm_judge_std",
        "router_delta_vs_baseline_llm_judge",
        "router_delta_vs_candidate_llm_judge",
    ]
    reason_fields = [
        "category",
        "selected",
        "reason",
        "rows",
        "baseline_f1_mean",
        "candidate_f1_mean",
        "router_f1_mean",
        "router_delta_vs_baseline_f1",
        "router_delta_vs_candidate_f1",
        "baseline_llm_judge_mean",
        "candidate_llm_judge_mean",
        "router_llm_judge_mean",
        "router_delta_vs_baseline_llm_judge",
        "router_delta_vs_candidate_llm_judge",
    ]
    run_fields = [
        "run",
        "rows",
        "selected_baseline_rows",
        "selected_candidate_rows",
        "baseline_f1",
        "candidate_f1",
        "router_f1",
        "baseline_llm_judge",
        "candidate_llm_judge",
        "router_llm_judge",
    ]
    write_rows(out_path, summary_rows, summary_fields)
    write_rows(reasons_path, reason_rows, reason_fields)
    write_rows(runs_path, run_rows, run_fields)
    selected_fields = [
        "run",
        "category",
        "sample_id",
        "qa_idx",
        "question",
        "ground_truth",
        "selected",
        "selected_reason",
        "selected_prediction",
        "selected_f1",
        "selected_llm_judge",
        "baseline_prediction",
        "candidate_prediction",
        "baseline_f1",
        "candidate_f1",
        "baseline_llm_judge",
        "candidate_llm_judge",
        "selected_negative_memories",
        "selected_retrieved_memories",
    ]
    write_rows(selected_path, selected_rows, selected_fields)
    if not args.no_materialize:
        materialize_repeat_outputs(
            routed_rows,
            mode=args.mode,
            config_name=config_name,
            output_dir=materialized_dir,
            summary_path=repeat_summary_path,
        )
    print(f"Wrote question-router summary: {out_path}")
    print(f"Wrote question-router reasons: {reasons_path}")
    print(f"Wrote question-router runs: {runs_path}")
    print(f"Wrote question-router selected rows: {selected_path}")
    if not args.no_materialize:
        print(f"Wrote materialized router repeat summary: {repeat_summary_path}")
        print(f"Wrote materialized router outputs: {materialized_dir}")
    router_f1_mean, router_f1_std = mean_std(as_float(row["router_f1"]) for row in run_rows)
    router_judge_mean, router_judge_std = mean_std(as_float(row["router_llm_judge"]) for row in run_rows)
    print(
        "Router repeat mean over {n} runs: F1={f1_mean:.4f} +/- {f1_std:.4f}, "
        "LLM Judge={judge_mean:.4f} +/- {judge_std:.4f}".format(
            n=len(run_rows),
            f1_mean=router_f1_mean,
            f1_std=router_f1_std,
            judge_mean=router_judge_mean,
            judge_std=router_judge_std,
        )
    )
    print(f"Rows: {len(rows)}")
    print(f"Mode: {args.mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
