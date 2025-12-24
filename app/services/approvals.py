from __future__ import annotations

import logging
from typing import Dict

from app.clients.telegram import TelegramClient
from app.models import UserProfile

logger = logging.getLogger(__name__)


class ApprovalService:
    def __init__(self, telegram: TelegramClient):
        self.telegram = telegram
        self.pending: Dict[str, Dict] = {}

    async def send_request(self, requester: UserProfile, target: UserProfile, message: str, priority: int, context_key: str) -> None:
        keyboard = {"inline_keyboard": [[{"text": "Принять", "callback_data": f"approval:{context_key}:yes"}, {"text": "Отклонить", "callback_data": f"approval:{context_key}:no"}]]}
        await self.telegram.send_message(target.telegram_id, f"Запрос от {requester.display_name or requester.telegram_id} (приоритет {priority}): {message}", reply_markup=keyboard)
        self.pending[context_key] = {
            "requester": requester.telegram_id,
            "target": target.telegram_id,
            "message": message,
            "priority": priority,
        }

    def resolve(self, context_key: str) -> None:
        if context_key in self.pending:
            del self.pending[context_key]

