# Contributing to Omnixform

Thank you for helping improve Omnixform. Please follow the
[Code of Conduct](CODE_OF_CONDUCT.md) and avoid reporting security issues in a
public issue; use the process in [SECURITY.md](SECURITY.md).

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,all-formats,docs]"
make check
```

External integration tests need FFmpeg, Pandoc, and LibreOffice. Missing tools
must produce a skip, not a fabricated pass.

## Changes

- Keep patches narrow and preserve the public CLI and adapter API unless a
  breaking change is justified.
- Add a regression test for bug fixes.
- Never invoke external converters through a shell. Pass a list of arguments
  and use the timeout helpers in `omnixform.subprocesses`.
- Write output to a staging path, validate it, and atomically publish it.
- Document optional dependencies and platform limitations.
- Do not commit generated distributions, `*.egg-info`, caches, local paths,
  credentials, media of unknown provenance, or benchmark claims without
  reproducible evidence.

## Checks

```bash
ruff check src tests benchmarks
ruff format --check src tests benchmarks
mypy src tests --python-version 3.11
pytest -m "not integration"
pytest -m integration
pytest --cov=omnixform --cov-report=term-missing
python -m build
twine check --strict dist/*
python scripts/inspect_distributions.py --expected-version 0.1.0
mkdocs build --strict
```

Use `pytest -m "not integration"` when system tools are unavailable and state
which integration checks were skipped.

## Plugins

Plugins must subclass `omnixform.adapters.base.BaseAdapter` and register under
`omnixform.adapters`. A plugin has the same permissions as Omnixform itself;
review dependencies and subprocess handling accordingly. See
[docs/advanced/plugins.md](docs/advanced/plugins.md).

## Pull requests

Describe the problem, evidence, solution, tests actually run, skipped checks,
and user-visible changes. Maintainers should use the release checklist before
tagging or publishing.
