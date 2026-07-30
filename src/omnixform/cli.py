from __future__ import annotations

import glob
import json
import os
import sys
import time
from typing import Annotated, Any

import typer
from rich import box
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from omnixform import __version__
from omnixform.config import DEFAULT_TIMEOUT, PRESETS
from omnixform.detection import (
    detect_format,
    detect_format_from_magic,
    get_extension,
    guess_mime,
)
from omnixform.errors import (
    EXIT_BAD_ARGS,
    EXIT_CONVERSION_ERROR,
    EXIT_CORRUPT_INPUT,
    EXIT_FILE_NOT_FOUND,
    EXIT_MISSING_DEPENDENCY,
    EXIT_OUTPUT_EXISTS,
    EXIT_TIMEOUT,
    EXIT_UNSUPPORTED_FORMAT,
    EXIT_VALIDATION_ERROR,
    BadArgumentsError,
    ConversionError,
    CorruptInputError,
    MissingDependencyError,
    OmnixformError,
    OutputExistsError,
    UnsupportedFormatError,
)
from omnixform.formats import is_valid_format_name, normalize_format
from omnixform.paths import (
    make_staging_path,
    publish_staged_output,
    remove_staging_file,
    resolve_output_path,
)
from omnixform.registry import get_registry
from omnixform.subprocesses import check_dependency
from omnixform.validation import validate_output

app = typer.Typer(
    name="omnix",
    help=(
        "A local-first CLI for converting images, media, documents, text, "
        "and structured data through one extensible interface."
    ),
    no_args_is_help=True,
    invoke_without_command=True,
    pretty_exceptions_enable=False,
    add_completion=True,
)
console = Console(stderr=True)

_json_output = False
_quiet_output = False


def _error_exit(message: str, code: int, *, details: str | None = None) -> None:
    if _json_output:
        payload: dict[str, Any] = {
            "success": False,
            "error": {
                "code": code,
                "type": _error_type_name(code),
                "message": message,
            },
        }
        if details:
            payload["error"]["details"] = details
        print(json.dumps(payload))
    elif not _quiet_output:
        console.print(f"[bold red]Error:[/] {message}")
        if details and os.environ.get("OMNIXFORM_VERBOSE"):
            console.print(f"[dim]{details}[/]")
    raise typer.Exit(code)


def _error_type_name(code: int) -> str:
    return {
        EXIT_BAD_ARGS: "bad_arguments",
        EXIT_FILE_NOT_FOUND: "file_not_found",
        EXIT_UNSUPPORTED_FORMAT: "unsupported_format",
        EXIT_MISSING_DEPENDENCY: "missing_dependency",
        EXIT_OUTPUT_EXISTS: "output_exists",
        EXIT_CORRUPT_INPUT: "corrupt_input",
        EXIT_CONVERSION_ERROR: "conversion_error",
        EXIT_TIMEOUT: "timeout",
        EXIT_VALIDATION_ERROR: "validation_error",
    }.get(code, "unknown_error")


def _format_size(size: int) -> str:
    """Format file size in human-readable form."""
    s = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if s < 1024:
            return f"{s:.1f} {unit}" if unit != "B" else f"{size} B"
        s /= 1024
    return f"{s:.1f} TB"


