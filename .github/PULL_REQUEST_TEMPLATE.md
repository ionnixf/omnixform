## Problem and evidence

<!-- What is wrong or missing? Link the issue and include factual evidence. -->

## Change

<!-- Explain the narrow solution and any public CLI/API impact. -->

## Verification

<!-- List exact commands run and their outcomes. Distinguish skipped/manual checks. -->

- [ ] Regression tests added or updated
- [ ] `ruff check src tests benchmarks`
- [ ] `ruff format --check src tests benchmarks`
- [ ] `mypy src tests --python-version 3.11`
- [ ] `pytest`
- [ ] Documentation updated when user-visible behavior changed
- [ ] No secrets, generated artifacts, unknown-provenance media, or personal paths

## Release and security

<!-- Note dependency, subprocess, parser, permission, or publication changes. -->

- [ ] This PR does not publish, tag, push an image, or change repository secrets/settings
- [ ] Breaking changes and known limitations are documented
