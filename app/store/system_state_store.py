from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from app.clients.google_sheets import SheetsClient
from app.state import SystemState


class SystemStateStore:
    def __init__(self, sheets: SheetsClient, sheet_id: str):
        self.sheets = sheets
        self.sheet_id = sheet_id

    def load(self, state: SystemState) -> None:
        kv = self.sheets.read_key_value(self.sheet_id, "SystemState")
        if "last_poll_dt" in kv and kv["last_poll_dt"]:
            try:
                state.last_poll_dt = datetime.fromisoformat(kv["last_poll_dt"])
            except Exception:
                state.last_poll_dt = None
        if "last_daily_plan_date" in kv:
            state.last_daily_plan_date = kv["last_daily_plan_date"] or None
        if "last_daily_digest_date" in kv:
            state.last_daily_digest_date = kv["last_daily_digest_date"] or None
        if "self_ping_last_dt" in kv and kv["self_ping_last_dt"]:
            try:
                state.self_ping_last_dt = datetime.fromisoformat(kv["self_ping_last_dt"])
            except Exception:
                state.self_ping_last_dt = None

    def save(self, state: SystemState) -> None:
        payload = {
            "last_poll_dt": "" if state.last_poll_dt is None else state.last_poll_dt.isoformat(),
            "last_daily_plan_date": state.last_daily_plan_date or "",
            "last_daily_digest_date": state.last_daily_digest_date or "",
            "self_ping_last_dt": "" if state.self_ping_last_dt is None else state.self_ping_last_dt.isoformat(),
        }
        for key, value in payload.items():
            self.sheets.upsert_key_value(self.sheet_id, "SystemState", key, value)
