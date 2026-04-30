"""Unit tests for CallAnsweringAgent.

Task 10.1 — Unit tests covering:
  - Human transfer on explicit request (Req 7.2)
  - Low-confidence transfer (Req 7.3)
  - New lead creation from inbound call (Req 7.6)
  - Interaction log persistence (Req 7.4)
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.call_answering.agent import (
    CallAnsweringAgent,
    CallerInfo,
    QualificationResult,
)
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
    phone: str = "+15550001234"
    company: str = "Acme Corp"
    status: LeadStatus = LeadStatus.new


def _make_db(existing_lead: Optional[FakeLead] = None) -> MagicMock:
    db = MagicMock()
    db.find_lead_by_phone = AsyncMock(return_value=existing_lead)
    db.create_lead = AsyncMock(return_value=FakeLead())
    db.create_interaction_log = AsyncMock()
    db.get_interactions_for_lead = AsyncMock(return_value=[])
    return db


def _make_telephony(transcript: str = "Hello, I am interested.") -> MagicMock:
    telephony = MagicMock()
    telephony.get_transcript = MagicMock(return_value=transcript)
    telephony.transfer_call = MagicMock()
    return telephony


def _make_llm() -> MagicMock:
    llm = MagicMock()
    llm.personalize = MagicMock(return_value="LLM qualification response")
    return llm


def _make_notification() -> MagicMock:
    notif = MagicMock()
    notif.notify_admin = MagicMock()
    return notif


def _agent(
    db=None,
    telephony=None,
    llm=None,
    notification=None,
    confidence_threshold: float = 0.70,
) -> CallAnsweringAgent:
    return CallAnsweringAgent(
        db_service=db or _make_db(),
        telephony_api=telephony or _make_telephony(),
        llm_service=llm or _make_llm(),
        notification_service=notification or _make_notification(),
        confidence_threshold=confidence_threshold,
    )


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Test: human transfer on explicit request (Req 7.2)
# ---------------------------------------------------------------------------

def test_qualify_caller_explicit_human_request_transfers():
    """Req 7.2: caller says 'speak to a human' → transfer to human queue."""
    telephony = _make_telephony(transcript="I want to speak to a human representative")
    agent = _agent(telephony=telephony, confidence_threshold=0.70)

    result = run(agent.qualify_caller("call_123"))

    assert result.transferred_to_human is True
    assert result.transfer_reason == "explicit_human_request" or result.outcome == "transferred"


def test_route_to_human_calls_telephony_transfer():
    """route_to_human calls telephony.transfer_call."""
    telephony = _make_telephony()
    agent = _agent(telephony=telephony)

    run(agent.route_to_human("call_123", reason="explicit_human_request"))

    telephony.transfer_call.assert_called_once_with("call_123", queue="human_reps")


def test_route_to_human_notifies_admin():
    """route_to_human notifies admin via notification service."""
    notification = _make_notification()
    agent = _agent(notification=notification)

    run(agent.route_to_human("call_123", reason="low_confidence"))

    notification.notify_admin.assert_called_once()


# ---------------------------------------------------------------------------
# Test: low-confidence transfer (Req 7.3)
# ---------------------------------------------------------------------------

def test_qualify_caller_low_confidence_transfers():
    """Req 7.3: low confidence → transfer to human queue."""
    # "xyzzy" → Intent.unknown → confidence=0.50 < threshold=0.70
    telephony = _make_telephony(transcript="xyzzy random gibberish")
    agent = _agent(telephony=telephony, confidence_threshold=0.70)

    result = run(agent.qualify_caller("call_456"))

    assert result.transferred_to_human is True
    assert result.transfer_reason == "low_confidence"
    telephony.transfer_call.assert_called_once()


def test_qualify_caller_high_confidence_no_transfer():
    """High confidence → no transfer to human."""
    telephony = _make_telephony(transcript="I am very interested in your product pricing")
    agent = _agent(telephony=telephony, confidence_threshold=0.70)

    result = run(agent.qualify_caller("call_789"))

    assert result.transferred_to_human is False


# ---------------------------------------------------------------------------
# Test: new lead creation from inbound call (Req 7.6)
# ---------------------------------------------------------------------------

def test_answer_call_unknown_caller_creates_lead():
    """Req 7.6: unknown caller → create new lead with source='inbound_call'."""
    db = _make_db(existing_lead=None)
    telephony = _make_telephony(transcript="I am interested in your product")
    agent = _agent(db=db, telephony=telephony)
    caller = CallerInfo(phone="+15550009999", name="Bob")
    session = MagicMock()

    run(agent.answer_call("call_new", caller, session))

    db.create_lead.assert_awaited_once()
    create_args = db.create_lead.call_args[0][1]
    assert create_args["source"] == "inbound_call"
    assert create_args["phone"] == "+15550009999"


def test_answer_call_known_caller_no_create():
    """Req 7.5: known caller → no new lead created."""
    lead = FakeLead(phone="+15550001234")
    db = _make_db(existing_lead=lead)
    telephony = _make_telephony(transcript="I am interested")
    agent = _agent(db=db, telephony=telephony)
    caller = CallerInfo(phone="+15550001234")
    session = MagicMock()

    run(agent.answer_call("call_known", caller, session))

    db.create_lead.assert_not_awaited()


def test_answer_call_known_caller_retrieves_history():
    """Req 7.5: known caller → interaction history retrieved."""
    lead = FakeLead(phone="+15550001234")
    db = _make_db(existing_lead=lead)
    telephony = _make_telephony(transcript="I am interested")
    agent = _agent(db=db, telephony=telephony)
    caller = CallerInfo(phone="+15550001234")
    session = MagicMock()

    run(agent.answer_call("call_known", caller, session))

    db.get_interactions_for_lead.assert_awaited_once_with(session, lead.id)


# ---------------------------------------------------------------------------
# Test: interaction log persistence (Req 7.4)
# ---------------------------------------------------------------------------

def test_log_call_persists_interaction():
    """Req 7.4: log_call persists transcript and outcome to InteractionLog."""
    lead = FakeLead()
    db = _make_db(existing_lead=lead)
    agent = _agent(db=db)
    session = MagicMock()

    result = QualificationResult(
        outcome="qualified",
        intent=Intent.interested,
        confidence=0.90,
        transcript="I am interested in your product.",
        summary="Qualified: interested",
    )

    run(agent.log_call("call_log", result, session, lead=lead))

    db.create_interaction_log.assert_awaited_once()
    log_data = db.create_interaction_log.call_args[0][1]
    assert log_data["lead_id"] == lead.id
    assert log_data["raw_transcript"] == "I am interested in your product."
    assert log_data["outcome"] == "qualified"


def test_answer_call_logs_interaction():
    """Req 7.4: answer_call always logs to InteractionLog."""
    lead = FakeLead(phone="+15550001234")
    db = _make_db(existing_lead=lead)
    telephony = _make_telephony(transcript="I am interested")
    agent = _agent(db=db, telephony=telephony)
    caller = CallerInfo(phone="+15550001234")
    session = MagicMock()

    run(agent.answer_call("call_log_test", caller, session))

    db.create_interaction_log.assert_awaited()


def test_log_call_no_lead_does_not_raise():
    """log_call with no lead should not raise an exception."""
    db = _make_db()
    agent = _agent(db=db)
    session = MagicMock()

    result = QualificationResult(outcome="failed")

    # Should not raise
    run(agent.log_call("call_no_lead", result, session, lead=None))

    db.create_interaction_log.assert_not_awaited()


# ---------------------------------------------------------------------------
# Test: telephony failure handling
# ---------------------------------------------------------------------------

def test_qualify_caller_telephony_failure_returns_failed():
    """Telephony failure → outcome='failed', no crash."""
    telephony = MagicMock()
    telephony.get_transcript = MagicMock(side_effect=RuntimeError("Telephony error"))
    agent = _agent(telephony=telephony)

    result = run(agent.qualify_caller("call_fail"))

    assert result.outcome == "failed"
    assert result.transcript is None
