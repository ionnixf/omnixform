# Omnixform release and security audit

Audit date: 2026-07-30

Target version: `0.1.0`

Verdict: **Ready with conditions**

This audit is based on the source tree, locally executed checks, built
artifacts, and read-only namespace queries. Documentation and earlier agent
reports were not accepted as evidence without matching code or runtime checks.

## Historical naming note

Before Git was initialized, Omnixform used **FileForge** as an internal working
name and `0.3.0` as an internal pre-release version. It had no public Git or
package release history. The first proposed public version is therefore
`0.1.0`; no fictional earlier release series is retained.

## Naming review

Technical namespace screening does not reserve a name and is not legal advice.

| Namespace | Result | Evidence on 2026-07-30 | Risk |
| --- | --- | --- | --- |
| PyPI | Available candidate | `GET https://pypi.org/pypi/omnixform/json` returned 404 | Could be claimed before publication |
| TestPyPI | Available candidate | `GET https://test.pypi.org/pypi/omnixform/json` returned 404 | Could be claimed independently |
| GitHub | Owner repository exists | Exact-name search found only `ionnixf/omnixform`; repository API returned 200 and an empty `main` repository | Repository ownership and access must still be verified by push |
| npm | Available candidate | `GET https://registry.npmjs.org/omnixform` returned 404 | Unrelated ecosystem; not reserved |
| crates.io | Available candidate | crates.io API reported that the crate does not exist | Unrelated ecosystem; not reserved |
| Docker Hub | Available candidate | Exact repository lookup/search returned no result | Does not reserve the proposed GHCR name |
| GHCR | Unclear | Anonymous tags request required authentication | Confirm immediately before container publication |
| Homebrew | Available candidate | Exact formula and cask API lookups returned 404 | Formula names are not reserved |
| Web search | No direct technical conflict found | Exact searches for `Omnixform`, `omnixform`, and `OmniXform` found no active file/media/document conversion product | Similar “Omnix” names exist in unrelated fields |
| Trademark | Not legally cleared | N/A | Separate legal review is required |

**Conclusion:** No direct technical conflict was found during namespace
screening. Trademark clearance was not performed.

No account, package, container, tag, or release was created by these checks.

## Local validation summary

- Python 3.11.15: Ruff lint and format, strict mypy, 168 collected tests,
  **165 passed and 3 skipped** because Pandoc and LibreOffice were absent on
  the host.
- Coverage: **67%** overall.
- Host integrations: FFmpeg 8.1.2 and optional Pillow/CairoSVG conversions
  passed.
- Documentation: `mkdocs build --strict` passed.
- Packaging: isolated wheel and sdist builds and strict Twine checks passed.
- Clean installs: wheel and sdist installed in independent Python 3.11
  environments; both passed `pip check`, metadata, import, version, help, and
  conversion scenarios.
- Python 3.14.6: clean wheel install, `pip check`, version, and help passed.
- Plugins: a separately built distribution was installed into the clean wheel
  environment; discovery, metadata, and actual conversion passed.
- Dependency audit: after requiring the fixed `setuptools>=83.0.0`, `pip-audit`
  reported no known vulnerabilities in the audited environment (the editable
  local distribution itself was skipped).
- Credential scan: `detect-secrets` reported zero candidates in the source
  tree.
- Container: final no-cache Podman build passed; UID 1000 runtime, help/version,
  Pandoc Markdown-to-DOCX, LibreOffice DOCX-to-PDF, and FFmpeg WAV-to-MP3
  conversions passed.
- Artifacts: archive names and extracted content contain no stale package name,
  temporary media corpus, caches, VCS data, local absolute paths, or detected
  secrets.

## Git and version review

- The working directory initially contained no usable Git repository or
  commits.
- A new repository was initialized on `main`; the initial public source commit
  is documented in the final local/push report.
- The remote is `git@github.com:ionnixf/omnixform.git`.
- The remote repository was observed as public and empty before the initial
  push.
- Version `0.1.0` is used consistently as the first public release candidate.

## Findings

### AUD-001 — External converter processes could outlive timeout

- Severity: **High**
- Files: `src/omnixform/subprocesses.py`, external adapters
- Confirmation: earlier implementation timed only process creation rather than
  the complete communication phase.
- Impact: a damaged or hostile input could hang automation and leave a child
  process or partial output.
- Resolution: timeout now covers communication; timeout and cancellation
  terminate/kill and reap the child or process group.
- Regression test: **Required and present.**
- Status: **Resolved.**

### AUD-002 — Output could be published before validation

