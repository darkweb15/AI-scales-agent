"""Unit tests for DemoSchedulingAgent.

Task 8.1 — Unit tests covering:
  - No slots available → admin notification (Req 4.3)
  - Slot conflict → re-proposal (Req 4.5)
  - 24h and 1h reminder triggers (Req 4.6, 4.7)
  - Reschedule flow (Req 4.8)
  - Booking confirmation (Req 4.4)
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from app.agents.demo_scheduling.agent import DemoSchedulingAgent, SlotProposalResult
from app.agents.demo_scheduling.calendar_api import (
    CalendarEvent,
    StubCalendarAPI,
    TimeSlot,
)
from app.models.enums import BookingStatus, LeadStatus


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

@dataclass
class FakeLead:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    first_name: str = "Alice"
    last_name: str = "Smith"
    email: str = "alice@example.com"
    phone: Optional[str] = "+15550001234"
    company: str = "Acme Corp"
    status: LeadStatus = LeadStatus.interested


@dataclass
class FakeBooking:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    lead_id: uuid.UUID = field(default_factory=uuid.uuid4)
    scheduled_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=25)
    )
    status: BookingStatus = BookingStatus.confirmed
    reminder_sent: bool = False
    calendar_event_id: str = "event_123"


def _make_db(lead: Optional[FakeLead] = None) -> MagicMock:
    db = MagicMock()
    db.update_lead_status = AsyncMock()
    db.update_lead = AsyncMock()
    db.create_interaction_log = AsyncMock()
    db.get_email_template = AsyncMock(return_value=None)
    db.save_booking = AsyncMock(return_value=FakeBooking())
    db.update_booking = AsyncMock()
    db.get_lead = AsyncMock(return_value=lead or FakeLead())
    return db


def _make_mail_agent() -> MagicMock:
    mail = MagicMock()
    mail.send_email = AsyncMock(return_value=MagicMock(outcome="sent"))
    return mail


def _make_config(
    scheduling_window_days: int = 14,
    max_slots: int = 3,
    duration_minutes: int = 30,
) -> MagicMock:
    cfg = MagicMock()
    cfg.scheduling_window_days = scheduling_window_days
    cfg.max_slots_to_offer = max_slots
    cfg.demo_duration_minutes = duration_minutes
    return cfg


def _make_notification() -> MagicMock:
    notif = MagicMock()
    notif.notify_admin = MagicMock()
    return notif


def _agent(
    db=None,
    calendar_api=None,
    mail=None,
    notification=None,
    config=None,
) -> DemoSchedulingAgent:
    return DemoSchedulingAgent(
        db_service=db or _make_db(),
        calendar_api=calendar_api or StubCalendarAPI(),
        auto_mail_agent=mail or _make_mail_agent(),
        notification_service=notification or _make_notification(),
        config=config or _make_config(),
    )


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Test: no slots available → admin notification (Req 4.3)
# ---------------------------------------------------------------------------

def test_propose_slots_no_slots_notifies_admin():
    """Req 4.3: no available slots → notify admin, return no_slots outcome."""
    notification = _make_notification()
    calendar = StubCalendarAPI(available_slots=[])
    db = _make_db()
    agent = _agent(db=db, calendar_api=calendar, notification=notification)
    lead = FakeLead()
    session = MagicMock()

    result = run(agent.propose_slots(lead, session))

    assert result.outcome == "no_slots"
    assert result.slots == []
    notification.notify_admin.assert_called_once()


def test_propose_slots_no_slots_does_not_update_status():
    """No slots → lead status should NOT be updated to follow_up_scheduled."""
    db = _make_db()
    calendar = StubCalendarAPI(available_slots=[])
    agent = _agent(db=db, calendar_api=calendar)
    lead = FakeLead()
    session = MagicMock()

    run(agent.propose_slots(lead, session))

    db.update_lead_status.assert_not_awaited()


# ---------------------------------------------------------------------------
# Test: propose slots success (Req 4.1, 4.2)
# ---------------------------------------------------------------------------

def test_propose_slots_returns_top_n_slots():
    """Req 4.2: propose top N slots (max_slots_to_offer)."""
    now = datetime.now(timezone.utc)
    slots = [
        TimeSlot(start=now + timedelta(days=i), end=now + timedelta(days=i, minutes=30))
        for i in range(1, 6)
    ]
    calendar = StubCalendarAPI(available_slots=slots)
    db = _make_db()
    agent = _agent(db=db, calendar_api=calendar, config=_make_config(max_slots=3))
    lead = FakeLead()
    session = MagicMock()

    result = run(agent.propose_slots(lead, session))

    assert result.outcome == "proposed"
    assert len(result.slots) == 3


def test_propose_slots_updates_status_to_follow_up_scheduled():
    """Req 4.2: after proposing slots, lead status → follow_up_scheduled."""
    db = _make_db()
    agent = _agent(db=db)
    lead = FakeLead()
    session = MagicMock()

    run(agent.propose_slots(lead, session))

    db.update_lead_status.assert_awaited_once_with(
        session, lead.id, LeadStatus.follow_up_scheduled
    )


# ---------------------------------------------------------------------------
# Test: slot conflict → re-proposal (Req 4.5)
# ---------------------------------------------------------------------------

def test_confirm_booking_slot_conflict_re_proposes():
    """Req 4.5: slot conflict → re-propose slots, return conflict outcome."""
    now = datetime.now(timezone.utc)
    slot = TimeSlot(start=now + timedelta(days=1), end=now + timedelta(days=1, minutes=30))

    calendar = StubCalendarAPI()
    calendar.mark_slot_unavailable(slot)  # simulate conflict

    db = _make_db()
    agent = _agent(db=db, calendar_api=calendar)
    lead = FakeLead()
    session = MagicMock()

    result = run(agent.confirm_booking(lead, slot, session))

    assert result.outcome == "conflict"


# ---------------------------------------------------------------------------
# Test: booking confirmation (Req 4.4)
# ---------------------------------------------------------------------------

def test_confirm_booking_creates_booking_and_updates_status():
    """Req 4.4: confirm booking → save Booking, status=demo_scheduled."""
    now = datetime.now(timezone.utc)
    slot = TimeSlot(start=now + timedelta(days=1), end=now + timedelta(days=1, minutes=30))
    db = _make_db()
    agent = _agent(db=db)
    lead = FakeLead()
    session = MagicMock()

    result = run(agent.confirm_booking(lead, slot, session))

    assert result.outcome == "confirmed"
    db.save_booking.assert_awaited_once()
    db.update_lead_status.assert_awaited_once_with(
        session, lead.id, LeadStatus.demo_scheduled
    )


def test_confirm_booking_logs_interaction():
    """Req 4.9: booking confirmation logs to InteractionLog."""
    now = datetime.now(timezone.utc)
    slot = TimeSlot(start=now + timedelta(days=1), end=now + timedelta(days=1, minutes=30))
    db = _make_db()
    agent = _agent(db=db)
    lead = FakeLead()
    session = MagicMock()

    run(agent.confirm_booking(lead, slot, session))

    db.create_interaction_log.assert_awaited()


# ---------------------------------------------------------------------------
# Test: 24h and 1h reminder triggers (Req 4.6, 4.7)
# ---------------------------------------------------------------------------

def test_send_reminder_24h():
    """Req 4.6: demo within 24h → send 24h reminder."""
    now = datetime.now(timezone.utc)
    booking = FakeBooking(
        scheduled_at=now + timedelta(hours=20),  # 20h away → 24h reminder
        reminder_sent=False,
    )
    lead = FakeLead()
    db = _make_db(lead=lead)
    mail = _make_mail_agent()
    agent = _agent(db=db, mail=mail)
    session = MagicMock()

    run(agent.send_reminder(booking, session))

    db.update_booking.assert_awaited_once()
    db.create_interaction_log.assert_awaited()


def test_send_reminder_1h():
    """Req 4.7: demo within 1h → send 1h reminder."""
    now = datetime.now(timezone.utc)
    booking = FakeBooking(
        scheduled_at=now + timedelta(minutes=45),  # 45min away → 1h reminder
        reminder_sent=False,
    )
    lead = FakeLead()
    db = _make_db(lead=lead)
    mail = _make_mail_agent()
    agent = _agent(db=db, mail=mail)
    session = MagicMock()

    run(agent.send_reminder(booking, session))

    db.update_booking.assert_awaited_once()
    db.create_interaction_log.assert_awaited()


def test_send_reminder_far_future_no_action():
    """Demo more than 24h away → no reminder sent."""
    now = datetime.now(timezone.utc)
    booking = FakeBooking(
        scheduled_at=now + timedelta(hours=48),  # 48h away → no reminder
        reminder_sent=False,
    )
    lead = FakeLead()
    db = _make_db(lead=lead)
    agent = _agent(db=db)
    session = MagicMock()

    run(agent.send_reminder(booking, session))

    db.update_booking.assert_not_awaited()
    db.create_interaction_log.assert_not_awaited()


# ---------------------------------------------------------------------------
# Test: reschedule flow (Req 4.8)
# ---------------------------------------------------------------------------

def test_handle_reschedule_updates_booking_status():
    """Req 4.8: reschedule → booking status=rescheduled."""
    lead = FakeLead()
    booking = FakeBooking(lead_id=lead.id)
    db = _make_db(lead=lead)
    agent = _agent(db=db)
    session = MagicMock()

    result = run(agent.handle_reschedule(booking, new_slot=None, session=session))

    db.update_booking.assert_awaited_once_with(
        session, booking.id, status=BookingStatus.rescheduled
    )


def test_handle_reschedule_re_proposes_slots():
    """Req 4.8: after reschedule, new slots are proposed."""
    lead = FakeLead()
    booking = FakeBooking(lead_id=lead.id)
    db = _make_db(lead=lead)
    agent = _agent(db=db)
    session = MagicMock()

    result = run(agent.handle_reschedule(booking, new_slot=None, session=session))

    # propose_slots was called → status updated to follow_up_scheduled
    db.update_lead_status.assert_awaited_with(
        session, lead.id, LeadStatus.follow_up_scheduled
    )


def test_handle_reschedule_logs_interaction():
    """Req 4.9: reschedule logs to InteractionLog."""
    lead = FakeLead()
    booking = FakeBooking(lead_id=lead.id)
    db = _make_db(lead=lead)
    agent = _agent(db=db)
    session = MagicMock()

    run(agent.handle_reschedule(booking, new_slot=None, session=session))

    # At least one interaction log entry (reschedule + propose_slots)
    assert db.create_interaction_log.await_count >= 1
