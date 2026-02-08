"""Resume AI test fixtures -- mocked Anthropic client."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_anthropic(monkeypatch):
    """Provide a mock Anthropic client that returns controlled responses.

    Overrides the autouse _block_anthropic guard for tests that need
    to simulate LLM responses.

    Usage in tests::

        def test_tailor(mock_anthropic):
            mock_anthropic.messages.create.return_value = ...
    """
    mock_client = MagicMock()

    # Default response structure matching Anthropic SDK
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Mock AI response")]
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50
    mock_client.messages.create.return_value = mock_response

    try:
        import anthropic

        monkeypatch.setattr(anthropic, "Anthropic", lambda **kw: mock_client)
    except ImportError:
        pass

    return mock_client