def _convert_single(
    input_path: str,
    target_fmt: str,
    output: str | None,
    output_dir: str | None,
    overwrite: bool,
    keep_metadata: bool,
    options: dict[str, Any],
    dry_run: bool,
    quiet: bool,
) -> tuple[dict[str, Any], float]:
    """Convert a single file and return (result_dict, duration_ms)."""
    start_time = time.monotonic()
    staging_path: str | None = None

    try:
        source_fmt = detect_format(input_path)
        if not source_fmt:
            raise CorruptInputError(input_path, details=f"Could not detect format of: {input_path}")

        if source_fmt == target_fmt:
            raise BadArgumentsError(
                f"Source and target formats are the same ({source_fmt}). Nothing to convert."
            )

        out_path, exists = resolve_output_path(
            input_path,
            target_fmt,
            output=output,
            output_dir=output_dir,
            overwrite=overwrite,
        )

        if exists and not overwrite:
            raise OutputExistsError(out_path)

        registry = get_registry()
        adapter = registry.select_adapter(source_fmt, target_fmt)

        if adapter is None:
            raise UnsupportedFormatError(source_fmt, target_fmt)

        assert adapter is not None
        if not adapter.is_conversion_available(source_fmt, target_fmt):
            raise MissingDependencyError(
                adapter.name,
                install_hint=(
                    f"Adapter '{adapter.name}' cannot run {source_fmt} → {target_fmt} "
                    "in this environment. Run 'omnix doctor' for details."
                ),
            )

        if dry_run:
            plan = {
                "input": input_path,
                "output": out_path,
                "source_format": source_fmt,
                "target_format": target_fmt,
                "adapter": adapter.name,
            }
            return {
                "success": True,
                "dry_run": True,
                **plan,
                "duration_ms": 0,
            }, 0.0

        staging_path = make_staging_path(out_path, target_fmt)
        actual_output = adapter.convert(
            input_path,
            target_fmt,
            output_path=staging_path,
            options=options,
        )
        if os.path.normcase(os.path.abspath(actual_output)) != os.path.normcase(staging_path):
            raise ConversionError(
                "Adapter returned an unexpected output path",
                input_path=input_path,
                adapter=adapter.name,
                details=f"expected={staging_path} actual={actual_output}",
            )

        validate_output(staging_path, target_fmt)
        publish_staged_output(staging_path, out_path, overwrite=overwrite)
        staging_path = None
        duration_ms = (time.monotonic() - start_time) * 1000

        result = {
            "success": True,
            "input": os.path.abspath(input_path),
            "output": out_path,
            "source_format": source_fmt,
            "target_format": target_fmt,
            "adapter": adapter.name,
            "duration_ms": round(duration_ms, 1),
        }
        return result, duration_ms

    except OmnixformError as e:
        duration_ms = (time.monotonic() - start_time) * 1000
        return {
            "success": False,
            "input": os.path.abspath(input_path),
            "source_format": source_fmt if "source_fmt" in locals() else "unknown",
            "target_format": target_fmt,
            "adapter": adapter.name if "adapter" in locals() and adapter else "unknown",
            "duration_ms": round(duration_ms, 1),
            "error": {
                "code": e.exit_code,
                "type": _error_type_name(e.exit_code),
                "message": str(e),
            },
        }, duration_ms
    except FileNotFoundError as e:
        duration_ms = (time.monotonic() - start_time) * 1000
        return {
            "success": False,
            "input": os.path.abspath(input_path),
            "source_format": "unknown",
            "target_format": target_fmt,
            "adapter": "unknown",
            "duration_ms": round(duration_ms, 1),
            "error": {
                "code": EXIT_FILE_NOT_FOUND,
                "type": "file_not_found",
                "message": str(e),
            },
        }, duration_ms
    except Exception as e:
        duration_ms = (time.monotonic() - start_time) * 1000
        adapter_name = adapter.name if "adapter" in locals() and adapter else "unknown"
        error = ConversionError(
            "Adapter raised an unexpected error",
            input_path=input_path,
            adapter=adapter_name,
            details=str(e),
        )
        return {
            "success": False,
            "input": os.path.abspath(input_path),
            "source_format": source_fmt if "source_fmt" in locals() else "unknown",
            "target_format": target_fmt,
            "adapter": adapter_name,
            "duration_ms": round(duration_ms, 1),
            "error": {
                "code": error.exit_code,
                "type": _error_type_name(error.exit_code),
                "message": str(error),
            },
        }, duration_ms
    finally:
        remove_staging_file(staging_path)


@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", help="Detailed diagnostic output"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress human-readable output"),
    show_version: bool = typer.Option(
        False,
        "--version",
        is_eager=True,
        help="Show version information and exit",
    ),
) -> None:
    global _json_output, _quiet_output
    _json_output = json_output
    _quiet_output = quiet or json_output
    if verbose:
        os.environ["OMNIXFORM_VERBOSE"] = "1"
    ctx.meta["quiet"] = quiet or json_output
    if show_version:
        _print_version()
        raise typer.Exit()


