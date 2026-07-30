from __future__ import annotations

import csv
import io
import json
import os
from typing import Any

import yaml

from omnixform.adapters.base import BaseAdapter
from omnixform.errors import ConversionError, CorruptInputError, UnsupportedFormatError
from omnixform.formats import normalize_format
from omnixform.models import Category
from omnixform.paths import atomic_write, replace_extension


class StructuredDataAdapter(BaseAdapter):
    name = "structured_data"
    category = Category.STRUCTURED_DATA
    description = "JSON, YAML, CSV, and TSV conversion"
    input_extensions = ["json", "yaml", "yml", "csv", "tsv"]
    output_extensions = ["json", "yaml", "yml", "csv", "tsv"]
    priority = 10
    options = {
        "encoding": {"type": "str", "default": "utf-8"},
        "delimiter": {"type": "str", "default": None},
        "indent": {"type": "int", "default": 2},
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
        source_ext = normalize_format(os.path.splitext(input_path)[1])

        if target_format not in self.output_extensions:
            raise UnsupportedFormatError(source_ext, target_format)

        if not output_path:
            output_path = replace_extension(input_path, target_format)

        encoding = opts.get("encoding", "utf-8")
        indent = opts.get("indent", 2)

        try:
            with open(input_path, encoding=encoding) as f:
                source_content = f.read()
        except OSError as e:
            raise CorruptInputError(input_path, details=str(e)) from e

        try:
            if source_ext in ("json",):
                data = json.loads(source_content)
            elif source_ext in ("yaml",):
                data = yaml.safe_load(source_content)
            elif source_ext in ("csv", "tsv"):
                delimiter = opts.get("delimiter") or ("\t" if source_ext == "tsv" else ",")
                data = self._parse_tabular(source_content, delimiter)
            else:
                raise UnsupportedFormatError(source_ext, target_format)

            if target_format in ("json",):
                result = self._to_json(data, indent)
            elif target_format in ("yaml",):
                result = self._to_yaml(data, indent)
            elif target_format in ("csv", "tsv"):
                result = self._to_tabular(data, target_format, opts)
            else:
                raise UnsupportedFormatError(source_ext, target_format)

            atomic_write(output_path, content=result.encode(encoding))
            return output_path

        except json.JSONDecodeError as e:
            raise CorruptInputError(input_path, details=f"Invalid JSON: {e}") from e
        except yaml.YAMLError as e:
            raise CorruptInputError(input_path, details=f"Invalid YAML: {e}") from e
        except (csv.Error, ValueError) as e:
            raise CorruptInputError(input_path, details=str(e)) from e
        except UnsupportedFormatError:
            raise
        except Exception as e:
            raise ConversionError(
                "Structured data conversion failed",
                input_path=input_path,
                adapter=self.name,
                details=str(e),
            ) from e

    def _parse_tabular(self, content: str, delimiter: str) -> list[dict[str, str]]:
        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        return [{k: v for k, v in row.items()} for row in reader]

    def _to_json(self, data: Any, indent: int) -> str:
        if indent == 0:
            return json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        return json.dumps(data, ensure_ascii=False, indent=indent) + "\n"

    def _to_yaml(self, data: Any, indent: int) -> str:
        return str(yaml.dump(data, default_flow_style=False, indent=indent, allow_unicode=True))

    def _to_tabular(self, data: Any, target_format: str, opts: dict[str, Any]) -> str:
        delimiter = opts.get("delimiter") or ("\t" if target_format == "tsv" else ",")

        if not isinstance(data, list):
            raise ConversionError(
                "Cannot convert non-array data to CSV/TSV",
                details="Expected a list of objects",
            )

        if not data:
            return ""

        fieldnames: list[str] = []
        for item in data:
            if isinstance(item, dict):
                for key in item:
                    if key not in fieldnames:
                        fieldnames.append(key)

        if not fieldnames:
            raise ConversionError(
                "Cannot convert data without object keys to CSV/TSV",
                details="Data must be a list of objects with string keys",
            )

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=delimiter, extrasaction="ignore")
        writer.writeheader()
        for item in data:
            if isinstance(item, dict):
                writer.writerow({k: self._csv_format(v) for k, v in item.items()})
            elif isinstance(item, (list, tuple)):
                writer.writerow(dict(zip(fieldnames, [self._csv_format(v) for v in item], strict=False)))
        return output.getvalue()

    @staticmethod
    def _csv_format(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)
