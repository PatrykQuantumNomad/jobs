"""Unit tests for apply_engine/engine.py -- ApplyEngine sync helper methods.

Tests the synchronous helper methods WITHOUT triggering Playwright or browser
imports. Uses mock settings object to avoid real config loading.
"""

import asyncio
import threading
from unittest.mock import MagicMock

import pytest

from apply_engine.engine import ApplyEngine
from apply_engine.events import ApplyEvent, ApplyEventType


def _make_mock_settings():
    """Create a mock settings object matching expected interface."""
    mock = MagicMock()
    mock.candidate_resume_path = "/tmp/default_resume.pdf"
    mock.apply.default_mode.value = "semi_auto"
    return mock


@pytest.mark.unit
class TestApplyEngineConfirm:
    """Verify confirm() sets threading.Event for active sessions."""

    def test_confirm_existing_session(self):
        """confirm() returns True and sets the event for an active session."""
        engine = ApplyEngine(settings=_make_mock_settings())
        event = threading.Event()
        engine._confirmations["key1"] = event

        result = engine.confirm("key1")
        assert result is True
        assert event.is_set()

    def test_confirm_nonexistent_session(self):
        """confirm() returns False for a nonexistent session key."""
        engine = ApplyEngine(settings=_make_mock_settings())
        result = engine.confirm("nonexistent")
        assert result is False


@pytest.mark.unit
class TestApplyEngineCancel:
    """Verify cancel() cleans up sessions and emits DONE event."""

    def test_cancel_existing_session(self):
        """cancel() returns True and removes session/confirmation for active session."""
        engine = ApplyEngine(settings=_make_mock_settings())
        queue = asyncio.Queue()
        event = threading.Event()
        engine._sessions["key1"] = queue
        engine._confirmations["key1"] = event

        result = engine.cancel("key1")
        assert result is True
        assert "key1" not in engine._sessions
        assert "key1" not in engine._confirmations

    def test_cancel_nonexistent_session(self):
        """cancel() returns False for a nonexistent session key."""
        engine = ApplyEngine(settings=_make_mock_settings())
        result = engine.cancel("nonexistent")
        assert result is False

    def test_cancel_sets_confirmation_event(self):
        """cancel() sets the confirmation event to unblock waiting thread."""
        engine = ApplyEngine(settings=_make_mock_settings())
        queue = asyncio.Queue()
        event = threading.Event()
        engine._sessions["key1"] = queue
        engine._confirmations["key1"] = event

        engine.cancel("key1")
        assert event.is_set()


@pytest.mark.unit
class TestApplyEngineGetSessionQueue:
    """Verify get_session_queue() returns correct queue or None."""

    def test_returns_queue_when_exists(self):
        """get_session_queue() returns the queue for an active session."""
        engine = ApplyEngine(settings=_make_mock_settings())
        queue = asyncio.Queue()
        engine._sessions["key1"] = queue

        result = engine.get_session_queue("key1")
        assert result is queue

    def test_returns_none_when_missing(self):
        """get_session_queue() returns None for a nonexistent session."""
        engine = ApplyEngine(settings=_make_mock_settings())
        result = engine.get_session_queue("missing")
        assert result is None


@pytest.mark.unit
class TestEmitSync:
    """Verify _emit_sync puts events onto the queue."""

    def test_puts_event_dict(self):
        """_emit_sync puts event.model_dump() onto queue."""
        queue = asyncio.Queue()
        event = ApplyEvent(
            type=ApplyEventType.PROGRESS,
            message="test",
            job_dedup_key="key1",
        )
        ApplyEngine._emit_sync(queue, event)

        result = queue.get_nowait()
        assert result["type"] == "progress"
        assert result["message"] == "test"

    def test_suppresses_errors(self):
        """_emit_sync suppresses exceptions from queue.put_nowait."""
        mock_queue = MagicMock()
        mock_queue.put_nowait.side_effect = RuntimeError("queue full")

        event = ApplyEvent(type=ApplyEventType.ERROR, message="err")
        # Should not raise
        ApplyEngine._emit_sync(mock_queue, event)


@pytest.mark.unit
class TestGetResumePath:
    """Verify _get_resume_path resolution logic."""

    def test_default_path_when_no_tailored_version(self):
        """_get_resume_path returns default resume path when DB has no tailored version."""
        engine = ApplyEngine(settings=_make_mock_settings())
        # With _fresh_db autouse, the resume_versions table is empty
        path = engine._get_resume_path("nonexistent::key")
        assert str(path) == "/tmp/default_resume.pdf"

    def test_tailored_path_when_file_exists(self, tmp_path):
        """_get_resume_path returns tailored path when DB has version and file exists."""
        from resume_ai.tracker import save_resume_version

        engine = ApplyEngine(settings=_make_mock_settings())

        # Create a temp file to simulate the tailored resume
        tailored_file = tmp_path / "tailored.pdf"
        tailored_file.write_bytes(b"fake pdf")

        # Insert a version record pointing to it
        save_resume_version(
            job_dedup_key="testco::engineer",
            resume_type="resume",
            file_path=str(tailored_file),
            original_resume_path="/tmp/orig.pdf",
            model_used="claude-test",
        )

        path = engine._get_resume_path("testco::engineer")
        assert path == tailored_file

    def test_falls_back_to_default_when_file_missing(self):
        """_get_resume_path falls back to default when tailored file doesn't exist."""
        from resume_ai.tracker import save_resume_version

        engine = ApplyEngine(settings=_make_mock_settings())

        # Insert a version record pointing to a nonexistent file
        save_resume_version(
            job_dedup_key="testco::engineer",
            resume_type="resume",
            file_path="/nonexistent/tailored.pdf",
            original_resume_path="/tmp/orig.pdf",
            model_used="claude-test",
        )

        path = engine._get_resume_path("testco::engineer")
        assert str(path) == "/tmp/default_resume.pdf"


@pytest.mark.unit
class TestMakeEmitter:
    """Verify _make_emitter returns a callable."""

    def test_returns_callable(self):
        """_make_emitter returns a callable function."""
        engine = ApplyEngine(settings=_make_mock_settings())
        queue = asyncio.Queue()
        loop = asyncio.new_event_loop()
        try:
            emitter = engine._make_emitter(queue, loop)
            assert callable(emitter)
        finally:
            loop.close()
