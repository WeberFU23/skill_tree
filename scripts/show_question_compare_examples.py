#!/usr/bin/env python3
"""Print readable worst/best examples from a question comparison TSV."""
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Dict, List


Row = Dict[str, str]


def as_float(value: str) -> float:
    try:
        if value is None or value == "":
            return math.nan
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def read_rows(path: Path) -> List[Row]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def compact(text: str, max_chars: int) -> str:
    text = " ".join((text or "").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def print_context(label: str, text: str, max_context_chars: int) -> None:
    compacted = compact(text, max_context_chars)
    if compacted:
        print(f"{label}: {compacted}")


def print_example(
    row: Row,
    max_context_chars: int,
    show_negative: bool,
    show_retrieved: bool,
) -> None:
    print("---")
    print(
        "run={run} category={category} sample_id={sample_id} qa_idx={qa_idx} "
        "delta_f1={delta_f1} delta_judge={delta_llm_judge}".format(**row)
    )
    print(f"Q: {row.get('question', '')}")
    print(f"GT: {row.get('ground_truth', '')}")
    print(f"baseline: {row.get('baseline_prediction', '')}")
    print(f"candidate: {row.get('candidate_prediction', '')}")
    if show_negative:
        print_context("baseline_neg", row.get("baseline_negative_memories", ""), max_context_chars)
        print_context("candidate_neg", row.get("candidate_negative_memories", ""), max_context_chars)
    if show_retrieved:
        print_context("baseline_retrieved", row.get("baseline_retrieved_memories", ""), max_context_chars)
        print_context("candidate_retrieved", row.get("candidate_retrieved_memories", ""), max_context_chars)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question_compare_tsv", type=Path)
    parser.add_argument("--categories", nargs="*", default=None)
    parser.add_argument(
        "--direction",
        choices=["worst", "best", "both"],
        default="both",
        help="Which side of the delta distribution to print.",
    )
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--max-context-chars", type=int, default=700)
    parser.add_argument("--show-retrieved", action="store_true", help="Print retrieved QA memories.")
    parser.add_argument("--hide-negative", action="store_true", help="Do not print negative memories.")
    args = parser.parse_args()

    rows = read_rows(args.question_compare_tsv)
    categories = args.categories or sorted({row.get("category", "") for row in rows})

    for category in categories:
        cat_rows = [row for row in rows if row.get("category", "") == category]
        if not cat_rows:
            continue
        print()
        print(f"================================================================================")
        print(f"Category {category}: rows={len(cat_rows)}")
        print(f"================================================================================")

        if args.direction in {"worst", "both"}:
            print()
            print(f"Worst {args.top}")
            for row in sorted(cat_rows, key=lambda item: as_float(item.get("delta_f1", "")))[: args.top]:
                print_example(row, args.max_context_chars, not args.hide_negative, args.show_retrieved)

        if args.direction in {"best", "both"}:
            print()
            print(f"Best {args.top}")
            for row in sorted(cat_rows, key=lambda item: as_float(item.get("delta_f1", "")), reverse=True)[: args.top]:
                print_example(row, args.max_context_chars, not args.hide_negative, args.show_retrieved)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
