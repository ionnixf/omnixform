"""Shell completion generation tests."""

from __future__ import annotations

from typer.testing import CliRunner

from omnixform.cli import app


def test_supported_shell_completion_scripts_are_generated() -> None:
    runner = CliRunner()

    for shell in ("bash", "zsh", "fish", "powershell"):
        result = runner.invoke(app, ["completion", shell])

        assert result.exit_code == 0
        assert "omnix" in result.stdout.lower()
        assert "_OMNIXFORM_COMPLETE" in result.stdout
        assert "command not found" not in result.stdout.lower()
