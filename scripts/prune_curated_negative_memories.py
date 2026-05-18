#!/usr/bin/env python3
"""Copy a curated negative-memory directory while excluding selected lessons."""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path
from typing import Iterable, List, Optional


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def find_excluded_key(text: str, exclude_keys: Iterable[str]) -> Optional[str]:
    normalized = normalize(text)
    for key in exclude_keys:
        if normalize(key) in normalized:
            return key
    return None


def ensure_safe_output(input_dir: Path, out_dir: Path) -> None:
    input_resolved = input_dir.resolve()
    output_resolved = out_dir.resolve()
    if input_resolved == output_resolved:
        raise ValueError("--out-dir must differ from --dir")
    if output_resolved == Path(output_resolved.anchor):
        raise ValueError("Refusing to use filesystem root as --out-dir")
    if not output_resolved.name:
        raise ValueError("Invalid --out-dir")


def copy_pruned(
    input_dir: Path,
    out_dir: Path,
    exclude_keys: List[str],
    overwrite: bool,
) -> List[dict]:
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    ensure_safe_output(input_dir, out_dir)

    if out_dir.exists():
        if not overwrite:
            raise FileExistsError(f"Output directory exists: {out_dir}")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: List[dict] = []
    for source in sorted(input_dir.rglob("*")):
        relative = source.relative_to(input_dir)
        target = out_dir / relative
        if source.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        if source.suffix.lower() != ".md":
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            rows.append({
                "status": "copied",
                "path": str(relative).replace("\\", "/"),
                "matched_key": "",
            })
            continue

        text = read_text(source)
        matched_key = find_excluded_key(text, exclude_keys)
        if matched_key is not None:
            rows.append({
                "status": "pruned",
                "path": str(relative).replace("\\", "/"),
                "matched_key": matched_key,
            })
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        rows.append({
            "status": "copied",
            "path": str(relative).replace("\\", "/"),
            "matched_key": "",
        })
    return rows


def write_report(path: Path, rows: List[dict], input_dir: Path, out_dir: Path, exclude_keys: List[str]) -> None:
    copied = [row for row in rows if row["status"] == "copied" and row["path"].endswith(".md")]
    pruned = [row for row in rows if row["status"] == "pruned"]
    lines = [
        "# Curated Negative Memory Pruning Report",
        "",
        f"Input dir: `{input_dir}`",
        f"Output dir: `{out_dir}`",
        f"Copied markdown files: `{len(copied)}`",
        f"Pruned markdown files: `{len(pruned)}`",
        "",
        "## Exclude Keys",
        "",
    ]
    lines.extend(f"- `{key}`" for key in exclude_keys)
    lines.extend(["", "## Files", "", "| Status | Path | Matched key |", "| --- | --- | --- |"])
    for row in rows:
        lines.append(f"| {row['status']} | `{row['path']}` | `{row['matched_key']}` |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, required=True, help="Input curated negative-memory directory")
    parser.add_argument("--out-dir", type=Path, required=True, help="Output pruned directory")
    parser.add_argument("--exclude-key", action="append", default=[], help="Substring identifying a lesson to prune")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args()

    if not args.exclude_key:
        raise SystemExit("At least one --exclude-key is required.")

    rows = copy_pruned(
        input_dir=args.dir,
        out_dir=args.out_dir,
        exclude_keys=args.exclude_key,
        overwrite=args.overwrite,
    )
    report_path = args.report or (args.out_dir / "PRUNING_REPORT.md")
    write_report(report_path, rows, args.dir, args.out_dir, args.exclude_key)

    copied_md = sum(1 for row in rows if row["status"] == "copied" and row["path"].endswith(".md"))
    pruned_md = sum(1 for row in rows if row["status"] == "pruned")
    print(f"Copied markdown files: {copied_md}")
    print(f"Pruned markdown files: {pruned_md}")
    print(f"Wrote report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
