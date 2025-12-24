from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.orchestrator import Orchestrator
from app.store.conversation import ConversationStore

logger = logging.getLogger(__name__)


class TelegramRouter:
    def __init__(self, orchestrator: Orchestrator, conversations: ConversationStore):
        self.orchestrator = orchestrator
        self.conversations = conversations

    async def handle_update(self, update: Dict[str, Any]) -> Dict[str, Any]:
        message = update.get("message") or update.get("edited_message")
        callback = update.get("callback_query")

        if message:
            chat_id = str(message["chat"]["id"])
            text = message.get("text", "")
            self.conversations.add_message(chat_id, "user", text)
            await self.orchestrator.process_text_message(chat_id, text)
        elif callback:
            chat_id = str(callback["from"]["id"])
            data = callback.get("data", "")
            await self.orchestrator.process_callback(chat_id, data, callback.get("id"))
        else:
            logger.debug("Unsupported update received")

        return {"ok": True}

