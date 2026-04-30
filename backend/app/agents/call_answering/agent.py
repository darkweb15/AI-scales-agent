"""Call Answering Agent — handles inbound calls, qualifies callers, routes to humans.

Requirements: 7.1 – 7.6
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AgentType, Channel, Direction, Intent, LeadStatus

logger = logging.getLogger(__name__)


@dataclass
class QualificationResult:
    outcome: str  # 'qualified', 'transferred', 'unknown'
    intent: Optional[Intent] = None
    confidence: float = 0.0
    transcript: str = ""
    lead_id: Optional[Any] = None


class CallAnsweringAgent:
    """Handles inbound calls autonomously and routes to humans when needed."""

    def __init__(
        self,
        db_service: Optional[Any] = None,
        telephony_api: Optional[Any] = None,
        nlp_engine: Optional[Any] = None,
        confidence_threshold: float = 0.70,
    ) -> None:
        self._db = db_service
        self._telephony = telephony_api
        self._nlp = nlp_engine
        self._threshold = confidence_threshold

    async def answer_call(
        self,
        call_id: str,
        caller_phone: str,
        session: AsyncSession,
    ) -> QualificationResult:
        """Answer inbound call, qualify caller, route if needed. Req 7.1–7.6"""

        # Req 7.5 — lookup existing lead
        lead = None
        if self._db:
            lead = await self._db.find_lead_by_phone(session, caller_phone)

        # Run qualification conversation
        result = await self.qualify_caller(call_id)

        # Req 7.6 — create new lead if not found
        if lead is None and self._db:
            lead = await self._db.create_lead(session, {
                "first_name": "Inbound",
                "last_name": "Caller",
                "email": f"inbound_{caller_phone.replace('+','')}@unknown.com",
                "phone": caller_phone,
                "status": LeadStatus.new,
                "source": "inbound_call",
                "call_attempts": 0,
                "email_attempts": 0,
            })

        result.lead_id = lead.id if lead else None

        # Req 7.2 / 7.3 — transfer to human if requested or low confidence
        if result.outcome == "transfer_requested" or result.confidence < self._threshold:
            reason = "caller_requested" if result.outcome == "transfer_requested" else "low_confidence"
            await self.route_to_human(call_id, reason)
            result.outcome = "transferred"

        # Req 7.4 — log call
        await self.log_call(call_id, result, lead, session)

        return result

    async def qualify_caller(self, call_id: str) -> QualificationResult:
        """Run AI qualification conversation. Req 7.1"""
        transcript = ""
        if self._telephony:
            transcript = self._telephony.get_transcript(call_id)

        intent = Intent.unknown
        confidence = 0.5

        if self._nlp and transcript:
            intent = self._nlp.extract_intent(transcript)
            confidence = self._nlp.get_confidence_score(intent)

        # Check for explicit human transfer request
        transfer_keywords = ["speak to a human", "talk to someone", "real person", "agent please"]
        if any(kw in transcript.lower() for kw in transfer_keywords):
            return QualificationResult(
                outcome="transfer_requested",
                intent=intent,
                confidence=confidence,
                transcript=transcript,
            )

        outcome = "qualified" if confidence >= self._threshold else "unknown"
        return QualificationResult(
            outcome=outcome,
            intent=intent,
            confidence=confidence,
            transcript=transcript,
        )

    async def route_to_human(self, call_id: str, reason: str) -> None:
        """Transfer call to human representative queue. Req 7.2, 7.3"""
        logger.info("Routing call %s to human — reason: %s", call_id, reason)
        if self._telephony and hasattr(self._telephony, "transfer_to_human"):
            self._telephony.transfer_to_human(call_id, reason)

    async def log_call(
        self,
        call_id: str,
        result: QualificationResult,
        lead: Any,
        session: AsyncSession,
    ) -> None:
        """Persist transcript and qualification outcome. Req 7.4"""
        if not self._db or not lead:
            return
        await self._db.create_interaction_log(session, {
            "lead_id": lead.id,
            "agent_type": AgentType.call_answering,
            "channel": Channel.call,
            "direction": Direction.inbound,
            "timestamp": datetime.now(timezone.utc),
            "summary": f"Inbound call — outcome: {result.outcome}, intent: {result.intent}",
            "intent_detected": result.intent,
            "outcome": result.outcome,
            "raw_transcript": result.transcript,
        })