- Severity: **High**
- Files: `src/omnixform/cli.py`, `src/omnixform/paths.py`,
  `src/omnixform/validation.py`
- Confirmation: external adapters previously wrote directly to the destination
  and validation failures could be downgraded.
- Impact: an interrupted conversion could replace a valid destination with
  incomplete data.
- Resolution: conversion uses a private same-directory staging path, validates
  it, and atomically publishes only successful output. Failure cleanup and
  cross-device fallback behavior are explicit.
- Regression test: **Required and present.**
- Status: **Resolved.**

### AUD-003 — Same-file, symlink, and overwrite races

- Severity: **High**
- Files: `src/omnixform/paths.py`, `src/omnixform/cli.py`
- Confirmation: path-string comparison and an early existence check did not
  cover aliases or a destination created during conversion.
- Impact: input destruction or replacement of a concurrently created output.
- Resolution: existing paths use realpath/same-file checks; no-overwrite
  publication uses an atomic no-replace operation; symlink outputs are refused.
- Regression test: **Required and present.**
- Status: **Resolved.**

### AUD-004 — Failure exit status was inconsistent

- Severity: **High**
- Files: `src/omnixform/cli.py`
- Confirmation: JSON, quiet, and mixed batch failures previously returned zero.
- Impact: scripts and CI could accept failed conversions.
- Resolution: errors preserve non-zero status, JSON remains parseable, and any
  failed batch returns conversion-error status.
- Regression test: **Required and present.**
- Status: **Resolved.**

### AUD-005 — Plugin failure and discovery boundaries

- Severity: **Medium**
- Files: `src/omnixform/registry.py`, `src/omnixform/cli.py`,
  `pyproject.toml`
- Confirmation: discovery metadata and ordinary third-party exceptions needed
  end-to-end verification.
- Impact: a broken plugin could prevent registry construction or corrupt CLI
  automation.
- Resolution: the only active group is `omnixform.adapters`; entry points are
  loaded independently, ordinary failures are isolated, duplicate names follow
  deterministic priority rules, and installed-plugin conversion is tested.
- Regression test: **Required and present.**
- Status: **Resolved.**

### AUD-006 — CI and publication permissions

- Severity: **High**
- Files: `.github/workflows/ci.yml`,
  `.github/workflows/publish-pypi.yml`
- Confirmation: release automation previously mixed external mutations and
  long-lived credentials.
- Impact: excessive permissions and supply-chain exposure.
- Resolution: CI defaults to `contents: read`, actions are pinned to full
  revisions, and PyPI publishing is a separate manual workflow whose publish
  job receives only OIDC `id-token: write`.
- Regression test: workflow source review and hosted CI.
- Status: **Resolved in source; hosted execution remains open.**

### AUD-007 — Container build and privilege model

- Severity: **High**
- Files: `Dockerfile`, `.dockerignore`
- Confirmation: the former build order could not install the package.
- Impact: unusable published image and misleading documentation.
- Resolution: a wheel is built in a separate stage and installed into a runtime
  virtual environment; the runtime user is unprivileged.
- Regression test: **Required.**
- Status: **Resolved locally; registry publication remains blocked.**

### AUD-008 — Optional dependencies and damaged inputs

- Severity: **Medium**
- Files: adapters, detection, CLI error handling
- Confirmation: optional programs and codecs cannot be assumed present; native
  converters process complex untrusted data.
- Impact: platform-dependent failures and parser exposure.
- Resolution: availability is detected per conversion, missing dependencies and
  invalid inputs return explicit non-zero errors, and documentation states that
  external tools are not a sandbox.
- Regression test: detection/error paths plus integrations where available.
- Status: **Resolved with documented platform limitations.**

### AUD-009 — Pandoc masked the working office-to-PDF fallback

- Severity: **Medium**
- Files: `src/omnixform/adapters/pandoc.py`,
  `src/omnixform/registry.py`, `src/omnixform/cli.py`
- Confirmation: a real container conversion selected Pandoc for DOCX to PDF
  even though no PDF engine was installed, returned exit 8, and never tried the
  available LibreOffice adapter.
- Reproduction:
  `omnix convert container.docx --to pdf` in the locally built image returned
  `pdflatex not found` from Pandoc.
- Impact: a documented conversion failed despite a capable installed backend.
- Resolution: Pandoc now reports PDF conversion available only when a supported
  PDF engine is present; registry selection then falls back to LibreOffice for
  office-to-PDF, and pair-specific unavailability becomes a missing-dependency
  error instead of attempting a known-unavailable conversion.
