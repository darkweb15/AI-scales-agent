"""Cold Calling Agent.

Implements Requirements 2.1 – 2.10:
  2.1  DNC check → blocked outcome, status=do_not_contact
  2.2  Calling-hours guard → deferred outcome
  2.3  no_answer / busy → increment call_attempts, no_answer outcome
  2.4  voicemail → leave scripted voicemail, voicemail outcome
  2.5  answered → run AI conversation, transcribe, extract intent
  2.6  intent=interested → status=interested
  2.7  intent=not_interested → status=not_interested
  2.8  other intent → status=contacted
  2.9  log every call interaction to InteractionLog
  2.10 telephony failure → mark task failed, increment retry, exponential backoff
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional, Set

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AgentType, Channel, Direction, Intent, LeadStatus, TaskStatus

from .nlp import NLPEngine, StubNLPEngine
from .scripts import load_script
from .telephony import CallSession, TelephonyAPI, StubTelephonyAPI

logger = logging.getLogger(__name__)


@dataclass
class Transcript:
    """Represents a transcribed call."""

    call_id: str
    text: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class CallResult:
    """Outcome of a single call attempt."""

    # 'deferred', 'blocked', 'no_answer', 'voicemail',
    # 'interested', 'not_interested', 'contacted', 'failed'
    outcome: str
    transcript: Optional[str] = None
    intent: Optional[Intent] = None
    call_id: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Calling-hours helper (pure, injectable for testing)
# ---------------------------------------------------------------------------

def is_within_calling_hours(
    phone: str,
    now: Optional[datetime] = None,
    calling_hours_start: int = 9,
    calling_hours_end: int = 17,
) -> bool:
    """Return True if *now* falls within the configured calling window.

    The check is performed in UTC for simplicity; a production implementation
    would resolve the lead's local timezone from the phone number prefix.

    Parameters
    ----------
    phone:
        Lead phone number (used for timezone lookup in production).
    now:
        Current time.  Defaults to ``datetime.now(timezone.utc)``.
    calling_hours_start:
        First hour of the calling window (inclusive, 24h format).
    calling_hours_end:
        Last hour of the calling window (exclusive, 24h format).
    """
    if now is None:
        now = datetime.now(timezone.utc)
    return calling_hours_start <= now.hour < calling_hours_end


# ---------------------------------------------------------------------------
# DNC list helper (pure, injectable for testing)
# ---------------------------------------------------------------------------

def is_on_dnc_list(phone: str, dnc_list: Optional[Set[str]] = None) -> bool:
    """Return True if *phone* is on the do-not-call list."""
    if dnc_list is None:
        return False
    return phone in dnc_list


# ---------------------------------------------------------------------------
# Exponential backoff helper
# ---------------------------------------------------------------------------

def compute_backoff_seconds(retry_count: int, base: float = 2.0, cap: float = 300.0) -> float:
    """Return the backoff delay in seconds for the given retry attempt.

    Uses ``base ** retry_count`` capped at *cap* seconds.
    """
    return min(base ** retry_count, cap)


# ---------------------------------------------------------------------------
# ColdCallingAgent
# ---------------------------------------------------------------------------

class ColdCallingAgent:
    """Autonomous agent that initiates outbound AI-driven phone calls.

    All external dependencies (telephony, NLP, database) are injected via
    the constructor so the agent is fully testable without infrastructure.

    Parameters
    ----------
    telephony_api:
        Telephony provider implementation.
    nlp_engine:
        NLP engine for intent extraction.
    db_service:
        DatabaseService instance for persisting outcomes.
    dnc_list:
        Set of phone numbers on the do-not-call list.
    calling_hours_start / calling_hours_end:
        Configurable calling window (24h, inclusive start, exclusive end).
    max_retries:
        Maximum number of telephony retries before marking the task failed.
    """

    def __init__(
        self,
        telephony_api: Optional[TelephonyAPI] = None,
        nlp_engine: Optional[NLPEngine] = None,
        db_service: Optional[Any] = None,
        dnc_list: Optional[Set[str]] = None,
        calling_hours_start: int = 9,
        calling_hours_end: int = 17,
        max_retries: int = 3,
        now_fn=None,  # injectable clock for testing
    ) -> None:
        self._telephony = telephony_api or StubTelephonyAPI()
        self._nlp = nlp_engine or StubNLPEngine()
        self._db = db_service
        self._dnc_list: Set[str] = dnc_list or set()
        self._calling_hours_start = calling_hours_start
        self._calling_hours_end = calling_hours_end
        self._max_retries = max_retries
        self._now_fn = now_fn or (lambda: datetime.now(timezone.utc))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def call(
        self,
        lead: Any,
        session: Optional[AsyncSession] = None,
        task: Optional[Any] = None,
    ) -> CallResult:
        """Execute an outbound call for *lead*.

        Implements the full call flow from the design pseudocode:
          1. Calling-hours guard (Req 2.2)
          2. DNC check (Req 2.1)
          3. Initiate call via telephony API (with retry on failure, Req 2.10)
          4. Handle no_answer / busy (Req 2.3)
          5. Handle voicemail (Req 2.4)
          6. Handle answered: transcribe, extract intent, update status (Req 2.5–2.8)
          7. Log interaction (Req 2.9)
        """
        now = self._now_fn()

        # Req 2.2 — calling-hours guard (checked FIRST per design pseudocode)
        if not is_within_calling_hours(
            lead.phone or "",
            now=now,
            calling_hours_start=self._calling_hours_start,
            calling_hours_end=self._calling_hours_end,
        ):
            logger.info("Call deferred for lead %s: outside calling hours", lead.id)
            return CallResult(outcome="deferred")

        # Req 2.1 — DNC check
        if is_on_dnc_list(lead.phone or "", self._dnc_list):
            logger.info("Call blocked for lead %s: phone on DNC list", lead.id)
            if session and self._db:
                await self._db.update_lead_status(session, lead.id, LeadStatus.do_not_contact)
            return CallResult(outcome="blocked")

        # Req 2.10 — initiate call with exponential backoff retry
        call_session: Optional[CallSession] = None
        last_error: Optional[str] = None
        retry_count = getattr(task, "retry_count", 0) if task else 0

        for attempt in range(self._max_retries + 1):
            try:
                call_session = self._telephony.initiate_call(lead.phone or "")
                break  # success
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "Telephony API failure for lead %s (attempt %d/%d): %s",
                    lead.id, attempt + 1, self._max_retries + 1, exc,
                )
                if attempt < self._max_retries:
                    backoff = compute_backoff_seconds(attempt)
                    logger.info("Retrying in %.1f seconds…", backoff)
                    await asyncio.sleep(backoff)

        if call_session is None:
            # All retries exhausted — mark task failed (Req 2.10)
            logger.error("All telephony retries exhausted for lead %s", lead.id)
            if session and self._db and task:
                await self._db.update_task_status(session, task.id, TaskStatus.failed)
            return CallResult(outcome="failed", error=last_error)

        # Req 2.3 — no_answer / busy
        if call_session.status in ("no_answer", "busy"):
            if session and self._db:
                await self._db.increment_call_attempts(session, lead.id)
            return CallResult(outcome="no_answer", call_id=call_session.call_id)

        # Req 2.4 — voicemail
        if call_session.status == "voicemail":
            await self.handle_voicemail(lead, call_session.call_id)
            if session and self._db:
                await self._db.increment_call_attempts(session, lead.id)
                await self._log_interaction(
                    session=session,
                    lead=lead,
                    call_id=call_session.call_id,
                    transcript=None,
                    intent=None,
                    outcome="voicemail",
                    duration=call_session.duration_seconds,
                )
            return CallResult(outcome="voicemail", call_id=call_session.call_id)

        # Req 2.5 — call answered: transcribe and extract intent
        transcript_obj = await self.transcribe_call(call_session.call_id)
        intent = self._nlp.extract_intent(transcript_obj.text)

        # Req 2.9 — log interaction
        if session and self._db:
            await self._db.increment_call_attempts(session, lead.id)
            await self._log_interaction(
                session=session,
                lead=lead,
                call_id=call_session.call_id,
                transcript=transcript_obj.text,
                intent=intent,
                outcome=intent.value,
                duration=call_session.duration_seconds,
            )

            # Req 2.6 / 2.7 / 2.8 — update lead status based on intent
            new_status = self._intent_to_status(intent)
            await self._db.update_lead_status(session, lead.id, new_status)

        return CallResult(
            outcome=intent.value,
            transcript=transcript_obj.text,
            intent=intent,
            call_id=call_session.call_id,
        )

    async def handle_voicemail(self, lead: Any, call_id: Optional[str] = None) -> None:
        """Leave a scripted voicemail for *lead* (Req 2.4)."""
        script = load_script("voicemail", lead)
        effective_call_id = call_id or f"vm_{getattr(lead, 'id', 'unknown')}"
        self._telephony.leave_voicemail(effective_call_id, script)
        logger.info("Voicemail left for lead %s (call_id=%s)", getattr(lead, "id", "?"), effective_call_id)

    async def transcribe_call(self, call_id: str) -> Transcript:
        """Fetch and return the transcript for *call_id* (Req 2.5)."""
        raw_text = self._telephony.get_transcript(call_id)
        return Transcript(call_id=call_id, text=raw_text)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _intent_to_status(self, intent: Intent) -> LeadStatus:
        """Map extracted intent to the appropriate LeadStatus (Req 2.6–2.8)."""
        if intent == Intent.interested:
            return LeadStatus.interested
        if intent == Intent.not_interested:
            return LeadStatus.not_interested
        return LeadStatus.contacted

    async def _log_interaction(
        self,
        session: AsyncSession,
        lead: Any,
        call_id: Optional[str],
        transcript: Optional[str],
        intent: Optional[Intent],
        outcome: str,
        duration: Optional[int] = None,
    ) -> None:
        """Persist an InteractionLog entry for the call (Req 2.9)."""
        if not self._db:
            return

        summary = f"Outbound call — outcome: {outcome}"
        if intent:
            summary += f", intent: {intent.value}"

        await self._db.create_interaction_log(
            session,
            {
                "lead_id": lead.id,
                "agent_type": AgentType.cold_calling,
                "channel": Channel.call,
                "direction": Direction.outbound,
                "timestamp": datetime.now(timezone.utc),
                "duration_seconds": duration,
                "summary": summary,
                "intent_detected": intent,
                "outcome": outcome,
                "raw_transcript": transcript,
            },
        )
