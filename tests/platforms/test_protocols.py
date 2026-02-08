"""Unit tests for platforms/protocols.py -- BrowserPlatform and APIPlatform.

Tests cover:
- Runtime isinstance checks against protocol classes
- Protocol structural typing verification
"""

from unittest.mock import MagicMock

import pytest

from platforms.protocols import APIPlatform, BrowserPlatform


class _MockBrowserPlatform:
    """Concrete implementation satisfying BrowserPlatform protocol."""

    platform_name = "mock_browser"

    def init(self, context):
        pass

    def login(self):
        return True

    def is_logged_in(self):
        return True

    def search(self, query):
        return []

    def get_job_details(self, job):
        return job

    def apply(self, job, resume_path=None):
        return True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class _MockAPIPlatform:
    """Concrete implementation satisfying APIPlatform protocol."""

    platform_name = "mock_api"

    def init(self):
        pass

    def search(self, query):
        return []

    def get_job_details(self, job):
        return job

    def apply(self, job, resume_path=None):
        return True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class _NotAPlatform:
    """Class that does NOT satisfy either protocol."""

    pass


@pytest.mark.unit
class TestBrowserPlatformProtocol:
    """Verify BrowserPlatform runtime_checkable protocol."""

    def test_conforming_class_is_instance(self):
        """A class with all required methods is recognized as BrowserPlatform."""
        obj = _MockBrowserPlatform()
        assert isinstance(obj, BrowserPlatform)

    def test_non_conforming_class_is_not_instance(self):
        """A class without required methods is NOT recognized."""
        obj = _NotAPlatform()
        assert not isinstance(obj, BrowserPlatform)

    def test_methods_return_expected_types(self):
        """BrowserPlatform methods return correct types when called."""
        obj = _MockBrowserPlatform()
        assert obj.login() is True
        assert obj.is_logged_in() is True
        assert obj.search(MagicMock()) == []
        assert obj.apply(MagicMock()) is True


@pytest.mark.unit
class TestAPIPlatformProtocol:
    """Verify APIPlatform runtime_checkable protocol."""

    def test_conforming_class_is_instance(self):
        """A class with all required methods is recognized as APIPlatform."""
        obj = _MockAPIPlatform()
        assert isinstance(obj, APIPlatform)

    def test_non_conforming_class_is_not_instance(self):
        """A class without required methods is NOT recognized."""
        obj = _NotAPlatform()
        assert not isinstance(obj, APIPlatform)

    def test_context_manager_works(self):
        """APIPlatform can be used as a context manager."""
        with _MockAPIPlatform() as p:
            assert p.platform_name == "mock_api"
