from __future__ import annotations

import logging
from typing import Dict

from app.clients.google_sheets import SheetsClient


logger = logging.getLogger(__name__)


class HealthService:
    def __init__(self, sheets: SheetsClient):
        self.sheets = sheets

    def update_daily_totals(self, sheet_id: str, payload: Dict[str, any]) -> None:
        row = [
            payload["date"],
            payload.get("weight_kg", ""),
            payload.get("height_cm", ""),
            payload.get("sleep_hours", ""),
            payload.get("training_minutes", ""),
            payload.get("kcal_total", ""),
            payload.get("protein_g", ""),
            payload.get("fat_g", ""),
            payload.get("carbs_g", ""),
            payload.get("source", "manual"),
            payload.get("health_note", ""),
        ]
        self.sheets.append_row(sheet_id, "Health!A:K", row)

