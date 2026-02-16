"""Protocol definitions for pluggable platform architecture.

Two runtime-checkable Protocol classes define the contracts that platform
adapters must implement:

- **BrowserPlatform** -- for platforms that require Playwright browser automation
  (Indeed, Dice).
- **APIPlatform** -- for platforms that use pure HTTP APIs (RemoteOK).

The orchestrator programs against these protocols, not concrete classes, enabling
new platforms to be added without modifying orchestration code.

Import chain: models -> protocols -> registry (no cycles).
"""

from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from core.models import Job, SearchQuery

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext


@runtime_checkable
class BrowserPlatform(Protocol):
    """Contract for browser-automated job platforms (Indeed, Dice).

    Implementations receive a Playwright ``BrowserContext`` via ``init()``,
    handle login/session management, search, detail enrichment, and
    application submission with human-in-the-loop confirmation.
    """

    platform_name: str

    def init(self, context: BrowserContext) -> None:
        """Receive Playwright BrowserContext from orchestrator."""
        ...

    def login(self) -> bool:
        """Authenticate. Return True if fresh login performed."""
        ...

    def is_logged_in(self) -> bool:
        """Check whether an active session exists."""
        ...

    def search(self, query: SearchQuery) -> list[Job]:
        """Search and return scored Job models."""
        ...

    def get_job_details(self, job: Job) -> Job:
        """Enrich a Job with full description and metadata."""
        ...

    def apply(self, job: Job, resume_path: Path | None = None) -> bool:
        """Submit application with human confirmation before final submit."""
        ...

    def __enter__(self) -> BrowserPlatform:
        """Context manager entry."""
        ...

    def __exit__(
        self, exc_type: type | None, exc_val: BaseException | None, exc_tb: object
    ) -> None:
        """Context manager exit -- cleanup resources."""
        ...


@runtime_checkable
class APIPlatform(Protocol):
    """Contract for HTTP API-based job platforms (RemoteOK).

    API platforms do not require browser automation or login management.
    They initialize an HTTP client via ``init()`` and interact through
    pure HTTP requests.
    """

    platform_name: str

    def init(self) -> None:
        """Initialize HTTP client (no BrowserContext needed)."""
        ...

    def search(self, query: SearchQuery) -> list[Job]:
        """Search and return scored Job models."""
        ...

    def get_job_details(self, job: Job) -> Job:
        """Enrich a Job with full description and metadata."""
        ...

    def apply(self, job: Job, resume_path: Path | None = None) -> bool:
        """Submit application (typically redirects to external ATS)."""
        ...

    def __enter__(self) -> APIPlatform:
        """Context manager entry."""
        ...

    def __exit__(
        self, exc_type: type | None, exc_val: BaseException | None, exc_tb: object
    ) -> None:
        """Context manager exit -- cleanup resources."""
        ...
