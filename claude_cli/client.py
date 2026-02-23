"""Async subprocess wrapper for invoking Claude CLI with typed Pydantic output.

Provides a single ``run()`` function that shells out to the ``claude`` binary,
passes a JSON Schema derived from a Pydantic model, and returns a validated
model instance.  Includes timeout handling, auth error detection, and automatic
cold-start retry (one retry on first-invocation failures).
"""

import asyncio
import json
import logging
import shutil

from pydantic import BaseModel

from claude_cli.exceptions import (
    CLIAuthError,
    CLIMalformedOutputError,
    CLINotFoundError,
    CLIProcessError,
    CLITimeoutError,
)
from claude_cli.parser import parse_cli_response

log = logging.getLogger(__name__)

_AUTH_KEYWORDS = ["not authenticated", "login", "auth", "setup-token", "subscription"]


def _detect_auth_error(stderr: str, envelope: dict | None) -> bool:
    """Check whether a CLI error indicates an authentication failure.

    Inspects stderr text and, when available, the response envelope's ``result``
    field for known authentication-related keywords.

    Args:
        stderr: Decoded stderr output.
        envelope: Parsed JSON envelope, or None if stdout was not valid JSON.

    Returns:
        True if the error appears to be an auth failure.
    """
    stderr_lower = stderr.lower()
    if any(kw in stderr_lower for kw in _AUTH_KEYWORDS):
        return True
    if envelope and envelope.get("is_error"):
        result_text = str(envelope.get("result", "")).lower()
        if any(kw in result_text for kw in _AUTH_KEYWORDS):
            return True
    return False


async def run[T: BaseModel](
    *,
    system_prompt: str,
    user_message: str,
    output_model: type[T],
    model: str = "sonnet",
    max_turns: int = 3,
    timeout_seconds: float = 120.0,
) -> T:
    """Invoke Claude CLI and return a validated Pydantic model instance.

    Builds a command that passes the user message via ``-p``, sets
    ``--output-format json`` and ``--json-schema`` from the model's schema,
    then parses the JSON envelope returned on stdout.

    Includes a single automatic retry for cold-start failures (GitHub #23265).

    Args:
        system_prompt: System prompt for Claude.
        user_message: User message / prompt content.
        output_model: Pydantic model class whose JSON Schema is sent to the CLI
            and used to validate the response.
        model: Claude model alias (default ``"sonnet"``).
        max_turns: Maximum conversation turns (default 3; minimum 2 for structured output).
        timeout_seconds: Seconds before the subprocess is killed (default 120).

    Returns:
        A validated instance of ``output_model``.

    Raises:
        CLINotFoundError: If ``claude`` is not on PATH.
        CLITimeoutError: If the subprocess exceeds ``timeout_seconds``.
        CLIAuthError: If an authentication failure is detected.
        CLIProcessError: If the subprocess exits with a non-zero code.
        CLIMalformedOutputError: If the response cannot be parsed or validated.
        CLIResponseError: If the CLI envelope has ``is_error=true``.
    """
    claude_path = shutil.which("claude")
    if claude_path is None:
        raise CLINotFoundError(
            "Claude CLI not found on PATH. Install it or ensure it is in your PATH."
        )

    schema_json = json.dumps(output_model.model_json_schema())

    cmd = [
        claude_path,
        "-p",
        user_message,
        "--output-format",
        "json",
        "--json-schema",
        schema_json,
        "--system-prompt",
        system_prompt,
        "--model",
        model,
        "--max-turns",
        str(max_turns),
        "--no-session-persistence",
        "--tools",
        "",
    ]

    log.debug("Claude CLI command: %s", " ".join(cmd[:6]) + " ...")

    last_error: CLIProcessError | CLIMalformedOutputError | None = None

    for attempt in range(2):  # max 1 retry (cold-start)
        if attempt > 0:
            log.warning("CLI cold-start retry (attempt %d)", attempt + 1)

        try:
            result = await _execute(cmd, timeout_seconds)
            return result.validate(output_model)
        except (CLIProcessError, CLIMalformedOutputError) as exc:
            last_error = exc
            if attempt == 0:
                continue
            raise

    # Should not reach here, but satisfy type checker
    raise last_error  # type: ignore[misc]


class _ExecutionResult:
    """Intermediate result holding raw subprocess output for parsing."""

    def __init__(self, stdout: str, stderr: str, returncode: int) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode

    def validate[M: BaseModel](self, output_model: type[M]) -> M:
        """Parse stdout and return a validated model, raising typed exceptions on failure."""
        # Check for non-zero exit first
        if self.returncode != 0:
            envelope = self._try_parse_envelope()
            if _detect_auth_error(self.stderr, envelope):
                raise CLIAuthError(
                    f"Claude CLI authentication failure (exit code {self.returncode}). "
                    "Run 'claude setup-token' to authenticate."
                )
            raise CLIProcessError(
                f"Claude CLI exited with code {self.returncode}",
                returncode=self.returncode,
                stderr=self.stderr,
            )

        # Try to detect auth errors in a successful-exit envelope too
        try:
            parsed = parse_cli_response(self.stdout, output_model)
        except Exception:
            envelope = self._try_parse_envelope()
            if envelope and _detect_auth_error(self.stderr, envelope):
                raise CLIAuthError(
                    "Claude CLI authentication failure detected in response. "
                    "Run 'claude setup-token' to authenticate."
                ) from None
            raise

        return parsed

    def _try_parse_envelope(self) -> dict | None:
        """Attempt to parse stdout as JSON, returning None on failure."""
        try:
            return json.loads(self.stdout)
        except json.JSONDecodeError:
            return None
        except ValueError:
            return None


async def _execute(cmd: list[str], timeout_seconds: float) -> _ExecutionResult:
    """Run the subprocess with timeout, returning an _ExecutionResult.

    Raises CLITimeoutError if the process exceeds the timeout.
    """
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout_seconds,
        )
    except TimeoutError:
        proc.kill()
        await proc.wait()
        raise CLITimeoutError(f"Claude CLI timed out after {timeout_seconds}s") from None

    return _ExecutionResult(
        stdout=stdout_bytes.decode(errors="replace"),
        stderr=stderr_bytes.decode(errors="replace"),
        returncode=proc.returncode,  # type: ignore[arg-type]
    )
