"""Demo Scheduling Agent — coordinates calendar availability and books demos.

Requirements: 4.1 – 4.9
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AgentType, BookingStatus, Channel, Direction, LeadStatus
from .calendar_api import CalendarAPI, StubCalendarAPI, TimeSlot

logger = logging.getLogger(__name__)


@dataclass
class SlotProposalResult:
    outcome: str  # 'proposed', 'no_slots', 'suppressed'
    slots: List[TimeSlot] = None


class DemoSchedulingAgent:
    """Coordinates calendar availability and books product demos."""

    def __init__(
        self,
        db_service: Optional[Any] = None,
        calendar_api: Optional[CalendarAPI] = None,
        auto_mail_agent: Optional[Any] = None,
        notification_service: Optional[Any] = None,
        scheduling_window_days: int = 14,
        max_slots_to_offer: int = 3,
        demo_duration_minutes: int = 30,
    ) -> None:
        self._db = db_service
        self._calendar = calendar_api or StubCalendarAPI()
        self._mail = auto_mail_agent
        self._notify = notification_service
        self._window_days = scheduling_window_days
        self._max_slots = max_slots_to_offer
        self._duration = demo_duration_minutes

    async def propose_slots(self, lead: Any, session: AsyncSession) -> SlotProposalResult:
        """Fetch available slots and send proposal email. Req 4.1, 4.2, 4.3"""
        now = datetime.now(timezone.utc)
        slots = self._calendar.get_available_slots(
            from_dt=now,
            to_dt=now + timedelta(days=self._window_days),
            duration_minutes=self._duration,
        )

        if not slots:
            # Req 4.3 — notify admin
            logger.warning("No slots available for lead %s", lead.id)
            if self._notify:
                self._notify.notify_admin(f"No demo slots available for lead {lead.id}", "system")
            return SlotProposalResult(outcome="no_slots", slots=[])

        top_slots = slots[:self._max_slots]

        # Send slot proposal email
        if self._mail:
            from app.models.email_template import EmailTemplate
            slot_text = "\n".join([f"- {s.start.strftime('%a %b %d at %I:%M %p UTC')}" for s in top_slots])
            template = EmailTemplate(
                id=uuid.uuid4(),
                name="demo_slot_proposal",
                subject_template="Let's schedule your demo, {first_name}!",
                body_template=f"Hi {{first_name}},\n\nHere are available slots for your demo:\n\n{slot_text}\n\nReply with your preferred time!\n\nBest,\nSales Team",
                agent_type=AgentType.demo_scheduling,
                stage=LeadStatus.interested,
                variables=["first_name"],
            )
            await self._mail.send_email(session, lead, template)

        # Req 4.2 — update status to follow_up_scheduled
        if self._db:
            await self._db.update_lead_status(session, lead.id, LeadStatus.follow_up_scheduled)

        await self._log(session, lead, "proposed_slots", f"Offered {len(top_slots)} demo slots")
        return SlotProposalResult(outcome="proposed", slots=top_slots)

    async def confirm_booking(self, lead: Any, slot: TimeSlot, session: AsyncSession) -> Any:
        """Create calendar event, save Booking, update lead status. Req 4.4"""
        event = self._calendar.create_event(slot, lead, self._duration)

        booking_data = {
            "lead_id": lead.id,
            "calendar_event_id": event.event_id,
            "scheduled_at": slot.start,
            "duration_minutes": self._duration,
            "status": BookingStatus.confirmed,
            "reminder_sent": False,
            "meeting_link": event.meeting_link,
        }

        booking = None
        if self._db:
            booking = await self._db.save_booking(session, booking_data)
            await self._db.update_lead_status(session, lead.id, LeadStatus.demo_scheduled)
            await self._db.update_lead(session, lead.id, demo_scheduled_at=slot.start)

        # Send confirmation email
        if self._mail:
            from app.models.email_template import EmailTemplate
            template = EmailTemplate(
                id=uuid.uuid4(),
                name="demo_confirmation",
                subject_template="Your demo is confirmed, {first_name}!",
                body_template=f"Hi {{first_name}},\n\nYour demo is confirmed for {slot.start.strftime('%A, %B %d at %I:%M %p UTC')}.\n\nMeeting link: {event.meeting_link}\n\nSee you then!\n\nBest,\nSales Team",
                agent_type=AgentType.demo_scheduling,
                stage=LeadStatus.demo_scheduled,
                variables=["first_name"],
            )
            await self._mail.send_email(session, lead, template)

        await self._log(session, lead, "booking_confirmed", f"Demo confirmed for {slot.start.isoformat()}")
        return booking

    async def send_reminder(self, booking: Any, lead: Any, session: AsyncSession) -> None:
        """Send 24h or 1h reminder. Req 4.6, 4.7"""
        if not self._mail:
            return
        from app.models.email_template import EmailTemplate
        now = datetime.now(timezone.utc)
        hours_until = (booking.scheduled_at - now).total_seconds() / 3600

        if hours_until <= 1:
            subject = "Your demo starts in 1 hour, {first_name}!"
            body = "Hi {first_name},\n\nJust a reminder — your demo starts in 1 hour!\n\nMeeting link: " + (booking.meeting_link or "")
        else:
            subject = "Demo reminder: tomorrow, {first_name}"
            body = "Hi {first_name},\n\nReminder: your demo is scheduled for tomorrow.\n\nMeeting link: " + (booking.meeting_link or "")

        template = EmailTemplate(
            id=uuid.uuid4(), name="demo_reminder",
            subject_template=subject, body_template=body,
            agent_type=AgentType.demo_scheduling,
            stage=LeadStatus.demo_scheduled, variables=["first_name"],
        )
        await self._mail.send_email(session, lead, template)
        await self._log(session, lead, "reminder_sent", f"Reminder sent ({hours_until:.0f}h before demo)")

    async def handle_reschedule(self, booking: Any, lead: Any, session: AsyncSession) -> SlotProposalResult:
        """Update booking to rescheduled and re-propose slots. Req 4.8"""
        if self._db:
            await self._db.update_booking(session, booking.id, status=BookingStatus.rescheduled)
        await self._log(session, lead, "reschedule_requested", "Lead requested reschedule")
        return await self.propose_slots(lead, session)

    async def _log(self, session: AsyncSession, lead: Any, outcome: str, summary: str) -> None:
        if not self._db:
            return
        await self._db.create_interaction_log(session, {
            "lead_id": lead.id,
            "agent_type": AgentType.demo_scheduling,
            "channel": Channel.email,
            "direction": Direction.outbound,
            "timestamp": datetime.now(timezone.utc),
            "summary": summary,
            "outcome": outcome,
        })
