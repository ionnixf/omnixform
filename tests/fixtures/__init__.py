"""Helper functions for tests."""

from __future__ import annotations

import json
import tempfile
from typing import Any


def create_test_image(
    path: str,
    *,
    width: int = 100,
    height: int = 100,
    mode: str = "RGB",
    color: tuple[int, ...] = (255, 0, 0),
    with_alpha: bool = False,
) -> str:
    """Create a test image file using Pillow."""
    from PIL import Image

    if with_alpha:
        mode = "RGBA"
        color = (*color, 128)

    img = Image.new(mode, (width, height), color)
    img.save(path)
    return path


def create_test_markdown(path: str) -> str:
    """Create a test Markdown file."""
    content = "\n".join(
        [
            "# Test Document",
            "",
            "This is a **paragraph** with _emphasis_.",
            "",
            "- Item 1",
            "- Item 2",
            "",
            "## Code",
            "",
            "```python",
            'print("hello")',
            "```",
            "",
            "[A link](https://example.com)",
        ]
    )
    with open(path, "w") as f:
        f.write(content)
    return path


def create_test_html(path: str) -> str:
    """Create a test HTML file."""
    content = """<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body>
<h1>Test Document</h1>
<p>This is a <strong>paragraph</strong>.</p>
<ul>
<li>Item 1</li>
<li>Item 2</li>
</ul>
</body>
</html>"""
    with open(path, "w") as f:
        f.write(content)
    return path


def create_test_json(path: str, *, array_of_objects: bool = False) -> str:
    """Create a test JSON file."""
    data: Any
    if array_of_objects:
        data = [
            {"name": "Alice", "age": 30, "city": "New York"},
            {"name": "Bob", "age": 25, "city": "London"},
            {"name": "Charlie", "age": 35, "city": "Paris"},
        ]
    else:
        data = {
            "name": "test",
            "version": 1,
            "nested": {"key": "value"},
            "list": [1, 2, 3],
        }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def create_test_yaml(path: str) -> str:
    """Create a test YAML file."""
    content = """
name: test
version: 1
nested:
  key: value
list:
  - 1
  - 2
  - 3
"""
    with open(path, "w") as f:
        f.write(content)
    return path


def create_test_csv(path: str, *, delimiter: str = ",") -> str:
    """Create a test CSV file."""
    import csv

    with open(path, "w", newline="") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerow(["name", "age", "city"])
        writer.writerow(["Alice", 30, "New York"])
        writer.writerow(["Bob", 25, "London"])
    return path


def create_test_tsv(path: str) -> str:
    """Create a test TSV file."""
    return create_test_csv(path, delimiter="\t")


class TempDir:
    """Context manager for temporary directories."""

    def __init__(self) -> None:
        self.path: str = ""

    def __enter__(self) -> str:
        self.path = tempfile.mkdtemp(prefix="omnixform_test_")
        return self.path

    def __exit__(self, *args: object) -> None:
        import shutil

        shutil.rmtree(self.path, ignore_errors=True)
