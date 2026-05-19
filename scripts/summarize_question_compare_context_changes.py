#!/usr/bin/env python3
"""Summarize whether context changes explain question-level deltas.

Input is the TSV written by ``compare_locomo_repeat_questions.py``. The script
groups rows by category and whether the compared configs retrieved the same or
different context, then reports win/loss rates and mean deltas.
"""
from __future__ import annotations

import argparse
import csv
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


Row = Dict[str, str]


CONTEXT_COLUMNS = {
    "retrieved": ("baseline_retrieved_memories", "candidate_retrieved_memories"),
    "negative": ("baseline_negative_memories", "candidate_negative_memories"),
}


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


def mean(values: Iterable[float]) -> float:
    clean = [value for value in values if not math.isnan(value)]
    if not clean:
        return math.nan
    return sum(clean) / len(clean)


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", normalize(text)))


def jaccard(left: str, right: str) -> float:
    left_tokens = tokenize(left)
    right_tokens = tokenize(right)
    if not left_tokens and not right_tokens:
        return 1.0
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


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
    context_name: str,
    eps: float,
    max_examples: int,
    max_text_chars: int,
    include_all: bool,
) -> List[Row]:
    baseline_col, candidate_col = CONTEXT_COLUMNS[context_name]
    grouped: Dict[Tuple[str, str], List[Row]] = defaultdict(list)

    for row in rows:
        base_context = normalize(row.get(baseline_col, ""))
        cand_context = normalize(row.get(candidate_col, ""))
        status = "same" if base_context == cand_context else "changed"
        group_values = [row.get(group_by, "") or "<missing>"]
        if include_all:
            group_values.append("ALL")
        for group in group_values:
            grouped[(group, status)].append(row)

    output_rows: List[Row] = []
    for (group, status), items in sorted(grouped.items()):
        f1_deltas = [as_float(row.get("delta_f1", "")) for row in items]
        judge_deltas = [as_float(row.get("delta_llm_judge", "")) for row in items]
        labels = [classify(delta, eps) for delta in f1_deltas]
        jaccards = [
            jaccard(row.get(baseline_col, ""), row.get(candidate_col, ""))
            for row in items
        ]

        total = len(items)
        wins = labels.count("win")
        losses = labels.count("loss")
        ties = labels.count("tie")
        sorted_by_delta = sorted(items, key=lambda row: as_float(row.get("delta_f1", "")))
        worst = sorted_by_delta[:max_examples]
        best = list(reversed(sorted_by_delta[-max_examples:]))

        output_rows.append({
            group_by: group,
            "context": context_name,
            "context_status": status,
            "rows": str(total),
            "wins": str(wins),
            "losses": str(losses),
            "ties": str(ties),
            "win_rate": format_float(wins / total if total else math.nan),
            "loss_rate": format_float(losses / total if total else math.nan),
            "mean_delta_f1": format_signed(mean(f1_deltas)),
            "sum_delta_f1": format_signed(sum(v for v in f1_deltas if not math.isnan(v))),
            "mean_delta_llm_judge": format_signed(mean(judge_deltas)),
            "sum_delta_llm_judge": format_signed(sum(v for v in judge_deltas if not math.isnan(v))),
            "mean_context_jaccard": format_float(mean(jaccards)),
            "worst_questions": " || ".join(truncate(row.get("question", ""), max_text_chars) for row in worst),
            "best_questions": " || ".join(truncate(row.get("question", ""), max_text_chars) for row in best),
        })

    return output_rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question_compare_tsv", type=Path)
    parser.add_argument("--group-by", default="category")
    parser.add_argument("--context", choices=sorted(CONTEXT_COLUMNS), default="retrieved")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--eps", type=float, default=1e-9)
    parser.add_argument("--max-examples", type=int, default=5)
    parser.add_argument("--max-text-chars", type=int, default=500)
    parser.add_argument("--no-all", action="store_true", help="Do not include an aggregate ALL group.")
    args = parser.parse_args()

    rows = read_rows(args.question_compare_tsv)
    if not rows:
        raise SystemExit("No rows found.")
    required = [args.group_by, *CONTEXT_COLUMNS[args.context]]
    missing = [column for column in required if column not in rows[0]]
    if missing:
        available = ", ".join(rows[0].keys())
        raise SystemExit(f"Missing required columns {missing}. Available columns: {available}")

    out_path = args.out or args.question_compare_tsv.with_name(
        args.question_compare_tsv.stem + f"_{args.context}_context_summary.tsv"
    )
    output_rows = summarize(
        rows=rows,
        group_by=args.group_by,
        context_name=args.context,
        eps=args.eps,
        max_examples=args.max_examples,
        max_text_chars=args.max_text_chars,
        include_all=not args.no_all,
    )

    fieldnames = [
        args.group_by,
        "context",
        "context_status",
        "rows",
        "wins",
        "losses",
        "ties",
        "win_rate",
        "loss_rate",
        "mean_delta_f1",
        "sum_delta_f1",
        "mean_delta_llm_judge",
        "sum_delta_llm_judge",
        "mean_context_jaccard",
        "worst_questions",
        "best_questions",
    ]
    write_rows(out_path, output_rows, fieldnames)
    print(f"Wrote context-change summary: {out_path}")
    print(f"Rows: {len(rows)}")
    print(f"Groups: {len(output_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
