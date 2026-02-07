"""Platform modules -- auto-discovers and registers all platform implementations."""

from __future__ import annotations

import importlib
import logging
import pkgutil
from pathlib import Path

from platforms.registry import get_all_platforms, get_platform, get_platforms_by_type

logger = logging.getLogger(__name__)

# Modules that are infrastructure, not platform implementations
_INFRASTRUCTURE_MODULES = frozenset({
    "protocols",
    "registry",
    "mixins",
    "stealth",
    "base",
})


def _auto_discover() -> None:
    """Import all platform modules to trigger @register_platform decorators."""
    pkg_dir = str(Path(__file__).parent)
    for _finder, module_name, _is_pkg in pkgutil.iter_modules([pkg_dir]):
        if module_name in _INFRASTRUCTURE_MODULES or module_name.endswith("_selectors"):
            continue
        try:
            importlib.import_module(f"platforms.{module_name}")
        except Exception:
            logger.exception("Failed to load platform module '%s'", module_name)


_auto_discover()

# Re-export stealth functions for backward compatibility
from platforms.stealth import close_browser, get_browser_context  # noqa: E402

__all__ = [
    "get_platform",
    "get_all_platforms",
    "get_platforms_by_type",
    "get_browser_context",
    "close_browser",
]
