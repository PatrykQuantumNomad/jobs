"""Decorator-based platform registry with fail-fast protocol validation.

Provides ``@register_platform`` which validates that a class implements the
required Protocol (BrowserPlatform or APIPlatform) at import time. Missing
methods cause an immediate ``TypeError`` -- no silent failures at runtime.

Usage::

    from platforms.registry import register_platform

    @register_platform("indeed", name="Indeed", platform_type="browser",
                       capabilities=["search", "easy_apply"])
    class IndeedPlatform(BrowserPlatformMixin):
        platform_name = "indeed"
        ...

Import chain: models -> protocols -> registry (no cycles).
"""

import inspect
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlatformInfo:
    """Metadata about a registered platform adapter."""

    key: str
    name: str
    platform_type: str  # "browser" | "api"
    cls: type
    capabilities: list[str] = field(default_factory=list)


_REGISTRY: dict[str, PlatformInfo] = {}


def _validate_against_protocol(cls: type, protocol: type) -> None:
    """Validate that *cls* implements all methods required by *protocol*.

    Checks:
    1. ``platform_name`` class attribute exists.
    2. Every public method (plus ``__enter__`` / ``__exit__``) is present.
    3. Implementation parameter count does not exceed protocol's (extra required
       params would break callers).

    Raises ``TypeError`` listing all missing methods.
    """
    missing: list[str] = []

    # Check platform_name attribute
    if not hasattr(cls, "platform_name"):
        missing.append("platform_name (class attribute)")

    # Collect protocol-required methods
    required_methods: list[str] = []
    for name, obj in vars(protocol).items():
        # Skip private attributes except __enter__ and __exit__
        if name.startswith("_") and name not in ("__enter__", "__exit__"):
            continue
        # Skip non-callable (e.g., platform_name annotation, __abstractmethods__)
        if not callable(obj) and not isinstance(obj, (classmethod, staticmethod)):
            # It's an annotation or data descriptor -- handled separately
            continue
        required_methods.append(name)

    # Check each required method exists and has compatible signature
    for method_name in required_methods:
        if not hasattr(cls, method_name):
            missing.append(method_name)
            continue

        # Signature compatibility check: impl must not require MORE params
        try:
            # Use FORWARDREF to avoid resolving TYPE_CHECKING-only annotations
            # (e.g., BrowserContext) which would cause NameError in Python 3.14+.
            _ann_fmt = getattr(inspect, "Format", None)
            _sig_kwargs: dict = {}
            if _ann_fmt is not None:
                _sig_kwargs["annotation_format"] = _ann_fmt.FORWARDREF

            proto_sig = inspect.signature(getattr(protocol, method_name), **_sig_kwargs)
            impl_sig = inspect.signature(getattr(cls, method_name), **_sig_kwargs)

            # Count required parameters (no default) excluding 'self'
            proto_required = sum(
                1
                for p in proto_sig.parameters.values()
                if p.name != "self"
                and p.default is inspect.Parameter.empty
                and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            )
            impl_required = sum(
                1
                for p in impl_sig.parameters.values()
                if p.name != "self"
                and p.default is inspect.Parameter.empty
                and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            )

            if impl_required > proto_required:
                missing.append(
                    f"{method_name} (requires {impl_required} params, "
                    f"protocol allows {proto_required})"
                )
        except (ValueError, TypeError, NameError):
            # Some builtins/descriptors are not introspectable -- skip check.
            # NameError can occur if annotations reference unresolvable names.
            pass

    if missing:
        raise TypeError(
            f"{cls.__name__} is missing required protocol members for "
            f"{protocol.__name__}: {', '.join(missing)}"
        )


def register_platform(
    key: str,
    *,
    name: str | None = None,
    platform_type: str = "browser",
    capabilities: list[str] | None = None,
) -> Any:
    """Decorator that registers a platform adapter class.

    Validates the class against the appropriate Protocol at import time.
    Missing methods cause an immediate ``TypeError``.

    Parameters
    ----------
    key:
        Unique platform identifier (e.g., ``"indeed"``, ``"dice"``).
    name:
        Human-readable name. Defaults to *key* with title case.
    platform_type:
        ``"browser"`` or ``"api"``. Determines which Protocol is validated.
    capabilities:
        Optional list of capability tags (e.g., ``["search", "easy_apply"]``).
    """

    def decorator(cls: type) -> type:
        # Lazy import to avoid circular deps -- decorator runs at platform
        # module import time, before all modules are fully loaded.
        from platforms.protocols import APIPlatform, BrowserPlatform

        if key in _REGISTRY:
            raise ValueError(
                f"Duplicate platform key {key!r}: already registered to "
                f"{_REGISTRY[key].cls.__name__}"
            )

        # Select protocol based on platform type
        if platform_type == "browser":
            protocol = BrowserPlatform
        elif platform_type == "api":
            protocol = APIPlatform
        else:
            raise ValueError(
                f"Unknown platform_type {platform_type!r}. Expected 'browser' or 'api'."
            )

        # Fail-fast validation
        _validate_against_protocol(cls, protocol)

        # Register
        _REGISTRY[key] = PlatformInfo(
            key=key,
            name=name or key.title(),
            platform_type=platform_type,
            cls=cls,
            capabilities=capabilities or [],
        )

        return cls

    return decorator


def get_platform(key: str) -> PlatformInfo:
    """Return ``PlatformInfo`` for the given key.

    Raises ``KeyError`` with a helpful message listing available platforms.
    """
    if key not in _REGISTRY:
        available = ", ".join(sorted(_REGISTRY.keys())) or "(none)"
        raise KeyError(f"Platform {key!r} not registered. Available: {available}")
    return _REGISTRY[key]


def get_all_platforms() -> dict[str, PlatformInfo]:
    """Return a copy of the full platform registry."""
    return dict(_REGISTRY)


def get_platforms_by_type(platform_type: str) -> dict[str, PlatformInfo]:
    """Return platforms filtered by type (``'browser'`` or ``'api'``)."""
    return {k: v for k, v in _REGISTRY.items() if v.platform_type == platform_type}
