"""Pure routing functions for the Orchestrator.

These functions are intentionally free of database or I/O calls so they can
be unit- and property-tested without any infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ..models.enums import AgentType, LeadStatus


@dataclass
class RoutingConfig:
    """Subset of Config fields consumed by the routing layer."""

    max_cold_call_attempts: int = 3
    follow_up_delay_hours: int = 24
    cooldown_minutes: int = 60


@dataclass
class RoutingTask:
    """Lightweight task descriptor returned by evaluate_lead.

    The Orchestrator converts this into a full AgentTask before persisting.
    """

    lead_id: Any  # uuid.UUID in production; Any for testability
    agent_type: AgentType
    action: str
    payload: Dict[str, Any] = field(default_factory=dict)


def _hours_since(dt: datetime, now: datetime) -> float:
    """Return the number of hours elapsed since *dt* relative to *now*."""
    delta = now - dt
    return delta.total_seconds() / 3600.0


def _hours_until(dt: datetime, now: datetime) -> float:
    """Return the number of hours remaining until *dt* relative to *now*."""
    delta = dt - now
    return delta.total_seconds() / 3600.0


def is_on_cooldown(
    lead: Any,
    config: RoutingConfig,
    now: Optional[datetime] = None,
) -> bool:
    """Return True if the lead is within the cooldown window.

    Requirements 1.7, 1.8:
    - Returns True  when now() - last_contacted_at < config.cooldown_minutes
    - Returns False when last_contacted_at is NULL (never contacted)

    Parameters
    ----------
    lead:
        Any object with a ``last_contacted_at`` attribute (datetime | None).
    config:
        Routing configuration supplying ``cooldown_minutes``.
    now:
        Current UTC time.  Defaults to ``datetime.now(timezone.utc)`` when
        not provided (injectable for deterministic testing).
    """
    if now is None:
        now = datetime.now(timezone.utc)

    last_contacted_at = lead.last_contacted_at

    # Req 1.8 — NULL means never contacted → not on cooldown
    if last_contacted_at is None:
        return False

    # Normalise to UTC-aware if naive
    if last_contacted_at.tzinfo is None:
        last_contacted_at = last_contacted_at.replace(tzinfo=timezone.utc)

    elapsed_minutes = (now - last_contacted_at).total_seconds() / 60.0
    return elapsed_minutes < config.cooldown_minutes


def evaluate_lead(
    lead: Any,
    config: RoutingConfig,
    now: Optional[datetime] = None,
) -> Optional[RoutingTask]:
    """Apply routing rules and return the next task for *lead*, or None.

    This is a pure function — no DB calls, no side effects.

    Requirements 1.1 – 1.6:
    - do_not_contact / unsubscribed → None  (Req 1.6)
    - new + call_attempts < max  → COLD_CALLING_AGENT / call  (Req 1.1)
    - new + call_attempts >= max → AUTO_MAIL_AGENT / send_intro_email  (Req 1.2)
    - contacted + hours_since >= follow_up_delay → FOLLOW_UP_AGENT / follow_up  (Req 1.3)
    - interested → DEMO_SCHEDULING_AGENT / schedule_demo  (Req 1.4)
    - demo_scheduled + hours_until <= 24 → DEMO_SCHEDULING_AGENT / send_reminder  (Req 1.5)
    - all other statuses → None
    """
    if now is None:
        now = datetime.now(timezone.utc)

    status = lead.status

    # Req 1.6 — never dispatch to DNC or unsubscribed leads
    if status in (LeadStatus.do_not_contact, LeadStatus.unsubscribed):
        return None

    # Req 1.1 — new lead, still has cold-call attempts remaining
    if status == LeadStatus.new and lead.call_attempts < config.max_cold_call_attempts:
        return RoutingTask(
            lead_id=lead.id,
            agent_type=AgentType.cold_calling,
            action="call",
        )

    # Req 1.2 — new lead, exhausted cold-call attempts → intro email
    if status == LeadStatus.new and lead.call_attempts >= config.max_cold_call_attempts:
        return RoutingTask(
            lead_id=lead.id,
            agent_type=AgentType.auto_mail,
            action="send_intro_email",
        )

    # Req 1.3 — contacted lead past follow-up delay
    if status == LeadStatus.contacted:
        last_contacted_at = lead.last_contacted_at
        if last_contacted_at is not None:
            # Normalise timezone
            if last_contacted_at.tzinfo is None:
                last_contacted_at = last_contacted_at.replace(tzinfo=timezone.utc)
            if _hours_since(last_contacted_at, now) >= config.follow_up_delay_hours:
                return RoutingTask(
                    lead_id=lead.id,
                    agent_type=AgentType.follow_up,
                    action="follow_up",
                )
        return None

    # Req 1.4 — interested lead → schedule demo
    if status == LeadStatus.interested:
        return RoutingTask(
            lead_id=lead.id,
            agent_type=AgentType.demo_scheduling,
            action="schedule_demo",
        )

    # Req 1.5 — demo within 24 hours → send reminder
    if status == LeadStatus.demo_scheduled:
        demo_scheduled_at = lead.demo_scheduled_at
        if demo_scheduled_at is not None:
            if demo_scheduled_at.tzinfo is None:
                demo_scheduled_at = demo_scheduled_at.replace(tzinfo=timezone.utc)
            if _hours_until(demo_scheduled_at, now) <= 24:
                return RoutingTask(
                    lead_id=lead.id,
                    agent_type=AgentType.demo_scheduling,
                    action="send_reminder",
                )
        return None

    return None
