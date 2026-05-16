#!/usr/bin/env python3
"""Summarize LoCoMo category metrics from repeat-run logs.

Input is the summary.tsv produced by scripts/repeat_locomo_skilltree_core_configs.sh
or a compatible repeat script with columns including:
    config, run, f1, llm_judge, log

The script reads each log file, extracts lines like:
    Category 1: F1=0.1660, LLM Judge=0.2101
and writes a category_summary.tsv next to the input summary.
"""
from __future__ import annotations

import argparse
import csv
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


CATEGORY_RE = re.compile(
    r"^Category\s+(?P<category>[^:]+):\s+F1=(?P<f1>[0-9.]+),\s+LLM Judge=(?P<judge>[0-9.]+)"
)


def mean_std(values: Iterable[float]) -> Tuple[float, float]:
    vals = list(values)
    if not vals:
        return float("nan"), float("nan")
    mean = sum(vals) / len(vals)
    var = sum((value - mean) ** 2 for value in vals) / len(vals)
    return mean, math.sqrt(max(var, 0.0))


def parse_categories(log_path: Path) -> Dict[str, Tuple[float, float]]:
    metrics: Dict[str, Tuple[float, float]] = {}
    if not log_path.exists():
        return metrics
    with log_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            match = CATEGORY_RE.search(line.strip())
            if not match:
                continue
            category = str(match.group("category")).strip()
            metrics[category] = (
                float(match.group("f1")),
                float(match.group("judge")),
            )
    return metrics


def resolve_log_path(summary_path: Path, log_value: str) -> Path:
    """Resolve log paths written relative to either cwd or the repository root."""
    raw_path = Path(log_value)
    if raw_path.is_absolute():
        return raw_path

    candidates = [
        raw_path,
        summary_path.parent / raw_path,
    ]
    if len(summary_path.parents) >= 3:
        candidates.append(summary_path.parents[2] / raw_path)

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return raw_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "summary_tsv",
        type=Path,
        help="Path to repeat summary.tsv",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output TSV path. Defaults to category_summary.tsv next to summary_tsv.",
    )
    args = parser.parse_args()

    summary_path = args.summary_tsv
    out_path = args.out or summary_path.with_name("category_summary.tsv")

    rows = []
    with summary_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            rows.append(row)

    per_run = []
    grouped: Dict[Tuple[str, str], List[Tuple[float, float]]] = defaultdict(list)

    for row in rows:
        config = row.get("config", "")
        run_id = row.get("run", "")
        log_value = row.get("log", "")
        if not config or not log_value:
            continue
        log_path = resolve_log_path(summary_path, log_value)

        category_metrics = parse_categories(log_path)
        for category, (f1, judge) in sorted(category_metrics.items()):
            per_run.append({
                "config": config,
                "run": run_id,
                "category": category,
                "f1": f"{f1:.4f}",
                "llm_judge": f"{judge:.4f}",
                "log": str(log_path),
            })
            grouped[(config, category)].append((f1, judge))

    aggregate_rows = []
    for (config, category), values in sorted(grouped.items()):
        f1_mean, f1_std = mean_std(value[0] for value in values)
        judge_mean, judge_std = mean_std(value[1] for value in values)
        aggregate_rows.append({
            "config": config,
            "category": category,
            "n": str(len(values)),
            "f1_mean": f"{f1_mean:.4f}",
            "f1_std": f"{f1_std:.4f}",
            "llm_judge_mean": f"{judge_mean:.4f}",
            "llm_judge_std": f"{judge_std:.4f}",
        })

    with out_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "config",
            "category",
            "n",
            "f1_mean",
            "f1_std",
            "llm_judge_mean",
            "llm_judge_std",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(aggregate_rows)

    per_run_path = out_path.with_name(out_path.stem + "_per_run.tsv")
    with per_run_path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = ["config", "run", "category", "f1", "llm_judge", "log"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(per_run)

    print(f"Wrote aggregate category summary: {out_path}")
    print(f"Wrote per-run category summary: {per_run_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
