# Quick start

After installing from source:

```bash
# Core image conversion
omnix convert photo.png --to webp

# Built-in text conversion
omnix convert notes.md --to html

# Structured data
omnix convert records.csv --to json

# External FFmpeg adapter
omnix convert clip.mp4 --to mp3 --audio-only
```

Preview without writes:

```bash
omnix convert photo.png --to webp --dry-run
```

Batch convert a quoted glob:

```bash
omnix batch "photos/*.png" --to webp --output-dir converted
```

For scripts, place the global JSON flag before the command:

```bash
omnix --json convert photo.png --to webp
```

Stdout contains one JSON document. A failed single conversion uses its
specific exit code; a batch with any failure exits with code 8.

Omnixform refuses an existing destination unless `--overwrite` is explicit:

```bash
omnix convert photo.png --to webp --overwrite
```
