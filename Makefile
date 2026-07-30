.PHONY: install install-dev test lint format-check typecheck check clean

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

clean:
	rm -rf build/ dist/ *.egg-info/ .pytest_cache/ __pycache__/
	find . -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -delete
