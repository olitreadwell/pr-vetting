"""Rule-based verdicts for pull request authors.

The verdict comes from explicit, documented rules. The score is
informational only and never gates anything by itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

PASS_VERDICTS = frozenset({"maintainer", "vetted", "established", "known"})
BLOCK_VERDICTS = frozenset({"blocked", "review_required"})


@dataclass(frozen=True)
class VetThresholds:
    """Tunable policy knobs for the rules engine."""

    min_account_age_days: int = 90
    min_in_repo_merged_prs: int = 1
    min_global_merged_prs: int = 0
    require_signed_commits: bool = False
    allowlist: frozenset[str] = frozenset()


@dataclass(frozen=True)
class VetResult:
    """Outcome of vetting one pull request author."""

    verdict: str
    score: int
    reasons: list[str]


def vet_pull_author(signals: dict[str, Any], thresholds: VetThresholds) -> VetResult:
    """Classify an author into a trust tier with a plain-language score."""
    reasons: list[str] = []
    login = str(signals.get("login", ""))

    if login in thresholds.allowlist:
        return VetResult("maintainer", 100, ["author is on the maintainer allowlist"])

    meta = signals.get("meta", {})
    if not meta.get("account_exists", True):
        return VetResult("blocked", 0, ["GitHub account not found for the pull request author"])

    account = signals.get("account", {})
    if account.get("type") != "User":
        return VetResult("blocked", 0, [f"account type is {account.get('type')}, not a human user"])

    commits = signals.get("commits", {})
    commit_count = int(commits.get("count", 0))
    verified_count = int(commits.get("verified", 0))
    if thresholds.require_signed_commits and commit_count > 0 and verified_count < commit_count:
        reasons.append(f"{verified_count} of {commit_count} commits are signed; all must be signed")

    history = signals.get("history", {})
    activity = signals.get("activity", {})
    repos = signals.get("repos", {})
    in_repo = int(history.get("in_repo_merged_prs", 0))
    global_merged = int(history.get("global_merged_prs", 0))
    age_days = int(account.get("age_days", 0))
    age_ok = age_days >= thresholds.min_account_age_days
    if not age_ok:
        reasons.append(
            f"account is {age_days} days old; minimum is {thresholds.min_account_age_days}"
        )
    if in_repo < thresholds.min_in_repo_merged_prs:
        reasons.append(
            f"{in_repo} merged PRs in this repo; minimum is {thresholds.min_in_repo_merged_prs}"
        )
    if global_merged < thresholds.min_global_merged_prs:
        reasons.append(
            f"{global_merged} merged PRs across GitHub; minimum is "
            f"{thresholds.min_global_merged_prs}"
        )

    work_activity = (
        int(activity.get("commits", 0))
        + int(activity.get("reviews", 0))
        + int(activity.get("issues", 0))
    )
    if work_activity == 0:
        reasons.append("no public commit, review, or issue activity in the last year")
    if int(repos.get("content_repo_count", 0)) == 0:
        reasons.append("owns no public repositories with content")

    signed_ok = verified_count >= commit_count if commit_count else True
    if in_repo >= thresholds.min_in_repo_merged_prs and signed_ok:
        if reasons:
            return VetResult("known", _compute_score(signals), reasons)
        return VetResult("established", _compute_score(signals), [])

    if age_ok and (in_repo + global_merged) >= 1 and work_activity >= 1 and signed_ok:
        if reasons:
            return VetResult("known", _compute_score(signals), reasons)
        return VetResult("known", _compute_score(signals), [])

    if not reasons:
        reasons.append("no history of merged pull requests")
    return VetResult("review_required", _compute_score(signals), reasons)


def _compute_score(signals: dict[str, Any]) -> int:
    """Informational 0-100 score; never used to gate."""
    account = signals.get("account", {})
    history = signals.get("history", {})
    commits = signals.get("commits", {})

    activity = signals.get("activity", {})
    repos = signals.get("repos", {})

    age_score = min(int(account.get("age_days", 0)) / 365 * 20, 20)
    in_repo_score = min(int(history.get("in_repo_merged_prs", 0)) * 15, 30)
    global_score = min(int(history.get("global_merged_prs", 0)) * 2, 10)
    work_activity = (
        int(activity.get("commits", 0))
        + int(activity.get("reviews", 0))
        + int(activity.get("issues", 0))
    )
    activity_score = min(work_activity * 3, 25)
    signed = (
        10
        if int(commits.get("count", 0)) > 0
        and int(commits.get("verified", 0)) >= int(commits.get("count", 0))
        else 0
    )
    org_score = min(int(account.get("org_count", 0)) * 2, 5)
    repo_score = 5 if int(repos.get("content_repo_count", 0)) > 0 else 0
    profile_score = 5 if _has_full_profile(account) else 0
    issue_score = 10 if history.get("referenced_issue_by_author") else 0

    raw = (
        age_score
        + in_repo_score
        + global_score
        + activity_score
        + signed
        + org_score
        + repo_score
        + profile_score
        + issue_score
    )
    return min(round(raw), 100)


def _has_full_profile(account: dict[str, Any]) -> bool:
    fields = ("bio", "blog", "location", "email")
    return all(bool(account.get(field)) for field in fields)
