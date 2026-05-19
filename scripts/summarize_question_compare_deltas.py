#!/usr/bin/env python3
"""Summarize question-level comparison deltas by category or another column.

Input is the TSV written by ``compare_locomo_repeat_questions.py``. The script
reports win/loss/tie counts, mean deltas, and representative worst/best
questions for each group.
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


def classify(delta: float, eps: float) -> str:
    if math.isnan(delta) or abs(delta) <= eps:
        return "tie"
    if delta > 0:
        return "win"
    return "loss"


def truncate(text: str, max_chars: int) -> str:
    text = " ".join((text or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def read_rows(path: Path) -> List[Row]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_rows(path: Path, rows: List[Row], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def summarize(
    rows: List[Row],
    group_by: str,
    eps: float,
    max_examples: int,
    max_text_chars: int,
) -> Tuple[List[Row], List[Row]]:
    grouped: Dict[str, List[Row]] = defaultdict(list)
    for row in rows:
        grouped[row.get(group_by, "") or "<missing>"].append(row)

    summary_rows: List[Row] = []
    example_rows: List[Row] = []

    for group, items in grouped.items():
        f1_deltas = [as_float(row.get("delta_f1", "")) for row in items]
        judge_deltas = [as_float(row.get("delta_llm_judge", "")) for row in items]
        f1_labels = [classify(delta, eps) for delta in f1_deltas]
        judge_labels = [classify(delta, eps) for delta in judge_deltas]

        wins = f1_labels.count("win")
        losses = f1_labels.count("loss")
        ties = f1_labels.count("tie")
        judge_wins = judge_labels.count("win")
        judge_losses = judge_labels.count("loss")
        judge_ties = judge_labels.count("tie")
        f1_mean, f1_std = mean_std(f1_deltas)
        judge_mean, judge_std = mean_std(judge_deltas)
        clean_f1 = [value for value in f1_deltas if not math.isnan(value)]
        clean_judge = [value for value in judge_deltas if not math.isnan(value)]
        total = len(items)

        sorted_by_f1 = sorted(items, key=lambda row: as_float(row.get("delta_f1", "")))
        worst = sorted_by_f1[:max_examples]
        best = list(reversed(sorted_by_f1[-max_examples:]))

        summary_rows.append({
            group_by: group,
            "rows": str(total),
            "wins": str(wins),
            "losses": str(losses),
            "ties": str(ties),
            "win_rate": format_float(wins / total if total else math.nan),
            "loss_rate": format_float(losses / total if total else math.nan),
            "mean_delta_f1": format_signed(f1_mean),
            "std_delta_f1": format_float(f1_std),
            "sum_delta_f1": format_signed(sum(clean_f1) if clean_f1 else math.nan),
            "worst_delta_f1": format_signed(min(clean_f1) if clean_f1 else math.nan),
            "best_delta_f1": format_signed(max(clean_f1) if clean_f1 else math.nan),
            "judge_wins": str(judge_wins),
            "judge_losses": str(judge_losses),
            "judge_ties": str(judge_ties),
            "mean_delta_llm_judge": format_signed(judge_mean),
            "std_delta_llm_judge": format_float(judge_std),
            "sum_delta_llm_judge": format_signed(sum(clean_judge) if clean_judge else math.nan),
            "worst_questions": " || ".join(truncate(row.get("question", ""), max_text_chars) for row in worst),
            "best_questions": " || ".join(truncate(row.get("question", ""), max_text_chars) for row in best),
        })

        for direction, selected in (("worst", worst), ("best", best)):
            for row in selected:
                example_rows.append({
                    group_by: group,
                    "direction": direction,
                    "run": row.get("run", ""),
                    "sample_id": row.get("sample_id", ""),
                    "qa_idx": row.get("qa_idx", ""),
                    "delta_f1": row.get("delta_f1", ""),
                    "delta_llm_judge": row.get("delta_llm_judge", ""),
                    "question": row.get("question", ""),
                    "ground_truth": row.get("ground_truth", ""),
                    "baseline_prediction": row.get("baseline_prediction", ""),
                    "candidate_prediction": row.get("candidate_prediction", ""),
                    "baseline_negative_memories": truncate(row.get("baseline_negative_memories", ""), max_text_chars),
                    "candidate_negative_memories": truncate(row.get("candidate_negative_memories", ""), max_text_chars),
                })

    summary_rows.sort(key=lambda row: row[group_by])
    example_rows.sort(key=lambda row: (row[group_by], row["direction"], as_float(row["delta_f1"])))
    return summary_rows, example_rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question_compare_tsv", type=Path)
    parser.add_argument("--group-by", default="category")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--examples-out", type=Path, default=None)
    parser.add_argument("--eps", type=float, default=1e-9)
    parser.add_argument("--max-examples", type=int, default=5)
    parser.add_argument("--max-text-chars", type=int, default=500)
    args = parser.parse_args()

    rows = read_rows(args.question_compare_tsv)
    if rows and args.group_by not in rows[0]:
        available = ", ".join(rows[0].keys())
        raise SystemExit(f"Missing group-by column {args.group_by!r}. Available columns: {available}")

    out_path = args.out or args.question_compare_tsv.with_name(
        args.question_compare_tsv.stem + f"_{args.group_by}_summary.tsv"
    )
    examples_path = args.examples_out or args.question_compare_tsv.with_name(
        args.question_compare_tsv.stem + f"_{args.group_by}_examples.tsv"
    )

    summary_rows, example_rows = summarize(
        rows=rows,
        group_by=args.group_by,
        eps=args.eps,
        max_examples=args.max_examples,
        max_text_chars=args.max_text_chars,
    )

    summary_fields = [
        args.group_by,
        "rows",
        "wins",
        "losses",
        "ties",
        "win_rate",
        "loss_rate",
        "mean_delta_f1",
        "std_delta_f1",
        "sum_delta_f1",
        "worst_delta_f1",
        "best_delta_f1",
        "judge_wins",
        "judge_losses",
        "judge_ties",
        "mean_delta_llm_judge",
        "std_delta_llm_judge",
        "sum_delta_llm_judge",
        "worst_questions",
        "best_questions",
    ]
    example_fields = [
        args.group_by,
        "direction",
        "run",
        "sample_id",
        "qa_idx",
        "delta_f1",
        "delta_llm_judge",
        "question",
        "ground_truth",
        "baseline_prediction",
        "candidate_prediction",
        "baseline_negative_memories",
        "candidate_negative_memories",
    ]
    write_rows(out_path, summary_rows, summary_fields)
    write_rows(examples_path, example_rows, example_fields)
    print(f"Wrote grouped delta summary: {out_path}")
    print(f"Wrote grouped delta examples: {examples_path}")
    print(f"Rows: {len(rows)}")
    print(f"Groups: {len(summary_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
