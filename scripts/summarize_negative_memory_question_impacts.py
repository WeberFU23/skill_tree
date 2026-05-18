#!/usr/bin/env python3
"""Summarize question-level wins/losses by retrieved negative memory.

Input is the TSV written by ``compare_locomo_repeat_questions.py``. The script
groups rows by the retrieved negative-memory lesson and reports whether each
lesson tends to help or hurt a candidate config relative to a baseline.
"""
from __future__ import annotations

import argparse
import csv
import math
import re
from collections import Counter, defaultdict
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


def split_memories(text: str) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    return [part.strip() for part in text.split(" || ") if part.strip()]


def memory_key(memory: str) -> str:
    text = re.sub(r"\s+", " ", memory).strip()
    text = re.sub(r"^\[Negative Memory\]\s*", "", text)

    match = re.search(r"(curated auto failure locomo\s+conv-[\w.-]+\s+\d+)", text)
    if match:
        return match.group(1)

    for marker in (" Date:", " Tags:", " Trigger:", " Wrong Behavior:", " Correction:"):
        if marker in text:
            text = text.split(marker, 1)[0].strip()
            break
    return text[:120]


def truncate(text: str, max_chars: int) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def mean(values: Iterable[float]) -> float:
    clean = [value for value in values if not math.isnan(value)]
    if not clean:
        return math.nan
    return sum(clean) / len(clean)


def read_rows(path: Path) -> List[Row]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, rows: List[Row], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def classify_delta(delta: float, eps: float) -> str:
    if math.isnan(delta) or abs(delta) <= eps:
        return "tie"
    if delta > 0:
        return "win"
    return "loss"


