from __future__ import annotations

import os
from typing import Any

import markdown as md_lib

from omnixform.adapters.base import BaseAdapter
from omnixform.errors import ConversionError, CorruptInputError, UnsupportedFormatError
from omnixform.formats import normalize_format
from omnixform.models import Category
from omnixform.paths import atomic_write, replace_extension


class TextAdapter(BaseAdapter):
    name = "text"
    category = Category.TEXT
    description = "Markdown, HTML, and plain text conversion"
    input_extensions = ["txt", "md", "html", "htm"]
    output_extensions = ["txt", "md", "html", "htm"]
    priority = 10
    options = {
        "encoding": {"type": "str", "default": "utf-8"},
    }

    def is_available(self) -> bool:
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
        source_ext = normalize_format(os.path.splitext(input_path)[1]) or target_format

        if target_format not in self.output_extensions:
            raise UnsupportedFormatError(source_ext, target_format)

        if not output_path:
            output_path = replace_extension(input_path, target_format)

        encoding = opts.get("encoding", "utf-8")

        try:
            with open(input_path, encoding=encoding) as f:
                content = f.read()
        except UnicodeDecodeError as e:
            raise CorruptInputError(input_path, details=f"Encoding error: {e}") from e
        except OSError as e:
            raise CorruptInputError(input_path, details=str(e)) from e

        try:
            result = self._convert_text(content, source_ext, target_format)
            atomic_write(output_path, content=result.encode(encoding))
            return output_path
        except Exception as e:
            if isinstance(e, (UnsupportedFormatError, CorruptInputError)):
                raise
            raise ConversionError(
                "Text conversion failed",
                input_path=input_path,
                adapter=self.name,
                details=str(e),
            ) from e

    def _convert_text(self, content: str, source: str, target: str) -> str:
        if source == target:
            return content

        if source == "md" and target == "html":
            result: str = md_lib.markdown(
                content,
                extensions=["fenced_code", "codehilite", "tables", "nl2br"],
            )
            return result

        if source == "html" and target == "txt":
            import re

            text = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
            text = re.sub(r"<[^>]+>", "", text)
            text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            text = text.replace("&quot;", '"').replace("&#39;", "'")
            lines = [line.strip() for line in text.splitlines()]
            return "\n".join(line for line in lines if line)

        if source == "txt" and target == "md":
            return content

        if source == "txt" and target == "html":
            import html as html_mod

            escaped = html_mod.escape(content)
            paragraphs = [f"<p>{line}</p>" for line in escaped.splitlines() if line.strip()]
            return "<!DOCTYPE html>\n<html>\n<body>\n" + "\n".join(paragraphs) + "\n</body>\n</html>\n"

        if source == "md" and target == "txt":
            import re

            text = content
            text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
            text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
            text = re.sub(r"_{1,3}([^_]+)_{1,3}", r"\1", text)
            text = re.sub(r"`([^`]+)`", r"\1", text)
            text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
            text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
            text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
            text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)
            text = re.sub(r"^[\s]*[-*+]\s+", "", text, flags=re.MULTILINE)
            text = re.sub(r"^[\s]*\d+\.\s+", "", text, flags=re.MULTILINE)
            text = re.sub(r"```[\w]*\n?", "", text)
            text = re.sub(r"<[^>]+>", "", text)
            lines = [line.strip() for line in text.splitlines()]
            return "\n".join(line for line in lines if line)

        if source == "html" and target == "md":
            import re

            return re.sub(r"<[^>]+>", "", content).strip()

        raise UnsupportedFormatError(source, target)
