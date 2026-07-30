from __future__ import annotations

import os
from typing import Any

from omnixform.adapters.base import BaseAdapter
from omnixform.errors import (
    ConversionError,
    MissingDependencyError,
    OmnixformError,
    UnsupportedFormatError,
    ValidationError,
)
from omnixform.models import Category
from omnixform.paths import make_staging_path, publish_staged_output, remove_staging_file, replace_extension
from omnixform.subprocesses import check_dependency, run_subprocess_sync


class MultimediaAdapter(BaseAdapter):
    name = "ffmpeg"
    category = Category.AUDIO_VIDEO
    description = "Audio and video conversion using FFmpeg"
    input_extensions = ["mp3", "wav", "flac", "aac", "m4a", "mp4", "webm", "mov", "mkv"]
    output_extensions = ["mp3", "wav", "flac", "aac", "m4a", "mp4", "webm", "mov", "mkv"]
    priority = 10
    options = {
        "audio_codec": {"type": "str", "default": None},
        "video_codec": {"type": "str", "default": None},
        "audio_bitrate": {"type": "str", "default": None},
        "video_bitrate": {"type": "str", "default": None},
        "fps": {"type": "float", "default": None},
        "resolution": {"type": "str", "default": None},
        "crf": {"type": "int", "default": None},
        "preset": {"type": "str", "default": None},
        "max_duration": {"type": "float", "default": None},
        "audio_only": {"type": "bool", "default": False},
        "no_audio": {"type": "bool", "default": False},
    }

    _audio_extensions = {"mp3", "wav", "flac", "aac", "m4a"}
    _video_extensions = {"mp4", "webm", "mov", "mkv"}

    _default_codecs = {
        "mp3": (None, "libmp3lame"),
        "m4a": (None, "aac"),
        "mp4": ("libx264", "aac"),
        "webm": ("libvpx", "libopus"),
        "wav": (None, "pcm_s16le"),
        "flac": (None, "flac"),
    }

    def __init__(self) -> None:
        self._ffmpeg_path: str | None = None
        self._ffprobe_path: str | None = None

    def is_available(self) -> bool:
        self._ffmpeg_path = check_dependency("ffmpeg")
        self._ffprobe_path = check_dependency("ffprobe")
        return self._ffmpeg_path is not None

    def _ensure_ffmpeg(self) -> str:
        if self._ffmpeg_path is None:
            self._ffmpeg_path = check_dependency("ffmpeg")
        if self._ffmpeg_path is None:
            raise MissingDependencyError(
                "ffmpeg",
                install_hint=(
                    "Install FFmpeg:\n"
                    "  Linux: sudo apt install ffmpeg\n"
                    "  macOS: brew install ffmpeg\n"
                    "  Windows: choco install ffmpeg"
                ),
            )
        return self._ffmpeg_path

    def convert(
        self,
        input_path: str,
        target_format: str,
        *,
        output_path: str = "",
        options: dict[str, Any] | None = None,
    ) -> str:
        opts = options or {}
        ffmpeg = self._ensure_ffmpeg()
        target_format = target_format.lstrip(".").lower()

        if target_format not in self.output_extensions:
            raise UnsupportedFormatError(os.path.splitext(input_path)[1], target_format)

        if not output_path:
            output_path = replace_extension(input_path, target_format)

        source_ext = os.path.splitext(input_path)[1].lstrip(".").lower()
        source_is_video = source_ext in self._video_extensions
        target_is_audio = target_format in self._audio_extensions
        target_is_video = target_format in self._video_extensions

        staging_path = make_staging_path(output_path, target_format)
        args = [
            ffmpeg,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            os.path.abspath(input_path),
        ]

        audio_only = opts.get("audio_only", False) or (target_is_audio and source_is_video)
        no_audio = opts.get("no_audio", False)

        if audio_only:
            args.extend(["-vn"])
        elif no_audio:
            args.extend(["-an"])

        if opts.get("audio_bitrate"):
            args.extend(["-b:a", str(opts["audio_bitrate"])])
        if opts.get("video_bitrate"):
            args.extend(["-b:v", str(opts["video_bitrate"])])
        if opts.get("resolution"):
            args.extend(["-s", opts["resolution"]])
        if opts.get("fps"):
            args.extend(["-r", str(opts["fps"])])
        if opts.get("max_duration"):
            args.extend(["-t", str(opts["max_duration"])])

        default_vcodec, default_acodec = self._default_codecs.get(target_format, (None, None))
        if default_vcodec and not opts.get("video_codec") and target_is_video:
            args.extend(["-c:v", default_vcodec])
        if default_acodec and not opts.get("audio_codec") and not no_audio:
            args.extend(["-c:a", default_acodec])

        if opts.get("video_codec"):
            args.extend(["-c:v", opts["video_codec"]])
        if opts.get("audio_codec") and not no_audio:
            args.extend(["-c:a", opts["audio_codec"]])
        if opts.get("crf") is not None and target_is_video:
            args.extend(["-crf", str(opts["crf"])])
        if opts.get("preset") and target_is_video:
            args.extend(["-preset", str(opts["preset"])])

        args.append(staging_path)

        try:
            result = run_subprocess_sync(args, timeout=float(opts.get("timeout", 300)))
        except OmnixformError:
            remove_staging_file(staging_path)
            raise
        except Exception as e:
            remove_staging_file(staging_path)
            raise ConversionError(
                "FFmpeg conversion failed",
                input_path=input_path,
                adapter=self.name,
                details=str(e),
            ) from e

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")[:2000]
            remove_staging_file(staging_path)
            raise ConversionError(
                f"FFmpeg exited with code {result.returncode}",
                input_path=input_path,
                adapter=self.name,
                details=stderr,
            )

        try:
            if self._ffprobe_path:
                self._verify_output(staging_path)
            publish_staged_output(staging_path, output_path, overwrite=True)
            return output_path
        finally:
            remove_staging_file(staging_path)

    def _verify_output(self, path: str) -> None:
        if self._ffprobe_path is None:
            return
        result = run_subprocess_sync(
            [
                self._ffprobe_path,
                "-v",
                "error",
                "-show_entries",
                "format=format_name",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                os.path.abspath(path),
            ],
            timeout=30,
        )
        if result.returncode != 0 or not result.stdout.strip():
            raise ValidationError(path, "FFmpeg output could not be verified by ffprobe")
