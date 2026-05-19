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
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Pattern, Tuple


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


def compile_patterns(patterns: Iterable[str]) -> List[Pattern[str]]:
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]


BASELINE_RISK_PATTERNS = compile_patterns([
    r"\bwhich country\b",
    r"\bwhich us state\b",
    r"\bwhich state\b",
    r"\bwould\b.+\bprefer\b",
    r"\bdoes\b.+\blive close\b",
    r"\bwhat role\b",
    r"\bconsidering\b",
    r"\bbased on\b",
    r"\bin light of\b",
    r"\bhow do\b",
    r"\bhow might\b",
    r"\bwhat challenges\b",
    r"\bwhat advice\b",
    r"\bis it likely\b",
    r"\bunderlying condition\b",
    r"\bbesides\b",
    r"\bboth\b.+\b(and|or)\b",
])


def normalize_question(question: str) -> str:
    return " ".join((question or "").strip().lower().split())


def route_question(question: str, mode: str) -> Tuple[str, str]:
    text = normalize_question(question)
    if mode == "candidate_all":
        return "candidate", "candidate_all"
    if mode == "baseline_all":
        return "baseline", "baseline_all"
    if mode != "risk_baseline_v1":
        raise ValueError(f"Unknown router mode: {mode}")

    for pattern in BASELINE_RISK_PATTERNS:
        if pattern.search(text):
            return "baseline", f"risk:{pattern.pattern}"
    return "candidate", "default_candidate"


def metric(row: Row, prefix: str, name: str) -> float:
    return as_float(row.get(f"{prefix}_{name}", ""))


def summarize(rows: List[Row], mode: str) -> Tuple[List[Row], List[Row]]:
    grouped: Dict[str, List[Tuple[Row, str, str]]] = defaultdict(list)
    reason_counts: Counter[Tuple[str, str, str]] = Counter()

    for row in rows:
        prefix, reason = route_question(row.get("question", ""), mode)
        category = row.get("category", "") or "<missing>"
        grouped[category].append((row, prefix, reason))
        grouped["ALL"].append((row, prefix, reason))
        reason_counts[(category, prefix, reason)] += 1
        reason_counts[("ALL", prefix, reason)] += 1

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

    reason_rows = [
        {
            "category": category,
            "selected": selected,
            "reason": reason,
            "rows": str(count),
        }
        for (category, selected, reason), count in sorted(reason_counts.items())
    ]
    return summary_rows, reason_rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question_compare_tsv", type=Path)
    parser.add_argument(
        "--mode",
        choices=["risk_baseline_v1", "candidate_all", "baseline_all"],
        default="risk_baseline_v1",
    )
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--reasons-out", type=Path, default=None)
    args = parser.parse_args()

    rows = read_rows(args.question_compare_tsv)
    if not rows:
        raise SystemExit("No rows found.")
    required = [
        "question",
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
        args.question_compare_tsv.stem + f"_question_router_{args.mode}.tsv"
    )
    reasons_path = args.reasons_out or args.question_compare_tsv.with_name(
        args.question_compare_tsv.stem + f"_question_router_{args.mode}_reasons.tsv"
    )
    summary_rows, reason_rows = summarize(rows, args.mode)

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
    reason_fields = ["category", "selected", "reason", "rows"]
    write_rows(out_path, summary_rows, summary_fields)
    write_rows(reasons_path, reason_rows, reason_fields)
    print(f"Wrote question-router summary: {out_path}")
    print(f"Wrote question-router reasons: {reasons_path}")
    print(f"Rows: {len(rows)}")
    print(f"Mode: {args.mode}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
