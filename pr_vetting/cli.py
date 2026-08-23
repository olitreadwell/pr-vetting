"""Command line entry point for PR vetting.

Usage:
    python -m pr_vetting --repo owner/name --pr 87 --login author [options]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import Any

from .github_api import GitHubApiError, fetch_pull_request_body
from .rules import PASS_VERDICTS, VetResult, VetThresholds, vet_pull_author
from .signals import PullRequestContext, collect_pull_signals


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pr-vetting", description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/name of the repository")
    parser.add_argument("--pr", required=True, type=int, help="pull request number")
    parser.add_argument("--login", required=True, help="pull request author login")
    parser.add_argument("--token", default=None, help="GitHub token (defaults to GITHUB_TOKEN)")
    parser.add_argument("--min-account-age-days", type=int, default=90)
    parser.add_argument("--min-in-repo-merged-prs", type=int, default=1)
    parser.add_argument("--min-global-merged-prs", type=int, default=0)
    parser.add_argument("--require-signed-commits", action="store_true")
    parser.add_argument("--allowlist", default="", help="comma-separated logins")
    parser.add_argument("--fail-open", action="store_true", help="exit 0 on API errors")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = vars(_parse_args(argv))
    repo = args.pop("repo")
    pr_number = args.pop("pr")
    login = args.pop("login")
    token = args.pop("token")
    fail_open = args.pop("fail_open")
    allowlist = frozenset(part.strip() for part in args.pop("allowlist").split(",") if part.strip())

    thresholds = VetThresholds(
        min_account_age_days=args.pop("min_account_age_days"),
        min_in_repo_merged_prs=args.pop("min_in_repo_merged_prs"),
        min_global_merged_prs=args.pop("min_global_merged_prs"),
        require_signed_commits=args.pop("require_signed_commits"),
        allowlist=allowlist,
    )
    owner, repo_name = repo.split("/", 1)

    if login in allowlist:
        result = VetResult("maintainer", 100, ["author is on the maintainer allowlist"])
        payload = _build_output(result, {"login": login})
        print(json.dumps(payload, indent=2))
        return 0

    try:
        pr_body = fetch_pull_request_body(owner, repo_name, pr_number, token)
        ctx = PullRequestContext(owner, repo_name, pr_number, login, pr_body)
        signals = collect_pull_signals(ctx, token)
        result = vet_pull_author(signals, thresholds)
    except (GitHubApiError, KeyError, ValueError) as exc:
        reason = f"vetting failed: {exc}"
        if fail_open:
            print(json.dumps({"verdict": "error", "reasons": [reason]}))
            return 0
        print(json.dumps({"verdict": "error", "reasons": [reason]}))
        return 2

    payload = _build_output(result, signals)
    print(json.dumps(payload, indent=2))
    return 0 if result.verdict in PASS_VERDICTS else 1


def _build_output(result: VetResult, signals: dict[str, Any]) -> dict[str, Any]:
    return {
        "verdict": result.verdict,
        "score": result.score,
        "reasons": result.reasons,
        "signals": signals,
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return build_arg_parser().parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
