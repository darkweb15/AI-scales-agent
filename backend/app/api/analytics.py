"""Analytics REST API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import get_session
from app.models.lead import Lead
from app.models.interaction_log import InteractionLog
from app.models.enums import LeadStatus

router = APIRouter()


@router.get("/kpis")
async def get_kpis(session: AsyncSession = Depends(get_session)):
    """KPI summary cards — real data from database."""
    from sqlalchemy import select, func as sqlfunc
    from app.models.lead import Lead
    from app.models.interaction_log import InteractionLog

    total_leads = (await session.execute(select(sqlfunc.count(Lead.id)))).scalar() or 0

    # Count leads with phone numbers
    with_phone = (await session.execute(
        select(sqlfunc.count(Lead.id)).where(Lead.phone.isnot(None))
    )).scalar() or 0

    # Count leads with emails
    with_email = (await session.execute(
        select(sqlfunc.count(Lead.id)).where(Lead.email.isnot(None))
    )).scalar() or 0

    # Total call attempts across all leads
    total_calls = (await session.execute(
        select(sqlfunc.sum(Lead.call_attempts))
    )).scalar() or 0

    # Total email attempts across all leads
    total_emails = (await session.execute(
        select(sqlfunc.sum(Lead.email_attempts))
    )).scalar() or 0

    demos = (await session.execute(
        select(sqlfunc.count(Lead.id)).where(
            Lead.status.in_(["demo_scheduled", "demo_completed"])
        )
    )).scalar() or 0

    converted = (await session.execute(
        select(sqlfunc.count(Lead.id)).where(Lead.status == LeadStatus.converted)
    )).scalar() or 0

    conversion_rate = round((converted / total_leads * 100), 2) if total_leads else 0

    return {
        "total_leads": total_leads,
        "leads_with_phone": with_phone,
        "leads_with_email": with_email,
        "calls_made": int(total_calls),
        "emails_sent": int(total_emails),
        "demos_scheduled": demos,
        "converted": converted,
        "conversion_rate": conversion_rate,
    }


@router.get("/funnel")
async def get_funnel(session: AsyncSession = Depends(get_session)):
    """Pipeline funnel counts per status."""
    result = await session.execute(
        select(Lead.status, func.count(Lead.id)).group_by(Lead.status)
    )
    rows = result.all()
    return [{"status": r[0], "count": r[1]} for r in rows]


@router.get("/agent-performance")
async def get_agent_performance(session: AsyncSession = Depends(get_session)):
    """Tasks completed per agent."""
    result = await session.execute(
        select(InteractionLog.agent_type, func.count(InteractionLog.id))
        .group_by(InteractionLog.agent_type)
    )
    rows = result.all()
    return [{"agent_type": r[0], "total_interactions": r[1]} for r in rows]


@router.get("/call-outcomes")
async def get_call_outcomes(session: AsyncSession = Depends(get_session)):
    """Call outcome distribution."""
    result = await session.execute(
        select(InteractionLog.outcome, func.count(InteractionLog.id))
        .where(InteractionLog.channel == "call")
        .group_by(InteractionLog.outcome)
    )
    rows = result.all()
    return [{"outcome": r[0], "count": r[1]} for r in rows]


@router.get("/lead-sources")
async def get_lead_sources(session: AsyncSession = Depends(get_session)):
    """Lead count by source."""
    result = await session.execute(
        select(Lead.source, func.count(Lead.id)).group_by(Lead.source)
    )
    rows = result.all()
    return [{"source": r[0] or "unknown", "count": r[1]} for r in rows]
