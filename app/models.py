from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class UserProfile:
    telegram_id: str
    display_name: Optional[str] = None
    sheet_id: Optional[str] = None
    calendar_id: Optional[str] = None


@dataclass
class ScheduleEvent:
    event_id: str
    title: str
    type: str
    start_dt: datetime
    end_dt: datetime
    is_recurring: bool
    rrule: Optional[str]
    priority: int
    flexibility: int
    buffer_before_min: int
    buffer_after_min: int
    status: str
    created_by: str
    notes: Optional[str]
    gcal_event_id: Optional[str]
    recurrence_id: Optional[str]


@dataclass
class FoodLog:
    food_id: str
    dt: datetime
    text_input: Optional[str]
    photo_file_id: Optional[str]
    estimated_kcal: int
    protein_g: int
    fat_g: int
    carbs_g: int
    confidence: float
    needs_clarification: bool
    clarification_question: Optional[str]
    resolved: bool


@dataclass
class HealthDaily:
    date: str
    weight_kg: Optional[float]
    height_cm: Optional[int]
    sleep_hours: Optional[float]
    training_minutes: Optional[int]
    kcal_total: Optional[int]
    protein_g: Optional[int]
    fat_g: Optional[int]
    carbs_g: Optional[int]
    source: str
    health_note: Optional[str]


ActionPayload = Dict[str, Any]


@dataclass
class Action:
    type: str
    payload: ActionPayload
    idempotency_key: Optional[str] = None


@dataclass
class LLMResponse:
    assistant_text: str
    actions: List[Action]
    followup_required: bool = False
    debug: Optional[Dict[str, Any]] = None
