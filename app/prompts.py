from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, List


logger = logging.getLogger(__name__)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SAYNA_PROMPT_PATH = PROJECT_ROOT / "prompts" / "sayna_system.txt"


def _resolve_prompt_path() -> Path:
    env_path = os.getenv("SAYNA_SYSTEM_PROMPT_PATH")
    if env_path:
        return Path(env_path).expanduser()
    return DEFAULT_SAYNA_PROMPT_PATH


@lru_cache(maxsize=1)
def load_sayna_system_prompt() -> str:
    path = _resolve_prompt_path()
    if not path.is_file():
        raise FileNotFoundError(f"Sayna system prompt file not found at {path}")

    prompt = path.read_text(encoding="utf-8")
    logger.info("Loaded Sayna system prompt: %d chars", len(prompt))
    return prompt


def build_sayna_messages(messages: List[Dict[str, str]], system_prompt: str | None = None) -> List[Dict[str, str]]:
    """Ensure Sayna system prompt is the first message and deduplicate system role.

    Any incoming system-level messages are removed to avoid accidental override.
    """

    prompt = system_prompt if system_prompt is not None else load_sayna_system_prompt()
    sanitized = [msg for msg in messages if msg.get("role") != "system"]
    return [{"role": "system", "content": prompt}, *sanitized]
