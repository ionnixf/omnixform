# `omnix convert`

```text
omnix [GLOBAL OPTIONS] convert INPUT --to FORMAT [OPTIONS]
```

`--to` is always required, including when a preset is used.

## Output and execution

| Option | Behavior |
| --- | --- |
| `-o`, `--output PATH` | explicit destination for one input |
| `--output-dir DIR` | destination directory |
| `--overwrite` | allow atomic replacement |
| `--dry-run` | show the plan without creating directories or files |
| `--timeout SECONDS` | external process timeout |
| `--quiet` | suppress normal human output, not exit failures |

Global `--json`, `--quiet`, and `--verbose` precede the command. `convert` also
accepts local quiet/verbose flags.

## Image options

`--quality`, `--width`, `--height`, `--keep-aspect`,
`--no-keep-aspect`, `--background`, and `--keep-metadata`.
Metadata preservation is best-effort for EXIF and ICC profiles; transformations
and target formats may discard metadata.

## Multimedia options

`--audio-codec`, `--video-codec`, `--audio-bitrate`, `--video-bitrate`,
`--fps`, `--resolution`, `--audio-only`, and `--no-audio`.
Accepted codec/container combinations depend on the local FFmpeg build.

## Data options

`--encoding`, `--delimiter`, and `--indent`.

## Presets

`--preset NAME` applies an option bundle but does not choose the destination
format. List bundles with:

```bash
omnix convert placeholder --to png --list-presets
```

Some codec presets require encoders or containers that the local FFmpeg build
may not provide. A preset is not a platform guarantee.

## Exit codes

| Code | Meaning |
| ---: | --- |
| 0 | success |
| 2 | bad arguments |
| 3 | missing input |
| 4 | unsupported format pair |
| 5 | missing dependency |
| 6 | output exists |
| 7 | corrupt/invalid input |
| 8 | conversion or partial batch failure |
| 9 | timeout |
| 10 | invalid output |
