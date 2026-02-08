"""Unit tests for platforms/mixins.py -- BrowserPlatformMixin utility methods.

Tests cover:
- element_exists with mock page
- screenshot with mock page
- wait_for_confirmation in dashboard mode and unattended mode
- human_delay timing
"""

import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from platforms.mixins import BrowserPlatformMixin


class _TestPlatform(BrowserPlatformMixin):
    """Concrete class using BrowserPlatformMixin for testing."""

    platform_name = "test_platform"
    _dashboard_mode: bool
    _confirmation_event: threading.Event | None
    _unattended: bool

    def __init__(self, page=None):
        self.page = page or MagicMock()


@pytest.mark.unit
class TestElementExists:
    """Verify element_exists wraps wait_for_selector correctly."""

    def test_element_found(self):
        """element_exists returns True when selector is found."""
        mock_page = MagicMock()
        mock_page.wait_for_selector.return_value = MagicMock()
        platform = _TestPlatform(page=mock_page)

        result = platform.element_exists("div.job-card", timeout=3000)
        assert result is True
        mock_page.wait_for_selector.assert_called_once_with("div.job-card", timeout=3000)

    def test_element_not_found(self):
        """element_exists returns False when selector times out."""
        mock_page = MagicMock()
        mock_page.wait_for_selector.side_effect = TimeoutError("not found")
        platform = _TestPlatform(page=mock_page)

        result = platform.element_exists("div.missing", timeout=1000)
        assert result is False


@pytest.mark.unit
class TestScreenshot:
    """Verify screenshot saves file via page.screenshot."""

    def test_screenshot_calls_page(self, tmp_path):
        """screenshot calls page.screenshot and returns a Path."""

        mock_page = MagicMock()
        platform = _TestPlatform(page=mock_page)

        result = platform.screenshot("test_capture")
        assert isinstance(result, Path)
        assert "test_platform" in result.name
        assert "test_capture" in result.name
        mock_page.screenshot.assert_called_once()


@pytest.mark.unit
class TestWaitForConfirmation:
    """Verify wait_for_confirmation in dashboard and CLI modes."""

    def test_dashboard_mode_confirmed(self):
        """In dashboard mode, returns True when event is set."""
        platform = _TestPlatform()
        platform._dashboard_mode = True
        event = threading.Event()
        event.set()  # Pre-set to simulate immediate confirmation
        platform._confirmation_event = event

        result = platform.wait_for_confirmation("Confirm?", timeout=1)
        assert result is True

    def test_dashboard_mode_timeout(self):
        """In dashboard mode, returns False when event times out."""
        platform = _TestPlatform()
        platform._dashboard_mode = True
        platform._confirmation_event = threading.Event()  # Not set

        result = platform.wait_for_confirmation("Confirm?", timeout=0)
        assert result is False

    def test_dashboard_mode_no_event(self):
        """In dashboard mode with no confirmation event, returns False."""
        platform = _TestPlatform()
        platform._dashboard_mode = True
        # No _confirmation_event set

        result = platform.wait_for_confirmation("Confirm?", timeout=1)
        assert result is False

    def test_unattended_mode_returns_false(self):
        """In unattended mode (no dashboard), returns False."""
        platform = _TestPlatform()
        platform._unattended = True

        result = platform.wait_for_confirmation("Confirm?", timeout=1)
        assert result is False

    @patch("builtins.input", return_value="yes")
    def test_cli_fallback_returns_true(self, mock_input):
        """In CLI mode (no dashboard), wait_for_confirmation falls back to wait_for_human."""
        platform = _TestPlatform()
        result = platform.wait_for_confirmation("Confirm?", timeout=1)
        assert result is True


@pytest.mark.unit
class TestWaitForHuman:
    """Verify wait_for_human in attended and unattended modes."""

    def test_unattended_raises_runtime_error(self):
        """wait_for_human raises RuntimeError in unattended mode."""
        platform = _TestPlatform()
        platform._unattended = True

        with pytest.raises(RuntimeError, match="unattended mode"):
            platform.wait_for_human("Please solve CAPTCHA")

    @patch("builtins.input", return_value="yes")
    def test_attended_returns_input(self, mock_input):
        """wait_for_human returns stripped user input in attended mode."""
        platform = _TestPlatform()
        result = platform.wait_for_human("Solve CAPTCHA")
        assert result == "yes"
        mock_input.assert_called_once()

    @patch("builtins.input", return_value="  confirmed  ")
    def test_attended_strips_whitespace(self, mock_input):
        """wait_for_human strips whitespace from user input."""
        platform = _TestPlatform()
        result = platform.wait_for_human("Confirm?")
        assert result == "confirmed"


@pytest.mark.unit
class TestHumanDelay:
    """Verify human_delay calls time.sleep with correct ranges."""

    @patch("platforms.mixins.time.sleep")
    def test_nav_delay(self, mock_sleep):
        """human_delay('nav') sleeps with nav delay range."""
        platform = _TestPlatform()
        platform.human_delay("nav")
        mock_sleep.assert_called_once()
        # Verify the sleep duration is within expected range
        duration = mock_sleep.call_args[0][0]
        assert isinstance(duration, float)
        assert duration > 0

    @patch("platforms.mixins.time.sleep")
    def test_form_delay(self, mock_sleep):
        """human_delay('form') sleeps with form delay range."""
        platform = _TestPlatform()
        platform.human_delay("form")
        mock_sleep.assert_called_once()
        duration = mock_sleep.call_args[0][0]
        assert isinstance(duration, float)
        assert duration > 0
