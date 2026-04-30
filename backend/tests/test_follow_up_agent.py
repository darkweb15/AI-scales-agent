"""Unit and property-based tests for FollowUpAgent.

Task 7.1 — Property test: channel selection safety (Req 3.2–3.5)
Task 7.2 — Property test: follow-up escalation at max attempts (Req 3.1)
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.agents.follow_up.agent import FollowUpAgent, FollowUpResult
from app.models.enums import Channel, LeadStatus


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
    status: LeadStatus = LeadStatus.contacted
    call_attempts: int = 0
    email_attempts: int = 0


@dataclass
class FakeInteraction:
    channel: Channel
    direction: str = "outbound"
    outcome: str = "contacted"
    summary: str = ""


def _make_db() -> MagicMock:
    db = MagicMock()
    db.update_lead_status = AsyncMock()
    db.create_interaction_log = AsyncMock()
    db.get_last_interaction = AsyncMock(return_value=None)
    db.get_interactions_for_lead = AsyncMock(return_value=[])
    db.get_email_template = AsyncMock(return_value=None)
    return db


def _make_llm() -> MagicMock:
    llm = MagicMock()
    llm.personalize = MagicMock(return_value="Personalized follow-up content")
    return llm


def _make_mail_agent() -> MagicMock:
    mail = MagicMock()
    mail.send_email = AsyncMock(return_value=MagicMock(outcome="sent"))
    return mail


def _make_call_agent() -> MagicMock:
    call = MagicMock()
    call.call = AsyncMock(return_value=MagicMock(outcome="contacted"))
    return call


def _make_config(max_attempts: int = 5) -> MagicMock:
    cfg = MagicMock()
    cfg.max_total_follow_up_attempts = max_attempts
    return cfg


def _agent(db=None, mail=None, call=None, llm=None, config=None) -> FollowUpAgent:
    return FollowUpAgent(
        db_service=db or _make_db(),
        auto_mail_agent=mail or _make_mail_agent(),
        cold_calling_agent=call or _make_call_agent(),
        llm_service=llm or _make_llm(),
        config=config or _make_config(),
    )


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Unit tests — select_channel
# ---------------------------------------------------------------------------

def test_select_channel_no_prior_interaction_returns_call():
    """Req 3.5: no prior interaction → call."""
    agent = _agent()
    lead = FakeLead(phone="+15550001234")
    result = agent.select_channel(lead, last_interaction=None)
    assert result == Channel.call


def test_select_channel_last_was_call_returns_email():
    """Req 3.2: last interaction was call → email."""
    agent = _agent()
    lead = FakeLead(phone="+15550001234")
    last = FakeInteraction(channel=Channel.call)
    result = agent.select_channel(lead, last_interaction=last)
    assert result == Channel.email


def test_select_channel_last_email_with_phone_returns_call():
    """Req 3.3: last was email + has phone → call."""
    agent = _agent()
    lead = FakeLead(phone="+15550001234")
    last = FakeInteraction(channel=Channel.email)
    result = agent.select_channel(lead, last_interaction=last)
    assert result == Channel.call


def test_select_channel_last_email_no_phone_returns_email():
    """Req 3.4: last was email + no phone → email."""
    agent = _agent()
    lead = FakeLead(phone=None)
    last = FakeInteraction(channel=Channel.email)
    result = agent.select_channel(lead, last_interaction=last)
    assert result == Channel.email


def test_select_channel_null_phone_never_returns_sms():
    """Null-phone guard: never return SMS for null-phone leads."""
    agent = _agent()
    lead = FakeLead(phone=None)
    for channel in [Channel.call, Channel.email, Channel.sms]:
        last = FakeInteraction(channel=channel)
        result = agent.select_channel(lead, last_interaction=last)
        assert result != Channel.sms


# ---------------------------------------------------------------------------
# Unit tests — execute_follow_up
# ---------------------------------------------------------------------------

def test_execute_follow_up_escalates_at_max_attempts():
    """Req 3.1: total attempts >= max → escalate, status=not_interested."""
    db = _make_db()
    agent = _agent(db=db, config=_make_config(max_attempts=5))
    lead = FakeLead(call_attempts=3, email_attempts=2)  # total=5 == max
    session = MagicMock()

    result = run(agent.execute_follow_up(lead, session))

    assert result.outcome == "escalated"
    db.update_lead_status.assert_awaited_once_with(
        session, lead.id, LeadStatus.not_interested
    )


def test_execute_follow_up_logs_interaction():
    """Req 3.7: every follow-up logs to InteractionLog."""
    db = _make_db()
    db.get_last_interaction = AsyncMock(return_value=None)
    agent = _agent(db=db, config=_make_config(max_attempts=10))
    lead = FakeLead(call_attempts=0, email_attempts=0)
    session = MagicMock()

    run(agent.execute_follow_up(lead, session))

    db.create_interaction_log.assert_awaited()


def test_execute_follow_up_uses_llm_for_personalization():
    """Req 3.6: LLM is called to personalize content."""
    llm = _make_llm()
    db = _make_db()
    db.get_last_interaction = AsyncMock(return_value=None)
    agent = _agent(db=db, llm=llm, config=_make_config(max_attempts=10))
    lead = FakeLead(call_attempts=0, email_attempts=0)
    session = MagicMock()

    run(agent.execute_follow_up(lead, session))

    llm.personalize.assert_called()


def test_schedule_follow_up_enqueues_task():
    """schedule_follow_up enqueues a deferred task via task_queue."""
    task_queue = MagicMock()
    task_queue.enqueue = MagicMock(return_value="task-id-123")
    agent = _agent()
    agent.task_queue = task_queue
    lead = FakeLead()

    task_id = agent.schedule_follow_up(lead, delay_hours=24)

    assert task_id == "task-id-123"
    task_queue.enqueue.assert_called_once()


def test_schedule_follow_up_no_queue_returns_none():
    """schedule_follow_up returns None when no task_queue configured."""
    agent = _agent()
    agent.task_queue = None
    lead = FakeLead()

    result = agent.schedule_follow_up(lead, delay_hours=24)

    assert result is None


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------

# Hypothesis strategies
phone_strategy = st.one_of(
    st.none(),
    st.from_regex(r"\+1555\d{7}", fullmatch=True),
)

channel_strategy = st.sampled_from([Channel.call, Channel.email, Channel.sms])

last_interaction_strategy = st.one_of(
    st.none(),
    st.builds(FakeInteraction, channel=channel_strategy),
)


@given(
    phone=phone_strategy,
    last_interaction=last_interaction_strategy,
)
@settings(max_examples=200)
def test_property_select_channel_never_sms_for_null_phone(phone, last_interaction):
    """**Property 6: Channel Selection Safety**

    **Validates: Requirements 3.2, 3.3, 3.4, 3.5**

    For any lead with null phone and any interaction history,
    select_channel must never return SMS.
    """
    if phone is not None:
        return  # only test null-phone case

    agent = _agent()
    lead = FakeLead(phone=None)
    result = agent.select_channel(lead, last_interaction=last_interaction)
    assert result != Channel.sms, (
        f"select_channel returned SMS for null-phone lead "
        f"(last_interaction={last_interaction})"
    )


@given(
    phone=phone_strategy,
    last_interaction=last_interaction_strategy,
)
@settings(max_examples=200)
def test_property_select_channel_always_returns_valid_channel(phone, last_interaction):
    """select_channel always returns a valid Channel enum value."""
    agent = _agent()
    lead = FakeLead(phone=phone)
    result = agent.select_channel(lead, last_interaction=last_interaction)
    assert result in (Channel.call, Channel.email, Channel.sms)


@given(
    call_attempts=st.integers(min_value=0, max_value=20),
    email_attempts=st.integers(min_value=0, max_value=20),
    max_attempts=st.integers(min_value=1, max_value=10),
)
@settings(max_examples=200)
def test_property_escalation_at_max_attempts(
    call_attempts, email_attempts, max_attempts
):
    """**Property 7: Follow-up Escalation at Max Attempts**

    **Validates: Requirements 3.1**

    For any lead where email_attempts + call_attempts >= maxTotalFollowUpAttempts,
    execute_follow_up must always escalate.
    """
    total = call_attempts + email_attempts
    if total < max_attempts:
        return  # only test the escalation case

    db = _make_db()
    agent = _agent(db=db, config=_make_config(max_attempts=max_attempts))
    lead = FakeLead(call_attempts=call_attempts, email_attempts=email_attempts)
    session = MagicMock()

    result = run(agent.execute_follow_up(lead, session))

    assert result.outcome == "escalated", (
        f"Expected escalation for total_attempts={total} >= max={max_attempts}, "
        f"got outcome={result.outcome}"
    )
    db.update_lead_status.assert_awaited_with(
        session, lead.id, LeadStatus.not_interested
    )
