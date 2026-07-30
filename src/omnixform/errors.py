from __future__ import annotations

EXIT_SUCCESS = 0
EXIT_BAD_ARGS = 2
EXIT_FILE_NOT_FOUND = 3
EXIT_UNSUPPORTED_FORMAT = 4
EXIT_MISSING_DEPENDENCY = 5
EXIT_OUTPUT_EXISTS = 6
EXIT_CORRUPT_INPUT = 7
EXIT_CONVERSION_ERROR = 8
EXIT_TIMEOUT = 9
EXIT_VALIDATION_ERROR = 10


class OmnixformError(Exception):
    exit_code: int = EXIT_CONVERSION_ERROR

    def __init__(self, message: str, *, details: str | None = None) -> None:
        self.message = message
        self.details = details
        super().__init__(message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} ({self.details})"
        return self.message


class BadArgumentsError(OmnixformError):
    exit_code = EXIT_BAD_ARGS


class FileNotFoundError_(OmnixformError):
    exit_code = EXIT_FILE_NOT_FOUND

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"Input file not found: {path}")


class UnsupportedFormatError(OmnixformError):
    exit_code = EXIT_UNSUPPORTED_FORMAT

    def __init__(self, source: str, target: str, *, reason: str | None = None) -> None:
        self.source = source
        self.target = target
        msg = f"Conversion from {source} to {target} is not supported"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)


class MissingDependencyError(OmnixformError):
    exit_code = EXIT_MISSING_DEPENDENCY

    def __init__(self, name: str, install_hint: str = "") -> None:
        self.dependency = name
        msg = f"Required dependency not found: {name}"
        if install_hint:
            msg += f"\n{install_hint}"
        super().__init__(msg, details=f"dependency={name}")


class OutputExistsError(OmnixformError):
    exit_code = EXIT_OUTPUT_EXISTS

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(
            f"Output file already exists: {path}\n"
            "Use --overwrite to overwrite or specify a different output path."
        )


class CorruptInputError(OmnixformError):
    exit_code = EXIT_CORRUPT_INPUT

    def __init__(self, path: str, *, details: str = "") -> None:
        self.path = path
        msg = f"Input file is corrupt or invalid: {path}"
        if details:
            msg += f"\n{details}"
        super().__init__(msg)


class ConversionError(OmnixformError):
    exit_code = EXIT_CONVERSION_ERROR

    def __init__(
        self,
        message: str,
        *,
        input_path: str = "",
        adapter: str = "",
        details: str | None = None,
    ) -> None:
        self.input_path = input_path
        self.adapter = adapter
        parts = [message]
        if input_path:
            parts.append(f"File: {input_path}")
        if adapter:
            parts.append(f"Adapter: {adapter}")
        super().__init__(" | ".join(parts), details=details)


class TimeoutError_(OmnixformError):
    exit_code = EXIT_TIMEOUT

    def __init__(self, command: str, timeout: float) -> None:
        self.command = command
        self.timeout = timeout
        super().__init__(f"External process timed out after {timeout}s: {command}")


class ValidationError(OmnixformError):
    exit_code = EXIT_VALIDATION_ERROR

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        super().__init__(f"Output validation failed for {path}: {reason}")
