"""Unit tests for claude_cli exception hierarchy."""

import pytest

from claude_cli.exceptions import (
    CLIAuthError,
    CLIError,
    CLIMalformedOutputError,
    CLINotFoundError,
    CLIProcessError,
    CLIResponseError,
    CLITimeoutError,
)


@pytest.mark.unit
class TestExceptionHierarchy:
    """Verify exception construction, attributes, and inheritance."""

    def test_cli_error_is_base_exception(self):
        exc = CLIError("base error")
        assert isinstance(exc, Exception)
        assert str(exc) == "base error"

    def test_cli_not_found_error(self):
        exc = CLINotFoundError("not found")
        assert isinstance(exc, CLIError)
        assert isinstance(exc, Exception)
        assert str(exc) == "not found"

    def test_cli_timeout_error(self):
        exc = CLITimeoutError("timed out")
        assert isinstance(exc, CLIError)
        assert str(exc) == "timed out"

    def test_cli_auth_error(self):
        exc = CLIAuthError("not authenticated")
        assert isinstance(exc, CLIError)
        assert str(exc) == "not authenticated"

    def test_cli_process_error_stores_attributes(self):
        exc = CLIProcessError("exit code 1", returncode=1, stderr="some error output")
        assert isinstance(exc, CLIError)
        assert exc.returncode == 1
        assert exc.stderr == "some error output"
        assert str(exc) == "exit code 1"

    def test_cli_malformed_output_error_stores_raw_output(self):
        exc = CLIMalformedOutputError("bad json", raw_output='{"broken":')
        assert isinstance(exc, CLIError)
        assert exc.raw_output == '{"broken":'
        assert str(exc) == "bad json"

    def test_cli_response_error_stores_envelope(self):
        envelope = {"type": "result", "is_error": True, "result": "auth failed"}
        exc = CLIResponseError("error response", envelope=envelope)
        assert isinstance(exc, CLIError)
        assert exc.envelope == envelope
        assert exc.envelope["is_error"] is True

    def test_all_exceptions_inherit_from_cli_error(self):
        """Every exception in the hierarchy is a subclass of CLIError."""
        exceptions = [
            CLINotFoundError,
            CLITimeoutError,
            CLIAuthError,
            CLIProcessError,
            CLIMalformedOutputError,
            CLIResponseError,
        ]
        for exc_class in exceptions:
            assert issubclass(exc_class, CLIError), f"{exc_class.__name__} not subclass of CLIError"
            assert issubclass(exc_class, Exception), (
                f"{exc_class.__name__} not subclass of Exception"
            )
