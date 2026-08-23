# Security

## Reporting

Private issues preferred: open an issue on this repository, or email the
maintainer (see the commit author email).

Do not open a public issue for an active vulnerability.

## Threat model

PR Vetting filters casual spam and bot accounts. It is not a
certification that a contributor is human or safe. Treat every merged PR
as something that still deserves a human review.

Signals are public and gameable. Never gate on the score alone. The
verdict rules are the contract; keep them conservative.

## Hardening checklist

- Token used by the action: prefer `github.token` with
  `permissions: pull-requests: write` only.
- Run the action on `pull_request_target`, never `pull_request`, so the
  token has base-branch context. Never check out PR code in the same
  workflow.
- Set `fail-open: false` (the default) so API outages fail the check
  instead of admitting unknown authors.
- Keep the allowlist short. Every login on it can merge without review.
