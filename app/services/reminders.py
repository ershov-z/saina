from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from app.clients.telegram import TelegramClient
from app.services.schedule import ScheduleService
from app.state import SystemState
from app.time_utils import format_dt, get_tz

logger = logging.getLogger(__name__)


class ReminderService:
    def __init__(self, schedule_service: ScheduleService, telegram: TelegramClient, buffer_minutes: int = 10, reminder_minutes: int = 5):
        self.schedule_service = schedule_service
        self.telegram = telegram
        self.buffer_minutes = buffer_minutes
        self.reminder_minutes = reminder_minutes

    async def send_pre_event_reminders(self, user_profile, tz_name: str, state: SystemState) -> None:
        events = self.schedule_service.read_events(user_profile)
        now = datetime.now(get_tz(tz_name))
        for event in events:
            if event.status != "planned":
                continue
            reminder_time = event.start_dt - timedelta(minutes=self.reminder_minutes)
            if reminder_time <= now <= event.start_dt:
                if state.sent_reminders.get(event.event_id):
                    continue
                await self.telegram.send_message(user_profile.telegram_id, f"Напоминание: в {event.start_dt.strftime('%H:%M')} — {event.title}")
                state.sent_reminders[event.event_id] = datetime.now(timezone.utc).isoformat()

    async def send_confirmation_pings(self, user_profile, tz_name: str, state: SystemState, interval_min: int, max_pings: int, window_min: int) -> None:
        events = self.schedule_service.read_events(user_profile)
        now = datetime.now(get_tz(tz_name))
        window_limit = timedelta(minutes=window_min)
        for event in events:
            if event.status not in ("planned", "moved"):
                continue
            if now < event.end_dt + timedelta(minutes=1):
                continue
            elapsed = now - event.end_dt
            if elapsed > window_limit:
                continue
            pending = state.pending_confirmations.get(event.event_id, {"count": 0})
            if pending["count"] >= max_pings:
                continue
            last_ts = pending.get("last_ts")
            if last_ts and now - datetime.fromisoformat(last_ts) < timedelta(minutes=interval_min):
                continue
            keyboard = {"inline_keyboard": [[{"text": "Сделал", "callback_data": f"confirm:{event.event_id}:done"}], [{"text": "Не сделал", "callback_data": f"confirm:{event.event_id}:not_done"}], [{"text": "Продлить на 10 минут", "callback_data": f"confirm:{event.event_id}:extend:10"}]]}
            await self.telegram.send_message(
                user_profile.telegram_id,
                f"Как прошло «{event.title}»? Ответь, пожалуйста.",
                reply_markup=keyboard,
            )
            state.pending_confirmations[event.event_id] = {
                "count": pending["count"] + 1,
                "last_ts": now.isoformat(),
            }

