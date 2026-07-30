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
- [x] PyPI workflow rejects branch refs, mismatched tags/versions, unfinished
      release documents, and uninspected distributions.
- [x] Container base image is pinned to an immutable multi-platform digest and
      covered by Dependabot.
- [ ] Human review of security-critical subprocess, path, plugin, workflow, and
      container changes.
- [x] Hosted CI on Linux, macOS, and Windows passed for audited commit
      `1c462be99a51b65f9b49110896dec9686e068eea` (run `30562522583`).
- [ ] Reconfirm hosted CI for the eventual tagged release commit.

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
- [x] Automated distribution inspection is enforced before PyPI publication
- [x] Dependency vulnerability audit
- [x] Secret and generated-artifact scans
- [x] No-cache container build and non-root smoke test
- [x] Python 3.11 check
- [x] Python 3.14 check

## Publication checkpoints

- [ ] Confirm the `omnixform` PyPI namespace immediately before release.
- [ ] Create and protect the `pypi` GitHub environment (the read-only API
      reported no environments on 2026-07-30).
- [ ] Configure and review PyPI trusted publishing for that environment.
- [ ] Enable or verify GitHub private vulnerability reporting.
- [ ] Replace `Unreleased` with the actual release date/status in
      `CHANGELOG.md` and `RELEASE_NOTES.md`.
- [ ] Obtain explicit owner permission to create and push tag `v0.1.0`.
- [ ] Obtain explicit owner permission to create a GitHub Release.
- [ ] Obtain explicit owner permission to publish to PyPI.
- [ ] Obtain explicit owner permission to publish
      `ghcr.io/ionnixf/omnixform`.
- [ ] Download the published artifacts and repeat metadata, signature, install,
      and CLI smoke checks.

No tag, GitHub Release, PyPI distribution, or container image may be published
merely because the local checks pass.
