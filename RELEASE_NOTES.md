# Omnixform 0.1.0 release notes

Status: **Unreleased**

Omnixform 0.1.0 is the planned first public release. It provides one
local-first CLI for built-in image, text, and structured-data conversions and
for optional FFmpeg, CairoSVG, Pandoc, and LibreOffice workflows.

## Highlights

- Single and batch conversion with dry-run and overwrite protection.
- Parseable JSON output and reliable non-zero failure exit codes.
- Presets, shell completions, inspection, and dependency diagnostics.
- Third-party adapter discovery through `omnixform.adapters`.
- Timeout and process cleanup for external converters.
- Validated staging output followed by atomic publication.

## Compatibility

There is no earlier public release and no compatibility package or deprecated
CLI alias. The initial public contracts are:

- distribution and import: `omnixform`;
- executable: `omnix`;
- plugin entry-point group: `omnixform.adapters`;
- environment variable prefix: `OMNIXFORM_`.

## Known limitations

- PyPI and the container image have not been published.
- Cross-platform hosted CI passed for the audited source commit; it must run
  again for the eventual tagged release commit.
- The required protected GitHub environment and PyPI trusted-publisher binding
  are not configured yet.
- External converters and plugins are not sandboxed.
- Format and codec availability varies by platform and installed tools.
- Pandoc PDF output may need an additional PDF engine.
- Built-in markup and structured-data conversions can be lossy.
- The container base image is digest-pinned, but Debian packages installed
  during the build are not version-locked or bit-for-bit reproducible.
- Portable process-group termination on Windows remains dependent on converter
  behavior; hostile inputs should be handled in an OS sandbox or disposable
  container/VM.
- Trademark clearance was not performed.
