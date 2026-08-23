# AGENTS.md

Instructions for AI coding agents working in this repo.

## Layout

- `pr_vetting/` - the library. One concept per module:
  - `github_api.py` - all GitHub HTTP access, nothing else.
  - `signals.py` - collects public signals into a flat dict.
  - `rules.py` - verdict rules, pure and testable.
  - `cli.py` - argparse entry point.
- `tests/` - pytest, named after the module under test.
- `action.yml` - composite GitHub Action wrapper. Thin shell, no logic.
- `Makefile` - the single `check` command.

## Conventions

- 2-3 word domain-prefixed names for exports
  (`collect_pull_signals`, not `collect`).
- One spelling per concept. `review_required` everywhere, not
  `needs_review` in one file and `review` in another.
- Doc comment above every exported function.
- No third-party runtime dependencies. Tests use pytest, ruff, mypy.
- Never store data, never write state. Every run is stateless API calls.
- The score never gates. The verdict gates. Keep it that way.

## Commands

```bash
make install   # pip install -e ".[dev]"
make check     # format + lint + type + test
```

## Signals are gameable

Treat every reputation signal as a weak proxy. The point of the tool is
to filter casual bots and to force a human decision for unknown
accounts, not to certify people. When adding a signal, add its weakness
to the README table.

If a new convention is established, update this file in the same change.
