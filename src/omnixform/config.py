"""Configuration constants for Omnixform."""

from __future__ import annotations

from typing import Any, Final

# Format groups
RASTER_IMAGE_FORMATS: Final[set[str]] = {"png", "jpg", "jpeg", "webp", "bmp", "tiff", "tif"}
AUDIO_FORMATS: Final[set[str]] = {"mp3", "wav", "flac", "aac", "m4a"}
VIDEO_FORMATS: Final[set[str]] = {"mp4", "webm", "mov", "mkv"}
TEXT_FORMATS: Final[set[str]] = {"txt", "md", "html", "htm"}
PANDOC_FORMATS: Final[set[str]] = {"docx", "odt", "epub", "pdf", "rst", "latex", "tex"}
STRUCTURED_FORMATS: Final[set[str]] = {"json", "yaml", "yml", "csv", "tsv"}
OFFICE_FORMATS: Final[set[str]] = {"docx", "odt", "pptx", "odp", "xlsx", "ods", "pdf"}

# Default options
DEFAULT_QUALITY: Final[int] = 90
DEFAULT_INDENT: Final[int] = 2
DEFAULT_ENCODING: Final[str] = "utf-8"
DEFAULT_TIMEOUT: Final[int] = 300
DEFAULT_CSV_DELIMITER: Final[str] = ","
DEFAULT_TSV_DELIMITER: Final[str] = "\t"

# Presets - predefined option combinations for common use cases
# Each preset has a "description" string and category-specific option dicts
PresetValue = dict[str, Any]  # Can be str (description) or dict[str, Any] (options)

PRESETS: Final[dict[str, PresetValue]] = {
    # Web optimization presets
    "web": {
        "description": "Optimize for web delivery (small files, fast loading)",
        "image": {"quality": 85},
        "video": {"video_codec": "libx264", "audio_codec": "aac", "crf": 23, "preset": "medium"},
        "audio": {"audio_codec": "aac", "audio_bitrate": "128k"},
    },
    "web-max": {
        "description": "Maximum web compression (smallest files)",
        "image": {"quality": 70},
        "video": {"video_codec": "libx265", "audio_codec": "opus", "crf": 28, "preset": "slow"},
        "audio": {"audio_codec": "opus", "audio_bitrate": "96k"},
    },
    # Print presets
    "print": {
        "description": "High quality for print (300 DPI, lossless)",
        "image": {"quality": 100, "dpi": 300},
        "video": {"video_codec": "prores", "video_bitrate": "100M"},
    },
    # Archive presets
    "archive": {
        "description": "Long-term archival (lossless, open formats)",
        "image": {"quality": 100},
        "audio": {"audio_codec": "flac", "audio_bitrate": "0"},
        "video": {"video_codec": "ffv1", "video_bitrate": "0"},
    },
    # Social media presets
    "instagram": {
        "description": "Instagram-ready (1080x1080, max 30s video)",
        "image": {
            "quality": 90,
            "width": 1080,
            "height": 1080,
        },
        "video": {
            "video_codec": "libx264",
            "audio_codec": "aac",
            "resolution": "1080x1080",
            "fps": 30,
            "max_duration": 30,
        },
    },
    "tiktok": {
        "description": "TikTok/Reels/Shorts (9:16 vertical, max 60s)",
        "image": {
            "quality": 90,
            "width": 1080,
            "height": 1920,
        },
        "video": {
            "video_codec": "libx264",
            "audio_codec": "aac",
            "resolution": "1080x1920",
            "fps": 30,
            "max_duration": 60,
        },
    },
    "twitter": {
        "description": "Twitter/X optimized",
        "image": {
            "quality": 85,
            "width": 1200,
            "height": 675,
        },
        "video": {
            "video_codec": "libx264",
            "audio_codec": "aac",
            "resolution": "1280x720",
            "max_duration": 140,
        },
    },
    # Platform-specific
    "ios": {
        "description": "iOS/macOS optimized (HEIC/HEVC)",
        "image": {"quality": 90},
        "video": {"video_codec": "hevc", "audio_codec": "aac"},
    },
    "android": {
        "description": "Android optimized (WebP/VP9)",
        "image": {"quality": 85},
        "video": {"video_codec": "libvpx-vp9", "audio_codec": "opus"},
    },
    # Performance presets
    "fast": {
        "description": "Fastest conversion (speed over quality)",
        "image": {"quality": 80},
        "video": {"video_codec": "libx264", "preset": "ultrafast", "crf": 28},
        "audio": {"audio_codec": "aac", "audio_bitrate": "128k"},
    },
    "small": {
        "description": "Smallest output files",
        "image": {"quality": 60},
        "video": {"video_codec": "libx265", "preset": "slow", "crf": 30},
        "audio": {"audio_codec": "opus", "audio_bitrate": "64k"},
    },
}

# Known file signatures (magic bytes)
MAGIC_SIGNATURES: Final[dict[str, bytes]] = {
    "png": b"\x89PNG\r\n\x1a\n",
    "jpeg": b"\xff\xd8\xff",
    "jpg": b"\xff\xd8\xff",
    "webp": b"RIFF",
    "bmp": b"BM",
    "tiff_le": b"II*\x00",
    "tiff_be": b"MM\x00*",
    "gif": b"GIF8",
    "pdf": b"%PDF",
    "zip": b"PK\x03\x04",
    "flac": b"fLaC",
    "ogg": b"OggS",
}
