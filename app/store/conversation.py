from __future__ import annotations

import collections
from typing import Deque, Dict, List, Optional

from app.time_utils import now_local


class ConversationStore:
    """Keeps last N messages per user in memory."""

    def __init__(self, max_messages: int = 15):
        self.max_messages = max_messages
        self._messages: Dict[str, Deque[Dict[str, str]]] = collections.defaultdict(collections.deque)

    def add_message(self, telegram_id: str, role: str, text: str) -> None:
        queue = self._messages[telegram_id]
        queue.append({"role": role, "text": text, "dt": now_local().isoformat()})
        while len(queue) > self.max_messages:
            queue.popleft()

    def get_recent(self, telegram_id: str) -> List[Dict[str, str]]:
        return list(self._messages.get(telegram_id, []))

