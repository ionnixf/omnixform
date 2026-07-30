# Omnixform release checklist

This checklist does not authorize publication. Version `0.1.0` is the planned
first public release.

## Source and review

- [x] Distribution, import package, CLI, plugin group, environment prefix,
      documentation, workflows, and container configuration use the approved
      names.
- [x] Temporary owner test assets are absent from source and distributions.
- [x] Version metadata and release documents use `0.1.0`.
- [x] Project policy files and GitHub templates are present.
- [x] No compatibility package or deprecated command was added.
- [ ] Human review of security-critical subprocess, path, plugin, workflow, and
      container changes.
- [ ] Hosted CI passes on Linux, macOS, and Windows.

## Local verification

- [x] `ruff check .`
- [x] `ruff format --check .`
- [x] `mypy src tests`
- [x] Full `pytest` and coverage run
- [x] `mkdocs build --strict`
- [x] Wheel and sdist build
- [x] `twine check --strict dist/*`
- [x] Clean wheel and sdist installations with `pip check`
- [x] Installed CLI help/version and user-scenario smoke tests
- [x] Installed third-party plugin discovery and conversion
- [x] Wheel/sdist content inspection
- [x] Dependency vulnerability audit
- [x] Secret and generated-artifact scans
- [x] No-cache container build and non-root smoke test
- [x] Python 3.11 check
- [x] Python 3.14 check

## Publication checkpoints

- [ ] Confirm the `omnixform` PyPI namespace immediately before release.
- [ ] Configure and review PyPI trusted publishing for the protected `pypi`
      GitHub environment.
- [ ] Obtain explicit owner permission to create and push tag `v0.1.0`.
- [ ] Obtain explicit owner permission to create a GitHub Release.
- [ ] Obtain explicit owner permission to publish to PyPI.
- [ ] Obtain explicit owner permission to publish
      `ghcr.io/ionnixf/omnixform`.
- [ ] Download the published artifacts and repeat metadata, signature, install,
      and CLI smoke checks.

No tag, GitHub Release, PyPI distribution, or container image may be published
merely because the local checks pass.
