import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class SystemState:
    """In-memory system state with lightweight locking for background tasks."""

    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_poll_dt: Optional[datetime] = None
    last_daily_plan_date: Optional[str] = None
    last_daily_digest_date: Optional[str] = None
    sent_reminders: Dict[str, Any] = field(default_factory=dict)
    pending_confirmations: Dict[str, Any] = field(default_factory=dict)
    self_ping_last_dt: Optional[datetime] = None

    def __post_init__(self) -> None:
        self._lock = asyncio.Lock()

    @property
    def uptime_seconds(self) -> int:
        return int((datetime.now(timezone.utc) - self.start_time).total_seconds())

    def as_health_payload(self) -> Dict[str, Any]:
        return {
            "last_poll_dt": self.last_poll_dt.isoformat() if self.last_poll_dt else None,
            "last_daily_plan_date": self.last_daily_plan_date,
            "last_daily_digest_date": self.last_daily_digest_date,
            "self_ping_last_dt": self.self_ping_last_dt.isoformat() if self.self_ping_last_dt else None,
        }

    async def mark_poll(self, *, last_plan_date: Optional[str] = None, last_digest_date: Optional[str] = None) -> None:
        async with self._lock:
            self.last_poll_dt = datetime.now(timezone.utc)
            if last_plan_date:
                self.last_daily_plan_date = last_plan_date
            if last_digest_date:
                self.last_daily_digest_date = last_digest_date

    async def record_self_ping(self) -> None:
        async with self._lock:
            self.self_ping_last_dt = datetime.now(timezone.utc)

