"""Clock port — wraps ``datetime.now`` for deterministic tests."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone

__all__ = ["Clock", "SystemClock"]


class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime:
        """Return the current instant in UTC."""


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(timezone.utc)
