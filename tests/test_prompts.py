from pathlib import Path

from app.prompts import load_sayna_system_prompt, with_sayna_system_prompt


def test_loads_system_prompt_contains_file_content():
    prompt_text = load_sayna_system_prompt()
    file_text = (Path(__file__).resolve().parent.parent / "prompts" / "sayna_system.txt").read_text(encoding="utf-8").strip()
    assert prompt_text == file_text


def test_system_prompt_is_first_message():
    messages = [{"role": "user", "content": "привет"}, {"role": "assistant", "content": "ok"}]
    prepared = with_sayna_system_prompt(messages)
    assert prepared[0]["role"] == "system"
    file_text = load_sayna_system_prompt()
    assert prepared[0]["content"] == file_text
    # ensure history preserved after system
    assert prepared[1:] == [m for m in messages if m["role"] != "system"]
