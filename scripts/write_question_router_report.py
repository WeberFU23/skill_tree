#!/usr/bin/env python3
"""Write a compact markdown report for materialized question-router results."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, Iterable, List


Row = Dict[str, str]


def read_rows(path: Path) -> List[Row]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def markdown_table(rows: Iterable[Row], columns: List[str], headers: List[str] | None = None) -> List[str]:
    rows = list(rows)
    headers = headers or columns
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        values = [str(row.get(column, "")).replace("|", "\\|") for column in columns]
        lines.append("| " + " | ".join(values) + " |")
    return lines


def pick_row(rows: List[Row], key: str, value: str) -> Row:
    for row in rows:
        if row.get(key) == value:
            return row
    return {}


def report_delta_rows(rows: List[Row]) -> List[Row]:
    fields = [
        "category",
        "rows",
        "wins",
        "losses",
        "ties",
        "mean_delta_f1",
        "mean_delta_llm_judge",
        "sum_delta_f1",
        "sum_delta_llm_judge",
    ]
    return [{field: row.get(field, "") for field in fields} for row in rows]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat-dir", type=Path, required=True)
    parser.add_argument("--router-mode", default="risk_profile_baseline_v2")
    parser.add_argument("--router-config", default="question_router_risk_profile_baseline_v2")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    repeat_dir = args.repeat_dir
    out_path = args.out or repeat_dir / f"question_router_{args.router_mode}_report.md"
    overall_path = repeat_dir / f"question_router_{args.router_mode}_overall_summary.tsv"
    category_path = repeat_dir / f"question_router_{args.router_mode}_category_summary.tsv"
    vs_pruned_path = repeat_dir / f"question_compare_{args.router_config}_vs_pruned_bad3_all_category_summary.tsv"
    vs_evolved_path = repeat_dir / f"question_compare_{args.router_config}_vs_evolved_checkpoint_all_category_summary.tsv"

    overall_rows = read_rows(overall_path)
    category_rows = read_rows(category_path)
    vs_pruned_rows = read_rows(vs_pruned_path)
    vs_evolved_rows = read_rows(vs_evolved_path)

    router = pick_row(overall_rows, "label", args.router_config)
    pruned = pick_row(overall_rows, "label", "pruned_bad3")
    evolved = pick_row(overall_rows, "label", "evolved_checkpoint")

    lines: List[str] = [
        "# Question Router v2 Result",
        "",
        "## Summary",
        "",
        (
            f"`{args.router_config}` is the current best LoCoMo10 development result: "
            f"F1 {router.get('f1_mean', '?')} +/- {router.get('f1_std', '?')}, "
            f"LLM Judge {router.get('llm_judge_mean', '?')} +/- {router.get('llm_judge_std', '?')}."
        ),
        "",
        (
            "It improves over pruned bad3 "
            f"({pruned.get('f1_mean', '?')} / {pruned.get('llm_judge_mean', '?')}) "
            "and the evolved checkpoint "
            f"({evolved.get('f1_mean', '?')} / {evolved.get('llm_judge_mean', '?')}). "
            "The result is a materialized question-text router assembled from repeated "
            "baseline and evolved-checkpoint outputs, not a single-pass end-to-end eval."
        ),
        "",
        "## Overall",
        "",
        *markdown_table(
            overall_rows,
            ["label", "n", "f1_mean", "f1_std", "llm_judge_mean", "llm_judge_std"],
            ["Config", "n", "F1 Mean", "F1 Std", "Judge Mean", "Judge Std"],
        ),
        "",
        "## Router Categories",
        "",
        *markdown_table(
            category_rows,
            ["category", "n", "f1_mean", "f1_std", "llm_judge_mean", "llm_judge_std"],
            ["Category", "n", "F1 Mean", "F1 Std", "Judge Mean", "Judge Std"],
        ),
        "",
        "## Router vs Pruned Bad3",
        "",
        *markdown_table(
            report_delta_rows(vs_pruned_rows),
            [
                "category",
                "rows",
                "wins",
                "losses",
                "ties",
                "mean_delta_f1",
                "mean_delta_llm_judge",
                "sum_delta_f1",
                "sum_delta_llm_judge",
            ],
            ["Category", "Rows", "Wins", "Losses", "Ties", "Delta F1", "Delta Judge", "Sum F1", "Sum Judge"],
        ),
        "",
        "## Router vs Evolved Checkpoint",
        "",
        *markdown_table(
            report_delta_rows(vs_evolved_rows),
            [
                "category",
                "rows",
                "wins",
                "losses",
                "ties",
                "mean_delta_f1",
                "mean_delta_llm_judge",
                "sum_delta_f1",
                "sum_delta_llm_judge",
            ],
            ["Category", "Rows", "Wins", "Losses", "Ties", "Delta F1", "Delta Judge", "Sum F1", "Sum Judge"],
        ),
        "",
        "## Readout",
        "",
        "- The router's main value over the evolved checkpoint is Cat3 recovery.",
        "- Cat2 and Cat4 mostly preserve the evolved checkpoint gains.",
        "- Cat1 remains the main residual weakness relative to pruned bad3.",
        "",
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote router report: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
