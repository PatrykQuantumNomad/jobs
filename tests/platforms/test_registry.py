"""Integration tests for platform registry auto-discovery and protocol compliance.

API-03: Platform registry -- verifies all 3 platforms discovered with correct
        metadata, KeyError for nonexistent keys, type-based filtering.
API-04: Protocol compliance -- verifies isinstance checks against APIPlatform
        and BrowserPlatform, method existence, context manager support.
"""

import pytest

import platforms  # noqa: F401 -- triggers _auto_discover()
from platforms.protocols import APIPlatform, BrowserPlatform
from platforms.registry import (
    PlatformInfo,
    get_all_platforms,
    get_platform,
    get_platforms_by_type,
)


@pytest.mark.integration
class TestPlatformRegistry:
    """API-03: Platform registry discovery tests."""

    def test_registry_contains_indeed(self):
        """Registry contains 'indeed' after auto-discovery."""
        all_platforms = get_all_platforms()
        assert "indeed" in all_platforms

    def test_registry_contains_dice(self):
        """Registry contains 'dice' after auto-discovery."""
        all_platforms = get_all_platforms()
        assert "dice" in all_platforms

    def test_registry_contains_remoteok(self):
        """Registry contains 'remoteok' after auto-discovery."""
        all_platforms = get_all_platforms()
        assert "remoteok" in all_platforms

    def test_registry_has_exactly_three_platforms(self):
        """Registry contains exactly 3 platforms."""
        assert len(get_all_platforms()) == 3

    def test_indeed_metadata(self):
        """Indeed has correct PlatformInfo metadata."""
        info = get_platform("indeed")
        assert isinstance(info, PlatformInfo)
        assert info.name == "Indeed"
        assert info.platform_type == "browser"

    def test_dice_metadata(self):
        """Dice has correct PlatformInfo metadata."""
        info = get_platform("dice")
        assert isinstance(info, PlatformInfo)
        assert info.name == "Dice"
        assert info.platform_type == "browser"

    def test_remoteok_metadata(self):
        """RemoteOK has correct PlatformInfo metadata."""
        info = get_platform("remoteok")
        assert isinstance(info, PlatformInfo)
        assert info.name == "RemoteOK"
        assert info.platform_type == "api"

    def test_get_platform_nonexistent_raises_keyerror(self):
        """Requesting a nonexistent platform raises KeyError."""
        with pytest.raises(KeyError, match="not registered"):
            get_platform("glassdoor")

    def test_get_platforms_by_type_browser(self):
        """Filtering by 'browser' returns indeed and dice, not remoteok."""
        browser = get_platforms_by_type("browser")
        assert "indeed" in browser
        assert "dice" in browser
        assert "remoteok" not in browser

    def test_get_platforms_by_type_api(self):
        """Filtering by 'api' returns remoteok, not indeed or dice."""
        api = get_platforms_by_type("api")
        assert "remoteok" in api
        assert "indeed" not in api
        assert "dice" not in api

    def test_platform_info_has_cls(self):
        """Each PlatformInfo has a non-None callable cls."""
        for info in get_all_platforms().values():
            assert info.cls is not None
            assert callable(info.cls)


@pytest.mark.integration
class TestProtocolCompliance:
    """API-04: Protocol compliance tests via isinstance and hasattr."""

    def test_remoteok_is_api_platform(self):
        """RemoteOK instance satisfies APIPlatform protocol."""
        info = get_platform("remoteok")
        instance = info.cls()
        assert isinstance(instance, APIPlatform)

    def test_indeed_is_browser_platform(self):
        """Indeed instance satisfies BrowserPlatform protocol."""
        info = get_platform("indeed")
        instance = info.cls()
        assert isinstance(instance, BrowserPlatform)

    def test_dice_is_browser_platform(self):
        """Dice instance satisfies BrowserPlatform protocol."""
        info = get_platform("dice")
        instance = info.cls()
        assert isinstance(instance, BrowserPlatform)

    def test_remoteok_is_not_browser_platform(self):
        """RemoteOK does NOT satisfy BrowserPlatform (no login/is_logged_in)."""
        instance = get_platform("remoteok").cls()
        assert not isinstance(instance, BrowserPlatform)

    def test_all_platforms_have_platform_name(self):
        """Every platform instance has a non-empty platform_name attribute."""
        for info in get_all_platforms().values():
            instance = info.cls()
            assert hasattr(instance, "platform_name")
            assert isinstance(instance.platform_name, str)
            assert len(instance.platform_name) > 0

    def test_all_platforms_have_search_method(self):
        """Every platform instance has a callable search method."""
        for info in get_all_platforms().values():
            instance = info.cls()
            assert hasattr(instance, "search")
            assert callable(instance.search)

    def test_all_platforms_have_apply_method(self):
        """Every platform instance has a callable apply method."""
        for info in get_all_platforms().values():
            instance = info.cls()
            assert hasattr(instance, "apply")
            assert callable(instance.apply)

    def test_all_platforms_have_get_job_details_method(self):
        """Every platform instance has a callable get_job_details method."""
        for info in get_all_platforms().values():
            instance = info.cls()
            assert hasattr(instance, "get_job_details")
            assert callable(instance.get_job_details)

    def test_all_platforms_are_context_managers(self):
        """Every platform instance supports the context manager protocol."""
        for info in get_all_platforms().values():
            instance = info.cls()
            assert hasattr(instance, "__enter__")
            assert hasattr(instance, "__exit__")
