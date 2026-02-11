"""Shared fixtures for claude_cli tests.

Provides a sample Pydantic model, CLI envelope builder, and mock subprocess
fixture.  All tests use mocked subprocess calls -- never real CLI invocations.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel


class SampleModel(BaseModel):
    """Simple model used across all claude_cli tests."""

    answer: int
    reasoning: str


def sample_envelope(
    *,
    structured_output: dict | None = None,
    result: str = "",
    is_error: bool = False,
    subtype: str = "success",
) -> str:
    """Build a JSON string matching the Claude CLI envelope format.

    Args:
        structured_output: The structured_output field value (or None).
        result: The result field string.
        is_error: Whether the envelope indicates an error.
        subtype: The subtype field (e.g. "success", "error_max_structured_output_retries").

    Returns:
        A JSON-encoded string of the envelope.
    """
    envelope = {
        "type": "result",
        "subtype": subtype,
        "is_error": is_error,
        "result": result,
        "structured_output": structured_output,
        "duration_ms": 1000,
        "num_turns": 2,
    }
    return json.dumps(envelope)


@pytest.fixture
def mock_subprocess():
    """Patch asyncio.create_subprocess_exec and return a configurable mock process.

    The returned mock has:
    - ``stdout``: bytes to return from communicate() (default: empty envelope)
    - ``stderr``: bytes to return from communicate() (default: b"")
    - ``returncode``: int (default: 0)
    - ``communicate``: AsyncMock returning (stdout, stderr)
    - ``kill``: MagicMock
    - ``wait``: AsyncMock

    Also patches ``shutil.which`` to return ``"/usr/local/bin/claude"`` by default.
    """
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = sample_envelope(
        structured_output={"answer": 42, "reasoning": "because"}
    ).encode()
    mock_proc.stderr = b""

    async def _communicate():
        return mock_proc.stdout, mock_proc.stderr

    mock_proc.communicate = _communicate
    mock_proc.kill = MagicMock()
    mock_proc.wait = AsyncMock()

    with (
        patch(
            "claude_cli.client.asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=mock_proc),
        ) as mock_exec,
        patch("claude_cli.client.shutil.which", return_value="/usr/local/bin/claude"),
    ):
        # Expose the process mock and exec mock on the fixture for test access
        mock_exec.mock_proc = mock_proc
        yield mock_exec