def _print_version() -> None:
    if _json_output:
        print(json.dumps({"version": __version__, "name": "omnixform", "command": "omnix"}))
    else:
        typer.echo(f"Omnixform {__version__}")


@app.command()
def version(
    ctx: typer.Context,
) -> None:
    """Show version information."""
    _print_version()


@app.command(name="convert")
def convert(
    ctx: typer.Context,
    input_path: Annotated[list[str], typer.Argument(help="Input file path(s) or glob pattern(s)")],
    to: str = typer.Option(..., "--to", help="Target format"),
    output: str | None = typer.Option(None, "-o", "--output", help="Explicit output path (single file only)"),
    output_dir: str | None = typer.Option(None, "--output-dir", help="Output directory"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Allow overwriting existing files"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show plan without executing"),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress human-readable output"),
    verbose: bool = typer.Option(False, "--verbose", help="Detailed diagnostic output"),
    keep_metadata: bool = typer.Option(False, "--keep-metadata", help="Preserve metadata when applicable"),
    timeout: int | None = typer.Option(None, "--timeout", help="Timeout in seconds for external processes"),
    # Image options
    quality: int | None = typer.Option(None, "--quality", help="Output quality (1-100)"),
    width: int | None = typer.Option(None, "--width", help="Resize width"),
    height: int | None = typer.Option(None, "--height", help="Resize height"),
    keep_aspect: bool = typer.Option(True, "--keep-aspect/--no-keep-aspect", help="Keep aspect ratio"),
    background: str | None = typer.Option(None, "--background", help="Background color for alpha->RGB"),
    # Multimedia options
    audio_codec: str | None = typer.Option(None, "--audio-codec", help="Audio codec"),
    video_codec: str | None = typer.Option(None, "--video-codec", help="Video codec"),
    audio_bitrate: str | None = typer.Option(None, "--audio-bitrate", help="Audio bitrate (e.g., 192k)"),
    video_bitrate: str | None = typer.Option(None, "--video-bitrate", help="Video bitrate (e.g., 1M)"),
    fps: float | None = typer.Option(None, "--fps", help="Frame rate"),
    resolution: str | None = typer.Option(None, "--resolution", help="Resolution (e.g., 1280x720)"),
    audio_only: bool = typer.Option(False, "--audio-only", help="Remove video stream"),
    no_audio: bool = typer.Option(False, "--no-audio", help="Remove audio stream"),
    # Data options
    encoding: str | None = typer.Option(None, "--encoding", help="Character encoding"),
    delimiter: str | None = typer.Option(None, "--delimiter", help="CSV/TSV delimiter"),
    indent: int | None = typer.Option(None, "--indent", help="JSON/YAML indent"),
    # Preset options
    preset: str | None = typer.Option(
        None,
        "--preset",
        help="Apply a preset option bundle; use --list-presets to list names",
    ),
    list_presets: bool = typer.Option(False, "--list-presets", help="List all available presets"),
) -> None:
    global _quiet_output
    _quiet_output = _quiet_output or quiet

    target_fmt = normalize_format(to)
    if not is_valid_format_name(target_fmt):
        _error_exit(f"Invalid target format: {to}", EXIT_BAD_ARGS)

    # Prepare options first (so presets can merge into them)
    options: dict[str, Any] = {"keep_aspect": keep_aspect, "keep_metadata": keep_metadata}
    for key, val in [
        ("quality", quality),
        ("width", width),
        ("height", height),
        ("background", background),
        ("audio_codec", audio_codec),
        ("video_codec", video_codec),
        ("audio_bitrate", audio_bitrate),
        ("video_bitrate", video_bitrate),
        ("fps", fps),
        ("resolution", resolution),
        ("encoding", encoding),
        ("delimiter", delimiter),
        ("indent", indent),
    ]:
        if val is not None:
            options[key] = val
    if audio_only:
        options["audio_only"] = True
    if no_audio:
        options["no_audio"] = True
    options["timeout"] = timeout or DEFAULT_TIMEOUT

    # Handle --list-presets
    if list_presets:
        if _json_output:
            print(json.dumps({"presets": {name: p.get("description", "") for name, p in PRESETS.items()}}))
        else:
            console.print("[bold]Available Presets:[/]")
            for name, config in PRESETS.items():
                desc = config.get("description", "")
                console.print(f"  [cyan]{name}[/]: {desc}")
        return

    # Handle --preset
    if preset:
        if preset not in PRESETS:
            _error_exit(f"Unknown preset: {preset}. Run --list-presets to see available.", EXIT_BAD_ARGS)

        preset_config = PRESETS[preset]
        # Merge preset options with explicit CLI options (CLI options take precedence)
        for category in ("image", "video", "audio", "document", "data"):
            if category in preset_config:
                for key, val in preset_config[category].items():
                    if key != "format" and key not in options:
                        options[key] = val

    # Expand patterns ourselves on POSIX. On Windows, the process runtime may
    # expand wildcards before Typer sees them, so accepting multiple positional
    # paths keeps the same command portable.
    input_files: list[str] = []
    for candidate in input_path:
        has_glob = any(c in candidate for c in "*?[")
        matches = glob.glob(candidate) if has_glob else [candidate]
        input_files.extend(matches)

    if not input_files:
        _error_exit(f"No files match input: {', '.join(input_path)}", EXIT_FILE_NOT_FOUND)

    if len(input_files) > 1 and output:
        _error_exit("Cannot use --output with multiple input files", EXIT_BAD_ARGS)

    # Single file - use original logic
    if len(input_files) == 1:
        result, _ = _convert_single(
            input_files[0],
            target_fmt,
            output,
            output_dir,
            overwrite,
            keep_metadata,
            options,
            dry_run,
            quiet,
        )

        if _json_output:
            print(json.dumps(result))
        if not result["success"]:
            if not _json_output and not (ctx.meta.get("quiet") or quiet):
                console.print(f"[bold red]Error:[/] {result['error']['message']}")
            raise typer.Exit(result["error"]["code"])
        if _json_output:
            return
        if not result.get("dry_run") and not (ctx.meta.get("quiet") or quiet):
            if result["success"]:
                console.print(
                    f"[green]✓[/] Converted: "
                    f"{os.path.basename(result['input'])} → {os.path.basename(result['output'])}"
                )
                console.print(f"  Format:    {result['source_format']} → {result['target_format']}")
                console.print(f"  Adapter:   {result['adapter']}")
                console.print(f"  Duration:  {result['duration_ms']:.0f} ms")
        elif result.get("dry_run"):
            plan = {k: v for k, v in result.items() if k not in ("success", "duration_ms")}
            console.print("[bold]Dry run[/] — no conversion will be performed:")
            console.print(f"  Input:  {plan['input']}")
            console.print(f"  Output: {plan['output']}")
            console.print(f"  From:   {plan['source_format']}")
            console.print(f"  To:     {plan['target_format']}")
            console.print(f"  Adapter: {plan['adapter']}")
        return

    # Batch conversion with progress bar
    results: list[dict[str, Any]] = []
    total_files = len(input_files)
    success_count = 0
    total_duration = 0.0

    if _json_output:
        # JSON mode - no progress bar, just process and output all results
        for input_file in input_files:
            result, duration = _convert_single(
                input_file,
                target_fmt,
                None,
                output_dir,
                overwrite,
                keep_metadata,
                options,
                dry_run,
                quiet,
            )
            results.append(result)
            total_duration += duration
            if result["success"]:
                success_count += 1
        print(
            json.dumps(
                {
                    "batch": True,
                    "total": total_files,
                    "successful": success_count,
                    "failed": total_files - success_count,
                    "total_duration_ms": round(total_duration, 1),
                    "results": results,
                }
            )
        )
        if success_count != total_files:
            raise typer.Exit(EXIT_CONVERSION_ERROR)
        return

    # Human-readable mode with progress bar
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
        disable=quiet,
    )

    with progress:
        task = progress.add_task(f"Converting {total_files} file(s) to {target_fmt}", total=total_files)
        for input_file in input_files:
            result, duration = _convert_single(
                input_file,
                target_fmt,
                None,
                output_dir,
                overwrite,
                keep_metadata,
                options,
                dry_run,
                quiet,
            )
            results.append(result)
            total_duration += duration
            if result["success"]:
                success_count += 1
                if not dry_run and not quiet:
                    progress.console.print(
                        f"  [green]✓[/] {os.path.basename(input_file)} → "
                        f"{os.path.basename(result['output'])} "
                        f"({result['duration_ms']:.0f} ms)"
                    )
            else:
                if not quiet:
                    progress.console.print(
                        f"  [red]✗[/] {os.path.basename(input_file)}: {result['error']['message']}"
                    )
            progress.advance(task)

    # Summary
    if not quiet:
        console.print()
        console.print(
            f"[bold]Summary:[/] {success_count}/{total_files} succeeded, "
            f"{total_files - success_count} failed in {total_duration:.0f} ms"
        )
    if success_count != total_files:
        raise typer.Exit(EXIT_CONVERSION_ERROR)


