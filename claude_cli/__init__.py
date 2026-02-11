"""Claude CLI subprocess wrapper with typed Pydantic structured output.

Public API for invoking the Claude CLI binary and receiving validated
Pydantic model instances.  All AI features in v1.2+ use this package
instead of the Anthropic Python SDK.

Usage::

    from pydantic import BaseModel
    from claude_cli import run

    class Answer(BaseModel):
        value: int
        reasoning: str

    result = await run(
        system_prompt="You are a math expert.",
        user_message="What is 6 * 7?",
        output_model=Answer,
    )
    print(result.value)  # 42
"""

from claude_cli.client import run
from claude_cli.exceptions import (
    CLIAuthError,
    CLIError,
    CLIMalformedOutputError,
    CLINotFoundError,
    CLIProcessError,
    CLIResponseError,
    CLITimeoutError,
)

__all__ = [
    "CLIAuthError",
    "CLIError",
    "CLIMalformedOutputError",
    "CLINotFoundError",
    "CLIProcessError",
    "CLIResponseError",
    "CLITimeoutError",
    "run",
]
