"""Tests for plugin system (entry point based adapters)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from omnixform.adapters.base import BaseAdapter
from omnixform.models import Category
from omnixform.registry import Registry, get_registry, reset_registry


class MockPluginAdapter(BaseAdapter):
    """Mock adapter for testing plugins."""

    name = "mockplugin"
    category = Category.IMAGE
    description = "Mock plugin adapter"
    input_extensions = ["mock"]
    output_extensions = ["mock", "png", "jpg"]
    priority = 5  # Higher priority than built-in pillow (10)

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
        return output_path or input_path.replace(".mock", f".{target_format}")


class LowPriorityMockAdapter(BaseAdapter):
    """Mock adapter with lower priority."""

    name = "lowpriority"
    category = Category.IMAGE
    description = "Low priority mock"
    input_extensions = ["low"]
    output_extensions = ["low", "png"]
    priority = 50  # Lower than built-in

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
        return output_path or input_path.replace(".low", f".{target_format}")


def test_plugin_registration_via_entry_point() -> None:
    """Test that adapters can be registered via entry point mechanism."""
    reset_registry()
    registry = Registry()

    # Simulate entry point loading by manually registering
    registry.register(MockPluginAdapter())

    adapters = registry.get_all_adapters()
    names = [a.name for a in adapters]
    assert "mockplugin" in names

    # Check it's selectable
    adapter = registry.select_adapter("mock", "png")
    assert adapter is not None
    assert adapter.name == "mockplugin"


def test_plugin_invalid_entry_point_ignored() -> None:
    """Test that invalid entry points are ignored with warning."""
    reset_registry()

    with patch("importlib.metadata.entry_points") as mock_eps:
        # Create a mock entry point that raises on load
        mock_ep = MagicMock()
        mock_ep.name = "badplugin"
        mock_ep.load.side_effect = ImportError("No module named 'badplugin'")

        mock_eps.return_value = [mock_ep]

        with pytest.warns(UserWarning, match="Failed to load adapter"):
            registry = Registry()

    # Built-ins should still be there
    adapters = registry.get_all_adapters()
    assert len(adapters) >= 7


def test_plugin_wrong_base_class_warned() -> None:
    """Test that non-BaseAdapter entry points are warned about."""
    reset_registry()

    class NotAnAdapter:
        pass

    with patch("importlib.metadata.entry_points") as mock_eps:
        mock_ep = MagicMock()
        mock_ep.name = "notanadapter"
        mock_ep.load.return_value = NotAnAdapter

        mock_eps.return_value = [mock_ep]

        with pytest.warns(UserWarning, match="does not implement BaseAdapter"):
            registry = Registry()

    # Should not be in adapters
    adapters = registry.get_all_adapters()
    names = [a.name for a in adapters]
    assert "notanadapter" not in names


def test_plugin_can_override_builtin() -> None:
    """Test that a plugin with higher priority can override a built-in adapter."""
    reset_registry()
    registry = Registry()

    # Register a plugin with same name as built-in but higher priority
    class OverridePillow(BaseAdapter):
        name = "pillow"
        category = Category.IMAGE
        description = "Override pillow"
        input_extensions = ["png", "jpg"]
        output_extensions = ["png", "jpg", "webp"]
        priority = 1  # Higher priority than built-in (10)

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
            return output_path or "overridden"

    registry.register(OverridePillow())

    # The override should be used
    adapter = registry.select_adapter("png", "webp")
    assert adapter is not None
    assert adapter.name == "pillow"
    assert adapter.priority == 1  # Our override

    # The old pillow (priority 10) should be replaced
    adapters = registry.get_all_adapters()
    pillow_adapters = [a for a in adapters if a.name == "pillow"]
    assert len(pillow_adapters) == 1
    assert pillow_adapters[0].priority == 1


def test_plugin_lower_priority_not_override() -> None:
    """Test that a plugin with lower priority doesn't override built-in."""
    reset_registry()
    registry = Registry()

    class LowPriorityPillow(BaseAdapter):
        name = "pillow"
        category = Category.IMAGE
        description = "Low priority pillow"
        input_extensions = ["png"]
        output_extensions = ["png"]
        priority = 100  # Much lower than built-in (10)

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
            return "low"

    registry.register(LowPriorityPillow())

    # Built-in should still be used
    adapter = registry.select_adapter("png", "jpg")
    assert adapter is not None
    assert adapter.priority == 10  # Built-in priority

    # Only one pillow adapter
    adapters = registry.get_all_adapters()
    pillow_adapters = [a for a in adapters if a.name == "pillow"]
    assert len(pillow_adapters) == 1


def test_registry_reset() -> None:
    """Test that registry can be reset for testing."""
    reset_registry()
    registry1 = get_registry()
    initial_count = len(registry1.get_all_adapters())

    # Add something
    registry1.register(MockPluginAdapter())
    assert len(registry1.get_all_adapters()) == initial_count + 1

    # Reset
    reset_registry()
    registry2 = get_registry()
    assert len(registry2.get_all_adapters()) == initial_count
    assert registry2 is not registry1


def test_plugin_entry_points_discovered() -> None:
    """Test that entry points from installed packages are discovered."""
    reset_registry()

    # The built-in entry points should be registered
    with patch("importlib.metadata.entry_points") as mock_eps:
        # Mock the entry points our pyproject.toml defines
        def make_mock_ep(name: str, adapter_class: type[BaseAdapter]) -> MagicMock:
            ep = MagicMock()
            ep.name = name
            ep.load.return_value = adapter_class
            return ep

        from omnixform.adapters.images import ImageAdapter
        from omnixform.adapters.multimedia import MultimediaAdapter

        mock_eps.return_value = [
            make_mock_ep("pillow", ImageAdapter),
            make_mock_ep("ffmpeg", MultimediaAdapter),
        ]

        registry = Registry()

    # Built-ins should still be there (loaded first)
    adapters = registry.get_all_adapters()
    assert len(adapters) >= 7


def test_get_adapter_infos_includes_plugins() -> None:
    """Test that get_adapter_infos includes plugin adapters."""
    reset_registry()
    registry = Registry()
    registry.register(MockPluginAdapter())

    infos = registry.get_adapter_infos()
    names = [i.name for i in infos]
    assert "mockplugin" in names

    mock_info = next(i for i in infos if i.name == "mockplugin")
    assert mock_info.category == Category.IMAGE
    assert mock_info.available is True
    assert mock_info.priority == 5


def test_possible_targets_includes_plugins() -> None:
    """Test that get_possible_targets includes plugin formats."""
    reset_registry()
    registry = Registry()
    registry.register(MockPluginAdapter())

    targets = registry.get_possible_targets("mock")
    formats = [t["format"] for t in targets]
    assert "png" in formats
    assert "jpg" in formats

    # Check adapter name is correct
    png_target = next(t for t in targets if t["format"] == "png")
    assert png_target["adapter"] == "mockplugin"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
