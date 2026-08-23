"""Thin GitHub API client used by the vetting pipeline.

Only public data is read. A token is optional; without one the search
endpoints rate limit at 10 requests per minute.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, cast

API_BASE = "https://api.github.com"
GRAPHQL_URL = "https://api.github.com/graphql"


class GitHubApiError(RuntimeError):
    """Raised when the GitHub API returns an error we cannot work around."""


class UserNotFoundError(GitHubApiError):
    """Raised when the author login does not resolve to a GitHub user."""


def _auth_header(token: str | None) -> dict[str, str]:
    resolved = token or os.environ.get("GITHUB_TOKEN", "")
    headers: dict[str, str] = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "pr-vetting",
    }
    if resolved:
        headers["Authorization"] = f"Bearer {resolved}"
    return headers


def _get_json_any(url: str, token: str | None) -> Any:
    req = urllib.request.Request(url, headers=_auth_header(token))
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise UserNotFoundError(f"GitHub returned 404 for {url}") from exc
        raise GitHubApiError(f"GitHub API returned {exc.code} for {url}") from exc


def _graphql(query: str, variables: dict[str, Any], token: str | None) -> dict[str, Any]:
    payload = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(GRAPHQL_URL, data=payload, headers=_auth_header(token))
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            result = cast(dict[str, Any], json.loads(resp.read().decode()))
    except urllib.error.HTTPError as exc:
        raise GitHubApiError(f"GraphQL returned {exc.code}") from exc
    if "errors" in result and "data" not in result:
        detail = str(result["errors"])[:200]
        raise GitHubApiError(f"GraphQL reported errors: {detail}")
    return result


def fetch_user_profile(login: str, token: str | None = None) -> dict[str, Any]:
    """Fetch the public profile of a GitHub user."""
    return cast(
        dict[str, Any], _get_json_any(f"{API_BASE}/users/{urllib.parse.quote(login)}", token)
    )


def fetch_user_org_count(login: str, token: str | None = None) -> int:
    """Count the public organizations a user belongs to."""
    orgs = cast(
        list[Any],
        _get_json_any(f"{API_BASE}/users/{urllib.parse.quote(login)}/orgs?per_page=100", token),
    )
    return len(orgs)


def count_author_merged_prs(owner: str, repo: str, login: str, token: str | None = None) -> int:
    """Count merged pull requests authored by a user in one repository."""
    query = f"repo:{owner}/{repo} type:pr author:{login} is:merged"
    return _count_search_results(query, token)


def count_global_merged_prs(login: str, token: str | None = None) -> int:
    """Count merged pull requests authored by a user across GitHub."""
    query = f"type:pr author:{login} is:merged"
    return _count_search_results(query, token)


def _count_search_results(query: str, token: str | None) -> int:
    encoded = urllib.parse.quote(query)
    result = cast(
        dict[str, Any], _get_json_any(f"{API_BASE}/search/issues?q={encoded}&per_page=1", token)
    )
    return int(result.get("total_count", 0))


def fetch_commit_verification(
    owner: str, repo: str, pr_number: int, token: str | None = None
) -> tuple[int, int]:
    """Return (commit_count, verified_count) for a pull request."""
    query = """
    query($owner: String!, $repo: String!, $number: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $number) {
          commits(first: 50) {
            nodes {
              commit {
                signature { isValid }
              }
            }
          }
        }
      }
    }
    """
    variables = {"owner": owner, "repo": repo, "number": pr_number}
    result = _graphql(query, variables, token)
    commits = result["data"]["repository"]["pullRequest"]["commits"]["nodes"]
    verified = sum(
        1
        for node in commits
        if node["commit"].get("signature") and node["commit"]["signature"].get("isValid")
    )
    return len(commits), verified


def fetch_contribution_totals(login: str, token: str | None = None) -> dict[str, int]:
    """Return last-year contribution totals for a user from GraphQL."""
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          totalCommitContributions
          totalPullRequestContributions
          totalPullRequestReviewContributions
          totalIssueContributions
        }
      }
    }
    """
    result = _graphql(query, {"login": login}, token)
    user = result.get("data", {}).get("user")
    if not user:
        raise UserNotFoundError(f"GitHub returned no user for {login}")
    collection = user["contributionsCollection"]
    return {
        "commits": int(collection["totalCommitContributions"]),
        "pull_requests": int(collection["totalPullRequestContributions"]),
        "reviews": int(collection["totalPullRequestReviewContributions"]),
        "issues": int(collection["totalIssueContributions"]),
    }


def fetch_public_repo_footprint(login: str, token: str | None = None) -> dict[str, int]:
    """Summarize the public repositories a user owns."""
    repos = cast(
        list[Any],
        _get_json_any(f"{API_BASE}/users/{urllib.parse.quote(login)}/repos?per_page=100", token),
    )
    content_count = 0
    fork_count = 0
    stars = 0
    for repo in repos:
        if repo.get("fork"):
            fork_count += 1
            continue
        stars += int(repo.get("stargazers_count", 0))
        if int(repo.get("size", 0)) > 0:
            content_count += 1
    return {"content_repo_count": content_count, "fork_count": fork_count, "stars": stars}


def fetch_pull_request_body(owner: str, repo: str, pr_number: int, token: str | None = None) -> str:
    """Return the body text of a pull request."""
    pr = cast(
        dict[str, Any], _get_json_any(f"{API_BASE}/repos/{owner}/{repo}/pulls/{pr_number}", token)
    )
    return str(pr.get("body", ""))


def find_issue_referenced_by_author(
    pr_body: str, owner: str, repo: str, login: str, token: str | None = None
) -> bool:
    """True when the PR body references an issue the author opened."""
    import re

    match = re.search(r"#(\d+)", pr_body or "")
    if not match:
        return False
    issue_number = int(match.group(1))
    try:
        issue = cast(
            dict[str, Any],
            _get_json_any(f"{API_BASE}/repos/{owner}/{repo}/issues/{issue_number}", token),
        )
    except GitHubApiError:
        return False
    author = issue.get("user", {})
    return bool(isinstance(issue, dict) and author.get("login") == login)
