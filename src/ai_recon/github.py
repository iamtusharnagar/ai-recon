"""Fetches the small set of files where AI-contribution policies actually
live in practice, based on real conventions observed across open-source
projects: a dedicated AI_POLICY.md (the convention go-git started and
several projects have since adapted), the emerging AGENTS.md standard,
CLAUDE.md (used by projects that specifically brief coding agents),
CONTRIBUTING.md, and README.md as a fallback.

No machine-readable standard for this exists yet -- see README.md -- so
this is inherently a best-effort list, not an authoritative one. A repo's
policy might live in its wiki (not fetched; GitHub wikis are a separate
git repo the REST API does not expose the same way) or in a doc this list
doesn't happen to check.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from base64 import b64decode
from dataclasses import dataclass

API_ROOT = "https://api.github.com"
USER_AGENT = "ai-recon-cli"

# Checked in this order; all existing ones are fetched and classified, not
# just the first match, since a repo can and sometimes does say different
# things in different places (see patterns.combine, which resolves that).
CANDIDATE_PATHS = [
    "AI_POLICY.md",
    ".github/AI_POLICY.md",
    "AGENTS.md",
    ".github/AGENTS.md",
    "CLAUDE.md",
    "CONTRIBUTING.md",
    ".github/CONTRIBUTING.md",
    "docs/CONTRIBUTING.md",
    "README.md",
]


class GitHubError(RuntimeError):
    """Raised when the GitHub API returns an error response beachhead didn't expect."""

    def __init__(self, status: int, message: str):
        super().__init__(f"GitHub API error {status}: {message}")
        self.status = status


class RepoNotFoundError(RuntimeError):
    """Raised when the target repo itself doesn't exist or isn't visible."""


@dataclass(frozen=True)
class FetchedFile:
    path: str
    text: str


def _request(path: str, token: str | None) -> tuple[int, dict]:
    url = f"{API_ROOT}{path}"
    request = urllib.request.Request(url, method="GET")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    request.add_header("User-Agent", USER_AGENT)
    request.add_header("Accept", "application/vnd.github+json")

    try:
        with urllib.request.urlopen(request) as response:
            payload = response.read()
            return response.status, (json.loads(payload) if payload else {})
    except urllib.error.HTTPError as error:
        payload = error.read()
        parsed = json.loads(payload) if payload else {}
        return error.code, parsed


def repo_exists(owner: str, repo: str, token: str | None = None) -> bool:
    status, payload = _request(f"/repos/{owner}/{repo}", token)
    if status == 200:
        return True
    if status == 404:
        return False
    raise GitHubError(status, payload.get("message", "unknown error"))


def _fetch_file(owner: str, repo: str, path: str, token: str | None) -> str | None:
    """Returns the file's decoded text, or None if it doesn't exist at this path."""
    status, payload = _request(f"/repos/{owner}/{repo}/contents/{path}", token)
    if status == 404:
        return None
    if status != 200:
        raise GitHubError(status, payload.get("message", "unknown error"))
    if not isinstance(payload, dict) or payload.get("encoding") != "base64":
        # A directory (payload is a list, not a dict), a submodule, or a
        # symlink was found at this path instead of a file; nothing to
        # classify.
        return None
    return b64decode(payload["content"]).decode("utf-8", errors="replace")


def fetch_policy_files(
    owner: str,
    repo: str,
    token: str | None = None,
    paths: list[str] | None = None,
) -> list[FetchedFile]:
    """Fetches every candidate policy file that exists in the repo.

    Raises RepoNotFoundError up front if the repo itself doesn't exist, so
    a typo'd repo name produces a clear error instead of a misleading
    NOT_FOUND policy verdict.
    """
    if not repo_exists(owner, repo, token):
        raise RepoNotFoundError(f"{owner}/{repo} does not exist or is not visible with this token")

    found = []
    for path in paths if paths is not None else CANDIDATE_PATHS:
        text = _fetch_file(owner, repo, path, token)
        if text is not None:
            found.append(FetchedFile(path, text))
    return found
