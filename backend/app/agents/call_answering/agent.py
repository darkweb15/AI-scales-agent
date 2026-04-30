"""Call Answering Agent — RAG-powered inbound call handler.

Uses ChromaDB RAG to retrieve relevant Pebble product knowledge before
answering any question. LLM reasons about caller intent — no keyword matching.

Requirements: 7.1 – 7.6
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AgentType, Channel, Direction, Intent, LeadStatus

logger = logging.getLogger(__name__)


@dataclass
class QualificationResult:
    outcome: str  # 'qualified', 'transferred', 'answered', 'unknown'
    intent: Optional[Intent] = None
    confidence: float = 0.0
    transcript: str = ""
    lead_id: Optional[Any] = None
    answer_given: str = ""
    reasoning: str = ""


class CallAnsweringAgent:
    """Handles inbound calls using RAG + LLM reasoning.
    
    Flow:
    1. Receive inbound call transcript/question
    2. Retrieve relevant product knowledge from ChromaDB (RAG)
    3. LLM classifies intent from transcript
    4. LLM generates accurate answer using retrieved context
    5. If low confidence or human requested → transfer
    6. Log everything
    """

    def __init__(
        self,
        db_service: Optional[Any] = None,
        telephony_api: Optional[Any] = None,
        confidence_threshold: float = 0.65,
    ) -> None:
        self._db = db_service
        self._telephony = telephony_api
        self._threshold = confidence_threshold

        # Real LLM + RAG (no stubs)
        from app.core.agent_llm import get_agent_llm
        from app.core.rag_knowledge_base import get_rag_knowledge_base
        self._llm = get_agent_llm()
        self._rag = get_rag_knowledge_base()

    async def answer_call(
        self,
        call_id: str,
        caller_phone: str,
        session: AsyncSession,
        transcript: str = "",
    ) -> QualificationResult:
        """Full inbound call handling pipeline. Req 7.1–7.6"""

        # Req 7.5 — lookup existing lead by phone
        lead = None
        if self._db:
            lead = await self._db.find_lead_by_phone(session, caller_phone)

        # Get interaction history for context
        interaction_history = ""
        if lead and self._db:
            interactions = await self._db.get_interactions_for_lead(session, lead.id)
            if interactions:
                history_lines = [
                    f"- {i.timestamp.strftime('%Y-%m-%d')}: {i.channel} — {i.summary}"
                    for i in interactions[-5:]
                ]
                interaction_history = "\n".join(history_lines)

        # Get transcript from telephony if not provided
        if not transcript and self._telephony:
            transcript = self._telephony.get_transcript(call_id)

        # Run qualification with RAG + LLM
        result = await self.qualify_caller(
            call_id=call_id,
            transcript=transcript,
            caller_name=lead.first_name if lead else "Caller",
            interaction_history=interaction_history,
        )

        # Req 7.6 — create new lead if not found
        if lead is None and self._db:
            lead = await self._db.create_lead(session, {
                "first_name": "Inbound",
                "last_name": "Caller",
                "email": f"inbound_{caller_phone.replace('+', '').replace(' ', '')}@unknown.com",
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

        # Req 7.4 — log full call
        await self.log_call(call_id, result, lead, session)

        return result

    async def qualify_caller(
        self,
        call_id: str,
        transcript: str,
        caller_name: str = "Caller",
        interaction_history: str = "",
    ) -> QualificationResult:
        """RAG + LLM qualification — no keyword matching.
        
        1. Retrieve relevant product knowledge for the question
        2. LLM classifies intent
        3. LLM generates accurate answer using RAG context
        """
        if not transcript:
            return QualificationResult(
                outcome="unknown",
                confidence=0.3,
                transcript="",
                answer_given="Hello! How can I help you today?",
            )

        # Step 1: RAG — retrieve relevant product knowledge
        rag_context = self._rag.retrieve(transcript, top_k=3)
        logger.debug("RAG retrieved context for call %s: %d chars", call_id, len(rag_context))

        # Step 2: LLM classifies intent
        intent_result = self._llm.classify_intent(
            text=transcript,
            context=f"Inbound call to Pebble POS. Caller history: {interaction_history}",
        )

        intent_str = intent_result.get("intent", "unknown")
        confidence = float(intent_result.get("confidence", 0.5))
        reasoning = intent_result.get("reasoning", "")

        # Map string to Intent enum
        try:
            intent = Intent(intent_str)
        except ValueError:
            intent = Intent.unknown

        # Check for explicit human transfer request
        transfer_phrases = ["speak to a human", "talk to someone", "real person", "agent please", "transfer me"]
        if any(phrase in transcript.lower() for phrase in transfer_phrases):
            return QualificationResult(
                outcome="transfer_requested",
                intent=intent,
                confidence=confidence,
                transcript=transcript,
                reasoning=reasoning,
            )

        # Step 3: LLM generates answer using RAG context
        answer = self._llm.answer_inbound_call_question(
            question=transcript,
            caller_name=caller_name,
            rag_context=rag_context,
            conversation_history=interaction_history,
        )

        outcome = "answered" if confidence >= self._threshold else "unknown"

        return QualificationResult(
            outcome=outcome,
            intent=intent,
            confidence=confidence,
            transcript=transcript,
            answer_given=answer,
            reasoning=reasoning,
        )

    async def handle_conversation_turn(
        self,
        call_id: str,
        caller_message: str,
        conversation_history: List[Dict],
        caller_name: str = "Caller",
    ) -> str:
        """Handle a single turn in an ongoing call conversation.
        
        Used for multi-turn conversations where the caller asks multiple questions.
        Each turn retrieves fresh RAG context for the specific question.
        """
        # RAG retrieval for this specific question
        rag_context = self._rag.retrieve(caller_message, top_k=3)

        # Build conversation history string
        history_str = ""
        if conversation_history:
            history_str = "\n".join([
                f"{turn.get('role', 'unknown')}: {turn.get('content', '')}"
                for turn in conversation_history[-6:]  # last 6 turns
            ])

        # LLM answers with RAG context
        answer = self._llm.answer_inbound_call_question(
            question=caller_message,
            caller_name=caller_name,
            rag_context=rag_context,
            conversation_history=history_str,
        )

        logger.info("📞 Call %s turn answered: %s...", call_id, answer[:50])
        return answer

    async def route_to_human(self, call_id: str, reason: str) -> None:
        """Transfer call to human representative. Req 7.2, 7.3"""
        logger.info("👤 Routing call %s to human — reason: %s", call_id, reason)
        if self._telephony and hasattr(self._telephony, "transfer_to_human"):
            self._telephony.transfer_to_human(call_id, reason)

    async def log_call(
        self,
        call_id: str,
        result: QualificationResult,
        lead: Any,
        session: AsyncSession,
    ) -> None:
        """Persist full transcript, RAG answer, and qualification outcome. Req 7.4"""
        if not self._db or not lead:
            return

        summary = (
            f"Inbound call — outcome: {result.outcome}, "
            f"intent: {result.intent}, "
            f"confidence: {result.confidence:.2f}, "
            f"reasoning: {result.reasoning}"
        )

        await self._db.create_interaction_log(session, {
            "lead_id": lead.id,
            "agent_type": AgentType.call_answering,
            "channel": Channel.call,
            "direction": Direction.inbound,
            "timestamp": datetime.now(timezone.utc),
            "summary": summary,
            "intent_detected": result.intent,
            "outcome": result.outcome,
            "raw_transcript": f"TRANSCRIPT:\n{result.transcript}\n\nAI ANSWER:\n{result.answer_given}",
        })
