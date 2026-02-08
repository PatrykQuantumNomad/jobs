"""Unit tests for apply_engine/events.py -- ApplyEventType, ApplyEvent,
make_progress_event, make_done_event.

Tests cover:
- Enum value verification
- Default field values on ApplyEvent
- model_dump serialization
- Factory function behavior
"""

import pytest

from apply_engine.events import ApplyEvent, ApplyEventType, make_done_event, make_progress_event


@pytest.mark.unit
class TestApplyEventType:
    """Verify ApplyEventType enum values."""

    def test_progress_value(self):
        """PROGRESS enum value is 'progress'."""
        assert ApplyEventType.PROGRESS == "progress"

    def test_awaiting_confirm_value(self):
        """AWAITING_CONFIRM enum value is 'awaiting_confirm'."""
        assert ApplyEventType.AWAITING_CONFIRM == "awaiting_confirm"

    def test_confirmed_value(self):
        """CONFIRMED enum value is 'confirmed'."""
        assert ApplyEventType.CONFIRMED == "confirmed"

    def test_captcha_value(self):
        """CAPTCHA enum value is 'captcha'."""
        assert ApplyEventType.CAPTCHA == "captcha"

    def test_error_value(self):
        """ERROR enum value is 'error'."""
        assert ApplyEventType.ERROR == "error"

    def test_done_value(self):
        """DONE enum value is 'done'."""
        assert ApplyEventType.DONE == "done"

    def test_ping_value(self):
        """PING enum value is 'ping'."""
        assert ApplyEventType.PING == "ping"


@pytest.mark.unit
class TestApplyEvent:
    """Verify ApplyEvent default values and serialization."""

    def test_defaults(self):
        """ApplyEvent with only type has sensible defaults."""
        event = ApplyEvent(type=ApplyEventType.PROGRESS)
        assert event.message == ""
        assert event.html == ""
        assert event.screenshot_path is None
        assert event.fields_filled == {}
        assert event.job_dedup_key == ""

    def test_all_fields_set(self):
        """ApplyEvent with all fields explicitly set."""
        event = ApplyEvent(
            type=ApplyEventType.ERROR,
            message="Something failed",
            html="<p>Error</p>",
            screenshot_path="/tmp/screenshot.png",
            fields_filled={"name": "John"},
            job_dedup_key="testco::engineer",
        )
        assert event.type == ApplyEventType.ERROR
        assert event.message == "Something failed"
        assert event.html == "<p>Error</p>"
        assert event.screenshot_path == "/tmp/screenshot.png"
        assert event.fields_filled == {"name": "John"}
        assert event.job_dedup_key == "testco::engineer"

    def test_model_dump(self):
        """model_dump() returns dict with all expected keys."""
        event = ApplyEvent(
            type=ApplyEventType.DONE,
            message="Complete",
            job_dedup_key="key1",
        )
        dumped = event.model_dump()
        expected_keys = {
            "type",
            "message",
            "html",
            "screenshot_path",
            "fields_filled",
            "job_dedup_key",
        }
        assert set(dumped.keys()) == expected_keys
        assert dumped["type"] == "done"
        assert dumped["message"] == "Complete"


@pytest.mark.unit
class TestMakeProgressEvent:
    """Verify make_progress_event factory function."""

    def test_creates_progress_event(self):
        """make_progress_event returns event with PROGRESS type."""
        event = make_progress_event("test msg", job_dedup_key="key1")
        assert event.type == ApplyEventType.PROGRESS
        assert event.message == "test msg"
        assert event.job_dedup_key == "key1"

    def test_with_html(self):
        """make_progress_event with html parameter."""
        event = make_progress_event("msg", html="<p>hi</p>")
        assert event.html == "<p>hi</p>"

    def test_defaults(self):
        """make_progress_event with only message has empty defaults."""
        event = make_progress_event("msg")
        assert event.html == ""
        assert event.job_dedup_key == ""


@pytest.mark.unit
class TestMakeDoneEvent:
    """Verify make_done_event factory function."""

    def test_default_message(self):
        """make_done_event without message uses default success message."""
        event = make_done_event()
        assert event.type == ApplyEventType.DONE
        assert event.message == "Application submitted successfully"

    def test_custom_message(self):
        """make_done_event with custom message uses that message."""
        event = make_done_event("Custom done message")
        assert event.message == "Custom done message"

    def test_with_job_key(self):
        """make_done_event with job_dedup_key."""
        event = make_done_event(job_dedup_key="key1")
        assert event.job_dedup_key == "key1"
