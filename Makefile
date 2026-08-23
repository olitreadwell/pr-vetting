PYTHON ?= python3

.PHONY: check format lint type test install

install:
	$(PYTHON) -m pip install -e ".[dev]"

format:
	$(PYTHON) -m ruff format --check .

lint:
	$(PYTHON) -m ruff check .

type:
	$(PYTHON) -m mypy pr_vetting

test:
	$(PYTHON) -m pytest

check: format lint type test
