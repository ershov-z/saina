from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.clients.google_calendar import CalendarClient
from app.clients.google_sheets import SheetsClient
from app.models import ScheduleEvent, UserProfile
from app.time_utils import format_dt, parse_dt


logger = logging.getLogger(__name__)


SCHEDULE_HEADER = [
    "event_id",
    "title",
    "type",
    "start_dt",
    "end_dt",
    "is_recurring",
    "rrule",
    "priority",
    "flexibility",
    "buffer_before_min",
    "buffer_after_min",
    "status",
    "created_by",
    "notes",
    "gcal_event_id",
    "recurrence_id",
]


class ScheduleService:
    def __init__(self, sheets: SheetsClient, calendar: CalendarClient):
        self.sheets = sheets
        self.calendar = calendar

    def _range(self, sheet_name: str = "Schedule") -> str:
        return f"{sheet_name}!A:P"

    def read_events(self, user: UserProfile, *, range_name: str = "Schedule") -> List[ScheduleEvent]:
        rows = self.sheets.read_range(user.sheet_id or "", f"{range_name}!A:P")
        if not rows:
            return []
        header = rows[0]
        events: List[ScheduleEvent] = []
        for row in rows[1:]:
            if len(row) < len(SCHEDULE_HEADER):
                continue
            data = dict(zip(header, row))
            events.append(
                ScheduleEvent(
                    event_id=data["event_id"],
                    title=data["title"],
                    type=data["type"],
                    start_dt=parse_dt(data["start_dt"]),
                    end_dt=parse_dt(data["end_dt"]),
                    is_recurring=data.get("is_recurring", "FALSE") in ("TRUE", "true", True),
                    rrule=data.get("rrule") or None,
                    priority=int(data.get("priority") or 1),
                    flexibility=int(data.get("flexibility") or 2),
                    buffer_before_min=int(data.get("buffer_before_min") or 10),
                    buffer_after_min=int(data.get("buffer_after_min") or 10),
                    status=data.get("status", "planned"),
                    created_by=data.get("created_by", "bot"),
                    notes=data.get("notes") or None,
                    gcal_event_id=data.get("gcal_event_id") or None,
                    recurrence_id=data.get("recurrence_id") or None,
                )
            )
        return events

    def create_event(self, user: UserProfile, payload: Dict[str, Any]) -> ScheduleEvent:
        event_id = str(uuid.uuid4())
        recurrence_id = str(uuid.uuid4()) if payload.get("is_recurring") else ""
        row = [
            event_id,
            payload["title"],
            payload["type"],
            payload["start_dt"],
            payload["end_dt"],
            str(payload.get("is_recurring", False)).upper(),
            payload.get("rrule", ""),
            payload.get("priority", 5),
            payload.get("flexibility", 2),
            payload.get("buffer_before_min", 10),
            payload.get("buffer_after_min", 10),
            "planned",
            payload.get("created_by", "bot"),
            payload.get("notes", ""),
            "",
            recurrence_id,
        ]
        self.sheets.append_row(user.sheet_id or "", self._range(), row)
        return ScheduleEvent(
            event_id=event_id,
            title=payload["title"],
            type=payload["type"],
            start_dt=parse_dt(payload["start_dt"]),
            end_dt=parse_dt(payload["end_dt"]),
            is_recurring=bool(payload.get("is_recurring", False)),
            rrule=payload.get("rrule"),
            priority=int(payload.get("priority", 5)),
            flexibility=int(payload.get("flexibility", 2)),
            buffer_before_min=int(payload.get("buffer_before_min", 10)),
            buffer_after_min=int(payload.get("buffer_after_min", 10)),
            status="planned",
            created_by=payload.get("created_by", "bot"),
            notes=payload.get("notes"),
            gcal_event_id=None,
            recurrence_id=recurrence_id or None,
        )

    def update_event(self, user: UserProfile, event_id: str, patch: Dict[str, Any]) -> None:
        rows = self.sheets.read_range(user.sheet_id or "", self._range())
        if not rows:
            return
        header = rows[0]
        for idx, row in enumerate(rows[1:], start=2):
            if row and row[0] == event_id:
                row_data = dict(zip(header, row))
                row_data.update({k: v for k, v in patch.items() if v is not None})
                updated_row = [row_data.get(col, "") for col in header]
                rows[idx - 1] = updated_row
                self.sheets.update_rows(user.sheet_id or "", self._range(), rows)
                return
        logger.warning("Event %s not found for user %s", event_id, user.telegram_id)

    def move_event(self, user: UserProfile, event_id: str, new_start_dt: str, new_end_dt: str) -> None:
        self.update_event(user, event_id, {"start_dt": new_start_dt, "end_dt": new_end_dt, "status": "moved"})

    def cancel_event(self, user: UserProfile, event_id: str) -> None:
        self.update_event(user, event_id, {"status": "cancelled"})

    def log_completion(self, user: UserProfile, event_id: str, confirm_status: str, dt: datetime, extend_min: Optional[int] = None, comment: Optional[str] = None) -> None:
        row = [
            str(uuid.uuid4()),
            event_id,
            format_dt(dt),
            confirm_status,
            extend_min or "",
            comment or "",
        ]
        self.sheets.append_row(user.sheet_id or "", "TaskLog!A:F", row)

    def sync_calendar(self, user: UserProfile, event: ScheduleEvent, mode: str = "upsert") -> Optional[str]:
        if not user.calendar_id:
            return None
        if mode == "delete" and event.gcal_event_id:
            self.calendar.delete_event(user.calendar_id, event.gcal_event_id)
            return None
        event_body = {
            "summary": event.title,
            "description": event.notes or "",
            "start": {"dateTime": event.start_dt.isoformat(), "timeZone": event.start_dt.tzinfo.key if event.start_dt.tzinfo else "UTC"},
            "end": {"dateTime": event.end_dt.isoformat(), "timeZone": event.end_dt.tzinfo.key if event.end_dt.tzinfo else "UTC"},
        }
        if event.is_recurring and event.rrule:
            event_body["recurrence"] = [event.rrule]
        event_id = self.calendar.upsert_event(user.calendar_id, event_body, event.gcal_event_id)
        self.update_event(user, event.event_id, {"gcal_event_id": event_id})
        return event_id

