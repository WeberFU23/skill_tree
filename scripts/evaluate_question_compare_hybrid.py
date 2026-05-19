#!/usr/bin/env python3
"""Evaluate a category-routed hybrid from question comparison rows.

Input is the TSV written by ``compare_locomo_repeat_questions.py``. The hybrid
uses candidate predictions for categories listed in ``--candidate-categories``
and baseline predictions for all other categories. This is an oracle diagnostic
when benchmark category labels are used; treat it as an upper bound for a future
question-router, not as a final comparable system.
"""
from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


Row = Dict[str, str]


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


def metric(row: Row, prefix: str, name: str) -> float:
    return as_float(row.get(f"{prefix}_{name}", ""))


def selected_prefix(row: Row, candidate_categories: set[str]) -> str:
    category = row.get("category", "")
    return "candidate" if category in candidate_categories else "baseline"


def summarize(rows: List[Row], candidate_categories: set[str]) -> List[Row]:
    grouped: Dict[str, List[Row]] = defaultdict(list)
    for row in rows:
        grouped[row.get("category", "") or "<missing>"].append(row)
        grouped["ALL"].append(row)

    output: List[Row] = []
    for category, items in sorted(grouped.items(), key=lambda pair: (pair[0] != "ALL", pair[0])):
        baseline_f1 = [metric(row, "baseline", "f1") for row in items]
        candidate_f1 = [metric(row, "candidate", "f1") for row in items]
        baseline_judge = [metric(row, "baseline", "llm_judge") for row in items]
        candidate_judge = [metric(row, "candidate", "llm_judge") for row in items]

        hybrid_f1 = []
        hybrid_judge = []
        selected_counts = defaultdict(int)
        for row in items:
            prefix = selected_prefix(row, candidate_categories)
            selected_counts[prefix] += 1
            hybrid_f1.append(metric(row, prefix, "f1"))
            hybrid_judge.append(metric(row, prefix, "llm_judge"))

        base_f1_mean, base_f1_std = mean_std(baseline_f1)
        cand_f1_mean, cand_f1_std = mean_std(candidate_f1)
        hybrid_f1_mean, hybrid_f1_std = mean_std(hybrid_f1)
        base_judge_mean, base_judge_std = mean_std(baseline_judge)
        cand_judge_mean, cand_judge_std = mean_std(candidate_judge)
        hybrid_judge_mean, hybrid_judge_std = mean_std(hybrid_judge)

        output.append({
            "category": category,
            "rows": str(len(items)),
            "selected_baseline_rows": str(selected_counts["baseline"]),
            "selected_candidate_rows": str(selected_counts["candidate"]),
            "baseline_f1_mean": format_float(base_f1_mean),
            "baseline_f1_std": format_float(base_f1_std),
            "candidate_f1_mean": format_float(cand_f1_mean),
            "candidate_f1_std": format_float(cand_f1_std),
            "hybrid_f1_mean": format_float(hybrid_f1_mean),
            "hybrid_f1_std": format_float(hybrid_f1_std),
            "hybrid_delta_vs_baseline_f1": format_signed(hybrid_f1_mean - base_f1_mean),
            "hybrid_delta_vs_candidate_f1": format_signed(hybrid_f1_mean - cand_f1_mean),
            "baseline_llm_judge_mean": format_float(base_judge_mean),
            "baseline_llm_judge_std": format_float(base_judge_std),
            "candidate_llm_judge_mean": format_float(cand_judge_mean),
            "candidate_llm_judge_std": format_float(cand_judge_std),
            "hybrid_llm_judge_mean": format_float(hybrid_judge_mean),
            "hybrid_llm_judge_std": format_float(hybrid_judge_std),
            "hybrid_delta_vs_baseline_llm_judge": format_signed(hybrid_judge_mean - base_judge_mean),
            "hybrid_delta_vs_candidate_llm_judge": format_signed(hybrid_judge_mean - cand_judge_mean),
        })
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question_compare_tsv", type=Path)
    parser.add_argument("--candidate-categories", nargs="+", required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    rows = read_rows(args.question_compare_tsv)
    if not rows:
        raise SystemExit("No rows found.")
    required = [
        "category",
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
        args.question_compare_tsv.stem
        + "_hybrid_candidate_cats_"
        + "_".join(args.candidate_categories)
        + ".tsv"
    )
    output_rows = summarize(rows, set(args.candidate_categories))
    fieldnames = [
        "category",
        "rows",
        "selected_baseline_rows",
        "selected_candidate_rows",
        "baseline_f1_mean",
        "baseline_f1_std",
        "candidate_f1_mean",
        "candidate_f1_std",
        "hybrid_f1_mean",
        "hybrid_f1_std",
        "hybrid_delta_vs_baseline_f1",
        "hybrid_delta_vs_candidate_f1",
        "baseline_llm_judge_mean",
        "baseline_llm_judge_std",
        "candidate_llm_judge_mean",
        "candidate_llm_judge_std",
        "hybrid_llm_judge_mean",
        "hybrid_llm_judge_std",
        "hybrid_delta_vs_baseline_llm_judge",
        "hybrid_delta_vs_candidate_llm_judge",
    ]
    write_rows(out_path, output_rows, fieldnames)
    print(f"Wrote hybrid summary: {out_path}")
    print(f"Rows: {len(rows)}")
    print(f"Candidate categories: {', '.join(args.candidate_categories)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
