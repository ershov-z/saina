from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


logger = logging.getLogger(__name__)


class CalendarClient:
    def __init__(self, *, client_id: str, client_secret: str, refresh_token: str, token_uri: str, scopes: str):
        creds = Credentials(
            None,
            refresh_token=refresh_token,
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes.split(),
        )
        self.service = build("calendar", "v3", credentials=creds, cache_discovery=False)

    def upsert_event(self, calendar_id: str, event_body: Dict[str, Any], event_id: Optional[str] = None) -> str:
        try:
            if event_id:
                updated = self.service.events().update(calendarId=calendar_id, eventId=event_id, body=event_body).execute()
                return updated["id"]
            created = self.service.events().insert(calendarId=calendar_id, body=event_body).execute()
            return created["id"]
        except HttpError as exc:
            logger.error("Failed to upsert event: %s", exc)
            raise

    def delete_event(self, calendar_id: str, event_id: str) -> None:
        try:
            self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        except HttpError as exc:
            logger.error("Failed to delete event: %s", exc)
            raise

