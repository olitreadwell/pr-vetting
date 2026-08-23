"""Tests for the command line entry point."""

from pr_vetting import cli, github_api


def test_allowlist_short_circuits_without_api(monkeypatch):
    monkeypatch.setattr("pr_vetting.cli.fetch_pull_request_body", lambda *a, **k: "")
    code = cli.main(["--repo", "ologie/repo", "--pr", "87", "--login", "ann", "--allowlist", "ann"])
    assert code == 0


def test_blocked_author_exits_one(monkeypatch):
    def fake_collect(ctx, token=None):
        return {
            "login": "ann",
            "account": {"type": "missing", "age_days": 0},
            "history": {},
            "commits": {"count": 0, "verified": 0},
            "meta": {"account_exists": False},
        }

    monkeypatch.setattr("pr_vetting.cli.fetch_pull_request_body", lambda *a, **k: "")
    monkeypatch.setattr("pr_vetting.cli.collect_pull_signals", fake_collect)
    code = cli.main(["--repo", "ologie/repo", "--pr", "87", "--login", "ann"])
    assert code == 1


def test_api_error_exits_two(monkeypatch):
    def boom(*args, **kwargs):
        raise github_api.GitHubApiError("rate limited")

    monkeypatch.setattr(github_api, "fetch_pull_request_body", boom)
    code = cli.main(["--repo", "ologie/repo", "--pr", "87", "--login", "ann"])
    assert code == 2


def test_api_error_with_fail_open_exits_zero(monkeypatch):
    def boom(*args, **kwargs):
        raise github_api.GitHubApiError("rate limited")

    monkeypatch.setattr(github_api, "fetch_pull_request_body", boom)
    code = cli.main(["--repo", "ologie/repo", "--pr", "87", "--login", "ann", "--fail-open"])
    assert code == 0
