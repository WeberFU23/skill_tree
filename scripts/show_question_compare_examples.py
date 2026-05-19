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


def print_example(row: Row, max_context_chars: int) -> None:
    print("---")
    print(
        "run={run} category={category} sample_id={sample_id} qa_idx={qa_idx} "
        "delta_f1={delta_f1} delta_judge={delta_llm_judge}".format(**row)
    )
    print(f"Q: {row.get('question', '')}")
    print(f"GT: {row.get('ground_truth', '')}")
    print(f"baseline: {row.get('baseline_prediction', '')}")
    print(f"candidate: {row.get('candidate_prediction', '')}")
    base_neg = compact(row.get("baseline_negative_memories", ""), max_context_chars)
    cand_neg = compact(row.get("candidate_negative_memories", ""), max_context_chars)
    if base_neg:
        print(f"baseline_neg: {base_neg}")
    if cand_neg:
        print(f"candidate_neg: {cand_neg}")


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
                print_example(row, args.max_context_chars)

        if args.direction in {"best", "both"}:
            print()
            print(f"Best {args.top}")
            for row in sorted(cat_rows, key=lambda item: as_float(item.get("delta_f1", "")), reverse=True)[: args.top]:
                print_example(row, args.max_context_chars)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
