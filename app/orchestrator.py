from __future__ import annotations

import json
import logging
import uuid
from typing import Dict, List

from app.clients.openai_client import OpenAIClient
from app.clients.telegram import TelegramClient
from app.config import Config
from app.models import Action, LLMResponse, UserProfile
from app.services.approvals import ApprovalService
from app.services.food import FoodService
from app.services.health import HealthService
from app.services.schedule import ScheduleService
from app.store.conversation import ConversationStore
from app.time_utils import format_dt, now_local
from app.prompts import build_sayna_messages


logger = logging.getLogger(__name__)


class Orchestrator:
    def __init__(
        self,
        config: Config,
        openai_client: OpenAIClient,
        telegram: TelegramClient,
        schedule_service: ScheduleService,
        food_service: FoodService,
        health_service: HealthService,
        approvals: ApprovalService,
        conversations: ConversationStore,
    ):
        self.config = config
        self.openai_client = openai_client
        self.telegram = telegram
        self.schedule_service = schedule_service
        self.food_service = food_service
        self.health_service = health_service
        self.approvals = approvals
        self.conversations = conversations
        self.user_profiles = self._build_profiles()

    def _build_profiles(self) -> Dict[str, UserProfile]:
        profiles: Dict[str, UserProfile] = {}
        for key, display in (("zakhar", "Захар"), ("sofa", "Софа"), ("katya", "Катя")):
            tg_id = self.config.telegram_ids.get(key, "")
            if not tg_id:
                continue
            profiles[tg_id] = UserProfile(
                telegram_id=tg_id,
                display_name=display,
                sheet_id=self.config.sheet_ids.get(key),
                calendar_id=self.config.gcal_ids.get(key),
            )
        return profiles

    def _profile(self, telegram_id: str) -> UserProfile:
        profile = self.user_profiles.get(telegram_id)
        if not profile:
            profile = UserProfile(telegram_id=telegram_id, display_name=telegram_id)
        return profile

    async def process_text_message(self, telegram_id: str, text: str) -> None:
        profile = self._profile(telegram_id)
        base_messages = [{"role": "user", "content": text}]

        # Attach recent context
        recent = self.conversations.get_recent(telegram_id)
        for msg in recent:
            base_messages.append({"role": msg["role"], "content": msg["text"]})

        messages = build_sayna_messages(base_messages)
        llm_response = await self.openai_client.generate_actions(messages)
        self.conversations.add_message(telegram_id, "assistant", llm_response.assistant_text)
        await self.telegram.send_message(telegram_id, llm_response.assistant_text)
        await self._execute_actions(profile, llm_response)

    async def process_callback(self, telegram_id: str, data: str, callback_id: str | None) -> None:
        if data.startswith("confirm:"):
            parts = data.split(":")
            if len(parts) >= 3:
                event_id = parts[1]
                action = parts[2]
                extra = parts[3] if len(parts) > 3 else None
                await self._handle_confirmation(telegram_id, event_id, action, extra)
        elif data.startswith("approval:"):
            _, context_key, decision = data.split(":")
            await self._handle_approval(telegram_id, context_key, decision)
        if callback_id:
            await self.telegram.answer_callback(callback_id)

    async def _handle_confirmation(self, telegram_id: str, event_id: str, action: str, extra: str | None) -> None:
        profile = self._profile(telegram_id)
        confirm_status = "done" if action == "done" else "not_done"
        if action.startswith("extend"):
            minutes = int(extra or "10")
            confirm_status = "extended"
            await self.schedule_service.log_completion(profile, event_id, confirm_status, now_local(self.config.timezone_name), int(minutes), comment="Продлено")
        else:
            await self.schedule_service.log_completion(profile, event_id, confirm_status, now_local(self.config.timezone_name))
        await self.telegram.send_message(telegram_id, "Спасибо! Обновила событие.")

    async def _handle_approval(self, telegram_id: str, context_key: str, decision: str) -> None:
        self.approvals.resolve(context_key)
        await self.telegram.send_message(telegram_id, "Ответ сохранён.")

    async def _execute_actions(self, profile: UserProfile, response: LLMResponse) -> None:
        for action in response.actions:
            await self._execute_action(profile, action)

    async def _execute_action(self, profile: UserProfile, action: Action) -> None:
        if action.type == "create_event":
            event = self.schedule_service.create_event(profile, action.payload)
            if profile.calendar_id:
                self.schedule_service.sync_calendar(profile, event, "upsert")
        elif action.type == "create_recurring_series":
            payload = dict(action.payload)
            payload["is_recurring"] = True
            event = self.schedule_service.create_event(profile, payload)
            if profile.calendar_id:
                self.schedule_service.sync_calendar(profile, event, "upsert")
        elif action.type == "update_event":
            self.schedule_service.update_event(profile, action.payload["event_id"], action.payload["patch"])
        elif action.type == "move_event":
            self.schedule_service.move_event(profile, action.payload["event_id"], action.payload["new_start_dt"], action.payload["new_end_dt"])
        elif action.type == "cancel_event":
            self.schedule_service.cancel_event(profile, action.payload["event_id"])
        elif action.type == "cancel_recurring_series":
            recurrence_id = action.payload["recurrence_id"]
            events = self.schedule_service.read_events(profile)
            for ev in events:
                if ev.recurrence_id == recurrence_id:
                    self.schedule_service.cancel_event(profile, ev.event_id)
        elif action.type == "cancel_recurring_occurrence":
            recurrence_id = action.payload["recurrence_id"]
            occurrence_date = action.payload["occurrence_date"]
            events = self.schedule_service.read_events(profile)
            for ev in events:
                if ev.recurrence_id == recurrence_id and ev.start_dt.strftime("%Y-%m-%d") == occurrence_date:
                    self.schedule_service.cancel_event(profile, ev.event_id)
        elif action.type == "sync_calendar_event":
            events = self.schedule_service.read_events(profile)
            for ev in events:
                if ev.event_id == action.payload["event_id"]:
                    mode = action.payload.get("mode", "upsert")
                    self.schedule_service.sync_calendar(profile, ev, mode)
        elif action.type == "log_food":
            self.food_service.log_food(profile.sheet_id or "", action.payload)
        elif action.type == "update_health_daily_totals":
            self.health_service.update_daily_totals(profile.sheet_id or "", action.payload)
        elif action.type == "ask_user_confirmation":
            options = action.payload.get("options", [])
            keyboard = {"inline_keyboard": [[{"text": opt, "callback_data": f"confirm_option:{action.payload['context_key']}:{opt}"}] for opt in options]}
            await self.telegram.send_message(profile.telegram_id, action.payload["question"], reply_markup=keyboard)
        elif action.type == "send_approval_request":
            requester = self._profile(action.payload["requester"]["telegram_id"])
            target = self._profile(action.payload["target_user"]["telegram_id"])
            await self.approvals.send_request(
                requester,
                target,
                action.payload["message"],
                action.payload["request_priority"],
                action.payload.get("context_key", str(uuid.uuid4())),
            )
        elif action.type == "mark_event_completion":
            extend_min = action.payload.get("extend_min")
            comment = action.payload.get("comment")
            self.schedule_service.log_completion(
                profile,
                action.payload["event_id"],
                action.payload["confirm_status"],
                now_local(self.config.timezone_name),
                extend_min,
                comment,
            )
        elif action.type == "propose_time_options":
            options = action.payload["options"]
            lines = [f"{idx+1}) {opt.get('label', '')} {opt['start_dt']}–{opt['end_dt']}" for idx, opt in enumerate(options)]
            await self.telegram.send_message(profile.telegram_id, "\n".join(lines))
        elif action.type == "set_memory_key":
            # For MVP, store memory in Sheets Memory tab
            self.schedule_service.sheets.upsert_key_value(profile.sheet_id or "", "Memory", action.payload["key"], action.payload["value"])
        elif action.type == "read_schedule":
            events = self.schedule_service.read_events(profile)
            await self.telegram.send_message(profile.telegram_id, f"Нашла {len(events)} событий в календаре.")
        else:
            logger.warning("Unsupported action %s", action.type)
