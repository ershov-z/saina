import os
import asyncio
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx

# =========================
# Basic config
# =========================

SERVICE_NAME = "family-assistant-bot"

BASE_URL = os.getenv("BASE_URL", "")
HEALTHCHECK_PATH = os.getenv("HEALTHCHECK_PATH", "/health")

SELF_PING_ENABLED = os.getenv("SELF_PING_ENABLED", "false").lower() == "true"
SELF_PING_INTERVAL_MIN = int(os.getenv("SELF_PING_INTERVAL_MIN", "12"))

TZ_NAME = os.getenv("TZ", "Asia/Yekaterinburg")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(SERVICE_NAME)

app = FastAPI()

START_TIME = datetime.now(timezone.utc)


# =========================
# Healthcheck
# =========================

@app.get(HEALTHCHECK_PATH)
async def healthcheck():
    """
    Healthcheck endpoint.
    Must be fast, independent, and never call external APIs.
    """
    uptime_seconds = int((datetime.now(timezone.utc) - START_TIME).total_seconds())

    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "time_utc": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime_seconds,
    }


# =========================
# Telegram webhook stub
# =========================

@app.post("/tg/webhook")
async def telegram_webhook(request: Request):
    """
    Telegram webhook entrypoint.
    Actual update handling will be implemented later.
    """
    update = await request.json()

    # IMPORTANT:
    # No business logic here yet.
    # Codex will plug dispatcher / router later.
    logger.debug("Received Telegram update")

    return JSONResponse({"ok": True})


# =========================
# Background tasks
# =========================

async def self_ping_loop():
    """
    Periodically pings /health to keep Render instance alive.
    """
    if not BASE_URL:
        logger.warning("BASE_URL not set, self-ping disabled")
        return

    url = f"{BASE_URL}{HEALTHCHECK_PATH}"
    logger.info(f"Self-ping enabled, target: {url}")

    async with httpx.AsyncClient(timeout=10) as client:
        while True:
            try:
                await asyncio.sleep(SELF_PING_INTERVAL_MIN * 60)
                response = await client.get(url)
                logger.info(f"Self-ping status={response.status_code}")
            except Exception as e:
                logger.warning(f"Self-ping failed: {e}")


async def polling_loop():
    """
    Placeholder for Google Sheets polling:
    - reminders
    - confirmations
    - daily plan
    - daily digest

    Real implementation will be added later.
    """
    logger.info("Polling loop started (stub)")
    while True:
        try:
            # TODO: implement polling logic
            await asyncio.sleep(60)
        except Exception as e:
            logger.exception(f"Polling loop error: {e}")
            await asyncio.sleep(10)


# =========================
# App lifecycle
# =========================

@app.on_event("startup")
async def on_startup():
    logger.info("Service starting up")

    if SELF_PING_ENABLED:
        asyncio.create_task(self_ping_loop())

    # Polling must run regardless of Telegram traffic
    asyncio.create_task(polling_loop())


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Service shutting down")
