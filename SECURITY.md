# Security Policy

## Supported versions

Omnixform has not had its first verified public release. Security fixes target
the current default branch until a supported-version table is published.

## Reporting a vulnerability

Use GitHub private vulnerability reporting from the repository's **Security**
tab. Do not open a public issue containing exploit details or sensitive sample
files.

The repository owner must enable private vulnerability reporting before public
launch. If that channel is not available, pause disclosure until the owner
publishes a private contact method; this project does not currently claim an
email address or domain.

Include the affected version/commit, platform, impact, minimal reproduction,
and whether untrusted files or plugins are involved. Do not include secrets or
personal data.

## Threat model

Omnixform treats paths as local-user input and avoids shell interpretation.
Third-party plugins are trusted code. FFmpeg, Pandoc, LibreOffice, CairoSVG,
and image codecs process complex inputs and are not sandboxed by Omnixform.
Use an OS sandbox, container, or disposable VM for hostile files and apply
security updates to all external tools.
