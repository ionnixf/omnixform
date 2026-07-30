# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project intends to follow Semantic Versioning after its first public
release.

## [0.1.0] - Unreleased

### Added

- Unified CLI for image, media, document, text, and structured-data conversion.
- Single-file and batch conversion, dry-run, JSON output, quiet mode, presets,
  overwrite protection, file inspection, dependency diagnostics, and shell
  completions.
- Built-in adapters and plugin discovery through `omnixform.adapters`.
- Security-hardened subprocess execution, staged output validation, and atomic
  publication.
- Cross-platform CI configuration, packaging checks, container build, project
  policies, and release documentation.

### Security

- External commands use argument vectors without a shell and are terminated
  and reaped after timeout or cancellation.
- FFmpeg runs non-interactively and LibreOffice uses an isolated profile.
- Conversion results are validated before publication and temporary output is
  removed after failures.
- GitHub Actions use minimal permissions and immutable action revisions.

[0.1.0]: https://github.com/ionnixf/omnixform/releases/tag/v0.1.0
