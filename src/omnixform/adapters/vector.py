from __future__ import annotations

import os
from typing import Any

from omnixform.adapters.base import BaseAdapter
from omnixform.errors import (
    ConversionError,
    MissingDependencyError,
    UnsupportedFormatError,
)
from omnixform.formats import normalize_format
from omnixform.models import Category
from omnixform.paths import atomic_write, replace_extension


class VectorAdapter(BaseAdapter):
    name = "cairosvg"
    category = Category.IMAGE
    description = "Vector image conversion via CairoSVG (SVG → PNG, PDF, EPS)"
    input_extensions = ["svg", "svgz"]
    output_extensions = ["png", "pdf", "eps", "ps", "svg"]
    priority = 20
    options = {
        "dpi": {"type": "int", "default": 96, "min": 10, "max": 600},
        "width": {"type": "int", "default": None},
        "height": {"type": "int", "default": None},
        "scale": {"type": "float", "default": 1.0, "min": 0.1, "max": 10.0},
        "background": {"type": "str", "default": None},
        "negate_colors": {"type": "bool", "default": False},
    }

    def __init__(self) -> None:
        self._cairosvg_available = False

    def is_available(self) -> bool:
        try:
            import cairosvg  # noqa: F401

            self._cairosvg_available = True
            return True
        except ImportError:
            self._cairosvg_available = False
            return False

    def convert(
        self,
        input_path: str,
        target_format: str,
        *,
        output_path: str = "",
        options: dict[str, Any] | None = None,
    ) -> str:
        if not self._cairosvg_available:
            try:
                import cairosvg  # noqa: F401

                self._cairosvg_available = True
            except ImportError:
                raise MissingDependencyError(
                    "cairosvg",
                    install_hint=(
                        "Install CairoSVG for vector conversion:\n"
                        "  pip install cairosvg\n"
                        "  or: pip install omnixform[all-formats]"
                    ),
                )

        target_format = normalize_format(target_format)
        source_ext = os.path.splitext(input_path)[1].lstrip(".").lower()

        if target_format not in self.output_extensions:
            raise UnsupportedFormatError(source_ext, target_format)

        if not output_path:
            output_path = replace_extension(input_path, target_format)

        try:
            import cairosvg

            opts = options or {}
            dpi = opts.get("dpi", 96)
            width = opts.get("width")
            height = opts.get("height")
            scale = opts.get("scale", 1.0)
            background = opts.get("background")
            negate_colors = opts.get("negate_colors", False)

            # Prepare CairoSVG arguments
            kwargs = {
                "url": input_path,
                "dpi": dpi,
                "scale": scale,
            }

            if width is not None:
                kwargs["output_width"] = width
            if height is not None:
                kwargs["output_height"] = height
            if background:
                kwargs["background_color"] = background
            if negate_colors:
                kwargs["negate_colors"] = True

            # Convert based on target format
            if target_format == "png":
                content = cairosvg.svg2png(**kwargs)
            elif target_format == "pdf":
                content = cairosvg.svg2pdf(**kwargs)
            elif target_format == "eps":
                content = cairosvg.svg2eps(**kwargs)
            elif target_format == "ps":
                content = cairosvg.svg2ps(**kwargs)
            elif target_format == "svg":
                atomic_write(output_path, source_path=input_path)
                return output_path
            else:
                raise UnsupportedFormatError(source_ext, target_format)

            atomic_write(output_path, content=content)
            return output_path

        except Exception as e:
            if isinstance(e, (UnsupportedFormatError, MissingDependencyError)):
                raise
            raise ConversionError(
                "Vector conversion failed",
                input_path=input_path,
                adapter=self.name,
                details=str(e),
            ) from e
