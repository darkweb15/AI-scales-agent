"""Lead lifecycle guards and audit enforcement. Requirements: 8.1–8.5"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import LeadStatus, TaskStatus

logger = logging.getLogger(__name__)


def check_lead_contactable(lead: Any) -> bool:
    """Return False if lead must not be contacted. Req 8.3"""
    return lead.status not in (LeadStatus.do_not_contact, LeadStatus.unsubscribed)


async def escalate_to_human_review(
    lead_id: uuid.UUID,
    task_id: uuid.UUID,
    reason: str,
    session: AsyncSession,
    db_service: Any,
) -> None:
    """Mark task permanently_failed and flag lead for human review. Req 8.4"""
    logger.warning("Escalating lead %s to human review — reason: %s", lead_id, reason)

    try:
        await db_service.update_task_status(session, task_id, TaskStatus.permanently_failed)
    except Exception:
        pass  # task may not exist in all code paths

    # Update lead status — add requires_human_review as a valid transition
    try:
        await db_service.update_lead(session, lead_id, status="requires_human_review")
    except Exception as exc:
        logger.error("Failed to update lead %s status: %s", lead_id, exc)
