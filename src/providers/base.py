"""Provider interfaces and error taxonomy (T013)."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional, Protocol, runtime_checkable

from src.models import Destination, ExtractedConfig, Post, SourceChannel, TestResult


class SourceFetchError(Exception):
    """Fetch failed; `retryable` decides whether fallback/retry applies."""

    def __init__(self, source_id: str, message: str,
                 retryable: bool = True) -> None:
        super().__init__(message)
        self.source_id = source_id
        self.retryable = retryable


class SourceAccessError(SourceFetchError):
    """Source cannot be accessed at all (invalid/private without access)."""

    def __init__(self, source_id: str, message: str) -> None:
        super().__init__(source_id, message, retryable=False)


@dataclass
class SendResult:
    ok: bool
    message_id: Optional[str] = None
    error_class: Optional[str] = None  # "retryable" | "permanent" | None


async def run_with_retry(operation: Callable[[], Awaitable[SendResult]],
                         max_attempts: int = 3,
                         backoff_s: tuple = (1, 2, 4),
                         sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
                         ) -> SendResult:
    """Retry a send-like operation per FR-033 (T054).

    Retries only `retryable` failures; permanent failures return at once.
    """
    last: SendResult = SendResult(ok=False, error_class="retryable")
    for attempt in range(max_attempts):
        last = await operation()
        if last.ok or last.error_class != "retryable":
            return last
        if attempt < max_attempts - 1:
            await sleep(backoff_s[min(attempt, len(backoff_s) - 1)])
    return last


@runtime_checkable
class SourceProvider(Protocol):
    name: str

    async def fetch_new_posts(self, source: SourceChannel,
                              since_id: int) -> list[Post]:
        """Return posts with id greater than since_id, ascending."""
        ...


@runtime_checkable
class DestinationSender(Protocol):
    name: str

    async def send(self, destination: Destination,
                   body: str) -> SendResult:
        """Send a ready-formatted message body to the destination."""
        ...


@runtime_checkable
class ConfigTester(Protocol):
    async def test(self, config: ExtractedConfig) -> TestResult:
        """Test one unique config; result is shared across destinations."""
        ...
