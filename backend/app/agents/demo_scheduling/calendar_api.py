"""Calendar API interface and stub."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional


@dataclass
class TimeSlot:
    start: datetime
    end: datetime
    slot_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class CalendarEvent:
    event_id: str
    title: str
    start: datetime
    end: datetime
    meeting_link: Optional[str] = None


class CalendarAPI:
    def get_available_slots(self, from_dt: datetime, to_dt: datetime, duration_minutes: int = 30) -> List[TimeSlot]:
        raise NotImplementedError

    def create_event(self, slot: TimeSlot, lead: object, duration_minutes: int = 30) -> CalendarEvent:
        raise NotImplementedError

    def cancel_event(self, event_id: str) -> bool:
        raise NotImplementedError


class StubCalendarAPI(CalendarAPI):
    """In-memory stub for testing."""

    def __init__(self, available: bool = True) -> None:
        self._available = available
        self.created_events: list = []

    def get_available_slots(self, from_dt: datetime, to_dt: datetime, duration_minutes: int = 30) -> List[TimeSlot]:
        if not self._available:
            return []
        slots = []
        current = from_dt.replace(hour=10, minute=0, second=0, microsecond=0)
        for _ in range(5):
            if current < to_dt:
                slots.append(TimeSlot(start=current, end=current + timedelta(minutes=duration_minutes)))
                current += timedelta(days=1)
        return slots

    def create_event(self, slot: TimeSlot, lead: object, duration_minutes: int = 30) -> CalendarEvent:
        event = CalendarEvent(
            event_id=str(uuid.uuid4()),
            title=f"Demo with {getattr(lead, 'first_name', 'Lead')}",
            start=slot.start,
            end=slot.end,
            meeting_link=f"https://meet.example.com/{uuid.uuid4().hex[:8]}",
        )
        self.created_events.append(event)
        return event

    def cancel_event(self, event_id: str) -> bool:
        return True
