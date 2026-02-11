"""Unit tests for the claude_cli resilient JSON parser.

Tests all parser paths: structured_output, result JSON, result markdown,
is_error, validation errors, max retries subtype, and empty result.
"""

import pytest

from claude_cli.exceptions import CLIMalformedOutputError, CLIResponseError
from claude_cli.parser import parse_cli_response
from tests.claude_cli.conftest import SampleModel, sample_envelope


@pytest.mark.unit
class TestParseCliResponse:
    """Tests for parse_cli_response covering all resolution paths."""

    def test_parse_structured_output_success(self):
        """Path 2: structured_output field present and valid."""
        raw = sample_envelope(structured_output={"answer": 42, "reasoning": "because"})
        result = parse_cli_response(raw, SampleModel)
        assert isinstance(result, SampleModel)
        assert result.answer == 42
        assert result.reasoning == "because"

    def test_parse_result_json_fallback(self):
        """Path 3: structured_output is null, result contains raw JSON string."""
        raw = sample_envelope(
            structured_output=None,
            result='{"answer": 42, "reasoning": "because"}',
        )
        result = parse_cli_response(raw, SampleModel)
        assert isinstance(result, SampleModel)
        assert result.answer == 42
        assert result.reasoning == "because"

    def test_parse_result_markdown_fallback(self):
        """Path 4: result contains JSON inside a markdown code block with json tag."""
        raw = sample_envelope(
            structured_output=None,
            result='```json\n{"answer": 42, "reasoning": "because"}\n```',
        )
        result = parse_cli_response(raw, SampleModel)
        assert isinstance(result, SampleModel)
        assert result.answer == 42

    def test_parse_result_markdown_no_lang_tag(self):
        """Path 4: markdown code block without 'json' language tag."""
        raw = sample_envelope(
            structured_output=None,
            result='```\n{"answer": 99, "reasoning": "no tag"}\n```',
        )
        result = parse_cli_response(raw, SampleModel)
        assert result.answer == 99

    def test_parse_is_error_raises_response_error(self):
        """Path 1: is_error=true in envelope raises CLIResponseError."""
        raw = sample_envelope(is_error=True, result="something went wrong")
        with pytest.raises(CLIResponseError) as exc_info:
            parse_cli_response(raw, SampleModel)
        assert exc_info.value.envelope["is_error"] is True
        assert "something went wrong" in str(exc_info.value)

    def test_parse_invalid_json_raises_malformed(self):
        """Raw stdout is not valid JSON at all."""
        with pytest.raises(CLIMalformedOutputError) as exc_info:
            parse_cli_response("not json at all {{{", SampleModel)
        assert "not valid JSON" in str(exc_info.value)
        assert len(exc_info.value.raw_output) <= 500

    def test_parse_structured_output_validation_error(self):
        """structured_output contains data that fails Pydantic validation."""
        raw = sample_envelope(structured_output={"answer": "not_a_number", "reasoning": "bad type"})
        with pytest.raises(CLIMalformedOutputError) as exc_info:
            parse_cli_response(raw, SampleModel)
        assert "validation" in str(exc_info.value).lower()

    def test_parse_max_retries_subtype(self):
        """Path 5: subtype is error_max_structured_output_retries."""
        raw = sample_envelope(
            structured_output=None,
            result="",
            subtype="error_max_structured_output_retries",
        )
        with pytest.raises(CLIMalformedOutputError) as exc_info:
            parse_cli_response(raw, SampleModel)
        assert "exhausted retries" in str(exc_info.value)

    def test_parse_empty_result_no_structured_output(self):
        """Path 6: No structured_output and empty result raises CLIMalformedOutputError."""
        raw = sample_envelope(structured_output=None, result="")
        with pytest.raises(CLIMalformedOutputError) as exc_info:
            parse_cli_response(raw, SampleModel)
        assert "neither structured_output nor parseable result" in str(exc_info.value)

    def test_parse_raw_output_truncated(self):
        """Error messages truncate raw_output to 500 chars max."""
        long_garbage = "x" * 1000
        with pytest.raises(CLIMalformedOutputError) as exc_info:
            parse_cli_response(long_garbage, SampleModel)
        assert len(exc_info.value.raw_output) <= 500

    def test_parse_structured_output_takes_precedence_over_result(self):
        """When both structured_output and result are present, structured_output wins."""
        raw = sample_envelope(
            structured_output={"answer": 1, "reasoning": "from structured"},
            result='{"answer": 2, "reasoning": "from result"}',
        )
        result = parse_cli_response(raw, SampleModel)
        assert result.answer == 1
        assert result.reasoning == "from structured"

    def test_parse_result_with_extra_text_around_code_block(self):
        """Result has text around the code block; only the JSON inside is used."""
        json_block = '```json\n{"answer": 7, "reasoning": "extracted"}\n```'
        md = "Here is the answer:\n" + json_block + "\nDone."
        raw = sample_envelope(structured_output=None, result=md)
        result = parse_cli_response(raw, SampleModel)
        assert result.answer == 7
