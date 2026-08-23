"""Collect public GitHub signals about a pull request author.

Signals are gathered from the GitHub API and shaped into a flat,
serializable dictionary so rule evaluation stays pure and testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import github_api


@dataclass(frozen=True)
class PullRequestContext:
    """Identifies the pull request and author being vetted."""

    owner: str
    repo: str
    pr_number: int
    login: str
    pr_body: str = ""


def collect_pull_signals(ctx: PullRequestContext, token: str | None = None) -> dict[str, Any]:
    """Gather all public signals for the author of a pull request."""
    try:
        profile = github_api.fetch_user_profile(ctx.login, token)
    except github_api.UserNotFoundError:
        return _signals_for_missing_account(ctx.login)

    import datetime

    created_at = profile.get("created_at", "")
    age_days = 0
    try:
        created = datetime.date.fromisoformat(created_at[:10])
        age_days = (datetime.date.today() - created).days
    except ValueError:
        pass

    commit_count, verified_count = github_api.fetch_commit_verification(
        ctx.owner, ctx.repo, ctx.pr_number, token
    )

    return {
        "login": ctx.login,
        "account": {
            "type": profile.get("type", ""),
            "age_days": age_days,
            "public_repos": profile.get("public_repos", 0),
            "followers": profile.get("followers", 0),
            "bio": bool(profile.get("bio")),
            "blog": bool(profile.get("blog")),
            "location": bool(profile.get("location")),
            "email": bool(profile.get("email")),
            "org_count": github_api.fetch_user_org_count(ctx.login, token),
        },
        "history": {
            "in_repo_merged_prs": github_api.count_author_merged_prs(
                ctx.owner, ctx.repo, ctx.login, token
            ),
            "global_merged_prs": github_api.count_global_merged_prs(ctx.login, token),
            "referenced_issue_by_author": github_api.find_issue_referenced_by_author(
                ctx.pr_body, ctx.owner, ctx.repo, ctx.login, token
            ),
        },
        "commits": {"count": commit_count, "verified": verified_count},
        "activity": github_api.fetch_contribution_totals(ctx.login, token),
        "repos": github_api.fetch_public_repo_footprint(ctx.login, token),
        "meta": {"account_exists": True},
    }


def _signals_for_missing_account(login: str) -> dict[str, Any]:
    return {
        "login": login,
        "account": {"type": "missing", "age_days": 0},
        "history": {},
        "commits": {"count": 0, "verified": 0},
        "meta": {"account_exists": False},
    }
