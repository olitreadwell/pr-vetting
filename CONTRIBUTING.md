# Contributing

Thanks for helping. Small, focused changes land fastest.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
make install
```

## Check

```bash
make check
```

This runs, in order: `ruff format --check`, `ruff check`, `mypy`, and
`pytest`. CI runs the same commands on every push and pull request.

## Conventions

- Follow the naming rules in `AGENTS.md`: 2-3 word domain-prefixed
  names, one spelling per concept.
- Doc comments live directly above the definition they explain.
- Every public function in `pr_vetting/` gets a docstring.
- Tests live in `tests/`, named after the module they cover.
- The core (`rules.py`, `signals.py`) stays pure and API-free. All
  GitHub access goes through `github_api.py` so tests can mock it.

## What to change

- New signals: add a function to `github_api.py`, call it from
  `collect_pull_signals`, document it in the README table.
- New rules: add them to `vet_pull_author` with a test. Keep verdicts
  explicit. Never gate on the numeric score.
- Action behavior: `action.yml` is the composite wrapper. Keep the shell
  thin; logic belongs in Python.

## Commits

Conventional Commits style, one idea per line:

```
feat: add organization membership signal

Adds org_count to the signals dict and weights it in the score.
```
