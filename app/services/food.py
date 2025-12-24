from __future__ import annotations

import logging
import uuid
from typing import Dict, Optional

from app.clients.google_sheets import SheetsClient


logger = logging.getLogger(__name__)


class FoodService:
    def __init__(self, sheets: SheetsClient):
        self.sheets = sheets

    def log_food(self, sheet_id: str, payload: Dict[str, any]) -> None:
        row = [
            payload.get("food_id", str(uuid.uuid4())),
            payload["dt"],
            payload.get("text_input", ""),
            payload.get("photo_file_id", ""),
            payload["estimated_kcal"],
            payload["protein_g"],
            payload["fat_g"],
            payload["carbs_g"],
            payload["confidence"],
            str(payload.get("needs_clarification", False)).upper(),
            payload.get("clarification_question", ""),
            str(payload.get("resolved", False)).upper(),
        ]
        self.sheets.append_row(sheet_id, "FoodLog!A:L", row)

