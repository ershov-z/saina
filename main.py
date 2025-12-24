import asyncio
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.clients.google_calendar import CalendarClient
from app.clients.google_sheets import SheetsClient
from app.clients.openai_client import OpenAIClient
from app.clients.telegram import TelegramClient
from app.config import load_config
from app.handlers.telegram_router import TelegramRouter
from app.orchestrator import Orchestrator
from app.scheduler import polling_loop, self_ping_loop
from app.services.approvals import ApprovalService
from app.services.food import FoodService
from app.services.health import HealthService
from app.services.reminders import ReminderService
from app.services.schedule import ScheduleService
from app.state import SystemState
from app.store.conversation import ConversationStore


# =========================
# Basic config
# =========================

config = load_config()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(config.service_name)

app = FastAPI()

TZ_INFO = ZoneInfo(config.timezone_name)
SYSTEM_STATE = SystemState()

# Clients
sheets_client = SheetsClient(
    client_id=config.google_client_id,
    client_secret=config.google_client_secret,
    refresh_token=config.google_refresh_token,
    token_uri=config.google_token_uri,
    scopes=config.google_scopes,
)
calendar_client = CalendarClient(
    client_id=config.google_client_id,
    client_secret=config.google_client_secret,
    refresh_token=config.google_refresh_token,
    token_uri=config.google_token_uri,
    scopes=config.google_scopes,
)
telegram_client = TelegramClient(config.telegram_bot_token)
openai_client = OpenAIClient(api_key=config.openai_api_key, model=config.openai_model, schema_path="action_contract.schema.json")

# Services and orchestrator
schedule_service = ScheduleService(sheets_client, calendar_client)
food_service = FoodService(sheets_client)
health_service = HealthService(sheets_client)
approval_service = ApprovalService(telegram_client)
conversation_store = ConversationStore()
orchestrator = Orchestrator(
    config,
    openai_client,
    telegram_client,
    schedule_service,
    food_service,
    health_service,
    approval_service,
    conversation_store,
)
reminder_service = ReminderService(schedule_service, telegram_client)
router = TelegramRouter(orchestrator, conversation_store)


# =========================
# Healthcheck
# =========================

@app.get(config.healthcheck_path)
async def healthcheck():
    """
    Healthcheck endpoint.
    Must be fast, independent, and never call external APIs.
    """

    now_utc = datetime.now(timezone.utc)
    now_local = datetime.now(TZ_INFO)

    status = "ok"
    if SYSTEM_STATE.last_poll_dt is None:
        status = "degraded"
    else:
        lag_seconds = (now_utc - SYSTEM_STATE.last_poll_dt).total_seconds()
        if lag_seconds > config.poll_interval_seconds * 5:
            status = "degraded"

    payload = {
        "status": status,
        "service": config.service_name,
        "time_ekb": now_local.isoformat(),
        "timezone": config.timezone_name,
        "uptime_seconds": SYSTEM_STATE.uptime_seconds,
    }
    payload.update(SYSTEM_STATE.as_health_payload())
    return payload


# =========================
# Telegram webhook stub
# =========================

@app.post(config.telegram_webhook_path)
async def telegram_webhook(request: Request):
    """
    Telegram webhook entrypoint.
    """
    update = await request.json()

    logger.debug("Received Telegram update: %s", update.get("update_id"))

    result = await router.handle_update(update)
    return JSONResponse(result)


# =========================
# App lifecycle
# =========================

@app.on_event("startup")
async def on_startup():
    logger.info("Service starting up in timezone %s", config.timezone_name)

    if config.self_ping_enabled:
        asyncio.create_task(self_ping_loop(config, SYSTEM_STATE))

    # Polling must run regardless of Telegram traffic
    asyncio.create_task(polling_loop(config, SYSTEM_STATE, reminder_service, orchestrator.user_profiles))


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Service shutting down")
