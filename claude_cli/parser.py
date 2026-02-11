"""Resilient JSON parser for Claude CLI response envelopes.

Handles both the normal ``structured_output`` field and the regression path
where structured data appears as JSON embedded in the ``result`` field
(see GitHub issue #18536).
"""

import json
import re

from pydantic import BaseModel, ValidationError

from claude_cli.exceptions import CLIMalformedOutputError, CLIResponseError

_MAX_RAW_OUTPUT_LEN = 500


def parse_cli_response[T: BaseModel](raw_stdout: str, model: type[T]) -> T:
    """Parse a CLI JSON envelope and return a validated Pydantic model instance.

    Resolution order:
        1. Parse raw stdout as JSON envelope.
        2. If ``is_error`` is true, raise ``CLIResponseError``.
        3. If ``structured_output`` is present, validate and return.
        4. If ``result`` is parseable JSON, validate and return.
        5. If ``result`` contains a markdown code block with JSON, extract, validate, return.
        6. If ``subtype`` is ``error_max_structured_output_retries``, raise.
        7. Otherwise raise ``CLIMalformedOutputError``.

    Args:
        raw_stdout: Raw stdout string from the Claude CLI process.
        model: The Pydantic model class to validate the structured data against.

    Returns:
        A validated instance of ``model``.

    Raises:
        CLIResponseError: If the envelope has ``is_error=true``.
        CLIMalformedOutputError: If the output cannot be parsed or validated.
    """
    # Parse the outer JSON envelope
    try:
        envelope = json.loads(raw_stdout)
    except json.JSONDecodeError as exc:
        raise CLIMalformedOutputError(
            f"CLI output is not valid JSON: {exc}",
            raw_output=raw_stdout[:_MAX_RAW_OUTPUT_LEN],
        ) from exc

    # Path 1: Check for CLI-level errors
    if envelope.get("is_error"):
        raise CLIResponseError(
            f"CLI reported error: {envelope.get('result', 'unknown')}",
            envelope=envelope,
        )

    # Path 2: structured_output field (correct behavior)
    structured = envelope.get("structured_output")
    if structured is not None:
        try:
            return model.model_validate(structured)
        except ValidationError as exc:
            raise CLIMalformedOutputError(
                f"structured_output failed validation: {exc}",
                raw_output=json.dumps(structured)[:_MAX_RAW_OUTPUT_LEN],
            ) from exc

    # Path 3: JSON embedded in result field (regression fallback)
    result_text = envelope.get("result", "")
    if result_text:
        # Try parsing result directly as JSON
        try:
            data = json.loads(result_text)
            return model.model_validate(data)
        except json.JSONDecodeError:
            pass
        except ValidationError:
            pass

        # Path 4: Try extracting JSON from markdown code block
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", result_text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                return model.model_validate(data)
            except json.JSONDecodeError:
                pass
            except ValidationError:
                pass

    # Path 5: Check subtype for structured output retry exhaustion
    subtype = envelope.get("subtype", "")
    if subtype == "error_max_structured_output_retries":
        raise CLIMalformedOutputError(
            "CLI exhausted retries producing valid structured output",
            raw_output=raw_stdout[:_MAX_RAW_OUTPUT_LEN],
        )

    # Path 6: Nothing worked
    raise CLIMalformedOutputError(
        "CLI response contains neither structured_output nor parseable result",
        raw_output=raw_stdout[:_MAX_RAW_OUTPUT_LEN],
    )
