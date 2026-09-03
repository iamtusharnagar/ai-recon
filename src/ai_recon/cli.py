"""The `ai-recon` command: check a repo's AI-contribution policy before you
invest time in it.
"""

from __future__ import annotations

import argparse
import os
import sys

from . import github
from .patterns import Evidence, PolicyResult, Verdict, classify_file, combine
from .reference import ParseError, parse_owner_repo

TOKEN_ENV_VAR = "GITHUB_TOKEN"

_VERDICT_MESSAGES = {
    Verdict.BANNED: "AI-assisted contributions appear to be BANNED.",
    Verdict.DISCLOSURE_REQUIRED: "AI-assisted contributions appear ALLOWED, WITH DISCLOSURE REQUIRED.",
    Verdict.ALLOWED: "AI-assisted contributions appear explicitly ALLOWED.",
    Verdict.MENTIONED_UNCLEAR: "AI is mentioned, but not in language this tool recognizes as a clear policy.",
    Verdict.NOT_FOUND: "No AI-contribution policy found in the files this tool checks.",
}


class ReconError(RuntimeError):
    """Raised for any ai-recon-specific failure with a user-facing message."""


def check(reference: str, *, token: str | None = None) -> tuple[PolicyResult, list[github.FetchedFile]]:
    """Fetches and classifies one repo's AI-contribution policy.

    Returns the combined verdict alongside every file that was actually
    fetched, so a caller (the CLI, or another program importing this) can
    show its own reasoning rather than trusting the verdict blind.
    """
    try:
        owner, repo = parse_owner_repo(reference)
    except ParseError as error:
        raise ReconError(str(error)) from error

    try:
        files = github.fetch_policy_files(owner, repo, token)
    except github.RepoNotFoundError as error:
        raise ReconError(str(error)) from error

    per_file_results = [classify_file(f.path, f.text) for f in files]
    return combine(per_file_results), files


def _format_result(result: PolicyResult, files: list[github.FetchedFile]) -> str:
    lines = [_VERDICT_MESSAGES[result.verdict]]

    if files:
        checked = ", ".join(f.path for f in files)
        lines.append(f"checked (found): {checked}")
    else:
        lines.append("none of the checked files exist in this repo")

    for evidence in result.evidence:
        lines.append(f"  {evidence.path}: \"{evidence.sentence}\"")

    if not result.confident:
        lines.append("")
        lines.append(
            "This is not a confident verdict -- read the source yourself before deciding."
        )

    if result.verdict == Verdict.NOT_FOUND:
        lines.append("")
        lines.append(
            "No policy found in this tool's known locations doesn't mean no policy exists: "
            "it may be in a wiki page, a linked external doc, or a file this tool doesn't "
            "yet check."
        )

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-recon",
        description=(
            "Check a repo's AI-contribution policy before you invest time in it. "
            "Checks AI_POLICY.md, AGENTS.md, CLAUDE.md, CONTRIBUTING.md, and README.md."
        ),
    )
    parser.add_argument(
        "reference", help="a GitHub URL (repo, issue, or PR) or owner/repo shorthand"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    token = os.environ.get(TOKEN_ENV_VAR)  # optional: public repos work without one

    try:
        result, files = check(args.reference, token=token)
    except (ReconError, github.GitHubError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(_format_result(result, files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
