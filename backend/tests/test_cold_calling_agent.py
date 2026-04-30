"""Unit tests for ColdCallingAgent.

Covers all 9 test cases from Task 5.1:
  1. DNC block path (Req 2.1)
  2. Outside calling hours → deferred (Req 2.2)
  3. No-answer → call_attempts incremented (Req 2.3)
  4. Voicemail → handle_voicemail called (Req 2.4)
  5. Answered + intent=interested → status=interested (Req 2.6)
  6. Answered + intent=not_interested → status=not_interested (Req 2.7)
  7. Answered + intent=question → status=contacted (Req 2.8)
  8. Telephony API failure → task failed, retry counter incremented (Req 2.10)
  9. Interaction log written for every completed call (Req 2.9)
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.cold_calling.agent import (
    CallResult,
    ColdCallingAgent,
    Transcript,
    compute_backoff_seconds,
    is_on_dnc_list,
    is_within_calling_hours,
)
from app.agents.cold_calling.telephony import CallSession, TelephonyAPI
from app.agents.cold_calling.nlp import NLPEngine
from app.models.enums import Intent, LeadStatus, TaskStatus


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
    call_attempts: int = 0


@dataclass
class FakeTask:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    retry_count: int = 0
    status: TaskStatus = TaskStatus.queued


def _make_telephony(status: str = "answered") -> MagicMock:
    """Return a mock TelephonyAPI that returns a CallSession with the given status."""
    mock = MagicMock(spec=TelephonyAPI)
    mock.initiate_call.return_value = CallSession(call_id="call_123", status=status)
    mock.get_transcript.return_value = "Hello, I am interested in your product."
    mock.leave_voicemail.return_value = None
    return mock


def _make_nlp(intent: Intent = Intent.interested) -> MagicMock:
    mock = MagicMock(spec=NLPEngine)
    mock.extract_intent.return_value = intent
    mock.get_confidence_score.return_value = 0.95
    return mock


def _make_db() -> MagicMock:
    """Return a mock DatabaseService with async methods."""
    db = MagicMock()
    db.update_lead_status = AsyncMock()
    db.increment_call_attempts = AsyncMock()
    db.create_interaction_log = AsyncMock()
    db.update_task_status = AsyncMock()
    return db


def _make_session() -> MagicMock:
    return MagicMock()


def _agent(
    telephony=None,
    nlp=None,
    db=None,
    dnc_list: Optional[Set[str]] = None,
    calling_hours_start: int = 9,
    calling_hours_end: int = 17,
    max_retries: int = 0,  # no retries by default in tests
    now_fn=None,
) -> ColdCallingAgent:
    return ColdCallingAgent(
        telephony_api=telephony or _make_telephony(),
        nlp_engine=nlp or _make_nlp(),
        db_service=db,
        dnc_list=dnc_list,
        calling_hours_start=calling_hours_start,
        calling_hours_end=calling_hours_end,
        max_retries=max_retries,
        now_fn=now_fn,
    )


# Fixed "now" within calling hours (10:00 UTC)
_WITHIN_HOURS = datetime(2024, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
# Fixed "now" outside calling hours (20:00 UTC)
_OUTSIDE_HOURS = datetime(2024, 6, 1, 20, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helper: run async coroutine in tests
# ---------------------------------------------------------------------------

def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Test 1 — DNC block path (Req 2.1)
# ---------------------------------------------------------------------------

def test_dnc_block_returns_blocked_outcome():
    """Phone on DNC list → outcome='blocked', status updated to do_not_contact."""
    lead = FakeLead(phone="+15550001234")
    db = _make_db()
    session = _make_session()
    agent = _agent(
        dnc_list={"+15550001234"},
        db=db,
        now_fn=lambda: _WITHIN_HOURS,
    )

    result = run(agent.call(lead, session=session))

    assert result.outcome == "blocked"
    db.update_lead_status.assert_awaited_once_with(
        session, lead.id, LeadStatus.do_not_contact
    )


def test_dnc_block_does_not_initiate_call():
    """DNC check must prevent any call from being initiated."""
    telephony = _make_telephony()
    lead = FakeLead(phone="+15550001234")
    agent = _agent(
        telephony=telephony,
        dnc_list={"+15550001234"},
        now_fn=lambda: _WITHIN_HOURS,
    )

    run(agent.call(lead))

    telephony.initiate_call.assert_not_called()


# ---------------------------------------------------------------------------
# Test 2 — Outside calling hours → deferred (Req 2.2)
# ---------------------------------------------------------------------------

def test_outside_calling_hours_returns_deferred():
    """Call outside configured hours → outcome='deferred', no call initiated."""
    telephony = _make_telephony()
    lead = FakeLead()
    agent = _agent(
        telephony=telephony,
        calling_hours_start=9,
        calling_hours_end=17,
        now_fn=lambda: _OUTSIDE_HOURS,
    )

    result = run(agent.call(lead))

    assert result.outcome == "deferred"
    telephony.initiate_call.assert_not_called()


def test_within_calling_hours_proceeds():
    """Call within configured hours should proceed past the hours guard."""
    telephony = _make_telephony(status="answered")
    lead = FakeLead()
    agent = _agent(
        telephony=telephony,
        calling_hours_start=9,
        calling_hours_end=17,
        now_fn=lambda: _WITHIN_HOURS,
    )

    run(agent.call(lead))

    telephony.initiate_call.assert_called_once()


# ---------------------------------------------------------------------------
# Test 3 — No-answer → call_attempts incremented (Req 2.3)
# ---------------------------------------------------------------------------

def test_no_answer_increments_call_attempts():
    """Telephony returns no_answer → call_attempts incremented, outcome='no_answer'."""
    telephony = _make_telephony(status="no_answer")
    db = _make_db()
    session = _make_session()
    lead = FakeLead()
    agent = _agent(telephony=telephony, db=db, now_fn=lambda: _WITHIN_HOURS)

    result = run(agent.call(lead, session=session))

    assert result.outcome == "no_answer"
    db.increment_call_attempts.assert_awaited_once_with(session, lead.id)


def test_busy_increments_call_attempts():
    """Telephony returns busy → same behaviour as no_answer."""
    telephony = _make_telephony(status="busy")
    db = _make_db()
    session = _make_session()
    lead = FakeLead()
    agent = _agent(telephony=telephony, db=db, now_fn=lambda: _WITHIN_HOURS)

    result = run(agent.call(lead, session=session))

    assert result.outcome == "no_answer"
    db.increment_call_attempts.assert_awaited_once_with(session, lead.id)


# ---------------------------------------------------------------------------
# Test 4 — Voicemail → handle_voicemail called (Req 2.4)
# ---------------------------------------------------------------------------

def test_voicemail_calls_handle_voicemail():
    """Telephony returns voicemail → leave_voicemail is called, outcome='voicemail'."""
    telephony = _make_telephony(status="voicemail")
    db = _make_db()
    session = _make_session()
    lead = FakeLead()
    agent = _agent(telephony=telephony, db=db, now_fn=lambda: _WITHIN_HOURS)

    result = run(agent.call(lead, session=session))

    assert result.outcome == "voicemail"
    telephony.leave_voicemail.assert_called_once()


def test_voicemail_increments_call_attempts():
    """Voicemail path also increments call_attempts."""
    telephony = _make_telephony(status="voicemail")
    db = _make_db()
    session = _make_session()
    lead = FakeLead()
    agent = _agent(telephony=telephony, db=db, now_fn=lambda: _WITHIN_HOURS)

    run(agent.call(lead, session=session))

    db.increment_call_attempts.assert_awaited_once_with(session, lead.id)


# ---------------------------------------------------------------------------
# Test 5 — Answered + intent=interested → status=interested (Req 2.6)
# ---------------------------------------------------------------------------

def test_answered_interested_updates_status_to_interested():
    """Answered call with intent=interested → lead status set to interested."""
    telephony = _make_telephony(status="answered")
    nlp = _make_nlp(intent=Intent.interested)
    db = _make_db()
    session = _make_session()
    lead = FakeLead()
    agent = _agent(telephony=telephony, nlp=nlp, db=db, now_fn=lambda: _WITHIN_HOURS)

    result = run(agent.call(lead, session=session))

    assert result.outcome == "interested"
    db.update_lead_status.assert_awaited_once_with(session, lead.id, LeadStatus.interested)


# ---------------------------------------------------------------------------
# Test 6 — Answered + intent=not_interested → status=not_interested (Req 2.7)
# ---------------------------------------------------------------------------

def test_answered_not_interested_updates_status_to_not_interested():
    """Answered call with intent=not_interested → lead status set to not_interested."""
    telephony = _make_telephony(status="answered")
    nlp = _make_nlp(intent=Intent.not_interested)
    db = _make_db()
    session = _make_session()
    lead = FakeLead()
    agent = _agent(telephony=telephony, nlp=nlp, db=db, now_fn=lambda: _WITHIN_HOURS)

    result = run(agent.call(lead, session=session))

    assert result.outcome == "not_interested"
    db.update_lead_status.assert_awaited_once_with(session, lead.id, LeadStatus.not_interested)


# ---------------------------------------------------------------------------
# Test 7 — Answered + intent=question → status=contacted (Req 2.8)
# ---------------------------------------------------------------------------

def test_answered_question_intent_updates_status_to_contacted():
    """Answered call with intent=question → lead status set to contacted."""
    telephony = _make_telephony(status="answered")
    nlp = _make_nlp(intent=Intent.question)
    db = _make_db()
    session = _make_session()
    lead = FakeLead()
    agent = _agent(telephony=telephony, nlp=nlp, db=db, now_fn=lambda: _WITHIN_HOURS)

    result = run(agent.call(lead, session=session))

    assert result.outcome == "question"
    db.update_lead_status.assert_awaited_once_with(session, lead.id, LeadStatus.contacted)


@pytest.mark.parametrize("intent", [
    Intent.objection,
    Intent.callback_requested,
    Intent.meeting_request,
    Intent.unknown,
])
def test_other_intents_update_status_to_contacted(intent: Intent):
    """Any intent that is not interested/not_interested → status=contacted."""
    telephony = _make_telephony(status="answered")
    nlp = _make_nlp(intent=intent)
    db = _make_db()
    session = _make_session()
    lead = FakeLead()
    agent = _agent(telephony=telephony, nlp=nlp, db=db, now_fn=lambda: _WITHIN_HOURS)

    run(agent.call(lead, session=session))

    db.update_lead_status.assert_awaited_once_with(session, lead.id, LeadStatus.contacted)


# ---------------------------------------------------------------------------
# Test 8 — Telephony API failure → task failed, retry counter (Req 2.10)
# ---------------------------------------------------------------------------

def test_telephony_failure_marks_task_failed():
    """Telephony raises exception → task status set to failed after retries."""
    telephony = MagicMock(spec=TelephonyAPI)
    telephony.initiate_call.side_effect = RuntimeError("Connection timeout")

    db = _make_db()
    session = _make_session()
    lead = FakeLead()
    task = FakeTask(retry_count=0)

    # max_retries=0 means one attempt only (no retries), so failure is immediate
    agent = _agent(telephony=telephony, db=db, max_retries=0, now_fn=lambda: _WITHIN_HOURS)

    result = run(agent.call(lead, session=session, task=task))

    assert result.outcome == "failed"
    assert result.error is not None
    db.update_task_status.assert_awaited_once_with(session, task.id, TaskStatus.failed)


def test_telephony_failure_retries_before_failing():
    """Telephony failure retries up to max_retries times."""
    telephony = MagicMock(spec=TelephonyAPI)
    telephony.initiate_call.side_effect = RuntimeError("Timeout")

    db = _make_db()
    session = _make_session()
    lead = FakeLead()
    task = FakeTask()

    # max_retries=2 → 3 total attempts
    agent = _agent(telephony=telephony, db=db, max_retries=2, now_fn=lambda: _WITHIN_HOURS)

    # Patch asyncio.sleep to avoid actual delays in tests
    with patch("app.agents.cold_calling.agent.asyncio.sleep", new_callable=AsyncMock):
        result = run(agent.call(lead, session=session, task=task))

    assert result.outcome == "failed"
    assert telephony.initiate_call.call_count == 3  # 1 initial + 2 retries


def test_telephony_succeeds_on_second_attempt():
    """Telephony fails once then succeeds → call proceeds normally."""
    telephony = MagicMock(spec=TelephonyAPI)
    telephony.initiate_call.side_effect = [
        RuntimeError("Timeout"),
        CallSession(call_id="call_ok", status="answered"),
    ]
    telephony.get_transcript.return_value = "I am interested."

    nlp = _make_nlp(intent=Intent.interested)
    db = _make_db()
    session = _make_session()
    lead = FakeLead()

    agent = _agent(telephony=telephony, nlp=nlp, db=db, max_retries=2, now_fn=lambda: _WITHIN_HOURS)

    with patch("app.agents.cold_calling.agent.asyncio.sleep", new_callable=AsyncMock):
        result = run(agent.call(lead, session=session))

    assert result.outcome == "interested"
    assert telephony.initiate_call.call_count == 2


# ---------------------------------------------------------------------------
# Test 9 — Interaction log written for every completed call (Req 2.9)
# ---------------------------------------------------------------------------

def test_interaction_log_written_for_answered_call():
    """Answered call → create_interaction_log called once."""
    telephony = _make_telephony(status="answered")
    nlp = _make_nlp(intent=Intent.interested)
    db = _make_db()
    session = _make_session()
    lead = FakeLead()
    agent = _agent(telephony=telephony, nlp=nlp, db=db, now_fn=lambda: _WITHIN_HOURS)

    run(agent.call(lead, session=session))

    db.create_interaction_log.assert_awaited_once()
    call_kwargs = db.create_interaction_log.call_args
    log_data = call_kwargs[0][1]  # second positional arg is the data dict
    assert log_data["lead_id"] == lead.id
    assert log_data["outcome"] == "interested"
    assert log_data["raw_transcript"] is not None


def test_interaction_log_written_for_voicemail():
    """Voicemail path → create_interaction_log called once."""
    telephony = _make_telephony(status="voicemail")
    db = _make_db()
    session = _make_session()
    lead = FakeLead()
    agent = _agent(telephony=telephony, db=db, now_fn=lambda: _WITHIN_HOURS)

    run(agent.call(lead, session=session))

    db.create_interaction_log.assert_awaited_once()


def test_interaction_log_not_written_for_deferred():
    """Deferred call (outside hours) → no interaction log."""
    db = _make_db()
    session = _make_session()
    lead = FakeLead()
    agent = _agent(db=db, now_fn=lambda: _OUTSIDE_HOURS)

    run(agent.call(lead, session=session))

    db.create_interaction_log.assert_not_awaited()


def test_interaction_log_not_written_for_blocked():
    """Blocked call (DNC) → no interaction log."""
    db = _make_db()
    session = _make_session()
    lead = FakeLead(phone="+15550001234")
    agent = _agent(db=db, dnc_list={"+15550001234"}, now_fn=lambda: _WITHIN_HOURS)

    run(agent.call(lead, session=session))

    db.create_interaction_log.assert_not_awaited()


# ---------------------------------------------------------------------------
# Unit tests for pure helper functions
# ---------------------------------------------------------------------------

def test_is_within_calling_hours_true():
    now = datetime(2024, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
    assert is_within_calling_hours("+1555", now=now, calling_hours_start=9, calling_hours_end=17)


def test_is_within_calling_hours_false_before():
    now = datetime(2024, 6, 1, 8, 59, 0, tzinfo=timezone.utc)
    assert not is_within_calling_hours("+1555", now=now, calling_hours_start=9, calling_hours_end=17)


def test_is_within_calling_hours_false_after():
    now = datetime(2024, 6, 1, 17, 0, 0, tzinfo=timezone.utc)
    assert not is_within_calling_hours("+1555", now=now, calling_hours_start=9, calling_hours_end=17)


def test_is_on_dnc_list_true():
    assert is_on_dnc_list("+15550001234", {"+15550001234", "+15550005678"})


def test_is_on_dnc_list_false():
    assert not is_on_dnc_list("+15550009999", {"+15550001234"})


def test_is_on_dnc_list_empty():
    assert not is_on_dnc_list("+15550001234", set())


def test_compute_backoff_seconds():
    assert compute_backoff_seconds(0) == 1.0   # 2^0 = 1
    assert compute_backoff_seconds(1) == 2.0   # 2^1 = 2
    assert compute_backoff_seconds(2) == 4.0   # 2^2 = 4
    assert compute_backoff_seconds(10) == 300.0  # capped at 300


def test_transcribe_call_returns_transcript():
    telephony = _make_telephony()
    telephony.get_transcript.return_value = "Hello world"
    agent = _agent(telephony=telephony)
    transcript = run(agent.transcribe_call("call_abc"))
    assert isinstance(transcript, Transcript)
    assert transcript.call_id == "call_abc"
    assert transcript.text == "Hello world"


def test_handle_voicemail_calls_leave_voicemail():
    telephony = _make_telephony()
    lead = FakeLead()
    agent = _agent(telephony=telephony)
    run(agent.handle_voicemail(lead, call_id="call_vm"))
    telephony.leave_voicemail.assert_called_once_with("call_vm", telephony.leave_voicemail.call_args[0][1])
