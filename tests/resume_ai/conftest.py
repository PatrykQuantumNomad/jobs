"""Resume AI test fixtures -- mocked Claude CLI subprocess."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_claude_cli():
    """Provide a mock Claude CLI subprocess that returns controlled responses.

    Overrides the autouse ``_block_cli`` guard for tests that need to simulate
    CLI responses.

    The fixture returns a controller object with two methods:

    - ``set_response(model_instance)`` -- configure the mock to return a
      successful CLI envelope containing the given Pydantic model instance.
    - ``set_error(returncode, stderr_text)`` -- configure the mock to simulate
      a CLI failure with the given exit code and stderr output.

    Usage in tests::

        async def test_tailor(mock_claude_cli):
            mock_claude_cli.set_response(make_some_model())
            result = await tailor_resume(...)
            assert result == ...
    """
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = b"{}"
    mock_proc.stderr = b""

    async def _communicate():
        return mock_proc.stdout, mock_proc.stderr

    mock_proc.communicate = _communicate
    mock_proc.kill = MagicMock()
    mock_proc.wait = AsyncMock()

    mock_exec = AsyncMock(return_value=mock_proc)

    class _Controller:
        """Helper to configure mock CLI subprocess responses."""

        def set_response(self, model_instance):
            """Set a successful response from the CLI.

            Serializes the model instance into a CLI envelope with
            ``structured_output`` set to the model's JSON dict.
            """
            envelope = {
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "result": "",
                "structured_output": model_instance.model_dump(mode="json"),
                "duration_ms": 500,
                "num_turns": 2,
            }
            mock_proc.stdout = json.dumps(envelope).encode()
            mock_proc.stderr = b""
            mock_proc.returncode = 0

        def set_error(self, returncode, stderr_text="CLI error"):
            """Set an error response from the CLI.

            Configures the mock process to return the given exit code and
            stderr output, simulating a CLI failure.
            """
            mock_proc.stdout = b""
            mock_proc.stderr = stderr_text.encode()
            mock_proc.returncode = returncode

    controller = _Controller()

    with (
        patch(
            "claude_cli.client.asyncio.create_subprocess_exec",
            new=mock_exec,
        ),
        patch("claude_cli.client.shutil.which", return_value="/usr/local/bin/claude"),
    ):
        yield controller
