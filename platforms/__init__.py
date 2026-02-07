"""Job platform automation modules."""

__all__ = ["BasePlatform", "get_browser_context", "close_browser"]


def __getattr__(name: str):
    if name == "BasePlatform":
        from .base import BasePlatform

        return BasePlatform
    if name in ("get_browser_context", "close_browser"):
        from . import stealth

        return getattr(stealth, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
