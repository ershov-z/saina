from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

DEFAULT_TZ_NAME = "Asia/Yekaterinburg"


def get_tz(tz_name: str = DEFAULT_TZ_NAME) -> ZoneInfo:
    return ZoneInfo(tz_name)


def now_local(tz_name: str = DEFAULT_TZ_NAME) -> datetime:
    return datetime.now(get_tz(tz_name))


def parse_dt(dt_str: str, tz_name: str = DEFAULT_TZ_NAME) -> datetime:
    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=get_tz(tz_name))


def format_dt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M")
