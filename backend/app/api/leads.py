"""Leads REST API endpoints."""
from __future__ import annotations

import csv
import io
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import get_session
from app.database.service import DatabaseService
from app.models.enums import LeadStatus

router = APIRouter()
db = DatabaseService()


class LeadCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    company: Optional[str] = None
    source: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None


class LeadUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None


class BulkAction(BaseModel):
    lead_ids: List[str]
    action: str  # 'change_status', 'mark_dnc', 'delete', 'export_csv'
    value: Optional[str] = None


@router.get("")
async def list_leads(
    status: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    from sqlalchemy import select, or_
    from app.models.lead import Lead

    q = select(Lead)
    if status:
        q = q.where(Lead.status == status)
    if source:
        q = q.where(Lead.source == source)
    if search:
        q = q.where(or_(
            Lead.first_name.ilike(f"%{search}%"),
            Lead.last_name.ilike(f"%{search}%"),
            Lead.email.ilike(f"%{search}%"),
            Lead.company.ilike(f"%{search}%"),
        ))
    q = q.offset(offset).limit(limit)
    result = await session.execute(q)
    leads = result.scalars().all()
    return [_lead_to_dict(l) for l in leads]


@router.post("")
async def create_lead(body: LeadCreate, session: AsyncSession = Depends(get_session)):
    data = body.model_dump()
    data["call_attempts"] = 0
    data["email_attempts"] = 0
    data["status"] = LeadStatus.new
    lead = await db.create_lead(session, data)
    await session.commit()
    return _lead_to_dict(lead)


@router.get("/{lead_id}")
async def get_lead(lead_id: str, session: AsyncSession = Depends(get_session)):
    lead = await db.get_lead(session, uuid.UUID(lead_id))
    if not lead:
        raise HTTPException(404, "Lead not found")
    return _lead_to_dict(lead)


@router.patch("/{lead_id}")
async def update_lead(lead_id: str, body: LeadUpdate, session: AsyncSession = Depends(get_session)):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    lead = await db.update_lead(session, uuid.UUID(lead_id), **fields)
    await session.commit()
    return _lead_to_dict(lead)


@router.delete("/{lead_id}")
async def delete_lead(lead_id: str, session: AsyncSession = Depends(get_session)):
    from sqlalchemy import delete
    from app.models.lead import Lead
    await session.execute(delete(Lead).where(Lead.id == uuid.UUID(lead_id)))
    await session.commit()
    return {"deleted": True}


@router.get("/{lead_id}/interactions")
async def get_interactions(lead_id: str, session: AsyncSession = Depends(get_session)):
    logs = await db.get_interactions_for_lead(session, uuid.UUID(lead_id))
    return [_log_to_dict(l) for l in logs]


@router.post("/bulk")
async def bulk_action(body: BulkAction, session: AsyncSession = Depends(get_session)):
    ids = [uuid.UUID(i) for i in body.lead_ids]
    if body.action == "change_status":
        for lid in ids:
            await db.update_lead_status(session, lid, body.value)
    elif body.action == "mark_dnc":
        for lid in ids:
            await db.update_lead_status(session, lid, LeadStatus.do_not_contact)
    elif body.action == "delete":
        from sqlalchemy import delete
        from app.models.lead import Lead
        for lid in ids:
            await session.execute(delete(Lead).where(Lead.id == lid))
    elif body.action == "export_csv":
        from sqlalchemy import select
        from app.models.lead import Lead
        result = await session.execute(select(Lead).where(Lead.id.in_(ids)))
        leads = result.scalars().all()
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["id","first_name","last_name","email","phone","company","status","source"])
        writer.writeheader()
        for l in leads:
            writer.writerow({"id": str(l.id), "first_name": l.first_name, "last_name": l.last_name,
                             "email": l.email, "phone": l.phone, "company": l.company,
                             "status": l.status, "source": l.source})
        output.seek(0)
        return StreamingResponse(output, media_type="text/csv",
                                 headers={"Content-Disposition": "attachment; filename=leads.csv"})
    await session.commit()
    return {"success": True, "count": len(ids)}


def _lead_to_dict(l) -> dict:
    return {
        "id": str(l.id), "first_name": l.first_name, "last_name": l.last_name,
        "email": l.email, "phone": l.phone, "company": l.company,
        "status": l.status, "source": l.source, "assigned_agent": l.assigned_agent,
        "call_attempts": l.call_attempts, "email_attempts": l.email_attempts,
        "last_contacted_at": l.last_contacted_at.isoformat() if l.last_contacted_at else None,
        "next_action_at": l.next_action_at.isoformat() if l.next_action_at else None,
        "demo_scheduled_at": l.demo_scheduled_at.isoformat() if l.demo_scheduled_at else None,
        "tags": l.tags or [], "notes": l.notes,
        "created_at": l.created_at.isoformat(), "updated_at": l.updated_at.isoformat(),
    }


def _log_to_dict(l) -> dict:
    return {
        "id": str(l.id), "lead_id": str(l.lead_id), "agent_type": l.agent_type,
        "channel": l.channel, "direction": l.direction,
        "timestamp": l.timestamp.isoformat(),
        "duration_seconds": l.duration_seconds, "summary": l.summary,
        "intent_detected": l.intent_detected, "outcome": l.outcome,
        "raw_transcript": l.raw_transcript,
    }
