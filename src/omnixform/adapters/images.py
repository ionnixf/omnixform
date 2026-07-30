from __future__ import annotations

import io
import os
from typing import Any

from PIL import Image, UnidentifiedImageError

from omnixform.adapters.base import BaseAdapter
from omnixform.errors import (
    ConversionError,
    CorruptInputError,
    MissingDependencyError,
    UnsupportedFormatError,
)
from omnixform.formats import normalize_format
from omnixform.models import Category
from omnixform.paths import atomic_write, replace_extension


class ImageAdapter(BaseAdapter):
    name = "pillow"
    category = Category.IMAGE
    description = "Raster image conversion using Pillow"
    input_extensions = [
        "png",
        "jpg",
        "jpeg",
        "webp",
        "bmp",
        "tiff",
        "tif",
        "avif",
        "heic",
        "heif",
        "jxl",
    ]
    output_extensions = [
        "png",
        "jpg",
        "jpeg",
        "webp",
        "bmp",
        "tiff",
        "tif",
        "avif",
        "heic",
        "jxl",
    ]
    priority = 10
    options = {
        "quality": {"type": "int", "default": 90, "min": 1, "max": 100},
        "width": {"type": "int", "default": None},
        "height": {"type": "int", "default": None},
        "keep_aspect": {"type": "bool", "default": True},
        "background": {"type": "str", "default": "white"},
        "remove_metadata": {"type": "bool", "default": False},
    }

    def is_available(self) -> bool:
        try:
            import PIL  # noqa: F401

            return True
        except ImportError:
            return False

    def _check_avif_support(self) -> bool:
        try:
            import pillow_avif  # noqa: F401

            return True
        except ImportError:
            return False

    def _check_heic_support(self) -> bool:
        try:
            import pillow_heif  # noqa: F401

            return True
        except ImportError:
            return False

    def _check_jxl_support(self) -> bool:
        try:
            import pillow_jxl  # noqa: F401

            return True
        except ImportError:
            return False

    def is_conversion_available(self, source_ext: str, target_ext: str) -> bool:
        source = source_ext.lstrip(".").lower()
        target = target_ext.lstrip(".").lower()
        if not super().is_conversion_available(source, target):
            return False
        if "avif" in (source, target):
            return self._check_avif_support()
        if source in ("heic", "heif") or target in ("heic", "heif"):
            return self._check_heic_support()
        if "jxl" in (source, target):
            return self._check_jxl_support()
        return True

    def convert(
        self,
        input_path: str,
        target_format: str,
        *,
        output_path: str = "",
        options: dict[str, Any] | None = None,
    ) -> str:
        opts = options or {}
        target_format = normalize_format(target_format)

        if target_format not in self.output_extensions:
            raise UnsupportedFormatError(os.path.splitext(input_path)[1], target_format)

        # Check format-specific dependencies
        source_ext = os.path.splitext(input_path)[1].lstrip(".").lower()

        if (source_ext == "avif" or target_format == "avif") and not self._check_avif_support():
            raise MissingDependencyError(
                "pillow-avif-plugin",
                install_hint=(
                    "Install AVIF support:\n"
                    "  pip install pillow-avif-plugin\n"
                    "  or: pip install omnixform[all-formats]"
                ),
            )
        if (
            source_ext in ("heic", "heif") or target_format in ("heic", "heif")
        ) and not self._check_heic_support():
            raise MissingDependencyError(
                "pillow-heif",
                install_hint=(
                    "Install HEIC/HEIF support:\n"
                    "  pip install pillow-heif\n"
                    "  or: pip install omnixform[all-formats]"
                ),
            )
        if (source_ext == "jxl" or target_format == "jxl") and not self._check_jxl_support():
            raise MissingDependencyError(
                "pillow-jxl-plugin",
                install_hint=(
                    "Install JPEG XL support:\n"
                    "  pip install pillow-jxl-plugin\n"
                    "  or: pip install omnixform[all-formats]"
                ),
            )

        if not output_path:
            output_path = replace_extension(input_path, target_format)

        try:
            # Register HEIF reading and writing when needed.
            if source_ext in ("heic", "heif") or target_format == "heic":
                try:
                    import pillow_heif

                    pillow_heif.register_heif_opener()
                except ImportError:
                    pass

            with Image.open(input_path) as img:
                needs_rgb = target_format in ("jpeg", "bmp")
                has_alpha = img.mode in ("RGBA", "LA", "P")

                if has_alpha and needs_rgb:
                    bg_color = opts.get("background", "white")
                    bg = Image.new("RGB", img.size, bg_color)
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    bg.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                    img = bg
                elif img.mode == "P":
                    img = img.convert("RGBA" if target_format in ("png", "webp", "tiff") else "RGB")

                if img.mode == "CMYK" and target_format != "tiff":
                    img = img.convert("RGB")

                width = opts.get("width")
                height = opts.get("height")
                if width is not None or height is not None:
                    if opts.get("keep_aspect", True):
                        img.thumbnail((width or img.width, height or img.height), Image.LANCZOS)
                    else:
                        img = img.resize(
                            (width or img.width, height or img.height),
                            Image.LANCZOS,
                        )

                buf = io.BytesIO()
                save_kwargs: dict[str, Any] = {}

                if target_format in ("jpeg",):
                    save_kwargs["quality"] = opts.get("quality", 90)
                    save_kwargs["optimize"] = True
                elif target_format == "webp":
                    save_kwargs["quality"] = opts.get("quality", 90)
                    save_kwargs["method"] = 6
                elif target_format == "png":
                    save_kwargs["compress_level"] = 6
                    save_kwargs["optimize"] = True
                elif target_format in ("tiff",):
                    save_kwargs["compression"] = "tiff_lzw"
                elif target_format == "avif" or target_format == "heic" or target_format == "jxl":
                    save_kwargs["quality"] = opts.get("quality", 90)

                if opts.get("dpi"):
                    dpi = int(opts["dpi"])
                    save_kwargs["dpi"] = (dpi, dpi)
                if opts.get("keep_metadata"):
                    for metadata_key in ("exif", "icc_profile"):
                        if metadata_key in img.info:
                            save_kwargs[metadata_key] = img.info[metadata_key]

                pillow_format = "HEIF" if target_format == "heic" else target_format.upper()
                img.save(buf, format=pillow_format, **save_kwargs)
                atomic_write(output_path, content=buf.getvalue())
            return output_path

        except UnidentifiedImageError as e:
            raise CorruptInputError(input_path, details=str(e)) from e
        except Exception as e:
            raise ConversionError(
                "Image conversion failed",
                input_path=input_path,
                adapter=self.name,
                details=str(e),
            ) from e
