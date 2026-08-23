"""Tests for the GitHub API client with a mocked HTTP layer."""

import json
import urllib.error

import pytest

from pr_vetting import github_api


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeUrlError(urllib.error.HTTPError):
    def __init__(self, code):
        self.code = code

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def fake_urlopen(payload):
    def _open(request, timeout=None):
        return FakeResponse(payload)

    return _open


def fake_urlopen_error(code):
    def _open(request, timeout=None):
        raise FakeUrlError(code)

    return _open


def test_get_json_success(monkeypatch):
    monkeypatch.setattr(github_api.urllib.request, "urlopen", fake_urlopen({"ok": 1}))
    assert github_api._get_json_any("https://api.github.com/x", None) == {"ok": 1}


def test_get_json_404_raises_user_not_found(monkeypatch):
    monkeypatch.setattr(github_api.urllib.request, "urlopen", fake_urlopen_error(404))
    with pytest.raises(github_api.UserNotFoundError):
        github_api._get_json_any("https://api.github.com/x", None)


def test_get_json_500_raises_api_error(monkeypatch):
    monkeypatch.setattr(github_api.urllib.request, "urlopen", fake_urlopen_error(500))
    with pytest.raises(github_api.GitHubApiError):
        github_api._get_json_any("https://api.github.com/x", None)


def test_fetch_user_profile_maps_public_fields(monkeypatch):
    monkeypatch.setattr(
        github_api.urllib.request, "urlopen", fake_urlopen({"type": "User", "public_repos": 2})
    )
    profile = github_api.fetch_user_profile("ann")
    assert profile["type"] == "User"
    assert profile["public_repos"] == 2


def test_count_author_merged_prs_reads_total_count(monkeypatch):
    monkeypatch.setattr(github_api.urllib.request, "urlopen", fake_urlopen({"total_count": 4}))
    assert github_api.count_author_merged_prs("owner", "repo", "ann") == 4


def test_fetch_commit_verification_parses_graphql(monkeypatch):
    payload = {
        "data": {
            "repository": {
                "pullRequest": {
                    "commits": {
                        "nodes": [
                            {"commit": {"signature": {"isValid": True}}},
                            {"commit": {"signature": {"isValid": False}}},
                        ]
                    }
                }
            }
        }
    }
    monkeypatch.setattr(github_api.urllib.request, "urlopen", fake_urlopen(payload))
    assert github_api.fetch_commit_verification("owner", "repo", 87) == (2, 1)


def test_find_issue_referenced_by_author_requires_author_match(monkeypatch):
    monkeypatch.setattr(
        github_api.urllib.request,
        "urlopen",
        fake_urlopen({"user": {"login": "ann"}}),
    )
    assert github_api.find_issue_referenced_by_author("Fixes #12", "owner", "repo", "ann") is True
    assert github_api.find_issue_referenced_by_author("Fixes #12", "owner", "repo", "bob") is False


def test_find_issue_referenced_by_author_ignores_missing_ref(monkeypatch):
    monkeypatch.setattr(github_api.urllib.request, "urlopen", fake_urlopen({}))
    assert (
        github_api.find_issue_referenced_by_author("No ref here", "owner", "repo", "ann") is False
    )


def test_fetch_pull_request_body_returns_string(monkeypatch):
    monkeypatch.setattr(github_api.urllib.request, "urlopen", fake_urlopen({"body": "hello"}))
    assert github_api.fetch_pull_request_body("owner", "repo", 87) == "hello"


def test_graphql_errors_raise_api_error(monkeypatch):
    monkeypatch.setattr(
        github_api.urllib.request,
        "urlopen",
        fake_urlopen({"errors": [{"message": "boom"}]}),
    )
    with pytest.raises(github_api.GitHubApiError, match="boom"):
        github_api.fetch_commit_verification("owner", "repo", 87)


def test_fetch_contribution_totals_parses_graphql(monkeypatch):
    payload = {
        "data": {
            "user": {
                "contributionsCollection": {
                    "totalCommitContributions": 3,
                    "totalPullRequestContributions": 1,
                    "totalPullRequestReviewContributions": 2,
                    "totalIssueContributions": 4,
                }
            }
        }
    }
    monkeypatch.setattr(github_api.urllib.request, "urlopen", fake_urlopen(payload))
    totals = github_api.fetch_contribution_totals("ann")
    assert totals == {"commits": 3, "pull_requests": 1, "reviews": 2, "issues": 4}


def test_fetch_public_repo_footprint_counts_content_and_forks(monkeypatch):
    payload = [
        {"fork": False, "size": 100, "stargazers_count": 2},
        {"fork": True, "size": 200, "stargazers_count": 0},
        {"fork": False, "size": 0, "stargazers_count": 0},
    ]
    monkeypatch.setattr(github_api.urllib.request, "urlopen", fake_urlopen(payload))
    footprint = github_api.fetch_public_repo_footprint("ann")
    assert footprint == {"content_repo_count": 1, "fork_count": 1, "stars": 2}
