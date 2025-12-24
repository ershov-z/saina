import asyncio
import logging
import random
from datetime import datetime, timezone

import httpx

from app.config import Config
from app.services.reminders import ReminderService
from app.state import SystemState


logger = logging.getLogger(__name__)


async def self_ping_loop(config: Config, state: SystemState) -> None:
    """
    Periodically pings the healthcheck endpoint to keep the Render service warm.
    The delay is randomized within ±2 minutes around the configured interval (default 10–14 minutes).
    """

    if not config.base_url:
        logger.warning("BASE_URL not set, self-ping disabled")
        return

    url = f"{config.base_url}{config.healthcheck_path}"
    logger.info("Self-ping enabled, target: %s", url)

    async with httpx.AsyncClient(timeout=10) as client:
        while True:
            base_delay = config.self_ping_interval_min
            randomized_minutes = max(1, base_delay + random.randint(-2, 2))
            await asyncio.sleep(randomized_minutes * 60)

            try:
                response = await client.get(url)
                logger.info("Self-ping status=%s", response.status_code)
                await state.record_self_ping()
            except Exception as exc:
                logger.warning("Self-ping failed: %s", exc)


async def polling_loop(config: Config, state: SystemState, reminder_service: ReminderService, user_profiles) -> None:
    """
    Polling loop that sends reminders and confirmation pings based on Sheets data.
    """

    logger.info("Polling loop started")
    while True:
        try:
            for profile in user_profiles.values():
                await reminder_service.send_pre_event_reminders(profile, config.timezone_name, state)
                await reminder_service.send_confirmation_pings(
                    profile,
                    config.timezone_name,
                    state,
                    config.confirm_ping_interval_min,
                    config.confirm_max_pings,
                    config.confirm_window_min,
                )
            await state.mark_poll()
            logger.debug("Polling heartbeat at %s", datetime.now(timezone.utc).isoformat())
            await asyncio.sleep(config.poll_interval_seconds)
        except Exception as exc:
            logger.exception("Polling loop error: %s", exc)
            await asyncio.sleep(min(10, config.poll_interval_seconds))
