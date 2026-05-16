#!/usr/bin/env python3
"""Compare two configs from a LoCoMo repeat category summary.

Input is category_summary.tsv from summarize_locomo_repeat_categories.py.
The output ranks category deltas between two configs, so we can see where a
candidate method helps or hurts relative to a baseline.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, Tuple


MetricRow = Dict[str, str]


def load_rows(path: Path) -> Dict[Tuple[str, str], MetricRow]:
    rows: Dict[Tuple[str, str], MetricRow] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            config = row.get("config", "")
            category = row.get("category", "")
            if config and category:
                rows[(config, category)] = row
    return rows


def as_float(row: MetricRow, key: str) -> float:
    try:
        return float(row.get(key, "nan"))
    except ValueError:
        return float("nan")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("category_summary_tsv", type=Path)
    parser.add_argument("--baseline", default="raw_top2")
    parser.add_argument("--candidate", default="curated_agg055_top1_chars1200")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    rows = load_rows(args.category_summary_tsv)
    out_path = args.out or args.category_summary_tsv.with_name(
        f"compare_{args.candidate}_vs_{args.baseline}.tsv"
    )

    categories = sorted({
        category
        for config, category in rows
        if config in {args.baseline, args.candidate}
    }, key=lambda value: int(value) if value.isdigit() else value)

    output_rows = []
    for category in categories:
        base = rows.get((args.baseline, category))
        cand = rows.get((args.candidate, category))
        if base is None or cand is None:
            continue
        base_f1 = as_float(base, "f1_mean")
        cand_f1 = as_float(cand, "f1_mean")
        base_judge = as_float(base, "llm_judge_mean")
        cand_judge = as_float(cand, "llm_judge_mean")
        output_rows.append({
            "category": category,
            "baseline": args.baseline,
            "candidate": args.candidate,
            "baseline_f1": f"{base_f1:.4f}",
            "candidate_f1": f"{cand_f1:.4f}",
            "delta_f1": f"{cand_f1 - base_f1:+.4f}",
            "baseline_llm_judge": f"{base_judge:.4f}",
            "candidate_llm_judge": f"{cand_judge:.4f}",
            "delta_llm_judge": f"{cand_judge - base_judge:+.4f}",
        })

    with out_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "category",
            "baseline",
            "candidate",
            "baseline_f1",
            "candidate_f1",
            "delta_f1",
            "baseline_llm_judge",
            "candidate_llm_judge",
            "delta_llm_judge",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Wrote config comparison: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
