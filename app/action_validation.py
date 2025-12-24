from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from jsonschema import Draft202012Validator


class ActionValidator:
    def __init__(self, schema_path: str) -> None:
        path = Path(schema_path)
        with path.open("r", encoding="utf-8") as f:
            self.schema: Dict[str, Any] = json.load(f)
        self._validator = Draft202012Validator(self.schema)

    def validate(self, payload: Dict[str, Any]) -> None:
        self._validator.validate(payload)

