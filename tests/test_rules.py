"""Tests for the verdict rules engine."""

from pr_vetting.rules import VetThresholds, vet_pull_author


def make_signals(**overrides):
    base = {
        "login": "ann",
        "account": {
            "type": "User",
            "age_days": 1000,
            "org_count": 1,
            "bio": True,
            "blog": True,
            "location": True,
            "email": True,
        },
        "history": {
            "in_repo_merged_prs": 0,
            "global_merged_prs": 0,
            "referenced_issue_by_author": False,
        },
        "commits": {"count": 2, "verified": 2},
        "activity": {"commits": 5, "pull_requests": 1, "reviews": 2, "issues": 1},
        "repos": {"content_repo_count": 1, "fork_count": 0, "stars": 0},
        "meta": {"account_exists": True},
    }
    base.update(overrides)
    return base


def test_allowlist_passes_as_maintainer():
    signals = make_signals()
    result = vet_pull_author(signals, VetThresholds(allowlist=frozenset({"ann"})))
    assert result.verdict == "maintainer"
    assert result.score == 100


def test_missing_account_is_blocked():
    signals = make_signals(meta={"account_exists": False})
    result = vet_pull_author(signals, VetThresholds())
    assert result.verdict == "blocked"


def test_non_user_account_is_blocked():
    signals = make_signals()
    signals["account"]["type"] = "Bot"
    result = vet_pull_author(signals, VetThresholds())
    assert result.verdict == "blocked"


def test_clean_history_is_established():
    signals = make_signals()
    signals["history"]["in_repo_merged_prs"] = 2
    result = vet_pull_author(signals, VetThresholds())
    assert result.verdict == "established"
    assert result.reasons == []


def test_young_account_with_in_repo_history_is_known():
    signals = make_signals()
    signals["account"]["age_days"] = 10
    signals["history"]["in_repo_merged_prs"] = 1
    result = vet_pull_author(signals, VetThresholds())
    assert result.verdict == "known"


def test_global_history_with_age_is_known():
    signals = make_signals()
    signals["history"]["global_merged_prs"] = 1
    result = vet_pull_author(signals, VetThresholds())
    assert result.verdict == "known"


def test_no_history_is_review_required():
    result = vet_pull_author(make_signals(), VetThresholds())
    assert result.verdict == "review_required"
    assert any("merged" in reason for reason in result.reasons)


def test_signed_commits_required_blocks_unsigned():
    signals = make_signals()
    signals["history"]["in_repo_merged_prs"] = 5
    signals["commits"] = {"count": 2, "verified": 0}
    result = vet_pull_author(signals, VetThresholds(require_signed_commits=True))
    assert result.verdict == "review_required"
    assert any("signed" in reason for reason in result.reasons)


def test_score_stays_in_bounds():
    result = vet_pull_author(make_signals(), VetThresholds())
    assert 0 <= result.score <= 100


def test_zero_cross_repo_activity_gets_review_reasons():
    signals = make_signals()
    signals["activity"] = {"commits": 0, "pull_requests": 1, "reviews": 0, "issues": 0}
    signals["repos"] = {"content_repo_count": 0, "fork_count": 1, "stars": 0}
    result = vet_pull_author(signals, VetThresholds())
    assert result.verdict == "review_required"
    assert any("no public commit" in reason for reason in result.reasons)
    assert any("no public repositories with content" in reason for reason in result.reasons)
