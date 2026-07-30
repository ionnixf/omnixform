# Security

Omnixform avoids shell interpretation, applies timeouts to external tools, and
stages CLI output before atomic publication. These controls do not make complex
file parsers safe for hostile input.

FFmpeg, Pandoc, LibreOffice, CairoSVG, optional image codecs, and plugins run
with the user's permissions. Use a disposable container/VM or OS sandbox for
untrusted files. Keep every parser and system tool updated.

Report vulnerabilities through GitHub private vulnerability reporting after
the repository owner enables it. Do not publish exploit details or sensitive
samples in a public issue.
