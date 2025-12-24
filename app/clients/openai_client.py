from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from jsonschema import ValidationError
from openai import AsyncOpenAI

from app.action_validation import ActionValidator
from app.models import Action, LLMResponse
from app.prompts import build_sayna_messages


logger = logging.getLogger(__name__)


class OpenAIClient:
    def __init__(self, *, api_key: str, model: str, schema_path: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.validator = ActionValidator(schema_path=schema_path)

    async def generate_actions(self, messages: List[Dict[str, str]]) -> LLMResponse:
        prepared_messages = build_sayna_messages(messages)
        response = await self._call_model(prepared_messages)
        validated = await self._validate_response(response, prepared_messages)
        return validated

    async def _call_model(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        completion = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": self.validator.schema,
            },
        )
        content = completion.choices[0].message.content
        return json.loads(content)

    async def _validate_response(self, payload: Dict[str, Any], messages: List[Dict[str, str]]) -> LLMResponse:
        try:
            self.validator.validate(payload)
        except ValidationError as exc:
            logger.warning("First validation failed: %s", exc)
            retry_messages = messages + [
                {
                    "role": "system",
                    "content": "Исправь actions по схеме action_contract.schema.json и верни только валидный JSON.",
                },
                {"role": "assistant", "content": json.dumps(payload, ensure_ascii=False)},
            ]
            corrected_payload = await self._call_model(retry_messages)
            self.validator.validate(corrected_payload)
            payload = corrected_payload

        actions = [Action(type=item["type"], payload=item["payload"], idempotency_key=item.get("idempotency_key")) for item in payload.get("actions", [])]
        return LLMResponse(
            assistant_text=payload["assistant_text"],
            actions=actions,
            followup_required=payload.get("followup_required", False),
            debug=payload.get("debug"),
        )
