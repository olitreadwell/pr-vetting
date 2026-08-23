# Changelog

All notable changes to this project are documented here. The format is
based on Keep a Changelog, and versioning follows Semantic Versioning.
Release tags use beta suffixes until v1: `v0.3.1-beta.1`.

## [Unreleased]

## [0.3.2-beta.1] - 2026-08-24

### Fixed

- Gate comments no longer stack. The action updates its previous
  `PR vetting check:` comment in place, or creates one if none exists.
  The comment body is written to a temp file instead of a process
  substitution, which `gh` could not read reliably.

## [0.3.1-beta.1] - 2026-08-24

### Fixed

- Composite action only passes `--fail-open` when the input is `true`.
  The boolean flag was always passed with a value, which made every run
  fail with `pr-vetting: error: unrecognized arguments: false`.

## [0.3.0-beta.1] - 2026-08-24

### Added

- Automation accounts pass the gate as trusted tooling when the login
  ends in `[bot]` (Dependabot and friends). The allowlist still wins
  when it explicitly lists the same login.
- Beta notice in the README. Consumption pins a beta tag until v1.

## [0.2.0] - 2026-08-24

### Added

- Last-year contribution totals from GraphQL: commits, pull requests,
  reviews, and issues.
- Public repository footprint: content repos vs forks and empty repos,
  plus stars received.

### Changed

- `known` tier now requires real cross-repo work in the last year, not
  just an aged account.
- Score rebalanced: activity worth up to 25, content repos worth 5,
  profile and age trimmed.
- Verdict reasons now name dormancy directly: no last-year activity and
  no content repos are both called out.

### Removed

- Events API recency check. It counted the PR itself as recent
  activity, and GraphQL totals cover the signal better.

## [0.1.0] - 2026-08-24

### Added

- Initial release: rules-based verdicts for pull request authors from
  public GitHub signals.
- Signals: account age and type, merged PRs in this repo and globally,
  commit signature verification, org membership, referenced issue by the
  author, profile completeness.
- Composite GitHub Action with threshold inputs, allowlist,
  `vetted-contributor` label override, and PR comments.
- Standalone CLI with JSON output and stable exit codes (0 pass, 1
  blocked, 2 API error).
- Zero runtime dependencies, mocked test suite, single `make check`.