@app.command()
def batch(
    ctx: typer.Context,
    pattern: Annotated[list[str], typer.Argument(help="Glob pattern(s) or input file path(s)")],
    to: str = typer.Option(..., "--to", help="Target format"),
    output_dir: str | None = typer.Option(None, "--output-dir", help="Output directory"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Allow overwriting existing files"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show plan without executing"),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress human-readable output"),
    verbose: bool = typer.Option(False, "--verbose", help="Detailed diagnostic output"),
    keep_metadata: bool = typer.Option(False, "--keep-metadata", help="Preserve metadata when applicable"),
    timeout: int | None = typer.Option(None, "--timeout", help="Timeout in seconds for external processes"),
    quality: int | None = typer.Option(None, "--quality", help="Output quality (1-100)"),
    width: int | None = typer.Option(None, "--width", help="Resize width"),
    height: int | None = typer.Option(None, "--height", help="Resize height"),
    keep_aspect: bool = typer.Option(True, "--keep-aspect/--no-keep-aspect", help="Keep aspect ratio"),
    background: str | None = typer.Option(None, "--background", help="Background color for alpha->RGB"),
    audio_codec: str | None = typer.Option(None, "--audio-codec", help="Audio codec"),
    video_codec: str | None = typer.Option(None, "--video-codec", help="Video codec"),
    audio_bitrate: str | None = typer.Option(None, "--audio-bitrate", help="Audio bitrate (e.g., 192k)"),
    video_bitrate: str | None = typer.Option(None, "--video-bitrate", help="Video bitrate (e.g., 1M)"),
    fps: float | None = typer.Option(None, "--fps", help="Frame rate"),
    resolution: str | None = typer.Option(None, "--resolution", help="Resolution (e.g., 1280x720)"),
    audio_only: bool = typer.Option(False, "--audio-only", help="Remove video stream"),
    no_audio: bool = typer.Option(False, "--no-audio", help="Remove audio stream"),
    encoding: str | None = typer.Option(None, "--encoding", help="Character encoding"),
    delimiter: str | None = typer.Option(None, "--delimiter", help="CSV/TSV delimiter"),
    indent: int | None = typer.Option(None, "--indent", help="JSON/YAML indent"),
    preset: str | None = typer.Option(None, "--preset", help="Apply a preset option bundle"),
) -> None:
    """Convert every file matching a glob pattern."""
    convert(
        ctx=ctx,
        input_path=pattern,
        to=to,
        output=None,
        output_dir=output_dir,
        overwrite=overwrite,
        dry_run=dry_run,
        quiet=quiet,
        verbose=verbose,
        keep_metadata=keep_metadata,
        timeout=timeout,
        quality=quality,
        width=width,
        height=height,
        keep_aspect=keep_aspect,
        background=background,
        audio_codec=audio_codec,
        video_codec=video_codec,
        audio_bitrate=audio_bitrate,
        video_bitrate=video_bitrate,
        fps=fps,
        resolution=resolution,
        audio_only=audio_only,
        no_audio=no_audio,
        encoding=encoding,
        delimiter=delimiter,
        indent=indent,
        preset=preset,
        list_presets=False,
    )


