# Plugins

Omnixform discovers adapter classes from the `omnixform.adapters` Python entry
point group.

```toml
[project.entry-points."omnixform.adapters"]
example = "example_plugin.adapter:ExampleAdapter"
```

The referenced object must subclass `BaseAdapter`:

```python
from typing import Any

from omnixform.adapters.base import BaseAdapter
from omnixform.models import Category


class ExampleAdapter(BaseAdapter):
    name = "example"
    category = Category.TEXT
    description = "Example conversion"
    input_extensions = ["example"]
    output_extensions = ["txt"]
    priority = 40

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
        # Write the complete result to output_path and return that exact path.
        ...
        return output_path
```

Lower numeric priority is preferred. `can_convert()` declares supported pairs;
`is_conversion_available()` may provide pair-specific dependency detection.

The CLI passes a private staging path as `output_path`, verifies that the plugin
returns that path, validates known target formats, and publishes successful
output. Ordinary plugin exceptions become exit-code-8 conversion failures, and
partial staging files are removed.

Plugins execute arbitrary Python with the user's permissions. Install only
trusted plugins. A plugin that starts subprocesses must use argument vectors,
timeouts, cleanup, and no shell interpretation. Omnixform cannot sandbox plugin
imports or side effects.
