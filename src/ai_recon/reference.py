"""Parses an owner/repo reference from a GitHub URL of any kind or shorthand.

Deliberately a separate, smaller implementation from beachhead.naming
rather than a shared dependency: ai-recon only ever needs owner/repo, never
an issue number, and pulling in a whole extra package for one regex would
undercut the same zero-dependency reasoning that applies to third-party
packages.
"""

from __future__ import annotations

import re

_URL_RE = re.compile(r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)")
_SHORTHAND_RE = re.compile(r"^(?P<owner>[^/\s]+)/(?P<repo>[^/\s#]+)")
_TRAILING_GIT_RE = re.compile(r"\.git$")


class ParseError(ValueError):
    """Raised when a string names neither a GitHub URL nor an owner/repo pair."""


def parse_owner_repo(text: str) -> tuple[str, str]:
    """Extracts (owner, repo) from a URL or owner/repo[#N] shorthand.

    Accepts issue, PR, or bare-repo URLs alike -- ai-recon only cares which
    repo, not which issue -- and strips a trailing ``.git``.
    """
    text = text.strip()

    match = _URL_RE.match(text)
    if match:
        return match["owner"], _TRAILING_GIT_RE.sub("", match["repo"])

    match = _SHORTHAND_RE.match(text)
    if match and match["owner"] and match["repo"]:
        return match["owner"], _TRAILING_GIT_RE.sub("", match["repo"])

    raise ParseError(f"not a recognizable GitHub repo reference: {text!r}")
