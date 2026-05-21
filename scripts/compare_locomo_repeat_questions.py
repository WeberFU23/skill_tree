#!/usr/bin/env python3
"""Compare LoCoMo question-level eval JSON files between two configs.

This script expects detailed JSON produced by ``main.py --out-file``. It can
compare one baseline/candidate pair directly, or pair all runs listed in a
repeat ``summary.tsv`` by config name and run id.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


Record = Dict[str, Any]

QUESTION_KEYS = ("question", "query", "qa_question")
GROUND_TRUTH_KEYS = ("ground_truth", "answer", "answers", "gold", "reference", "expected_answer")
PREDICTION_KEYS = ("prediction", "pred", "model_answer", "response", "generated_answer")
F1_KEYS = ("f1", "f1_score", "score")
JUDGE_KEYS = ("llm_judge", "llm_judge_score", "judge", "judge_score")
CATEGORY_KEYS = ("category", "question_type", "type")
ID_KEYS = ("qid", "qa_idx", "query_id", "question_id", "id")
ROUTER_SELECTED_KEYS = ("router_selected", "selected_route", "selected")
ROUTER_REASON_KEYS = ("router_reason", "selected_reason", "reason")


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def pick(mapping: Dict[str, Any], keys: Sequence[str], default: Any = "") -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    metadata = mapping.get("metadata")
    if isinstance(metadata, dict):
        for key in keys:
            if key in metadata and metadata[key] is not None:
                return metadata[key]
    return default


def stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def as_float(value: Any) -> float:
    try:
        if value is None or value == "":
            return math.nan
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def find_result_lists(obj: Any) -> List[List[Dict[str, Any]]]:
    found: List[List[Dict[str, Any]]] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            preferred = value.get("results")
            if isinstance(preferred, list) and all(isinstance(item, dict) for item in preferred):
                found.append(preferred)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            if value and all(isinstance(item, dict) for item in value):
                found.append(value)
            for child in value:
                visit(child)

    visit(obj)
    return found


def score_result_list(rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0
    score = 0
    sample = rows[: min(len(rows), 20)]
    for row in sample:
        if pick(row, QUESTION_KEYS):
            score += 3
        if pick(row, PREDICTION_KEYS):
            score += 3
        if pick(row, GROUND_TRUTH_KEYS):
            score += 2
        if pick(row, F1_KEYS) != "":
            score += 1
        if pick(row, CATEGORY_KEYS) != "":
            score += 1
    return score


def load_records(path: Path) -> List[Record]:
    obj = read_json(path)
    candidates = find_result_lists(obj)
    if not candidates:
        raise ValueError(f"No list-like result records found in {path}")
    rows = max(candidates, key=score_result_list)
    if score_result_list(rows) == 0:
        raise ValueError(f"Could not identify question-level records in {path}")

    records: List[Record] = []
    for idx, row in enumerate(rows):
        question = stringify(pick(row, QUESTION_KEYS))
        record = {
            "index": idx,
            "id": stringify(pick(row, ID_KEYS, idx)),
            "sample_id": stringify(row.get("sample_id", "")),
            "qa_idx": stringify(row.get("qa_idx", "")),
            "category": stringify(pick(row, CATEGORY_KEYS)),
            "question": question,
            "ground_truth": stringify(pick(row, GROUND_TRUTH_KEYS)),
            "prediction": stringify(pick(row, PREDICTION_KEYS)),
            "f1": as_float(pick(row, F1_KEYS)),
            "llm_judge": as_float(pick(row, JUDGE_KEYS)),
            "retrieved_memories": row.get("retrieved_memories", []),
            "negative_memories": row.get("negative_memories", []),
            "router_selected": stringify(pick(row, ROUTER_SELECTED_KEYS)),
            "router_reason": stringify(pick(row, ROUTER_REASON_KEYS)),
            "source_file": str(path),
        }
        records.append(record)
    return records


def record_key(record: Record) -> Tuple[str, str, str]:
    question = str(record.get("question") or "").strip().lower()
    if question:
        return (question, str(record.get("sample_id") or ""), str(record.get("category") or ""))
    return (str(record.get("index")), str(record.get("sample_id") or ""), str(record.get("category") or ""))


def format_metric(value: float) -> str:
    if math.isnan(value):
        return ""
    return f"{value:.4f}"


def format_delta(value: float) -> str:
    if math.isnan(value):
        return ""
    return f"{value:+.4f}"


def compact_list(values: Any, max_items: int, max_chars: int) -> str:
    if not isinstance(values, list):
        return stringify(values)[:max_chars]
    text = " || ".join(stringify(item).replace("\n", " ") for item in values[:max_items])
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    return text


def compare_pair(
    baseline_path: Path,
    candidate_path: Path,
    run: str = "",
    categories: Optional[Iterable[str]] = None,
    max_context_items: int = 2,
    max_context_chars: int = 900,
) -> List[Dict[str, str]]:
    wanted_categories = {str(category) for category in categories or []}
    baseline_records = load_records(baseline_path)
    candidate_records = load_records(candidate_path)

    candidate_by_key = {record_key(record): record for record in candidate_records}
    output_rows: List[Dict[str, str]] = []

    for base in baseline_records:
        cand = candidate_by_key.get(record_key(base))
        if cand is None:
            continue
        category = str(base.get("category") or cand.get("category") or "")
        if wanted_categories and category not in wanted_categories:
            continue

        base_f1 = float(base["f1"])
        cand_f1 = float(cand["f1"])
        base_judge = float(base["llm_judge"])
        cand_judge = float(cand["llm_judge"])
        delta_f1 = cand_f1 - base_f1 if not (math.isnan(base_f1) or math.isnan(cand_f1)) else math.nan
        delta_judge = cand_judge - base_judge if not (math.isnan(base_judge) or math.isnan(cand_judge)) else math.nan

        output_rows.append({
            "run": run,
            "category": category,
            "sample_id": str(base.get("sample_id") or cand.get("sample_id") or ""),
            "qa_idx": str(base.get("qa_idx") or cand.get("qa_idx") or ""),
            "question": str(base.get("question") or cand.get("question") or ""),
            "ground_truth": str(base.get("ground_truth") or cand.get("ground_truth") or ""),
            "baseline_prediction": str(base.get("prediction") or ""),
            "candidate_prediction": str(cand.get("prediction") or ""),
            "baseline_f1": format_metric(base_f1),
            "candidate_f1": format_metric(cand_f1),
            "delta_f1": format_delta(delta_f1),
            "baseline_llm_judge": format_metric(base_judge),
            "candidate_llm_judge": format_metric(cand_judge),
            "delta_llm_judge": format_delta(delta_judge),
            "baseline_router_selected": str(base.get("router_selected") or ""),
            "candidate_router_selected": str(cand.get("router_selected") or ""),
            "baseline_router_reason": str(base.get("router_reason") or ""),
            "candidate_router_reason": str(cand.get("router_reason") or ""),
            "baseline_router_category_reason": (
                f"cat{category}|{str(base.get('router_selected') or '')}|{str(base.get('router_reason') or '')}"
            ),
            "candidate_router_category_reason": (
                f"cat{category}|{str(cand.get('router_selected') or '')}|{str(cand.get('router_reason') or '')}"
            ),
            "baseline_negative_memories": compact_list(base.get("negative_memories"), max_context_items, max_context_chars),
            "candidate_negative_memories": compact_list(cand.get("negative_memories"), max_context_items, max_context_chars),
            "baseline_retrieved_memories": compact_list(base.get("retrieved_memories"), max_context_items, max_context_chars),
            "candidate_retrieved_memories": compact_list(cand.get("retrieved_memories"), max_context_items, max_context_chars),
        })

    output_rows.sort(key=lambda row: float(row["delta_f1"] or "0"))
    return output_rows


def read_summary_pairs(
    summary_tsvs: Sequence[Path],
    baseline_config: str,
    candidate_config: str,
) -> List[Tuple[str, Path, Path]]:
    rows: Dict[Tuple[str, str], Dict[str, str]] = {}
    for summary_tsv in summary_tsvs:
        with summary_tsv.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            for row in reader:
                config = row.get("config", "")
                run = row.get("run", "")
                if config and run:
                    rows[(config, run)] = row

    pairs: List[Tuple[str, Path, Path]] = []
    runs = sorted(
        {run for config, run in rows if config in {baseline_config, candidate_config}},
        key=lambda value: int(value) if value.isdigit() else value,
    )
    for run in runs:
        base = rows.get((baseline_config, run))
        cand = rows.get((candidate_config, run))
        if base is None or cand is None:
            continue
        base_path = Path(base.get("out_file", ""))
        cand_path = Path(cand.get("out_file", ""))
        pairs.append((run, base_path, cand_path))
    return pairs


def write_rows(path: Path, rows: List[Dict[str, str]]) -> None:
    fieldnames = [
        "run",
        "category",
        "sample_id",
        "qa_idx",
        "question",
        "ground_truth",
        "baseline_prediction",
        "candidate_prediction",
        "baseline_f1",
        "candidate_f1",
        "delta_f1",
        "baseline_llm_judge",
        "candidate_llm_judge",
        "delta_llm_judge",
        "baseline_router_selected",
        "candidate_router_selected",
        "baseline_router_reason",
        "candidate_router_reason",
        "baseline_router_category_reason",
        "candidate_router_category_reason",
        "baseline_negative_memories",
        "candidate_negative_memories",
        "baseline_retrieved_memories",
        "candidate_retrieved_memories",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, help="Baseline detailed eval JSON")
    parser.add_argument("--candidate", type=Path, help="Candidate detailed eval JSON")
    parser.add_argument("--summary-tsv", type=Path, nargs="+", help="One or more repeat summary.tsv files with out_file paths")
    parser.add_argument("--baseline-config", default="raw_top2")
    parser.add_argument("--candidate-config", default="curated_agg055_top1_chars1200")
    parser.add_argument("--categories", nargs="*", default=None)
    parser.add_argument("--max-context-items", type=int, default=2)
    parser.add_argument("--max-context-chars", type=int, default=900)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    all_rows: List[Dict[str, str]] = []
    if args.summary_tsv:
        pairs = read_summary_pairs(args.summary_tsv, args.baseline_config, args.candidate_config)
        if not pairs:
            raise SystemExit("No matching config/run pairs found in summary TSV.")
        for run, baseline_path, candidate_path in pairs:
            all_rows.extend(compare_pair(
                baseline_path=baseline_path,
                candidate_path=candidate_path,
                run=run,
                categories=args.categories,
                max_context_items=args.max_context_items,
                max_context_chars=args.max_context_chars,
            ))
        out_base = args.summary_tsv[0]
        out_path = args.out or out_base.with_name(
            f"question_compare_{args.candidate_config}_vs_{args.baseline_config}.tsv"
        )
    else:
        if args.baseline is None or args.candidate is None:
            raise SystemExit("Pass either --summary-tsv or both --baseline and --candidate.")
        all_rows = compare_pair(
            baseline_path=args.baseline,
            candidate_path=args.candidate,
            categories=args.categories,
            max_context_items=args.max_context_items,
            max_context_chars=args.max_context_chars,
        )
        out_path = args.out or args.candidate.with_name(
            f"question_compare_{args.candidate.stem}_vs_{args.baseline.stem}.tsv"
        )

    write_rows(out_path, all_rows)
    print(f"Wrote question-level comparison: {out_path}")
    print(f"Rows: {len(all_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
