from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class TelegramClient:
    def __init__(self, bot_token: str) -> None:
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.client = httpx.AsyncClient(timeout=15)

    async def send_message(self, chat_id: str, text: str, reply_markup: Optional[Dict[str, Any]] = None) -> None:
        if not self.bot_token:
            logger.warning("Telegram token missing, skipping send_message")
            return
        payload: Dict[str, Any] = {"chat_id": chat_id, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            response = await self.client.post(f"{self.base_url}/sendMessage", json=payload)
            response.raise_for_status()
        except Exception as exc:
            logger.error("Failed to send Telegram message: %s", exc)

    async def answer_callback(self, callback_query_id: str, text: str = "") -> None:
        if not self.bot_token:
            return
        try:
            await self.client.post(f"{self.base_url}/answerCallbackQuery", json={"callback_query_id": callback_query_id, "text": text})
        except Exception as exc:
            logger.error("Failed to answer callback: %s", exc)