def summarize(
    rows: List[Row],
    memory_column: str,
    include_empty: bool,
    eps: float,
    max_examples: int,
    max_text_chars: int,
) -> Tuple[List[Row], List[Row]]:
    grouped: Dict[str, List[Tuple[Row, str]]] = defaultdict(list)

    for row in rows:
        memories = split_memories(row.get(memory_column, ""))
        if not memories and include_empty:
            memories = ["<no retrieved negative memory>"]
        for memory in memories:
            grouped[memory_key(memory)].append((row, memory))

    summary_rows: List[Row] = []
    example_rows: List[Row] = []

    for key, items in grouped.items():
        deltas = [as_float(row.get("delta_f1", "")) for row, _ in items]
        judge_deltas = [as_float(row.get("delta_llm_judge", "")) for row, _ in items]
        labels = [classify_delta(delta, eps) for delta in deltas]
        counts = Counter(labels)
        categories = Counter(row.get("category", "") for row, _ in items)
        loss_categories = Counter(
            row.get("category", "")
            for (row, _), label in zip(items, labels)
            if label == "loss"
        )

        sorted_by_loss = sorted(
            items,
            key=lambda item: as_float(item[0].get("delta_f1", "")),
        )
        sorted_by_win = sorted(
            items,
            key=lambda item: as_float(item[0].get("delta_f1", "")),
            reverse=True,
        )

        loss_examples = [
            truncate(row.get("question", ""), max_text_chars)
            for row, _ in sorted_by_loss
            if classify_delta(as_float(row.get("delta_f1", "")), eps) == "loss"
        ][:max_examples]
        win_examples = [
            truncate(row.get("question", ""), max_text_chars)
            for row, _ in sorted_by_win
            if classify_delta(as_float(row.get("delta_f1", "")), eps) == "win"
        ][:max_examples]

        first_memory = items[0][1]
        total = len(items)
        summary_rows.append({
            "memory_key": key,
            "rows": str(total),
            "wins": str(counts["win"]),
            "losses": str(counts["loss"]),
            "ties": str(counts["tie"]),
            "win_rate": format_float(counts["win"] / total),
            "loss_rate": format_float(counts["loss"] / total),
            "mean_delta_f1": format_signed(mean(deltas)),
            "mean_delta_llm_judge": format_signed(mean(judge_deltas)),
            "worst_delta_f1": format_signed(min(deltas)),
            "best_delta_f1": format_signed(max(deltas)),
            "categories": ", ".join(f"{cat}:{count}" for cat, count in sorted(categories.items())),
            "loss_categories": ", ".join(f"{cat}:{count}" for cat, count in sorted(loss_categories.items())),
            "example_loss_questions": " || ".join(loss_examples),
            "example_win_questions": " || ".join(win_examples),
            "memory_text": truncate(first_memory, max_text_chars * 2),
        })

        selected_examples = sorted_by_loss[:max_examples] + sorted_by_win[:max_examples]
        seen = set()
        for row, memory in selected_examples:
            marker = (
                row.get("run", ""),
                row.get("sample_id", ""),
                row.get("qa_idx", ""),
                row.get("question", ""),
                memory,
            )
            if marker in seen:
                continue
            seen.add(marker)
            delta = as_float(row.get("delta_f1", ""))
            example_rows.append({
                "memory_key": key,
                "direction": classify_delta(delta, eps),
                "run": row.get("run", ""),
                "category": row.get("category", ""),
                "sample_id": row.get("sample_id", ""),
                "qa_idx": row.get("qa_idx", ""),
                "delta_f1": row.get("delta_f1", ""),
                "delta_llm_judge": row.get("delta_llm_judge", ""),
                "question": row.get("question", ""),
                "ground_truth": row.get("ground_truth", ""),
                "baseline_prediction": row.get("baseline_prediction", ""),
                "candidate_prediction": row.get("candidate_prediction", ""),
                "memory_text": truncate(memory, max_text_chars * 2),
            })

    summary_rows.sort(
        key=lambda row: (
            as_float(row["mean_delta_f1"]),
            -int(row["losses"]),
            -int(row["rows"]),
        )
    )
    example_rows.sort(
        key=lambda row: (
            row["memory_key"],
            as_float(row.get("delta_f1", "")),
        )
    )
    return summary_rows, example_rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question_compare_tsv", type=Path)
    parser.add_argument("--memory-column", default="candidate_negative_memories")
    parser.add_argument("--include-empty", action="store_true")
    parser.add_argument("--tie-eps", type=float, default=1e-9)
    parser.add_argument("--max-examples", type=int, default=3)
    parser.add_argument("--max-text-chars", type=int, default=240)
    parser.add_argument("--out-summary", type=Path, default=None)
    parser.add_argument("--out-examples", type=Path, default=None)
    args = parser.parse_args()

    rows = read_rows(args.question_compare_tsv)
    summary_rows, example_rows = summarize(
        rows=rows,
        memory_column=args.memory_column,
        include_empty=args.include_empty,
        eps=args.tie_eps,
        max_examples=args.max_examples,
        max_text_chars=args.max_text_chars,
    )

    default_stem = args.question_compare_tsv.with_suffix("")
    summary_path = args.out_summary or default_stem.with_name(default_stem.name + "_negative_memory_summary.tsv")
    examples_path = args.out_examples or default_stem.with_name(default_stem.name + "_negative_memory_examples.tsv")

    summary_fields = [
        "memory_key",
        "rows",
        "wins",
        "losses",
        "ties",
        "win_rate",
        "loss_rate",
        "mean_delta_f1",
        "mean_delta_llm_judge",
        "worst_delta_f1",
        "best_delta_f1",
        "categories",
        "loss_categories",
        "example_loss_questions",
        "example_win_questions",
        "memory_text",
    ]
    example_fields = [
        "memory_key",
        "direction",
        "run",
        "category",
        "sample_id",
        "qa_idx",
        "delta_f1",
        "delta_llm_judge",
        "question",
        "ground_truth",
        "baseline_prediction",
        "candidate_prediction",
        "memory_text",
    ]
    write_tsv(summary_path, summary_rows, summary_fields)
    write_tsv(examples_path, example_rows, example_fields)

    print(f"Wrote negative-memory summary: {summary_path}")
    print(f"Wrote negative-memory examples: {examples_path}")
    print(f"Memories: {len(summary_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
