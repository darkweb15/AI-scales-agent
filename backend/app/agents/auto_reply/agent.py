"""Auto Reply Agent — LLM-powered inbound email handler with RAG context.

No keyword matching. Real LLM intent classification + RAG-grounded replies.

Requirements: 6.1 – 6.8
"""
from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AgentType, Channel, Direction, Intent, LeadStatus

logger = logging.getLogger(__name__)

# Prompt injection guardrail — strip injection attempts from inbound content
_INJECTION_RE = re.compile(
    r"(ignore previous instructions|ignore all instructions|you are now|act as|"
    r"system prompt|<\|.*?\|>|\[INST\]|jailbreak|DAN mode)",
    re.IGNORECASE,
)


@dataclass
class InboundMessage:
    sender_email: str
    subject: str
    body: str
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))


@dataclass
class ReplyResult:
    outcome: str  # 'replied', 'escalated', 'suppressed'
    reply_text: Optional[str] = None
    intent: Optional[Intent] = None
    confidence: float = 0.0
    reasoning: str = ""


class AutoReplyAgent:
    """Handles inbound emails with real LLM reasoning + RAG product knowledge.
    
    Flow:
    1. Receive inbound email
    2. Sanitize against prompt injection (Req 8.7)
    3. Retrieve lead history for context
    4. LLM classifies intent (no keyword matching)
    5. If low confidence → escalate to human
    6. RAG retrieves relevant product knowledge
    7. LLM generates contextual, accurate reply
    8. Notify orchestrator for downstream routing
    """

    def __init__(
        self,
        db_service: Optional[Any] = None,
        email_provider: Optional[Any] = None,
        orchestrator: Optional[Any] = None,
        confidence_threshold: float = 0.75,
    ) -> None:
        self._db = db_service
        self._email = email_provider
        self._orchestrator = orchestrator
        self._threshold = confidence_threshold

        # Real LLM + RAG
        from app.core.agent_llm import get_agent_llm
        from app.core.rag_knowledge_base import get_rag_knowledge_base
        self._llm = get_agent_llm()
        self._rag = get_rag_knowledge_base()

    async def receive_message(self, message: InboundMessage, session: AsyncSession) -> ReplyResult:
        """Full inbound message handling pipeline. Req 6.1 – 6.8"""

        # Req 8.7 — sanitize inbound content against prompt injection
        safe_body = _INJECTION_RE.sub("[removed]", message.body)
        safe_subject = _INJECTION_RE.sub("[removed]", message.subject)
        safe_message = InboundMessage(
            sender_email=message.sender_email,
            subject=safe_subject,
            body=safe_body,
            received_at=message.received_at,
            message_id=message.message_id,
        )

        # Req 6.1 / 6.2 — lookup or create lead
        lead = None
        if self._db:
            lead = await self._db.find_lead_by_email(session, safe_message.sender_email)
            if lead is None:
                lead = await self._db.create_lead(session, {
                    "first_name": safe_message.sender_email.split("@")[0],
                    "last_name": "",
                    "email": safe_message.sender_email,
                    "status": LeadStatus.new,
                    "source": "inbound_email",
                    "call_attempts": 0,
                    "email_attempts": 0,
                })

        # Build interaction history context for LLM
        interaction_context = ""
        if lead and self._db:
            interactions = await self._db.get_interactions_for_lead(session, lead.id)
            if interactions:
                lines = [
                    f"- {i.timestamp.strftime('%Y-%m-%d')}: {i.channel} — {i.outcome}: {i.summary}"
                    for i in interactions[-5:]
                ]
                interaction_context = "\n".join(lines)

        # Step 1: LLM classifies intent (no keyword matching)
        full_text = f"Subject: {safe_message.subject}\n\n{safe_message.body}"
        lead_context = f"Lead history:\n{interaction_context}" if interaction_context else ""

        intent_result = self._llm.classify_intent(
            text=full_text,
            context=lead_context,
        )

        intent_str = intent_result.get("intent", "unknown")
        confidence = float(intent_result.get("confidence", 0.5))
        reasoning = intent_result.get("reasoning", "")
        next_action_hint = intent_result.get("next_action", "")

        try:
            intent = Intent(intent_str)
        except ValueError:
            intent = Intent.unknown

        logger.info(
            "📧 AutoReply: %s → intent=%s (%.2f confidence) — %s",
            safe_message.sender_email, intent_str, confidence, reasoning[:60],
        )

        # Req 6.3 — unsubscribe path (no LLM reply needed)
        if intent == Intent.unsubscribe:
            if self._db and lead:
                await self._db.update_lead_status(session, lead.id, LeadStatus.unsubscribed)
            reply = (
                "You've been successfully unsubscribed. "
                "You won't receive any further emails from us. "
                "If this was a mistake, please reply to this email."
            )
            await self._send_reply(safe_message.sender_email, "Unsubscribe Confirmation", reply)
            await self._log(session, lead, safe_message, intent, confidence, "suppressed")
            return ReplyResult(
                outcome="suppressed", reply_text=reply,
                intent=intent, confidence=confidence, reasoning=reasoning,
            )

        # Req 6.4 — low confidence → escalate to human
        if confidence < self._threshold:
            logger.info(
                "Low confidence (%.2f < %.2f) for %s — escalating to human",
                confidence, self._threshold, safe_message.sender_email,
            )
            await self._log(session, lead, safe_message, intent, confidence, "escalated")
            return ReplyResult(
                outcome="escalated", intent=intent,
                confidence=confidence, reasoning=reasoning,
            )

        # Step 2: RAG — retrieve relevant product knowledge for this message
        rag_context = self._rag.retrieve(
            query=f"{safe_message.subject} {safe_message.body}",
            top_k=3,
        )

        # Step 3: LLM generates contextual reply using RAG knowledge
        lead_name = f"{lead.first_name} {lead.last_name}".strip() if lead else "there"
        reply_text = self._llm.generate_inbound_reply(
            message=safe_message.body,
            lead_name=lead_name,
            intent=intent_str,
            rag_context=rag_context,
            interaction_history=interaction_context,
        )

        # Req 6.5 — send reply
        await self._send_reply(
            safe_message.sender_email,
            f"Re: {safe_message.subject}",
            reply_text,
        )

        # Req 6.7 — log interaction
        await self._log(session, lead, safe_message, intent, confidence, "replied")

        # Update lead status based on intent
        new_status = self._intent_to_status(intent)
        if new_status and self._db and lead:
            await self._db.update_lead_status(session, lead.id, new_status)

        # Req 6.8 — notify orchestrator for downstream routing
        if self._orchestrator and lead:
            from app.orchestrator.orchestrator import TaskOutcome
            await self._orchestrator.handle_outcome(TaskOutcome(
                lead_id=lead.id,
                new_status=new_status,
                last_contacted_at=datetime.now(timezone.utc),
            ))

        return ReplyResult(
            outcome="replied",
            reply_text=reply_text,
            intent=intent,
            confidence=confidence,
            reasoning=reasoning,
        )

    def _intent_to_status(self, intent: Intent) -> Optional[LeadStatus]:
        mapping = {
            Intent.interested:      LeadStatus.interested,
            Intent.meeting_request: LeadStatus.interested,
            Intent.not_interested:  LeadStatus.not_interested,
            Intent.unsubscribe:     LeadStatus.unsubscribed,
        }
        return mapping.get(intent)

    async def _send_reply(self, to: str, subject: str, body: str) -> None:
        if self._email:
            self._email.send(to=to, subject=subject, body=body, email_id=str(uuid.uuid4()))
        else:
            logger.info("📤 [No email provider] Would send to %s: %s", to, subject)

    async def _log(
        self,
        session: AsyncSession,
        lead: Any,
        message: InboundMessage,
        intent: Intent,
        confidence: float,
        outcome: str,
    ) -> None:
        if not self._db or not lead:
            return
        await self._db.create_interaction_log(session, {
            "lead_id": lead.id,
            "agent_type": AgentType.auto_reply,
            "channel": Channel.email,
            "direction": Direction.inbound,
            "timestamp": datetime.now(timezone.utc),
            "summary": (
                f"Inbound email — intent: {intent.value}, "
                f"confidence: {confidence:.2f}, outcome: {outcome}"
            ),
            "intent_detected": intent,
            "outcome": outcome,
            "raw_transcript": f"Subject: {message.subject}\n\n{message.body}",
        })
