"""Distribution strategies with a persistent cursor (T048)."""
from __future__ import annotations

import hashlib
import logging

from src.models import Destination

log = logging.getLogger("forwarder")


class Distributor:
    """Selects target destinations per config (quarantine never selected)."""

    def __init__(self, strategy: str = "round_robin",
                 cursor: int = 0,
                 counters: dict[str, int] | None = None) -> None:
        self.strategy = strategy or "round_robin"
        self.cursor = cursor
        self._counters: dict[str, int] = dict(counters or {})

    def _active(self, destinations: list[Destination]) -> list[Destination]:
        return [d for d in destinations
                if d.enabled and not d.quarantine]

    def select(self, destinations: list[Destination],
               source_id: str = "") -> list[Destination]:
        active = self._active(destinations)
        if not active:
            return []
        if self.strategy == "broadcast":
            return active
        if self.strategy == "source_based":
            digest = hashlib.sha256(source_id.encode()).hexdigest()
            return [active[int(digest, 16) % len(active)]]
        if self.strategy == "balanced":
            pick = min(active,
                       key=lambda d: self._counters.get(d.id, 0))
            self._counters[pick.id] = self._counters.get(pick.id, 0) + 1
            return [pick]
        if self.strategy == "per_destination":
            # هر مقصد قوانین خودش را اعمال می‌کند؛ همه دریافت می‌کنند.
            return active
        if self.strategy != "round_robin":
            log.warning("استراتژی توزیع ناشناس؛ چرخشی استفاده شد.")
        pick = active[self.cursor % len(active)]
        self.cursor += 1
        return [pick]
