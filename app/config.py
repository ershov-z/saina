import os
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class Config:
    service_name: str = "family-assistant-bot"
    base_url: str = ""
    healthcheck_path: str = "/health"

    telegram_bot_token: str = ""
    telegram_webhook_path: str = "/tg/webhook"

    openai_api_key: str = ""
    openai_model: str = ""

    google_client_id: str = ""
    google_client_secret: str = ""
    google_refresh_token: str = ""
    google_token_uri: str = ""
    google_scopes: str = ""

    sheet_ids: Dict[str, str] = field(default_factory=dict)
    gcal_ids: Dict[str, str] = field(default_factory=dict)
    telegram_ids: Dict[str, str] = field(default_factory=dict)

    poll_interval_seconds: int = 60
    confirm_ping_interval_min: int = 10
    confirm_max_pings: int = 6
    confirm_window_min: int = 120

    self_ping_enabled: bool = False
    self_ping_interval_min: int = 12

    timezone_name: str = "Asia/Yekaterinburg"


def load_config() -> Config:
    """Read configuration from environment variables."""

    sheet_ids = {
        "zakhar": os.getenv("SHEET_ID_ZAKHAR", ""),
        "sofa": os.getenv("SHEET_ID_SOFA", ""),
        "katya": os.getenv("SHEET_ID_KATYA", ""),
    }

    gcal_ids = {
        "zakhar": os.getenv("GCAL_ID_ZAKHAR", ""),
        "sofa": os.getenv("GCAL_ID_SOFA", ""),
        "katya": os.getenv("GCAL_ID_KATYA", ""),
    }

    telegram_ids = {
        "zakhar": os.getenv("TG_ID_ZAKHAR", ""),
        "sofa": os.getenv("TG_ID_SOFA", ""),
        "katya": os.getenv("TG_ID_KATYA", ""),
    }

    return Config(
        service_name=os.getenv("SERVICE_NAME", "family-assistant-bot"),
        base_url=os.getenv("BASE_URL", ""),
        healthcheck_path=os.getenv("HEALTHCHECK_PATH", "/health"),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_webhook_path=os.getenv("TELEGRAM_WEBHOOK_PATH", "/tg/webhook"),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        openai_model=os.getenv("OPENAI_MODEL", ""),
        google_client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
        google_client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
        google_refresh_token=os.getenv("GOOGLE_REFRESH_TOKEN", ""),
        google_token_uri=os.getenv("GOOGLE_TOKEN_URI", ""),
        google_scopes=os.getenv("GOOGLE_SCOPES", ""),
        sheet_ids=sheet_ids,
        gcal_ids=gcal_ids,
        telegram_ids=telegram_ids,
        poll_interval_seconds=int(os.getenv("POLL_INTERVAL_SECONDS", "60")),
        confirm_ping_interval_min=int(os.getenv("CONFIRM_PING_INTERVAL_MIN", "10")),
        confirm_max_pings=int(os.getenv("CONFIRM_MAX_PINGS", "6")),
        confirm_window_min=int(os.getenv("CONFIRM_WINDOW_MIN", "120")),
        self_ping_enabled=os.getenv("SELF_PING_ENABLED", "false").lower() == "true",
        self_ping_interval_min=int(os.getenv("SELF_PING_INTERVAL_MIN", "12")),
        timezone_name=os.getenv("TZ", "Asia/Yekaterinburg"),
    )