@app.command()
def formats(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """List available conversion formats."""
    registry = get_registry()
    infos = registry.get_adapter_infos()

    if json_output or _json_output:
        print(
            json.dumps(
                {
                    "adapters": [
                        {
                            "name": info.name,
                            "category": info.category.value,
                            "description": info.description,
                            "input_extensions": info.input_extensions,
                            "output_extensions": info.output_extensions,
                            "available": info.available,
                            "priority": info.priority,
                            "unavailability_reason": info.unavailability_reason,
                        }
                        for info in infos
                    ]
                }
            )
        )
        return

    table = Table(title="Available Adapters", box=box.ROUNDED)
    table.add_column("Adapter", style="cyan")
    table.add_column("Category", style="magenta")
    table.add_column("Input Formats", style="green")
    table.add_column("Output Formats", style="yellow")
    table.add_column("Status", style="bold")

    for info in infos:
        status = "[green]✓ Available[/]" if info.available else f"[red]✗ {info.unavailability_reason}[/]"
        table.add_row(
            info.name,
            info.category.value,
            ", ".join(info.input_extensions),
            ", ".join(info.output_extensions),
            status,
        )

    console.print(table)


@app.command()
def inspect(
    ctx: typer.Context,
    input_path: str = typer.Argument(..., help="Path to file to inspect"),
) -> None:
    """Inspect a file and show conversion options."""
    if not os.path.isfile(input_path):
        _error_exit(f"File not found: {input_path}", EXIT_FILE_NOT_FOUND)

    file_size = os.path.getsize(input_path)
    ext = get_extension(input_path)
    mime = guess_mime(input_path)
    detected_format = detect_format(input_path)
    content_format = detect_format_from_magic(input_path)
    registry = get_registry()

    warnings_list: list[str] = []
    is_expected_zip_container = content_format == "zip" and ext in {
        "docx",
        "odt",
        "pptx",
        "odp",
        "xlsx",
        "ods",
        "epub",
    }
    if ext and content_format and ext != content_format and not is_expected_zip_container:
        warnings_list.append(f"Extension ({ext}) differs from detected content ({content_format})")

    possible_targets = registry.get_possible_targets(detected_format) if detected_format else []

    available_targets = [t["format"] for t in possible_targets if t["available"]]
    adapter_name = ""
    if available_targets:
        first_target = available_targets[0]
        adapter = registry.select_adapter(detected_format or ext, first_target)
        if adapter:
            adapter_name = adapter.name

    if _json_output:
        data = {
            "path": os.path.abspath(input_path),
            "size": file_size,
            "extension": ext,
            "mime_type": mime,
            "detected_format": detected_format,
            "content_format": content_format,
            "warnings": warnings_list,
            "targets": [
                {
                    "format": t["format"],
                    "adapter": t["adapter"],
                    "available": t["available"],
                }
                for t in possible_targets
            ],
        }
        if adapter_name:
            data["recommended_adapter"] = adapter_name
        print(json.dumps(data))
    else:
        console.print(f"[bold]File:[/] {input_path}")
        console.print(f"  Size:        {_format_size(file_size)}")
        console.print(f"  Extension:   {ext or '(none)'}")
        console.print(f"  MIME type:   {mime}")
        console.print(f"  Content:     {content_format or 'unknown'}")
        if warnings_list:
            for w in warnings_list:
                console.print(f"  [yellow]⚠ Warning:[/] {w}")
        if adapter_name:
            console.print(f"  Adapter:     {adapter_name}")
        if available_targets:
            console.print(f"  Targets:     {', '.join(available_targets)}")
        else:
            console.print("  Targets:     (none available)")


@app.command()
def doctor(
    ctx: typer.Context,
) -> None:
    import importlib
    import tempfile

    results: list[dict[str, Any]] = []

    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 11)
    critical_failure = not py_ok
    results.append(
        {
            "check": "Python version",
            "status": "pass" if py_ok else "fail",
            "value": py_ver,
            "message": "" if py_ok else "Python 3.11+ required",
        }
    )

    for name, module_name in [
        ("Pillow", "PIL"),
        ("PyYAML", "yaml"),
        ("Markdown", "markdown"),
        ("Typer", "typer"),
        ("Rich", "rich"),
    ]:
        try:
            mod = importlib.import_module(module_name)
            results.append(
                {
                    "check": f"Python: {name}",
                    "status": "pass",
                    "value": str(getattr(mod, "__version__", "installed")),
                    "message": "",
                }
            )
        except ImportError:
            results.append(
                {
                    "check": f"Python: {name}",
                    "status": "fail",
                    "value": "missing",
                    "message": f"pip install {name.lower()}",
                }
            )

    for cmd, desc in [
        ("ffmpeg", "FFmpeg for audio/video conversion"),
        ("ffprobe", "FFprobe for media file verification"),
        ("pandoc", "Pandoc for document conversion"),
        ("soffice", "LibreOffice for office document conversion"),
    ]:
        path = check_dependency(cmd)
        if path:
            results.append(
                {
                    "check": f"External: {cmd}",
                    "status": "pass",
                    "value": path,
                    "message": "",
                }
            )
        else:
            results.append(
                {
                    "check": f"External: {cmd}",
                    "status": "warn",
                    "value": "not found",
                    "message": f"{desc} — install for extended functionality",
                }
            )

    for name, module_name, purpose in [
        ("AVIF", "pillow_avif", "AVIF image conversion"),
        ("HEIC/HEIF", "pillow_heif", "HEIC/HEIF image conversion"),
        ("JPEG XL", "pillow_jxl", "JPEG XL image conversion"),
        ("CairoSVG", "cairosvg", "SVG rendering"),
    ]:
        try:
            importlib.import_module(module_name)
            status = "pass"
            value = "installed"
            message = ""
        except (ImportError, OSError):
            status = "warn"
            value = "not found"
            message = f"{purpose} — install omnixform[all-formats]"
        results.append(
            {
                "check": f"Optional: {name}",
                "status": status,
                "value": value,
                "message": message,
            }
        )

    try:
        tmp = tempfile.mkdtemp()
        test_file = os.path.join(tmp, ".omnixform_test")
        with open(test_file, "w") as f:
            f.write("test")
        os.remove(test_file)
        os.rmdir(tmp)
        results.append(
            {
                "check": "Temp directory",
                "status": "pass",
                "value": tempfile.gettempdir(),
                "message": "",
            }
        )
    except OSError as e:
        critical_failure = True
        results.append(
            {
                "check": "Temp directory",
                "status": "fail",
                "value": str(e),
                "message": "Cannot write to temp directory",
            }
        )

    if _json_output:
        print(json.dumps({"healthy": not critical_failure, "checks": results}))
        if critical_failure:
            raise typer.Exit(1)
    else:
        for r in results:
            if r["status"] == "pass":
                console.print(f"  [green]✓[/] {r['check']}: {r['value']}")
            elif r["status"] == "warn":
                console.print(f"  [yellow]⚠[/] {r['check']}: [yellow]{r['value']}[/]")
                if r["message"]:
                    console.print(f"       {r['message']}")
            else:
                console.print(f"  [red]✗[/] {r['check']}: {r['value']}")
                if r["message"]:
                    console.print(f"       {r['message']}")

        if critical_failure:
            console.print("\n[bold red]✗ Critical issues found[/]")
            raise typer.Exit(1)
        else:
            console.print("\n[bold green]✓ All core checks passed[/]")


@app.command()
def completion(
    ctx: typer.Context,
    shell: str = typer.Argument(..., help="Shell to generate completion for (bash, zsh, fish, powershell)"),
) -> None:
    """Generate shell completion script."""
    if shell not in ("bash", "zsh", "fish", "powershell"):
        _error_exit(f"Unsupported shell: {shell}. Use: bash, zsh, fish, powershell", EXIT_BAD_ARGS)

    from typer._completion_shared import get_completion_script

    print(
        get_completion_script(
            prog_name="omnix",
            complete_var="_OMNIXFORM_COMPLETE",
            shell=shell,
        )
    )


if __name__ == "__main__":
    app()
