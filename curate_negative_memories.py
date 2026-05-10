#!/usr/bin/env python
"""Cluster and export curated markdown negative memories.

This tool is intentionally non-LLM: it removes exact/near duplicates and
selects representative lessons from a raw negative-memory directory. It is a
quality-control step before using auto-recorded failures as prompt guardrails.
"""
import argparse
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from src.negative_memory import NegativeMemoryEntry, NegativeMemoryStore


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in",
    "into", "is", "it", "of", "on", "or", "that", "the", "this", "to",
    "was", "were", "with",
    "answer", "dataset", "expected", "memory", "model", "prediction",
    "question", "retrieved", "similar",
}


@dataclass
class Cluster:
    entries: List[NegativeMemoryEntry]

    @property
    def size(self) -> int:
        return len(self.entries)


def _extract_section(body: str, heading: str) -> str:
    pattern = rf"^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s+|\Z)"
    match = re.search(pattern, body, flags=re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def _compact(text: str, max_chars: int = 260) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + " ...[truncated]"


def _slugify(text: str, max_len: int = 80) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", str(text).strip().lower()).strip("-")
    return (slug or "negative-memory")[:max_len]


def _escape_yaml(text: str) -> str:
    return str(text).replace("\\", "\\\\").replace('"', '\\"')


def _safe_tag(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_:-]+", "_", str(text).strip())[:80]


def _tokenize(text: str) -> set:
    tokens = {
        token.lower()
        for token in re.findall(r"[A-Za-z0-9_]+", str(text))
        if len(token) > 2
    }
    return {token for token in tokens if token not in STOPWORDS}


def _curation_text(entry: NegativeMemoryEntry) -> str:
    parts = [
        entry.title,
        " ".join(entry.tags),
        _extract_section(entry.body, "Problem"),
        _extract_section(entry.body, "Wrong Behavior"),
        _extract_section(entry.body, "Correction"),
        _extract_section(entry.body, "Lesson"),
        _extract_section(entry.body, "Trigger"),
    ]
    return "\n".join(part for part in parts if part).strip()


def _similarity(left: NegativeMemoryEntry, right: NegativeMemoryEntry) -> float:
    left_terms = _tokenize(_curation_text(left))
    right_terms = _tokenize(_curation_text(right))
    if not left_terms or not right_terms:
        return 0.0
    return len(left_terms & right_terms) / len(left_terms | right_terms)


def _quality(entry: NegativeMemoryEntry) -> Tuple[float, List[str]]:
    problem = _extract_section(entry.body, "Problem")
    wrong = _extract_section(entry.body, "Wrong Behavior")
    correction = _extract_section(entry.body, "Correction")
    lesson = _extract_section(entry.body, "Lesson")
    trigger = _extract_section(entry.body, "Trigger")

    score = 0.0
    reasons = []
    if len(problem) >= 40:
        score += 1.0
        reasons.append("problem")
    if len(wrong) >= 40:
        score += 1.0
        reasons.append("wrong")
    if "prediction:" in wrong.lower():
        score += 0.5
        reasons.append("prediction")
    if len(correction) >= 20:
        score += 2.0
        reasons.append("correction")
    if len(lesson) >= 80:
        score += 2.0
        reasons.append("lesson")
    if len(trigger) >= 40:
        score += 1.0
        reasons.append("trigger")
    tags = {tag.lower() for tag in entry.tags}
    if "correction_dialogue" in tags:
        score += 0.5
        reasons.append("dialogue")
    if "auto_failure" in tags:
        score += 0.25
        reasons.append("auto")

    generic_correction = correction.lower().strip()
    if generic_correction in {
        "",
        "follow the user/evaluator correction from this dialogue.",
    }:
        score -= 2.0
        reasons.append("generic-correction")
    if len(_tokenize(_curation_text(entry))) < 8:
        score -= 1.0
        reasons.append("too-short")
    return score, reasons


def _cluster(entries: Sequence[NegativeMemoryEntry], threshold: float) -> List[Cluster]:
    clusters: List[Cluster] = []
    for entry in sorted(entries, key=lambda item: item.path):
        best_cluster = None
        best_score = 0.0
        for cluster in clusters:
            score = max(_similarity(entry, member) for member in cluster.entries)
            if score > best_score:
                best_score = score
                best_cluster = cluster
        if best_cluster is not None and best_score >= threshold:
            best_cluster.entries.append(entry)
        else:
            clusters.append(Cluster(entries=[entry]))
    return clusters


def _representative(cluster: Cluster) -> NegativeMemoryEntry:
    return max(
        cluster.entries,
        key=lambda entry: (
            _quality(entry)[0],
            len(_curation_text(entry)),
            -len(entry.path),
        ),
    )


def _cluster_key(cluster: Cluster) -> tuple:
    rep = _representative(cluster)
    return (-cluster.size, -_quality(rep)[0], rep.title.lower())


def _select_clusters(
    clusters: Sequence[Cluster],
    *,
    min_cluster_size: int,
    min_quality: float,
    max_curated: int,
) -> List[Cluster]:
    selected = []
    for cluster in sorted(clusters, key=_cluster_key):
        rep = _representative(cluster)
        quality, _ = _quality(rep)
        if cluster.size < min_cluster_size:
            continue
        if quality < min_quality:
            continue
        selected.append(cluster)
        if max_curated > 0 and len(selected) >= max_curated:
            break
    return selected


def _yaml_list(items: Iterable[str]) -> str:
    cleaned = [_escape_yaml(item) for item in items if str(item).strip()]
    return "[" + ", ".join(f'"{item}"' for item in cleaned) + "]"


def _write_curated_entry(out_dir: Path, idx: int, cluster: Cluster) -> Path:
    rep = _representative(cluster)
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    title = f"curated {rep.title}"
    tags = ["negative", "curated"]
    for tag in rep.tags:
        tag = _safe_tag(tag)
        if tag and tag not in tags:
            tags.append(tag)
    tags.append(f"cluster_size_{cluster.size}")
    source_files = [entry.path + ".md" for entry in cluster.entries]
    scope_id = rep.scope_id or "null"
    visibility = rep.visibility or "shared"

    sections = {
        "Problem": _extract_section(rep.body, "Problem"),
        "Wrong Behavior": _extract_section(rep.body, "Wrong Behavior"),
        "Correction": _extract_section(rep.body, "Correction"),
        "Lesson": _extract_section(rep.body, "Lesson"),
        "Trigger": _extract_section(rep.body, "Trigger"),
    }
    slug = _slugify(title)
    file_path = out_dir / f"{idx:03d}-{slug}.md"
    content = (
        "---\n"
        "type: negative\n"
        f"title: \"{_escape_yaml(title)}\"\n"
        f"date: {date}\n"
        f"tags: [{', '.join(tags)}]\n"
        f"visibility: {visibility}\n"
        f"scope_id: {scope_id}\n"
        f"source_count: {cluster.size}\n"
        f"source_files: {_yaml_list(source_files)}\n"
        "---\n\n"
        f"# {title}\n\n"
        "## Problem\n\n"
        f"{sections['Problem']}\n\n"
        "## Wrong Behavior\n\n"
        f"{sections['Wrong Behavior']}\n\n"
        "## Correction\n\n"
        f"{sections['Correction']}\n\n"
        "## Lesson\n\n"
        f"{sections['Lesson']}\n\n"
        "## Trigger\n\n"
        f"{sections['Trigger']}\n\n"
        "## Source Files\n\n"
        + "\n".join(f"- {source}" for source in source_files)
        + "\n"
    )
    file_path.write_text(content, encoding="utf-8")
    return file_path


def _write_report(
    report_path: Path,
    *,
    input_dir: Path,
    output_dir: Path,
    clusters: Sequence[Cluster],
    selected: Sequence[Cluster],
    threshold: float,
) -> None:
    lines = [
        "# Negative Memory Curation Report",
        "",
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        f"Input dir: `{input_dir}`",
        f"Output dir: `{output_dir}`",
        f"Similarity threshold: `{threshold}`",
        f"Loaded entries: `{sum(cluster.size for cluster in clusters)}`",
        f"Clusters: `{len(clusters)}`",
        f"Selected representatives: `{len(selected)}`",
        "",
        "| Cluster | Size | Quality | Representative | Tags |",
        "| ---: | ---: | ---: | --- | --- |",
    ]
    for idx, cluster in enumerate(selected, start=1):
        rep = _representative(cluster)
        quality, reasons = _quality(rep)
        lines.append(
            f"| {idx} | {cluster.size} | {quality:.2f} | "
            f"`{rep.path}.md` | {', '.join(reasons)} |"
        )
    lines.extend(["", "## Cluster Details", ""])
    for idx, cluster in enumerate(selected, start=1):
        rep = _representative(cluster)
        quality, reasons = _quality(rep)
        lines.extend([
            f"### Cluster {idx}: {rep.title}",
            "",
            f"- Size: {cluster.size}",
            f"- Representative: `{rep.path}.md`",
            f"- Quality: {quality:.2f} ({', '.join(reasons)})",
            f"- Lesson: {_compact(_extract_section(rep.body, 'Lesson'), 500)}",
            f"- Trigger: {_compact(_extract_section(rep.body, 'Trigger'), 500)}",
            "- Source files:",
        ])
        for entry in cluster.entries:
            lines.append(f"  - `{entry.path}.md`")
        lines.append("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def _prepare_output_dir(input_dir: Path, output_dir: Path, overwrite: bool) -> None:
    input_resolved = input_dir.resolve()
    output_resolved = output_dir.resolve()
    if input_resolved == output_resolved:
        raise ValueError("--out-dir must differ from --dir")
    output_dir.mkdir(parents=True, exist_ok=True)
    if overwrite:
        for path in output_dir.glob("*.md"):
            path.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="./negative_memories",
                        help="Raw negative-memory markdown directory")
    parser.add_argument("--out-dir", default="./curated_negative_memories",
                        help="Directory for curated markdown representatives")
    parser.add_argument("--report", default=None,
                        help="Markdown report path")
    parser.add_argument("--similarity-threshold", type=float, default=0.55,
                        help="Jaccard threshold for near-duplicate clustering")
    parser.add_argument("--min-cluster-size", type=int, default=1,
                        help="Only export clusters with at least this many entries")
    parser.add_argument("--min-quality", type=float, default=0.0,
                        help="Only export representatives at or above this quality score")
    parser.add_argument("--max-curated", type=int, default=30,
                        help="Maximum curated representatives to export; <=0 means no limit")
    parser.add_argument("--write-curated", action="store_true",
                        help="Write curated markdown files")
    parser.add_argument("--overwrite", action="store_true",
                        help="Delete existing markdown files in --out-dir before writing")
    args = parser.parse_args()

    input_dir = Path(args.dir)
    output_dir = Path(args.out_dir)
    report = Path(args.report or (
        f"./results/negative_memory_curation_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.md"
    ))

    store = NegativeMemoryStore(root_dir=str(input_dir))
    clusters = _cluster(store.entries, threshold=args.similarity_threshold)
    selected = _select_clusters(
        clusters,
        min_cluster_size=args.min_cluster_size,
        min_quality=args.min_quality,
        max_curated=args.max_curated,
    )

    if args.write_curated:
        _prepare_output_dir(input_dir, output_dir, overwrite=args.overwrite)
        for idx, cluster in enumerate(selected, start=1):
            _write_curated_entry(output_dir, idx, cluster)

    _write_report(
        report,
        input_dir=input_dir,
        output_dir=output_dir,
        clusters=clusters,
        selected=selected,
        threshold=args.similarity_threshold,
    )
    print(f"Loaded entries: {len(store.entries)}")
    print(f"Clusters: {len(clusters)}")
    print(f"Selected representatives: {len(selected)}")
    if args.write_curated:
        print(f"Curated directory: {output_dir}")
    print(f"Report: {report}")


if __name__ == "__main__":
    main()
