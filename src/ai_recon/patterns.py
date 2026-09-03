"""Pure text classification of AI-contribution policy signals.

Nothing here touches the network or filesystem. Given raw text, it decides
whether that text contains a policy statement about AI-assisted
contributions, and if so, which of three outcomes it states. Keeping this
free of I/O means the classifier itself -- the part where getting it wrong
actually matters -- can be tested directly and exhaustively, the same way
beachhead's naming.py is.

This is a heuristic, not a parser for a real spec: no machine-readable
standard for AI contribution policies exists yet (see README), so this
pattern-matches the prose humans already write. It is deliberately
conservative in one direction: a BANNED signal always wins over anything
else found in the same or another file, because assuming a repo doesn't
mind and being wrong costs a real person a rejected PR, while assuming a
ban and being wrong just costs one avoidable double-check.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Verdict(str, Enum):
    BANNED = "banned"
    DISCLOSURE_REQUIRED = "disclosure_required"
    ALLOWED = "allowed"
    MENTIONED_UNCLEAR = "mentioned_unclear"
    NOT_FOUND = "not_found"


@dataclass(frozen=True)
class Evidence:
    """One sentence that drove the verdict, and where it came from."""

    path: str
    sentence: str


@dataclass(frozen=True)
class PolicyResult:
    verdict: Verdict
    evidence: list[Evidence]

    @property
    def confident(self) -> bool:
        """False for MENTIONED_UNCLEAR and NOT_FOUND: read the source yourself."""
        return self.verdict in (Verdict.BANNED, Verdict.DISCLOSURE_REQUIRED, Verdict.ALLOWED)


# A sentence must mention AI/LLMs at all before any ban/disclosure/allow
# pattern is even checked against it. This is what keeps "must not skip
# tests" from matching BAN_RE in a file that separately, elsewhere,
# happens to mention Claude.
_AI_KEYWORD_RE = re.compile(
    r"\b("
    r"AI|A\.I\.|LLMs?|genai|generative[- ]AI|"
    r"large language models?|language models?|"
    r"chatgpt|copilot|claude|gpt-?\d|gemini|"
    r"artificial intelligence"
    r")\b",
    re.IGNORECASE,
)

# Order matters: checked in this order, and the first match wins for a
# given sentence. BANNED is checked first across *all* sentences before
# DISCLOSURE_REQUIRED or ALLOWED is considered at the file-result level,
# not just the sentence level -- see classify().
_BAN_RE = re.compile(
    r"\b("
    r"not allowed|not permitted|not accepted|"
    r"prohibited|banned|disallowed|"
    r"must not|shall not|"
    r"will not be accepted|will be rejected|will be closed|"
    r"are not welcome|is not welcome|"
    r"tainted content|do not (accept|allow)|"
    r"no\b.{0,60}\b(is|are) (permitted|allowed|welcome)"
    r")\b",
    re.IGNORECASE,
)

_DISCLOSURE_RE = re.compile(
    r"\b("
    r"must disclose|should disclose|"
    r"disclosure is required|disclosure required|"
    r"disclose\b|"
    r"assisted-by|co-authored-by|"
    r"must be reviewed|please disclose|"
    r"declare (the )?(use|ai|tool)|"
    r"attribute the (ai|tool)|"
    r"trailer line|"
    r"higher standard|your code is your responsibility"
    r")\b",
    re.IGNORECASE,
)

_ALLOW_RE = re.compile(
    r"\b("
    r"are welcome|is welcome|"
    r"are allowed|is allowed|"
    r"are permitted|is permitted|"
    r"feel free to use|welcome ai|welcome the use"
    r")\b",
    re.IGNORECASE,
)

# Splits on sentence-ending punctuation OR a newline, so that bullet-point
# policy statements (extremely common in CONTRIBUTING.md) are captured as
# their own fragment even without a trailing period.
_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def _sentences(text: str) -> list[str]:
    fragments = (f.strip(" \t-*>#") for f in _SPLIT_RE.split(text))
    return [f for f in fragments if f]


def _ai_related_sentences(text: str) -> list[str]:
    return [s for s in _sentences(text) if _AI_KEYWORD_RE.search(s)]


def classify_file(path: str, text: str) -> PolicyResult:
    """Classifies a single file's content in isolation.

    A multi-file aggregate (what the CLI actually reports) is built by
    combining these with `combine()`, not by concatenating file contents
    first -- combining first would let a BAN_RE hit in one file's evidence
    quote leak into another file's sentence boundaries.
    """
    ai_sentences = _ai_related_sentences(text)
    if not ai_sentences:
        return PolicyResult(Verdict.NOT_FOUND, [])

    for sentence in ai_sentences:
        if _BAN_RE.search(sentence):
            return PolicyResult(Verdict.BANNED, [Evidence(path, sentence)])

    for sentence in ai_sentences:
        if _DISCLOSURE_RE.search(sentence):
            return PolicyResult(Verdict.DISCLOSURE_REQUIRED, [Evidence(path, sentence)])

    for sentence in ai_sentences:
        if _ALLOW_RE.search(sentence):
            return PolicyResult(Verdict.ALLOWED, [Evidence(path, sentence)])

    # AI is mentioned, but not with language this classifier recognizes as
    # a clear verdict. Surfaced separately from NOT_FOUND on purpose: "we
    # found nothing" and "we found something we can't confidently read"
    # call for different amounts of caution from whoever reads the result.
    return PolicyResult(Verdict.MENTIONED_UNCLEAR, [Evidence(path, ai_sentences[0])])


def combine(results: list[PolicyResult]) -> PolicyResult:
    """Combines per-file results into one verdict, worst-case-first.

    Precedence: a BANNED anywhere always wins, even if another file says
    ALLOWED -- e.g. a repo-wide AI_POLICY.md banning AI contributions
    outranks an unrelated README sentence that happens to read as
    welcoming. Same reasoning as the module docstring: the cost of a
    missed ban is higher than the cost of an extra double-check.
    """
    by_verdict: dict[Verdict, list[Evidence]] = {v: [] for v in Verdict}
    for result in results:
        by_verdict[result.verdict].extend(result.evidence)

    for verdict in (
        Verdict.BANNED,
        Verdict.DISCLOSURE_REQUIRED,
        Verdict.ALLOWED,
        Verdict.MENTIONED_UNCLEAR,
    ):
        if by_verdict[verdict]:
            return PolicyResult(verdict, by_verdict[verdict])

    return PolicyResult(Verdict.NOT_FOUND, [])