- Regression test: **Required and present.**
- Status: **Resolved.**

### AUD-010 — Optional Cairo runtime and Windows argument portability

- Severity: **Medium**
- Files: `src/omnixform/adapters/vector.py`, `src/omnixform/cli.py`, tests,
  `.github/workflows/ci.yml`
- Confirmation: the first hosted run passed Linux 3.11–3.14 but failed on
  macOS and Windows. CairoSVG could be importable while its native Cairo
  library was absent, raising an uncaught `OSError`. Windows also expanded a
  wildcard into multiple positional paths before Typer parsed the command.
- Impact: read-only CLI commands could crash on platforms without native Cairo,
  and otherwise valid batch conversion could be rejected on Windows.
- Resolution: native Cairo load failures mark the adapter unavailable; convert
  and batch accept one or more input paths or patterns; path and newline tests
  are platform-neutral. Actions were advanced to current, full-SHA-pinned
  Node.js 24 releases after the hosted runner reported Node.js 20 deprecation.
- Regression test: **Required and present.**
- Status: **Resolved locally; hosted rerun pending.**

### AUD-018 — Temporary `pictures/` corpus

- Severity: **Medium**
- Files: former untracked test directory
- Confirmation: filesystem, source, documentation, test, package, and archive
  scans find no directory, files, or active references.
- Impact: unknown-provenance assets could otherwise enter source or release
  artifacts.
- Resolution: the owner removed the directory; tests create minimal fixtures
  inside `tmp_path` using Pillow, text, data, or owned SVG content.
- Regression test: source and artifact scans.
- Status: **Resolved.**

## Product claims

| Claim | Status | Evidence |
| --- | --- | --- |
| Pillow adapter | Confirmed | Unit tests and real generated-image conversion |
| FFmpeg adapter | Confirmed where installed | Detection, timeout tests, and host/container integration |
| Text/Markdown/HTML | Confirmed | Unit and CLI scenario tests |
| JSON/YAML/CSV/TSV | Confirmed with documented shape limits | Unit and CLI scenario tests |
| CairoSVG adapter | Confirmed where optional package is installed | Generated SVG integration |
| Pandoc adapter | Conditional | Detection/error tests; real integration only where binary is installed |
| LibreOffice adapter | Conditional | Detection/error tests; real integration only where binary is installed |
| Third-party plugins | Confirmed | Separate installed distribution and actual conversion |
| Batch, dry-run, JSON, quiet, overwrite, presets | Confirmed | CLI regression and scenario tests |
| Shell completions | Confirmed | Generated bash/zsh/fish scripts and CLI help |
| Dockerfile | Conditional | Local no-cache build and non-root smoke when Podman/Docker is available |
| PyPI package | Not published | Namespace and artifact checks only |
| MkDocs documentation | Confirmed locally | Strict build |
| Linux/macOS/Windows CI | Partially confirmed | Workflow review; hosted runs still required |

## Security regression checklist

- [x] No `shell=True` or shell command construction.
- [x] User paths are passed as individual arguments.
- [x] Timeout, terminate/kill, and reap are tested.
- [x] FFmpeg is non-interactive.
- [x] LibreOffice uses an isolated temporary profile.
- [x] Temporary paths are cleaned after failure and interruption.
- [x] Output is validated before atomic publication.
- [x] Same-file, symlink, and overwrite protections are tested.
- [x] CLI errors return non-zero status and JSON remains parseable.
- [x] Plugin discovery and failure isolation are tested.
- [x] GitHub Actions have minimal permissions and pinned revisions.
- [x] Container runtime is configured as non-root.
- [x] Source and artifact secret scans are part of release verification.

## Rename checklist

- [x] Distribution renamed
- [x] Import package renamed
- [x] CLI renamed
- [x] Plugin namespace renamed
- [x] Tests renamed
- [x] Documentation renamed
- [x] Workflows renamed
- [x] Containers renamed
- [x] No stale branding outside this historical note
- [x] Clean wheel install passed
- [x] Clean sdist install passed
- [x] Namespace checks documented
- [x] No package, container, tag, or release publication performed

## Remaining release conditions

1. Obtain green hosted CI on Linux, macOS, and Windows.
2. Complete human review of subprocess, path-publication, plugin, workflow, and
   container code.
3. Configure the PyPI trusted publisher and protected environment.
4. Repeat the exact PyPI namespace check immediately before publication.
5. Obtain separate owner permission for tag, GitHub Release, PyPI publication,
   and container publication.
6. Treat trademark clearance as a separate legal decision.
