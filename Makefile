.PHONY: install install-dev test lint format-check typecheck check inspect-dist clean

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

test:
	pytest -x

lint:
	ruff check src/omnixform/ tests/ benchmarks/

format-check:
	ruff format --check src/omnixform/ tests/ benchmarks/

typecheck:
	mypy src/omnixform/ --python-version 3.11

check: lint format-check typecheck test

inspect-dist:
	python scripts/inspect_distributions.py --expected-version 0.1.0

clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ __pycache__/
	find . -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete
