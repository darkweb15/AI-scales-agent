"""Follow-up Agent — re-engages unresponsive leads via alternating channels.

Requirements: 3.1 – 3.7
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import AgentType, Channel, Direction, Intent, LeadStatus

logger = logging.getLogger(__name__)


@dataclass
class FollowUpResult:
    outcome: str  # 'escalated', 'called', 'emailed', 'failed'
    channel: Optional[str] = None
    error: Optional[str] = None


class FollowUpAgent:
    """Re-engages leads that did not respond to initial outreach.

    Constructor-injected dependencies for full testability.
    """

    def __init__(
        self,
        db_service: Optional[Any] = None,
        cold_calling_agent: Optional[Any] = None,
        auto_mail_agent: Optional[Any] = None,
        llm_service: Optional[Any] = None,
        max_total_follow_up_attempts: int = 5,
    ) -> None:
        self._db = db_service
        self._calling = cold_calling_agent
        self._mail = auto_mail_agent
        self._llm = llm_service
        self._max_attempts = max_total_follow_up_attempts

    # ------------------------------------------------------------------
    # Channel selection (pure — no I/O)
    # ------------------------------------------------------------------

    def select_channel(self, lead: Any, last_interaction: Optional[Any] = None) -> str:
        """Alternate channels to avoid fatigue. Never returns 'sms' for null-phone leads.

        Requirements 3.2, 3.3, 3.4, 3.5
        """
        if last_interaction is None:
            return Channel.call.value  # Req 3.5 — default to call

        if last_interaction.channel == Channel.call.value:
            return Channel.email.value  # Req 3.2

        if last_interaction.channel == Channel.email.value:
            if lead.phone:
                return Channel.call.value  # Req 3.3
            return Channel.email.value  # Req 3.4 — no phone, stay on email

        return Channel.email.value

    # ------------------------------------------------------------------
    # Execute follow-up
    # ------------------------------------------------------------------

    async def execute_follow_up(
        self,
        lead: Any,
        session: AsyncSession,
        task: Optional[Any] = None,
    ) -> FollowUpResult:
        """Execute a follow-up action for the lead.

        Requirements 3.1, 3.6, 3.7
        """
        total_attempts = (lead.call_attempts or 0) + (lead.email_attempts or 0)

        # Req 3.1 — max attempts reached → escalate
        if total_attempts >= self._max_attempts:
            logger.info("Lead %s reached max follow-up attempts, escalating", lead.id)
            if self._db:
                await self._db.update_lead_status(session, lead.id, LeadStatus.not_interested)
            await self._log_interaction(session, lead, Channel.email.value, "escalated", "Max attempts reached — escalated to human review")
            return FollowUpResult(outcome="escalated")

        # Get last interaction for channel selection
        last_interaction = None
        if self._db:
            last_interaction = await self._db.get_last_interaction(session, lead.id)

        channel = self.select_channel(lead, last_interaction)

        # Req 3.6 — personalize content using prior context
        context_summary = ""
        if last_interaction and self._llm:
            context_summary = f"Prior interaction: {last_interaction.summary}"

        try:
            if channel == Channel.call.value and self._calling:
                result = await self._calling.call(lead, session=session, task=task)
                outcome = result.outcome
            elif self._mail:
                from app.models.email_template import EmailTemplate
                template = EmailTemplate(
                    id=uuid.uuid4(),
                    name="follow_up",
                    subject_template="Following up, {first_name}",
                    body_template=f"Hi {{first_name}},\n\nJust following up on our previous conversation. {context_summary}\n\nWould love to connect!\n\nBest,\nSales Team",
                    agent_type=AgentType.follow_up,
                    stage=LeadStatus.contacted,
                    variables=["first_name"],
                )
                result = await self._mail.send_email(session, lead, template)
                outcome = result.outcome
            else:
                outcome = "failed"

            # Req 3.7 — log interaction
            await self._log_interaction(session, lead, channel, outcome, f"Follow-up via {channel} — {outcome}")
            return FollowUpResult(outcome=outcome, channel=channel)

        except Exception as exc:
            logger.exception("Follow-up failed for lead %s: %s", lead.id, exc)
            return FollowUpResult(outcome="failed", channel=channel, error=str(exc))

    async def schedule_follow_up(self, lead: Any, delay_hours: int = 24) -> str:
        """Enqueue a deferred follow-up task. Returns a placeholder task ID."""
        logger.info("Scheduling follow-up for lead %s in %dh", lead.id, delay_hours)
        return f"followup_{lead.id}_{delay_hours}h"

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _log_interaction(
        self,
        session: AsyncSession,
        lead: Any,
        channel: str,
        outcome: str,
        summary: str,
    ) -> None:
        if not self._db:
            return
        await self._db.create_interaction_log(session, {
            "lead_id": lead.id,
            "agent_type": AgentType.follow_up,
            "channel": channel,
            "direction": Direction.outbound,
            "timestamp": datetime.now(timezone.utc),
            "summary": summary,
            "outcome": outcome,
        })
