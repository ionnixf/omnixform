"""Tests for error handling and exceptions."""

from __future__ import annotations

from omnixform.errors import (
    EXIT_BAD_ARGS,
    EXIT_CONVERSION_ERROR,
    EXIT_CORRUPT_INPUT,
    EXIT_FILE_NOT_FOUND,
    EXIT_MISSING_DEPENDENCY,
    EXIT_OUTPUT_EXISTS,
    EXIT_TIMEOUT,
    EXIT_UNSUPPORTED_FORMAT,
    EXIT_VALIDATION_ERROR,
    BadArgumentsError,
    ConversionError,
    CorruptInputError,
    FileNotFoundError_,
    MissingDependencyError,
    OmnixformError,
    OutputExistsError,
    TimeoutError_,
    UnsupportedFormatError,
    ValidationError,
)


class TestExitCodes:
    def test_values(self) -> None:
        assert EXIT_BAD_ARGS == 2
        assert EXIT_FILE_NOT_FOUND == 3
        assert EXIT_UNSUPPORTED_FORMAT == 4
        assert EXIT_MISSING_DEPENDENCY == 5
        assert EXIT_OUTPUT_EXISTS == 6
        assert EXIT_CORRUPT_INPUT == 7
        assert EXIT_CONVERSION_ERROR == 8
        assert EXIT_TIMEOUT == 9
        assert EXIT_VALIDATION_ERROR == 10


class TestExceptions:
    def test_file_not_found(self) -> None:
        err = FileNotFoundError_("/path/to/file")
        assert err.exit_code == EXIT_FILE_NOT_FOUND
        assert "/path/to/file" in str(err)
        assert err.path == "/path/to/file"

    def test_unsupported_format(self) -> None:
        err = UnsupportedFormatError("png", "docx")
        assert err.exit_code == EXIT_UNSUPPORTED_FORMAT
        assert "png" in str(err)
        assert "docx" in str(err)

    def test_missing_dependency(self) -> None:
        err = MissingDependencyError("pandoc")
        assert err.exit_code == EXIT_MISSING_DEPENDENCY
        assert "pandoc" in str(err).lower()
        assert err.dependency == "pandoc"

    def test_output_exists(self) -> None:
        err = OutputExistsError("/path/to/output")
        assert err.exit_code == EXIT_OUTPUT_EXISTS
        assert "already exists" in str(err).lower()
        assert err.path == "/path/to/output"

    def test_corrupt_input(self) -> None:
        err = CorruptInputError("/path/to/file", details="bad data")
        assert err.exit_code == EXIT_CORRUPT_INPUT
        assert "/path/to/file" in str(err)
        assert err.path == "/path/to/file"

    def test_conversion_error(self) -> None:
        err = ConversionError("Something went wrong", input_path="input.jpg", adapter="pillow")
        assert err.exit_code == EXIT_CONVERSION_ERROR
        assert "input.jpg" in str(err)
        assert "pillow" in str(err)

    def test_timeout_error(self) -> None:
        err = TimeoutError_("ffmpeg", 30.0)
        assert err.exit_code == EXIT_TIMEOUT
        assert "30" in str(err)
        assert "ffmpeg" in str(err).lower()

    def test_validation_error(self) -> None:
        err = ValidationError("/path/to/output", "file is empty")
        assert err.exit_code == EXIT_VALIDATION_ERROR
        assert "empty" in str(err)

    def test_bad_arguments(self) -> None:
        err = BadArgumentsError("Invalid option")
        assert err.exit_code == EXIT_BAD_ARGS

    def test_base_error(self) -> None:
        err = OmnixformError("Base error")
        assert err.exit_code == EXIT_CONVERSION_ERROR

    def test_error_with_details(self) -> None:
        err = OmnixformError("Main msg", details="Detail msg")
        assert "Detail msg" in str(err)
