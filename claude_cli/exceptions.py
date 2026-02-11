"""Typed exception hierarchy for Claude CLI subprocess errors.

Each exception stores enough context for callers (webapp endpoints, CLI orchestrator)
to display user-friendly error messages and take appropriate recovery action.
"""


class CLIError(Exception):
    """Base exception for all Claude CLI errors."""


class CLINotFoundError(CLIError):
    """Claude CLI binary not found on PATH.

    Raised when ``shutil.which("claude")`` returns None, indicating the CLI
    is not installed or not on the system PATH.
    """


class CLITimeoutError(CLIError):
    """Claude CLI subprocess exceeded the configured timeout.

    The process is killed before this exception is raised.
    """


class CLIAuthError(CLIError):
    """Claude CLI authentication failure.

    Raised when stderr or the response envelope indicates the user is not
    authenticated. Recovery: run ``claude setup-token``.
    """


class CLIProcessError(CLIError):
    """Claude CLI exited with a non-zero return code.

    Attributes:
        returncode: The process exit code.
        stderr: Decoded stderr output from the process.
    """

    def __init__(self, message: str, *, returncode: int, stderr: str) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


class CLIMalformedOutputError(CLIError):
    """Claude CLI returned output that could not be parsed or validated.

    Raised when the JSON envelope is not valid JSON, or when neither
    ``structured_output`` nor ``result`` contains data that validates
    against the expected Pydantic model.

    Attributes:
        raw_output: Truncated (max 500 chars) raw output for debugging.
    """

    def __init__(self, message: str, *, raw_output: str) -> None:
        super().__init__(message)
        self.raw_output = raw_output


class CLIResponseError(CLIError):
    """Claude CLI returned ``is_error=true`` in its response envelope.

    Attributes:
        envelope: The full parsed JSON envelope dict for inspection.
    """

    def __init__(self, message: str, *, envelope: dict) -> None:
        super().__init__(message)
        self.envelope = envelope
