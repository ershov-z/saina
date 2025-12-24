from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import prompts


class SaynaPromptTests(unittest.TestCase):
    def setUp(self) -> None:
        prompts.load_sayna_system_prompt.cache_clear()

    def tearDown(self) -> None:
        prompts.load_sayna_system_prompt.cache_clear()

    def test_load_sayna_system_prompt_uses_env_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            prompt_path = os.path.join(tmp_dir, "sayna.txt")
            expected = "Test Sayna prompt content"
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write(expected)

            with mock.patch.dict(os.environ, {"SAYNA_SYSTEM_PROMPT_PATH": prompt_path}):
                content = prompts.load_sayna_system_prompt()

        self.assertEqual(expected, content)

    def test_build_sayna_messages_injects_system_first(self) -> None:
        base_messages = [
            {"role": "system", "content": "user override"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        custom_prompt = "Sayna root prompt"
        result = prompts.build_sayna_messages(base_messages, system_prompt=custom_prompt)

        self.assertEqual("system", result[0]["role"])
        self.assertEqual(custom_prompt, result[0]["content"])
        roles = [msg["role"] for msg in result]
        self.assertEqual(1, roles.count("system"))


if __name__ == "__main__":
    unittest.main()
