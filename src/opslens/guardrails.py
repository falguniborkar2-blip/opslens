"""Lightweight input/output guardrails.

These are heuristics, not a security boundary: they reduce obvious prompt-injection
attempts and keep credentials that appear in logs/tool output away from the LLM and users.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MAX_QUESTION_CHARS = 4000

_INJECTION = [
    re.compile(p, re.I)
    for p in (
        r"ignore (all |any )?(the )?(previous|prior|above) (instructions|prompts?)",
        r"disregard (the |your )?(system|previous) (prompt|instructions)",
        r"reveal (your |the )?(system prompt|hidden instructions)",
        r"you are now (dan|in developer mode)",
    )
]

_SECRETS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED_AWS_KEY]"),
    (re.compile(r"(?i)(bearer\s+)[a-z0-9._\-]{16,}"), r"\1[REDACTED_TOKEN]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}\b"), "[REDACTED_API_KEY]"),
    (
        re.compile(r"(?i)\b(password|passwd|secret|api[_-]?key|token)(\s*[=:]\s*)\S+"),
        r"\1\2[REDACTED]",
    ),
    (
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----"),
        "[REDACTED_PRIVATE_KEY]",
    ),
]


# Values a small LLM invents when it doesn't know a real argument,
# e.g. "your_unit_name", "<pod-name>", "pod_name", "example-app", "xxx".
_PLACEHOLDER = re.compile(
    r"^(<.*>|your[_\- ].*|(unit|pod|service|namespace|container)[_\- ]?name|example.*|x{3,})$",
    re.I,
)


@dataclass
class Verdict:
    allowed: bool
    reason: str = ""


def check_question(question: str) -> Verdict:
    if not question.strip():
        return Verdict(False, "empty question")
    if len(question) > MAX_QUESTION_CHARS:
        return Verdict(False, f"question longer than {MAX_QUESTION_CHARS} characters")
    for pat in _INJECTION:
        if pat.search(question):
            return Verdict(False, "possible prompt injection detected")
    return Verdict(True)


def redact_secrets(text: str) -> str:
    for pat, repl in _SECRETS:
        text = pat.sub(repl, text)
    return text


def find_placeholder_args(arguments: dict[str, object]) -> list[str]:
    """Return names of tool arguments whose values look like template placeholders."""
    return [
        key
        for key, value in arguments.items()
        if isinstance(value, str) and _PLACEHOLDER.match(value.strip())
    ]
