"""Unit and property-based tests for AutoReplyAgent.

Task 9.1 — Property test: intent classification coverage (Req 6.6)
Task 9.2 — Property test: low-confidence escalation (Req 6.4)
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

from app.agents.auto_reply.agent import AutoReplyAgent, InboundMessage, ReplyResult
from app.models.enums import Intent, LeadStatus


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


def _make_db(existing_lead: Optional[FakeLead] = None) -> MagicMock:
    db = MagicMock()
    db.find_lead_by_email = AsyncMock(return_value=existing_lead)
    db.create_lead = AsyncMock(return_value=FakeLead())
    db.update_lead_status = AsyncMock()
    db.create_interaction_log = AsyncMock()
    db.get_interactions_for_lead = AsyncMock(return_value=[])
    return db


def _make_email_provider() -> MagicMock:
    provider = MagicMock()
    provider.send = MagicMock(return_value=MagicMock(success=True))
    return provider


def _make_llm() -> MagicMock:
    llm = MagicMock()
    llm.personalize = MagicMock(return_value="Generated reply content")
    return llm


def _make_notification() -> MagicMock:
    notif = MagicMock()
    notif.notify_admin = MagicMock()
    notif.emit = MagicMock()
    return notif


def _make_config(threshold: float = 0.75) -> MagicMock:
    cfg = MagicMock()
    cfg.auto_reply_confidence_threshold = threshold
    return cfg


def _agent(
    db=None,
    email_provider=None,
    llm=None,
    notification=None,
    config=None,
) -> AutoReplyAgent:
    return AutoReplyAgent(
        db_service=db or _make_db(),
        email_provider=email_provider or _make_email_provider(),
        llm_service=llm or _make_llm(),
        notification_service=notification or _make_notification(),
        config=config or _make_config(),
    )


def _msg(
    body: str = "Hello, I am interested.",
    subject: str = "Inquiry",
    sender: str = "test@example.com",
) -> InboundMessage:
    return InboundMessage(
        sender_email=sender,
        subject=subject,
        body=body,
        received_at=datetime.now(timezone.utc),
    )


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Unit tests — receive_message
# ---------------------------------------------------------------------------

def test_receive_message_known_lead_no_create():
    """Req 6.1: known lead → no new lead created."""
    lead = FakeLead()
    db = _make_db(existing_lead=lead)
    agent = _agent(db=db)
    session = MagicMock()

    run(agent.receive_message(_msg(), session))

    db.create_lead.assert_not_awaited()


def test_receive_message_unknown_sender_creates_lead():
    """Req 6.2: unknown sender → create new lead with source='inbound_email'."""
    db = _make_db(existing_lead=None)
    agent = _agent(db=db)
    session = MagicMock()

    run(agent.receive_message(_msg(), session))

    db.create_lead.assert_awaited_once()
    create_args = db.create_lead.call_args[0][1]
    assert create_args["source"] == "inbound_email"


def test_receive_message_unsubscribe_updates_status():
    """Req 6.3: unsubscribe intent → status=unsubscribed, no LLM."""
    lead = FakeLead()
    db = _make_db(existing_lead=lead)
    llm = _make_llm()
    agent = _agent(db=db, llm=llm)
    session = MagicMock()

    result = run(agent.receive_message(_msg(body="Please unsubscribe me"), session))

    assert result.outcome == "unsubscribed"
    db.update_lead_status.assert_awaited_once_with(
        session, lead.id, LeadStatus.unsubscribed
    )
    # LLM should NOT be called for unsubscribe
    llm.personalize.assert_not_called()


def test_receive_message_low_confidence_escalates():
    """Req 6.4: low confidence → escalate, no reply sent."""
    lead = FakeLead()
    db = _make_db(existing_lead=lead)
    email_provider = _make_email_provider()
    notification = _make_notification()
    # Use high threshold so unknown intent (0.5 confidence) triggers escalation
    agent = _agent(
        db=db,
        email_provider=email_provider,
        notification=notification,
        config=_make_config(threshold=0.75),
    )
    session = MagicMock()

    # "unknown" body → Intent.unknown → confidence=0.5 < 0.75
    result = run(agent.receive_message(_msg(body="xyzzy random text"), session))

    assert result.outcome == "escalated"
    # No reply email sent
    email_provider.send.assert_not_called()


def test_receive_message_high_confidence_sends_reply():
    """Req 6.5: confidence >= threshold → generate and send reply."""
    lead = FakeLead()
    db = _make_db(existing_lead=lead)
    email_provider = _make_email_provider()
    agent = _agent(db=db, email_provider=email_provider, config=_make_config(threshold=0.75))
    session = MagicMock()

    result = run(agent.receive_message(_msg(body="I am interested in your product"), session))

    assert result.outcome == "replied"
    email_provider.send.assert_called_once()


def test_receive_message_logs_interaction():
    """Req 6.7: every message logs to InteractionLog."""
    lead = FakeLead()
    db = _make_db(existing_lead=lead)
    agent = _agent(db=db)
    session = MagicMock()

    run(agent.receive_message(_msg(body="I am interested"), session))

    db.create_interaction_log.assert_awaited()


def test_receive_message_notifies_orchestrator_on_reply():
    """Req 6.8: after reply sent, notify Orchestrator."""
    lead = FakeLead()
    db = _make_db(existing_lead=lead)
    notification = _make_notification()
    agent = _agent(db=db, notification=notification, config=_make_config(threshold=0.75))
    session = MagicMock()

    result = run(agent.receive_message(_msg(body="I am interested"), session))

    if result.outcome == "replied":
        notification.emit.assert_called()


# ---------------------------------------------------------------------------
# Unit tests — classify_intent
# ---------------------------------------------------------------------------

def test_classify_intent_unsubscribe():
    agent = _agent()
    msg = _msg(body="Please unsubscribe me from your list")
    assert agent.classify_intent(msg) == Intent.unsubscribe


def test_classify_intent_interested():
    agent = _agent()
    msg = _msg(body="I am interested in learning more about pricing")
    assert agent.classify_intent(msg) == Intent.interested


def test_classify_intent_meeting_request():
    agent = _agent()
    msg = _msg(body="Can we schedule a demo call?")
    assert agent.classify_intent(msg) == Intent.meeting_request


def test_classify_intent_not_interested():
    agent = _agent()
    msg = _msg(body="Not interested, please remove me")
    assert agent.classify_intent(msg) == Intent.not_interested


def test_classify_intent_question():
    agent = _agent()
    msg = _msg(body="How does your product work?")
    assert agent.classify_intent(msg) == Intent.question


def test_classify_intent_unknown_returns_unknown():
    agent = _agent()
    msg = _msg(body="xyzzy random gibberish text")
    assert agent.classify_intent(msg) == Intent.unknown


# ---------------------------------------------------------------------------
# Unit tests — generate_reply
# ---------------------------------------------------------------------------

def test_generate_reply_includes_guardrail():
    """Req 8.7: LLM prompt includes system-level guardrail."""
    llm = _make_llm()
    agent = _agent(llm=llm)
    lead = FakeLead()

    agent.generate_reply(lead, Intent.interested)

    call_args = llm.personalize.call_args[0][0]
    assert "guardrail" in call_args.lower() or "injection" in call_args.lower() or "role" in call_args.lower()


def test_generate_reply_returns_non_empty_string():
    agent = _agent()
    lead = FakeLead()
    result = agent.generate_reply(lead, Intent.question)
    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# Property-based tests
# ---------------------------------------------------------------------------

# Strategy: generate arbitrary message bodies
message_body_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs", "Po")),
    min_size=0,
    max_size=500,
)

message_subject_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Zs")),
    min_size=0,
    max_size=100,
)

valid_intents = set(Intent)


@given(
    body=message_body_strategy,
    subject=message_subject_strategy,
)
@settings(max_examples=300)
def test_property_classify_intent_always_returns_valid_intent(body, subject):
    """**Property 8: Auto Reply Intent Classification Coverage**

    **Validates: Requirements 6.6**

    For any inbound message string, classify_intent must always return
    a valid, non-null Intent value.
    """
    agent = _agent()
    msg = InboundMessage(
        sender_email="test@example.com",
        subject=subject,
        body=body,
    )
    result = agent.classify_intent(msg)
    assert result is not None, "classify_intent returned None"
    assert result in valid_intents, f"classify_intent returned invalid value: {result!r}"


@given(
    confidence=st.floats(min_value=0.0, max_value=0.749, allow_nan=False),
    threshold=st.floats(min_value=0.75, max_value=1.0, allow_nan=False),
)
@settings(max_examples=200)
def test_property_low_confidence_never_sends_reply(confidence, threshold):
    """**Property 9: Low-Confidence Escalation**

    **Validates: Requirements 6.4**

    For any message where confidence < threshold, no automated reply is sent
    and escalation always fires.
    """
    lead = FakeLead()
    db = _make_db(existing_lead=lead)
    email_provider = _make_email_provider()
    notification = _make_notification()
    agent = _agent(
        db=db,
        email_provider=email_provider,
        notification=notification,
        config=_make_config(threshold=threshold),
    )

    # Patch _get_confidence to return the test confidence value
    agent._get_confidence = lambda msg, intent: confidence

    session = MagicMock()
    # Use a body that won't trigger unsubscribe intent (unsubscribe bypasses confidence check)
    msg = _msg(body="hello world general inquiry")

    result = run(agent.receive_message(msg, session))

    # Must not send a reply
    email_provider.send.assert_not_called(), (
        f"Reply was sent despite confidence={confidence} < threshold={threshold}"
    )
    # Must escalate
    assert result.outcome == "escalated", (
        f"Expected escalation for confidence={confidence} < threshold={threshold}, "
        f"got outcome={result.outcome}"
    )
