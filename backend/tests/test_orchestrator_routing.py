"""Property tests for Orchestrator routing functions.

**Property 1 (Task 3.1): DNC and Unsubscribed Leads Never Dispatched**
**Validates: Requirements 1.6, 8.3**

**Property 2 (Task 3.2): Cooldown Window Correctness**
**Validates: Requirements 1.7, 1.8**

**Property 3 (Task 3.3): Lead Routing Determinism**
**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.models.enums import AgentType, LeadStatus
from app.orchestrator.routing import RoutingConfig, RoutingTask, evaluate_lead, is_on_cooldown

# ---------------------------------------------------------------------------
# Helpers / test doubles
# ---------------------------------------------------------------------------

_DEFAULT_CONFIG = RoutingConfig(
    max_cold_call_attempts=3,
    follow_up_delay_hours=24,
    cooldown_minutes=60,
)

_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


@dataclass
class FakeLead:
    """Minimal lead-like object for routing tests (no DB required)."""

    id: uuid.UUID
    status: LeadStatus
    call_attempts: int = 0
    email_attempts: int = 0
    last_contacted_at: Optional[datetime] = None
    demo_scheduled_at: Optional[datetime] = None


def _lead(
    status: LeadStatus,
    call_attempts: int = 0,
    last_contacted_at: Optional[datetime] = None,
    demo_scheduled_at: Optional[datetime] = None,
) -> FakeLead:
    return FakeLead(
        id=uuid.uuid4(),
        status=status,
        call_attempts=call_attempts,
        last_contacted_at=last_contacted_at,
        demo_scheduled_at=demo_scheduled_at,
    )


# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

dnc_statuses = st.sampled_from([LeadStatus.do_not_contact, LeadStatus.unsubscribed])

all_statuses = st.sampled_from(list(LeadStatus))

# Timestamps: anywhere from 7 days ago to 7 days in the future relative to _NOW
timestamp_strategy = st.datetimes(
    min_value=datetime(2024, 5, 25, 0, 0, 0),
    max_value=datetime(2024, 6, 8, 0, 0, 0),
).map(lambda dt: dt.replace(tzinfo=timezone.utc))

call_attempts_strategy = st.integers(min_value=0, max_value=10)


# ---------------------------------------------------------------------------
# Property 1 — DNC and Unsubscribed Leads Never Dispatched (Task 3.1)
# ---------------------------------------------------------------------------


@given(
    status=dnc_statuses,
    call_attempts=call_attempts_strategy,
    last_contacted_at=st.one_of(st.none(), timestamp_strategy),
)
@settings(max_examples=500)
def test_dnc_and_unsubscribed_leads_never_dispatched(
    status: LeadStatus,
    call_attempts: int,
    last_contacted_at: Optional[datetime],
) -> None:
    """Property 1: evaluate_lead always returns None for DNC/unsubscribed leads.

    **Validates: Requirements 1.6, 8.3**

    No matter what other fields the lead has, if its status is
    do_not_contact or unsubscribed, evaluate_lead must return None.
    """
    lead = _lead(
        status=status,
        call_attempts=call_attempts,
        last_contacted_at=last_contacted_at,
    )
    result = evaluate_lead(lead, _DEFAULT_CONFIG, now=_NOW)
    assert result is None, (
        f"evaluate_lead returned {result!r} for lead with status={status!r}; "
        "expected None (DNC/unsubscribed leads must never be dispatched)"
    )


# ---------------------------------------------------------------------------
# Property 2 — Cooldown Window Correctness (Task 3.2)
# ---------------------------------------------------------------------------


@given(last_contacted_at=timestamp_strategy)
@settings(max_examples=500)
def test_cooldown_within_window_returns_true(last_contacted_at: datetime) -> None:
    """Property 2a: is_on_cooldown returns True when within cooldown window.

    **Validates: Requirements 1.7**
    """
    # Place 'now' so that elapsed time is strictly less than cooldown_minutes
    elapsed_minutes = _DEFAULT_CONFIG.cooldown_minutes / 2  # 30 min < 60 min
    now = last_contacted_at + timedelta(minutes=elapsed_minutes)

    lead = _lead(status=LeadStatus.new, last_contacted_at=last_contacted_at)
    assert is_on_cooldown(lead, _DEFAULT_CONFIG, now=now) is True, (
        f"Expected is_on_cooldown=True when elapsed={elapsed_minutes}min "
        f"< cooldown={_DEFAULT_CONFIG.cooldown_minutes}min"
    )


@given(last_contacted_at=timestamp_strategy)
@settings(max_examples=500)
def test_cooldown_outside_window_returns_false(last_contacted_at: datetime) -> None:
    """Property 2b: is_on_cooldown returns False when outside cooldown window.

    **Validates: Requirements 1.7**
    """
    # Place 'now' so that elapsed time is strictly greater than cooldown_minutes
    elapsed_minutes = _DEFAULT_CONFIG.cooldown_minutes + 1  # 61 min > 60 min
    now = last_contacted_at + timedelta(minutes=elapsed_minutes)

    lead = _lead(status=LeadStatus.new, last_contacted_at=last_contacted_at)
    assert is_on_cooldown(lead, _DEFAULT_CONFIG, now=now) is False, (
        f"Expected is_on_cooldown=False when elapsed={elapsed_minutes}min "
        f"> cooldown={_DEFAULT_CONFIG.cooldown_minutes}min"
    )


@given(status=all_statuses)
@settings(max_examples=200)
def test_cooldown_null_last_contacted_always_false(status: LeadStatus) -> None:
    """Property 2c: is_on_cooldown returns False when last_contacted_at is NULL.

    **Validates: Requirements 1.8**

    A lead that has never been contacted is never on cooldown.
    """
    lead = _lead(status=status, last_contacted_at=None)
    assert is_on_cooldown(lead, _DEFAULT_CONFIG, now=_NOW) is False, (
        "Expected is_on_cooldown=False when last_contacted_at is None "
        "(never-contacted lead must not be treated as on cooldown)"
    )


# ---------------------------------------------------------------------------
# Property 3 — Lead Routing Determinism (Task 3.3)
# ---------------------------------------------------------------------------


@given(
    status=all_statuses,
    call_attempts=call_attempts_strategy,
    last_contacted_at=st.one_of(st.none(), timestamp_strategy),
    demo_scheduled_at=st.one_of(st.none(), timestamp_strategy),
)
@settings(max_examples=500)
def test_evaluate_lead_is_deterministic(
    status: LeadStatus,
    call_attempts: int,
    last_contacted_at: Optional[datetime],
    demo_scheduled_at: Optional[datetime],
) -> None:
    """Property 3: evaluate_lead is pure — same input always yields same output.

    **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**

    Calling evaluate_lead twice with identical arguments must return
    structurally identical results (same agent_type and action, or both None).
    """
    lead = _lead(
        status=status,
        call_attempts=call_attempts,
        last_contacted_at=last_contacted_at,
        demo_scheduled_at=demo_scheduled_at,
    )

    result_a = evaluate_lead(lead, _DEFAULT_CONFIG, now=_NOW)
    result_b = evaluate_lead(lead, _DEFAULT_CONFIG, now=_NOW)

    # Both calls must agree on whether a task is returned
    assert (result_a is None) == (result_b is None), (
        f"evaluate_lead returned different None-ness on two calls: "
        f"first={result_a!r}, second={result_b!r}"
    )

    if result_a is not None and result_b is not None:
        assert result_a.agent_type == result_b.agent_type, (
            f"evaluate_lead returned different agent_type: "
            f"{result_a.agent_type!r} vs {result_b.agent_type!r}"
        )
        assert result_a.action == result_b.action, (
            f"evaluate_lead returned different action: "
            f"{result_a.action!r} vs {result_b.action!r}"
        )


# ---------------------------------------------------------------------------
# Unit tests — specific routing branches (complement the property tests)
# ---------------------------------------------------------------------------


def test_new_lead_below_max_attempts_routes_to_cold_calling() -> None:
    """Req 1.1: new lead with call_attempts < max → COLD_CALLING_AGENT/call."""
    lead = _lead(status=LeadStatus.new, call_attempts=0)
    task = evaluate_lead(lead, _DEFAULT_CONFIG, now=_NOW)
    assert task is not None
    assert task.agent_type == AgentType.cold_calling
    assert task.action == "call"


def test_new_lead_at_max_attempts_routes_to_auto_mail() -> None:
    """Req 1.2: new lead with call_attempts >= max → AUTO_MAIL_AGENT/send_intro_email."""
    lead = _lead(status=LeadStatus.new, call_attempts=3)
    task = evaluate_lead(lead, _DEFAULT_CONFIG, now=_NOW)
    assert task is not None
    assert task.agent_type == AgentType.auto_mail
    assert task.action == "send_intro_email"


def test_contacted_lead_past_delay_routes_to_follow_up() -> None:
    """Req 1.3: contacted lead past follow_up_delay_hours → FOLLOW_UP_AGENT/follow_up."""
    last_contacted = _NOW - timedelta(hours=25)
    lead = _lead(status=LeadStatus.contacted, last_contacted_at=last_contacted)
    task = evaluate_lead(lead, _DEFAULT_CONFIG, now=_NOW)
    assert task is not None
    assert task.agent_type == AgentType.follow_up
    assert task.action == "follow_up"


def test_contacted_lead_within_delay_returns_none() -> None:
    """Req 1.3: contacted lead within follow_up_delay_hours → None."""
    last_contacted = _NOW - timedelta(hours=10)
    lead = _lead(status=LeadStatus.contacted, last_contacted_at=last_contacted)
    task = evaluate_lead(lead, _DEFAULT_CONFIG, now=_NOW)
    assert task is None


def test_interested_lead_routes_to_demo_scheduling() -> None:
    """Req 1.4: interested lead → DEMO_SCHEDULING_AGENT/schedule_demo."""
    lead = _lead(status=LeadStatus.interested)
    task = evaluate_lead(lead, _DEFAULT_CONFIG, now=_NOW)
    assert task is not None
    assert task.agent_type == AgentType.demo_scheduling
    assert task.action == "schedule_demo"


def test_demo_scheduled_within_24h_routes_to_reminder() -> None:
    """Req 1.5: demo within 24h → DEMO_SCHEDULING_AGENT/send_reminder."""
    demo_at = _NOW + timedelta(hours=12)
    lead = _lead(status=LeadStatus.demo_scheduled, demo_scheduled_at=demo_at)
    task = evaluate_lead(lead, _DEFAULT_CONFIG, now=_NOW)
    assert task is not None
    assert task.agent_type == AgentType.demo_scheduling
    assert task.action == "send_reminder"


def test_demo_scheduled_beyond_24h_returns_none() -> None:
    """Req 1.5: demo more than 24h away → None."""
    demo_at = _NOW + timedelta(hours=48)
    lead = _lead(status=LeadStatus.demo_scheduled, demo_scheduled_at=demo_at)
    task = evaluate_lead(lead, _DEFAULT_CONFIG, now=_NOW)
    assert task is None


def test_do_not_contact_returns_none() -> None:
    """Req 1.6: do_not_contact → None."""
    lead = _lead(status=LeadStatus.do_not_contact)
    assert evaluate_lead(lead, _DEFAULT_CONFIG, now=_NOW) is None


def test_unsubscribed_returns_none() -> None:
    """Req 1.6: unsubscribed → None."""
    lead = _lead(status=LeadStatus.unsubscribed)
    assert evaluate_lead(lead, _DEFAULT_CONFIG, now=_NOW) is None


def test_terminal_statuses_return_none() -> None:
    """Other terminal statuses (not_interested, converted, etc.) → None."""
    for status in (
        LeadStatus.not_interested,
        LeadStatus.converted,
        LeadStatus.demo_completed,
        LeadStatus.follow_up_scheduled,
    ):
        lead = _lead(status=status)
        assert evaluate_lead(lead, _DEFAULT_CONFIG, now=_NOW) is None, (
            f"Expected None for status={status!r}"
        )


def test_cooldown_exactly_at_boundary_is_not_on_cooldown() -> None:
    """Boundary: elapsed == cooldown_minutes → not on cooldown (strict <)."""
    last_contacted = _NOW - timedelta(minutes=_DEFAULT_CONFIG.cooldown_minutes)
    lead = _lead(status=LeadStatus.new, last_contacted_at=last_contacted)
    assert is_on_cooldown(lead, _DEFAULT_CONFIG, now=_NOW) is False


def test_cooldown_one_second_before_boundary_is_on_cooldown() -> None:
    """Boundary: elapsed < cooldown_minutes → on cooldown."""
    last_contacted = _NOW - timedelta(
        minutes=_DEFAULT_CONFIG.cooldown_minutes, seconds=-1
    )
    lead = _lead(status=LeadStatus.new, last_contacted_at=last_contacted)
    assert is_on_cooldown(lead, _DEFAULT_CONFIG, now=_NOW) is True
