"""
Markdown-backed negative memory support.

Negative memories are compact lessons from prior mistakes or user
corrections. They are retrieved as prompt guardrails; they should not contain
hidden chain-of-thought. Store the reusable error pattern, correction, and
lesson instead.
"""
import os
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

import numpy as np


@dataclass
class NegativeMemoryEntry:
    """One markdown negative memory entry."""
    path: str
    file_path: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    body: str = ""
    embedding: Optional[np.ndarray] = None

    @property
    def title(self) -> str:
        return str(self.metadata.get("title") or _extract_title(self.body) or self.path)

    @property
    def visibility(self) -> str:
        return str(self.metadata.get("visibility", "shared")).lower()

    @property
    def scope_id(self) -> Optional[str]:
        value = self.metadata.get("scope_id")
        if value is None:
            return None
        value = str(value).strip()
        if value.lower() in ("", "null", "none"):
            return None
        return value

    @property
    def tags(self) -> List[str]:
        tags = self.metadata.get("tags", [])
        if isinstance(tags, list):
            return [str(tag) for tag in tags]
        if isinstance(tags, str):
            return [tag.strip() for tag in tags.split(",") if tag.strip()]
        return []

    def is_visible(self, scope_ids: Optional[Iterable[str]] = None) -> bool:
        if self.visibility == "shared":
            return True
        allowed_scopes = {str(scope) for scope in (scope_ids or []) if scope is not None}
        return self.scope_id is not None and self.scope_id in allowed_scopes

    def retrieval_text(self) -> str:
        parts = [
            self.title,
            ", ".join(self.tags),
            _extract_section(self.body, "Problem"),
            _extract_section(self.body, "Wrong Behavior"),
            _extract_section(self.body, "Correction"),
            _extract_section(self.body, "Lesson"),
            _extract_section(self.body, "Trigger"),
        ]
        return "\n".join(part for part in parts if part).strip()

    def prompt_text(self, max_chars: int = 1200) -> str:
        sections = []
        date = str(self.metadata.get("date", "") or "").strip()
        if date:
            sections.append(f"Date: {date}")
        tags = ", ".join(self.tags)
        if tags:
            sections.append(f"Tags: {tags}")
        for heading in ("Trigger", "Wrong Behavior", "Correction", "Lesson"):
            text = _extract_section(self.body, heading)
            if text:
                sections.append(f"{heading}: {text}")
        if not sections:
            sections.append(self.body.strip())
        text = f"[Negative Memory] {self.title}\n" + "\n".join(sections)
        if len(text) > max_chars:
            text = text[:max_chars] + "\n...[truncated]"
        return text


class NegativeMemoryStore:
    """Load, retrieve, and write negative memories stored as markdown files."""

    def __init__(self, root_dir: str = "./negative_memories", encoder=None,
                 max_chars_per_memory: int = 1200):
        self.root_dir = os.path.abspath(root_dir)
        self.encoder = encoder
        self.max_chars_per_memory = max_chars_per_memory
        self._lock = threading.RLock()
        self.entries: List[NegativeMemoryEntry] = []
        self.load()

    def load(self):
        with self._lock:
            self.entries = []
            if not os.path.isdir(self.root_dir):
                return
            for dirpath, _, filenames in os.walk(self.root_dir):
                for filename in sorted(filenames):
                    if not filename.endswith(".md"):
                        continue
                    file_path = os.path.join(dirpath, filename)
                    entry = self._load_file(file_path)
                    if entry is not None:
                        self.entries.append(entry)
            if self.encoder is not None and self.entries:
                self.recompute_embeddings()

    def _load_file(self, file_path: str) -> Optional[NegativeMemoryEntry]:
        with open(file_path, "r", encoding="utf-8") as f:
            raw = f.read()
        metadata, body = _split_frontmatter(raw)
        entry_type = str(metadata.get("type", "")).lower()
        tags = metadata.get("tags", [])
        tag_set = set(tags if isinstance(tags, list) else str(tags).split(","))
        tag_set = {tag.strip().lower() for tag in tag_set if str(tag).strip()}
        if entry_type != "negative" and "negative" not in tag_set:
            return None
        rel_path = os.path.relpath(file_path, self.root_dir).replace(os.sep, "/")
        return NegativeMemoryEntry(
            path=rel_path[:-3] if rel_path.endswith(".md") else rel_path,
            file_path=file_path,
            metadata=metadata,
            body=body,
        )

    def recompute_embeddings(self):
        with self._lock:
            texts = [entry.retrieval_text() for entry in self.entries]
            embeddings = _encode_texts(self.encoder, texts)
            for entry, embedding in zip(self.entries, embeddings):
                entry.embedding = embedding

    def retrieve(self, query: str, top_k: int = 3,
                 scope_ids: Optional[Iterable[str]] = None,
                 min_score: Optional[float] = None,
                 required_tags: Optional[Iterable[str]] = None) -> List[str]:
        if top_k is None or int(top_k) <= 0:
            return []
        with self._lock:
            visible = [entry for entry in self.entries if entry.is_visible(scope_ids)]
            required_tag_set = {
                str(tag).strip().lower()
                for tag in (required_tags or [])
                if str(tag).strip()
            }
            if required_tag_set:
                visible = [
                    entry for entry in visible
                    if required_tag_set.issubset(
                        {str(tag).strip().lower() for tag in entry.tags}
                    )
                ]
            if not visible:
                return []

            actual_k = min(int(top_k), len(visible))
            if self.encoder is not None:
                for entry in visible:
                    if entry.embedding is None:
                        entry.embedding = _encode_texts(self.encoder, [entry.retrieval_text()])[0]
                query_embedding = _encode_texts(self.encoder, [query])[0]
                ranked = _rank_by_embedding(query_embedding, visible)
            else:
                ranked = _rank_by_keyword(query, visible)

            if min_score is not None:
                try:
                    threshold = float(min_score)
                    ranked = [(score, entry) for score, entry in ranked if score >= threshold]
                except Exception:
                    pass

            return [
                entry.prompt_text(self.max_chars_per_memory)
                for _, entry in ranked[:actual_k]
            ]

    def has_entry_for(self, problem: str, correction: str) -> bool:
        """Return True if an equivalent problem/correction pair is already stored."""
        target = _dedupe_key(problem, correction)
        with self._lock:
            for entry in self.entries:
                stored = _dedupe_key(
                    _extract_section(entry.body, "Problem"),
                    _extract_section(entry.body, "Correction"),
                )
                if stored == target:
                    return True
        return False

    def write_entry(self, problem: str, wrong_behavior: str, correction: str,
                    lesson: str, trigger: str = "", user_id: Optional[str] = None,
                    tags: Optional[List[str]] = None,
                    title: Optional[str] = None,
                    date: Optional[str] = None) -> str:
        """Persist one negative memory markdown file and reload the store."""
        with self._lock:
            os.makedirs(self.root_dir, exist_ok=True)
            date = date or datetime.utcnow().strftime("%Y-%m-%d")
            title = title or _slug_title(problem) or "negative-memory"
            slug = _slug_title(title) or "negative-memory"
            filename = f"{date}-{slug}.md"
            file_path = os.path.join(self.root_dir, filename)
            suffix = 1
            while os.path.exists(file_path):
                file_path = os.path.join(self.root_dir, f"{date}-{slug}-{suffix}.md")
                suffix += 1

            tag_list = ["negative"]
            for tag in tags or []:
                tag = str(tag).strip()
                if tag and tag not in tag_list:
                    tag_list.append(tag)

            visibility = "private" if user_id else "shared"
            scope_id = user_id if user_id else "null"
            tag_text = ", ".join(tag_list)
            content = (
                "---\n"
                "type: negative\n"
                f"title: \"{_escape_yaml(title)}\"\n"
                f"date: {date}\n"
                f"tags: [{tag_text}]\n"
                f"visibility: {visibility}\n"
                f"scope_id: {scope_id}\n"
                "---\n\n"
                f"# {title}\n\n"
                "## Problem\n\n"
                f"{problem.strip()}\n\n"
                "## Wrong Behavior\n\n"
                f"{wrong_behavior.strip()}\n\n"
                "## Correction\n\n"
                f"{correction.strip()}\n\n"
                "## Lesson\n\n"
                f"{lesson.strip()}\n\n"
                "## Trigger\n\n"
                f"{trigger.strip()}\n"
            )
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.load()
            return file_path


