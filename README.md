# PR Vetting

> **Beta.** The signal set and verdict rules are still settling. Pin a
> specific tag and review the output before trusting it in production.

CI-runable vetting of pull request authors. Uses only public GitHub
signals to classify an author into a trust tier, so unknown or bot
accounts cannot merge into your repository without a human decision.

Works as a GitHub Action and as a plain Python CLI. No database, no
external services, no dependencies.

## Verdicts

| Verdict | Meaning | Gate |
| --- | --- | --- |
| `maintainer` | Login on the allowlist | pass |
| `vetted` | Maintainer added the `vetted-contributor` label | pass |
| `established` | Enough merged PRs in this repo, no open questions | pass |
| `known` | Some history and an aged account | pass |
| `review_required` | New or unknown author, reasons listed | fail |
| `dormant` | No activity anywhere and no content repos; auto-close candidate | fail or close |
| `blocked` | Missing account, bot account, or worse | fail |
| `error` | API failure; fails unless `fail-open` is set | fail |

The 0-100 score is informational only. Gating uses the verdict.

## Signals

All data comes from the public GitHub API. Nothing is stored.

| Signal | Source | Notes |
| --- | --- | --- |
| Account age | `GET /users/{login}` | Bots age accounts; weak alone |
| Account type | `GET /users/{login}` | Bot vs User |
| Merged PRs in repo | search API | Strongest signal, task-specific |
| Merged PRs globally | search API | Cross-repo proof of work |
| Commit signatures | GraphQL | `signature.isValid` per commit |
| Contribution totals | GraphQL | Last-year commits, PRs, reviews, issues |
| Public repo footprint | `GET /users/{login}/repos` | Owns content vs forks and empties |
| Org membership | `GET /users/{id}/orgs` | Harder to fake |
| Referenced issue | PR body | Issue opened by same author first |
| Profile completeness | profile fields | bio, blog, location, email |

## Usage

As a required status check in a workflow on `pull_request_target`:

```yaml
name: gate

on:
  pull_request_target:
    types: [opened, reopened, synchronize, labeled, unlabeled]
    branches: [main]

permissions:
  pull-requests: write
  issues: write

jobs:
  vet:
    runs-on: ubuntu-latest
    steps:
      - uses: olitreadwell/pr-vetting@v0.4.0-beta.1
        id: vet
        with:
          pr-number: ${{ github.event.pull_request.number }}
          login: ${{ github.event.pull_request.user.login }}
          min-account-age-days: 90
          min-in-repo-merged-prs: 1
          require-signed-commits: false
          allowlist: "olitreadwell"
      - name: Fail the check for review_required
        if: steps.vet.outputs.verdict == 'review_required' || steps.vet.outputs.verdict == 'blocked'
        run: exit 1
```

The vetted label: a maintainer who has reviewed the PR adds the
`vetted-contributor` label and the check passes. Create the label once:

```bash
gh label create vetted-contributor --description "Account vetted by a maintainer" --color 0e8a16
```

Then require the status check in branch protection so the gate blocks
merges.

## Standalone CLI

```bash
python3 -m pr_vetting --repo owner/name --pr 87 --login ann --token "$GITHUB_TOKEN"
```

Output is JSON with `verdict`, `score`, `reasons`, and the raw signals.
Exit code is 0 for passing verdicts, 1 for blocking verdicts, and 2 for
API errors.

## Inputs

| Input | Default | Purpose |
| --- | --- | --- |
| `token` | `github.token` | API token |
| `repo` | current repo | owner/name |
| `pr-number` | required | PR number |
| `login` | required | PR author login |
| `min-account-age-days` | 90 | Age floor |
| `min-in-repo-merged-prs` | 1 | In-repo history floor |
| `min-global-merged-prs` | 0 | Global history floor |
| `require-signed-commits` | false | All commits must be verified |
| `allowlist` | "" | Always-pass logins; bots (login ends in `[bot]`) pass automatically |
| `vetted-label` | vetted-contributor | Manual override label |
| `comment-on-open` | true | Comment reasons on open |
| `auto-close-dormant` | false | Close PRs from dormant authors (opt-in, destructive) |
| `fail-open` | false | Pass on API errors |

## Development

```bash
python -m venv .venv && source .venv/bin/activate
make install
make check
```

`make check` runs format, lint, type check, and tests.

## Design constraints

- Public data only. 2FA status is not exposed by the public API, so it
  is never checked.
- Verdicts come from rules, not from an opaque weighted score.
- The gate is a filter for casual bots and spam, not a certification of
  humans. Manual review stays the final authority.
- Contributors keep the right to appeal: the label override exists for a
  reason.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

MIT. See [LICENSE](LICENSE).


## Auto-closing dormant accounts

Set `auto-close-dormant: true` to close pull requests from authors
who show no public activity anywhere and own no public repositories
with content. Only `dormant` verdicts are closed, and only on `opened`
or `reopened` events. The close comment explains the appeal path: a
maintainer adds the `vetted-contributor` label and reopens.
