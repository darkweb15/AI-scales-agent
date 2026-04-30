"""Email campaign API — send Pebble intro emails to leads."""
from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import get_session

router = APIRouter()
logger = logging.getLogger(__name__)


class CampaignRequest(BaseModel):
    limit: int = 10
    source: Optional[str] = None  # filter by source


@router.post("/send-intro-emails")
async def send_intro_emails(
    body: CampaignRequest,
    session: AsyncSession = Depends(get_session),
):
    """Send Pebble intro emails to leads with real email addresses."""
    from app.core.smart_sequence import SmartSequenceEngine
    from app.database.service import DatabaseService
    from app.models.enums import LeadStatus
    from dotenv import load_dotenv
    import os
    load_dotenv()  # Force reload

    db = DatabaseService()
    engine = SmartSequenceEngine()

    # Get leads with real emails (not placeholder business.com emails)
    result = await session.execute(
        text("""
            SELECT id, first_name, last_name, email, company, phone, status
            FROM leads
            WHERE email NOT LIKE '%business.com%'
            AND email IS NOT NULL
            AND status NOT IN ('unsubscribed', 'do_not_contact', 'converted')
            ORDER BY created_at DESC
            LIMIT :limit
        """),
        {"limit": body.limit}
    )
    leads = result.fetchall()

    sent = 0
    failed = 0
    skipped = 0
    results = []

    for lead in leads:
        lead_dict = {
            "id": str(lead[0]),
            "first_name": lead[1] or "there",
            "last_name": lead[2] or "",
            "email": lead[3],
            "company": lead[4] or "your business",
            "phone": lead[5],
            "status": lead[6],
        }

        result = engine.send_intro_email(lead_dict)

        if result["success"]:
            sent += 1
            # Update lead email_attempts
            await db.increment_email_attempts(session, lead[0])
        elif result.get("reason") == "no_real_email":
            skipped += 1
        else:
            failed += 1

        results.append({
            "lead": f"{lead_dict['first_name']} {lead_dict['last_name']}",
            "email": lead_dict["email"],
            "company": lead_dict["company"],
            **result,
        })

    await session.commit()

    return {
        "sent": sent,
        "failed": failed,
        "skipped": skipped,
        "total": len(leads),
        "results": results,
        "message": f"✅ Sent {sent} emails! Failed: {failed}, Skipped (no email): {skipped}",
    }


@router.get("/email-preview")
async def email_preview(business_name: str = "Your Restaurant"):
    """Preview the Pebble intro email template."""
    from app.core.smart_sequence import SmartSequenceEngine
    engine = SmartSequenceEngine()
    html = engine.get_email_template_preview(business_name)
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)


@router.get("/stats")
async def campaign_stats(session: AsyncSession = Depends(get_session)):
    """Get email campaign stats."""
    result = await session.execute(text("""
        SELECT 
            COUNT(*) as total_leads,
            COUNT(CASE WHEN email NOT LIKE '%business.com%' AND email IS NOT NULL THEN 1 END) as emailable,
            SUM(email_attempts) as total_emails_sent,
            COUNT(CASE WHEN status = 'interested' THEN 1 END) as interested,
            COUNT(CASE WHEN status = 'demo_scheduled' THEN 1 END) as demos,
            COUNT(CASE WHEN status = 'converted' THEN 1 END) as converted
        FROM leads
    """))
    row = result.fetchone()
    return {
        "total_leads": row[0],
        "emailable_leads": row[1],
        "total_emails_sent": row[2] or 0,
        "interested": row[3],
        "demos_scheduled": row[4],
        "converted": row[5],
    }