def _encode_texts(encoder, texts) -> np.ndarray:
    if isinstance(texts, str):
        texts = [texts]
    if hasattr(encoder, "_encode_texts"):
        embeddings = encoder._encode_texts(list(texts))
    else:
        embeddings = encoder.encode(list(texts))
    embeddings = np.asarray(embeddings, dtype=np.float32)
    if embeddings.ndim == 1:
        embeddings = embeddings.reshape(1, -1)
    return embeddings


def _rank_by_embedding(query_embedding: np.ndarray,
                       entries: List[NegativeMemoryEntry]):
    query = _normalize(query_embedding)
    scored = []
    for entry in entries:
        scored.append((float(np.dot(query, _normalize(entry.embedding))), entry))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored


def _rank_by_keyword(query: str,
                     entries: List[NegativeMemoryEntry]):
    query_terms = _token_set(query)
    scored = []
    for entry in entries:
        terms = _token_set(entry.retrieval_text())
        score = len(query_terms & terms) / max(len(query_terms), 1)
        scored.append((score, entry))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored


def _token_set(text: str) -> set:
    return set(re.findall(r"[A-Za-z0-9_]+", str(text).lower()))


def _dedupe_key(problem: str, correction: str) -> str:
    text = f"{problem}\n{correction}"
    return re.sub(r"\s+", " ", str(text).strip().lower())


def _normalize(vec: np.ndarray) -> np.ndarray:
    arr = np.asarray(vec, dtype=np.float32)
    if arr.ndim == 2:
        arr = arr[0]
    norm = np.linalg.norm(arr)
    if norm <= 1e-8:
        return arr
    return arr / norm


def _split_frontmatter(raw: str):
    if not raw.startswith("---"):
        return {}, raw
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", raw, flags=re.DOTALL)
    if not match:
        return {}, raw
    return _parse_simple_yaml(match.group(1)), match.group(2)


def _parse_simple_yaml(text: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value.lower() in ("null", "none", "~"):
            data[key] = None
        elif value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            data[key] = [] if not inner else [
                item.strip().strip("'\"") for item in inner.split(",")
            ]
        else:
            data[key] = value.strip("'\"")
    return data


def _extract_title(body: str) -> str:
    match = re.search(r"^#\s+(.+?)\s*$", body, flags=re.MULTILINE)
    return match.group(1).strip() if match else ""


def _extract_section(body: str, heading: str) -> str:
    pattern = rf"^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s+|\Z)"
    match = re.search(pattern, body, flags=re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def _slug_title(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", str(text).strip().lower()).strip("-")
    return slug[:80]


def _escape_yaml(text: str) -> str:
    return str(text).replace("\\", "\\\\").replace('"', '\\"')
