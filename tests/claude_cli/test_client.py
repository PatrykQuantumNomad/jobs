"""Unit tests for the claude_cli async subprocess client.

All tests use mocked subprocess calls -- never real CLI invocations.
Uses pytest-asyncio strict mode with explicit asyncio markers.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_cli.client import run
from claude_cli.exceptions import (
    CLIAuthError,
    CLINotFoundError,
    CLIProcessError,
    CLITimeoutError,
)
from tests.claude_cli.conftest import SampleModel, sample_envelope


@pytest.mark.unit
class TestRunSuccess:
    """Tests for successful invocations of run()."""

    @pytest.mark.asyncio
    async def test_run_success(self, mock_subprocess):
        """Valid envelope with structured_output returns validated model."""
        result = await run(
            system_prompt="test",
            user_message="what is 6*7?",
            output_model=SampleModel,
        )
        assert isinstance(result, SampleModel)
        assert result.answer == 42
        assert result.reasoning == "because"

        # Verify command construction
        mock_subprocess.assert_called_once()
        cmd = mock_subprocess.call_args[0]
        assert "-p" in cmd
        assert "--output-format" in cmd
        assert "json" in cmd
        assert "--json-schema" in cmd
        assert "--system-prompt" in cmd
        assert "--model" in cmd
        assert "--max-turns" in cmd
        assert "--no-session-persistence" in cmd
        assert "--tools" in cmd
        # Verify empty tools arg follows --tools
        tools_idx = list(cmd).index("--tools")
        assert cmd[tools_idx + 1] == ""

    @pytest.mark.asyncio
    async def test_run_custom_model_and_timeout(self, mock_subprocess):
        """Custom model and timeout_seconds appear in command and wait_for call."""
        result = await run(
            system_prompt="test",
            user_message="hello",
            output_model=SampleModel,
            model="opus",
            timeout_seconds=60.0,
            max_turns=5,
        )
        assert isinstance(result, SampleModel)

        cmd = mock_subprocess.call_args[0]
        # Find --model and check the next arg
        model_idx = list(cmd).index("--model")
        assert cmd[model_idx + 1] == "opus"
        # Find --max-turns and check the next arg
        turns_idx = list(cmd).index("--max-turns")
        assert cmd[turns_idx + 1] == "5"


@pytest.mark.unit
class TestRunErrors:
    """Tests for error paths in run()."""

    @pytest.mark.asyncio
    async def test_run_cli_not_found(self):
        """shutil.which returns None -> CLINotFoundError."""
        with (
            patch("claude_cli.client.shutil.which", return_value=None),
            pytest.raises(CLINotFoundError, match="(?i)not found"),
        ):
            await run(
                system_prompt="test",
                user_message="hello",
                output_model=SampleModel,
            )

    @pytest.mark.asyncio
    async def test_run_timeout(self):
        """Subprocess that hangs raises CLITimeoutError."""
        mock_proc = MagicMock()
        mock_proc.returncode = -9
        mock_proc.kill = MagicMock()
        mock_proc.wait = AsyncMock()

        async def _hang():
            await asyncio.sleep(999)
            return b"", b""  # pragma: no cover

        mock_proc.communicate = _hang

        with (
            patch(
                "claude_cli.client.asyncio.create_subprocess_exec",
                new=AsyncMock(return_value=mock_proc),
            ),
            patch("claude_cli.client.shutil.which", return_value="/usr/local/bin/claude"),
            pytest.raises(CLITimeoutError),
        ):
            await run(
                system_prompt="test",
                user_message="hello",
                output_model=SampleModel,
                timeout_seconds=0.1,
            )

    @pytest.mark.asyncio
    async def test_run_nonzero_exit(self, mock_subprocess):
        """Non-zero exit code raises CLIProcessError."""
        proc = mock_subprocess.mock_proc
        proc.returncode = 1
        proc.stderr = b"some error"
        proc.stdout = b"{}"

        with pytest.raises(CLIProcessError) as exc_info:
            await run(
                system_prompt="test",
                user_message="hello",
                output_model=SampleModel,
            )
        assert exc_info.value.returncode == 1
        assert "some error" in exc_info.value.stderr

    @pytest.mark.asyncio
    async def test_run_auth_error_detected(self, mock_subprocess):
        """Non-zero exit with auth keywords in stderr raises CLIAuthError."""
        proc = mock_subprocess.mock_proc
        proc.returncode = 1
        proc.stderr = b"Error: not authenticated, run setup-token to fix"
        proc.stdout = b"{}"

        with pytest.raises(CLIAuthError):
            await run(
                system_prompt="test",
                user_message="hello",
                output_model=SampleModel,
            )

    @pytest.mark.asyncio
    async def test_run_auth_error_in_envelope(self, mock_subprocess):
        """Exit code 0 but is_error=true with auth text raises CLIAuthError."""
        proc = mock_subprocess.mock_proc
        proc.returncode = 0
        proc.stdout = sample_envelope(
            is_error=True,
            result="not authenticated - please login",
        ).encode()

        with pytest.raises(CLIAuthError):
            await run(
                system_prompt="test",
                user_message="hello",
                output_model=SampleModel,
            )


@pytest.mark.unit
class TestColdStartRetry:
    """Tests for the cold-start retry mechanism."""

    @pytest.mark.asyncio
    async def test_run_cold_start_retry_success(self):
        """First call fails with CLIProcessError, second succeeds."""
        call_count = 0
        good_stdout = sample_envelope(
            structured_output={"answer": 42, "reasoning": "retried"}
        ).encode()

        mock_proc_fail = MagicMock()
        mock_proc_fail.returncode = 1
        mock_proc_fail.stderr = b"cold start error"
        mock_proc_fail.stdout = b"{}"
        mock_proc_fail.kill = MagicMock()
        mock_proc_fail.wait = AsyncMock()

        async def _communicate_fail():
            return mock_proc_fail.stdout, mock_proc_fail.stderr

        mock_proc_fail.communicate = _communicate_fail

        mock_proc_success = MagicMock()
        mock_proc_success.returncode = 0
        mock_proc_success.stderr = b""
        mock_proc_success.stdout = good_stdout
        mock_proc_success.kill = MagicMock()
        mock_proc_success.wait = AsyncMock()

        async def _communicate_success():
            return mock_proc_success.stdout, mock_proc_success.stderr

        mock_proc_success.communicate = _communicate_success

        async def _mock_exec(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_proc_fail
            return mock_proc_success

        with (
            patch(
                "claude_cli.client.asyncio.create_subprocess_exec",
                side_effect=_mock_exec,
            ),
            patch("claude_cli.client.shutil.which", return_value="/usr/local/bin/claude"),
        ):
            result = await run(
                system_prompt="test",
                user_message="hello",
                output_model=SampleModel,
            )
            assert result.answer == 42
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_run_cold_start_retry_exhausted(self):
        """Both calls fail -> raises the second exception."""
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stderr = b"persistent error"
        mock_proc.stdout = b"{}"
        mock_proc.kill = MagicMock()
        mock_proc.wait = AsyncMock()

        async def _communicate():
            return mock_proc.stdout, mock_proc.stderr

        mock_proc.communicate = _communicate

        with (
            patch(
                "claude_cli.client.asyncio.create_subprocess_exec",
                new=AsyncMock(return_value=mock_proc),
            ),
            patch("claude_cli.client.shutil.which", return_value="/usr/local/bin/claude"),
            pytest.raises(CLIProcessError),
        ):
            await run(
                system_prompt="test",
                user_message="hello",
                output_model=SampleModel,
            )

    @pytest.mark.asyncio
    async def test_cold_start_retry_does_not_retry_auth_errors(self):
        """Auth errors are NOT retried -- they propagate immediately."""
        call_count = 0

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stderr = b"not authenticated, run setup-token"
        mock_proc.stdout = b"{}"
        mock_proc.kill = MagicMock()
        mock_proc.wait = AsyncMock()

        async def _communicate():
            return mock_proc.stdout, mock_proc.stderr

        mock_proc.communicate = _communicate

        async def _mock_exec(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_proc

        with (
            patch("claude_cli.client.asyncio.create_subprocess_exec", side_effect=_mock_exec),
            patch("claude_cli.client.shutil.which", return_value="/usr/local/bin/claude"),
            pytest.raises(CLIAuthError),
        ):
            await run(
                system_prompt="test",
                user_message="hello",
                output_model=SampleModel,
            )
        # Auth errors raise CLIAuthError which is NOT in the retry catch list
        # (CLIProcessError, CLIMalformedOutputError), so it should NOT retry.
        # CLIAuthError propagates immediately without being caught by the retry loop.
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_run_json_schema_passed_to_cli(self, mock_subprocess):
        """The JSON schema from the model is passed via --json-schema flag."""
        await run(
            system_prompt="test",
            user_message="hello",
            output_model=SampleModel,
        )

        cmd = mock_subprocess.call_args[0]
        schema_idx = list(cmd).index("--json-schema")
        schema_str = cmd[schema_idx + 1]
        schema = json.loads(schema_str)
        # SampleModel has 'answer' (int) and 'reasoning' (str)
        assert "answer" in schema.get("properties", {})
        assert "reasoning" in schema.get("properties", {})
