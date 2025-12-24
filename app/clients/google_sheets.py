from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


logger = logging.getLogger(__name__)


class SheetsClient:
    def __init__(self, *, client_id: str, client_secret: str, refresh_token: str, token_uri: str, scopes: str):
        creds = Credentials(
            None,
            refresh_token=refresh_token,
            token_uri=token_uri,
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes.split(),
        )
        self.service = build("sheets", "v4", credentials=creds, cache_discovery=False)

    def read_range(self, spreadsheet_id: str, range_name: str) -> List[List[Any]]:
        try:
            result = self.service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
            return result.get("values", [])
        except HttpError as exc:
            logger.error("Failed to read range %s: %s", range_name, exc)
            raise

    def append_row(self, spreadsheet_id: str, range_name: str, row: List[Any]) -> None:
        try:
            self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body={"values": [row]},
            ).execute()
        except HttpError as exc:
            logger.error("Failed to append row to %s: %s", range_name, exc)
            raise

    def update_rows(self, spreadsheet_id: str, range_name: str, values: List[List[Any]]) -> None:
        try:
            self.service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body={"values": values},
            ).execute()
        except HttpError as exc:
            logger.error("Failed to update rows in %s: %s", range_name, exc)
            raise

    def upsert_key_value(self, spreadsheet_id: str, sheet_name: str, key: str, value: str) -> None:
        rows = self.read_range(spreadsheet_id, f"{sheet_name}!A:B")
        found_index: Optional[int] = None
        for idx, row in enumerate(rows):
            if row and row[0] == key:
                found_index = idx
                break

        if found_index is None:
            self.append_row(spreadsheet_id, f"{sheet_name}!A:B", [key, value])
        else:
            rows[found_index] = [key, value]
            self.update_rows(spreadsheet_id, f"{sheet_name}!A:B", rows)

    def read_key_value(self, spreadsheet_id: str, sheet_name: str) -> Dict[str, str]:
        kv_rows = self.read_range(spreadsheet_id, f"{sheet_name}!A:B")
        return {row[0]: row[1] if len(row) > 1 else "" for row in kv_rows if row}

