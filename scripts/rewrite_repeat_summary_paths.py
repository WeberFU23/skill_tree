#!/usr/bin/env python3
"""Rewrite repeat summary log/out_file paths into a canonical repeat directory."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List


Row = Dict[str, str]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary_tsv", type=Path)
    parser.add_argument("--repeat-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    out_path = args.out or args.repeat_dir / "summary.tsv"
    with args.summary_tsv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fieldnames = list(reader.fieldnames or [])
        rows: List[Row] = list(reader)

    for row in rows:
        log_value = row.get("log", "")
        if log_value:
            row["log"] = str(args.repeat_dir / "logs" / Path(log_value).name)
        out_value = row.get("out_file", "")
        if out_value:
            row["out_file"] = str(args.repeat_dir / Path(out_value).name)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote canonical repeat summary: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
