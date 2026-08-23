"""Tests for signal collection with mocked GitHub API calls."""

import pytest

from pr_vetting import github_api
from pr_vetting.signals import PullRequestContext, collect_pull_signals


@pytest.fixture
def ctx():
    return PullRequestContext("owner", "repo", 87, "ann", "Fixes #12")


def test_missing_account_returns_flagged_signals(monkeypatch, ctx):
    def raise_missing(*args, **kwargs):
        raise github_api.UserNotFoundError("gone")

    monkeypatch.setattr(github_api, "fetch_user_profile", raise_missing)
    signals = collect_pull_signals(ctx)
    assert signals["meta"]["account_exists"] is False
    assert signals["account"]["type"] == "missing"


def test_happy_path_collects_all_signals(monkeypatch, ctx):
    def fake_profile(login, token=None):
        return {
            "type": "User",
            "created_at": "2010-01-01T00:00:00Z",
            "public_repos": 5,
            "followers": 3,
            "bio": "x",
            "blog": None,
            "location": "Auckland",
            "email": None,
        }

    monkeypatch.setattr(github_api, "fetch_user_profile", fake_profile)
    monkeypatch.setattr(github_api, "fetch_user_org_count", lambda *a, **k: 2)
    monkeypatch.setattr(github_api, "count_author_merged_prs", lambda *a, **k: 1)
    monkeypatch.setattr(github_api, "count_global_merged_prs", lambda *a, **k: 4)
    monkeypatch.setattr(github_api, "fetch_commit_verification", lambda *a, **k: (3, 2))
    monkeypatch.setattr(github_api, "find_issue_referenced_by_author", lambda *a, **k: True)
    monkeypatch.setattr(
        github_api,
        "fetch_contribution_totals",
        lambda *a, **k: {"commits": 4, "pull_requests": 1, "reviews": 0, "issues": 2},
    )
    monkeypatch.setattr(
        github_api,
        "fetch_public_repo_footprint",
        lambda *a, **k: {"content_repo_count": 1, "fork_count": 0, "stars": 3},
    )

    signals = collect_pull_signals(ctx)
    assert signals["account"]["type"] == "User"
    assert signals["account"]["age_days"] > 365 * 10
    assert signals["account"]["org_count"] == 2
    assert signals["activity"]["commits"] == 4
    assert signals["repos"]["content_repo_count"] == 1
    assert signals["history"]["in_repo_merged_prs"] == 1
    assert signals["history"]["global_merged_prs"] == 4
    assert signals["history"]["referenced_issue_by_author"] is True
    assert signals["commits"] == {"count": 3, "verified": 2}
