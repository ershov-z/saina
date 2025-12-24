from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List


logger = logging.getLogger(__name__)

PROMPT_ENV_VAR = "SAYNA_SYSTEM_PROMPT_PATH"
DEFAULT_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "sayna_system.txt"


@lru_cache(maxsize=1)
def load_sayna_system_prompt() -> str:
    """Load the Sayna system prompt from disk with caching."""

    override_path = os.getenv(PROMPT_ENV_VAR)
    prompt_path = Path(override_path) if override_path else DEFAULT_PROMPT_PATH

    if not prompt_path.is_absolute():
        prompt_path = (Path(__file__).resolve().parent.parent / prompt_path).resolve()

    if not prompt_path.exists():
        raise FileNotFoundError(f"Sayna system prompt not found at {prompt_path}")

    text = prompt_path.read_text(encoding="utf-8").strip()
    logger.info("Loaded Sayna system prompt: %s chars", len(text))
    return text


def with_sayna_system_prompt(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Ensure the system prompt is the first message and cannot be overridden."""

    prompt = load_sayna_system_prompt()
    rest = [m for m in messages if m.get("role") != "system"]
    return [{"role": "system", "content": prompt}] + rest

