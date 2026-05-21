"""Question-text routing rules for LoCoMo router diagnostics/eval."""
from __future__ import annotations

import re
from typing import Iterable, List, Pattern, Tuple


def compile_patterns(patterns: Iterable[str]) -> List[Pattern[str]]:
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]


BASELINE_RISK_PATTERNS = compile_patterns([
    r"\bwhich country\b",
    r"\bwhich us state\b",
    r"\bwhich state\b",
    r"\bwould\b.+\bprefer\b",
    r"\bdoes\b.+\blive close\b",
    r"\bwhat role\b",
    r"\bconsidering\b",
    r"\bbased on\b",
    r"\bin light of\b",
    r"\bhow do\b",
    r"\bhow might\b",
    r"\bwhat challenges\b",
    r"\bwhat advice\b",
    r"\bis it likely\b",
    r"\bunderlying condition\b",
    r"\bbesides\b",
    r"\bboth\b.+\b(and|or)\b",
])


BASELINE_PROFILE_PATTERNS = compile_patterns([
    r"^who\b",
    r"\bwhat kind of\b",
    r"\bwhat (?:is|are|was|were)\b.+\b(?:job|profession|occupation|career|role|hobby|hobbies|interest|interests)\b",
    r"\bwhat (?:is|are|was|were)\b.+\b(?:favorite|favourite|allergic|allergy|condition|relationship)\b",
    r"\bwhere (?:is|are|was|were|does|do)\b.+\b(?:live|from|based)\b",
    r"\bhow many times\b",
    r"\bhow long\b",
])


BASELINE_RISK_STRONG_PATTERNS = compile_patterns([
    r"\bwhich country\b",
    r"\bwhich us state\b",
    r"\bwhich state\b",
    r"\bwould\b.+\bprefer\b",
    r"\bdoes\b.+\blive close\b",
])


BASELINE_PROFILE_STRONG_PATTERNS = compile_patterns([
    r"^who\b",
    r"\bwhat kind of\b",
    r"\bhow many times\b",
    r"\bhow long\b",
])


def normalize_question(question: str) -> str:
    return " ".join((question or "").strip().lower().split())


def route_question(question: str, mode: str) -> Tuple[str, str]:
    text = normalize_question(question)
    if mode == "candidate_all":
        return "candidate", "candidate_all"
    if mode == "baseline_all":
        return "baseline", "baseline_all"
    if mode not in {"risk_baseline_v1", "risk_profile_baseline_v1", "risk_profile_baseline_v2"}:
        raise ValueError(f"Unknown router mode: {mode}")

    risk_patterns = BASELINE_RISK_PATTERNS
    profile_patterns = BASELINE_PROFILE_PATTERNS
    if mode == "risk_profile_baseline_v2":
        risk_patterns = BASELINE_RISK_STRONG_PATTERNS
        profile_patterns = BASELINE_PROFILE_STRONG_PATTERNS

    for pattern in risk_patterns:
        if pattern.search(text):
            return "baseline", f"risk:{pattern.pattern}"
    if mode in {"risk_profile_baseline_v1", "risk_profile_baseline_v2"}:
        for pattern in profile_patterns:
            if pattern.search(text):
                return "baseline", f"profile:{pattern.pattern}"
    return "candidate", "default_candidate"
