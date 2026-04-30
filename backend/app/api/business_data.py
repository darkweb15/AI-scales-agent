"""Business data API — connects to the business_data table in Supabase."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import get_session

router = APIRouter()


@router.get("")
async def list_business_data(
    search: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    """Fetch real business records from business_data table."""
    if search:
        result = await session.execute(
            text("""
                SELECT id, task_id, name, address, phone
                FROM business_data
                WHERE name ILIKE :search OR address ILIKE :search OR phone ILIKE :search
                ORDER BY id
                LIMIT :limit OFFSET :offset
            """),
            {"search": f"%{search}%", "limit": limit, "offset": offset}
        )
    else:
        result = await session.execute(
            text("""
                SELECT id, task_id, name, address, phone
                FROM business_data
                ORDER BY id
                LIMIT :limit OFFSET :offset
            """),
            {"limit": limit, "offset": offset}
        )

    rows = result.fetchall()
    return [
        {
            "id": str(r[0]),
            "task_id": r[1],
            "name": r[2],
            "address": r[3],
            "phone": r[4],
        }
        for r in rows
    ]


@router.get("/stats")
async def get_business_stats(session: AsyncSession = Depends(get_session)):
    """Get comprehensive stats from business_data table."""
    total = (await session.execute(text("SELECT COUNT(*) FROM business_data"))).scalar()
    with_phone = (await session.execute(
        text("SELECT COUNT(*) FROM business_data WHERE phone IS NOT NULL AND phone != ''")
    )).scalar()
    with_address = (await session.execute(
        text("SELECT COUNT(*) FROM business_data WHERE address IS NOT NULL AND address != ''")
    )).scalar()

    # Skip state breakdown for now (slow on 26K records without index)
    states = []

    # Phone coverage
    no_phone = total - with_phone

    return {
        "total_records": total,
        "with_phone": with_phone,
        "without_phone": no_phone,
        "with_address": with_address,
        "phone_coverage_pct": round((with_phone / total * 100), 1) if total else 0,
        "address_coverage_pct": round((with_address / total * 100), 1) if total else 0,
        "top_states": states,
    }


@router.post("/import-as-leads")
async def import_as_leads(
    limit: int = Query(10, le=50),
    session: AsyncSession = Depends(get_session),
):
    """Import business_data records as leads into the leads table."""
    from app.database.service import DatabaseService
    from app.models.enums import LeadStatus

    db = DatabaseService()

    # Get businesses that aren't already leads
    result = await session.execute(
        text("""
            SELECT b.id, b.name, b.address, b.phone
            FROM business_data b
            WHERE b.phone IS NOT NULL AND b.phone != ''
            AND NOT EXISTS (
                SELECT 1 FROM leads l WHERE l.phone = b.phone
            )
            LIMIT :limit
        """),
        {"limit": limit}
    )
    rows = result.fetchall()

    imported = 0
    for row in rows:
        bid, name, address, phone = row
        # Parse name into first/last
        parts = (name or "Business").split(" ", 1)
        first = parts[0]
        last = parts[1] if len(parts) > 1 else ""

        try:
            await db.create_lead(session, {
                "first_name": first[:50],
                "last_name": last[:50],
                "email": f"contact_{bid}@business.com",
                "phone": phone,
                "company": name[:255] if name else "Unknown",
                "status": LeadStatus.new,
                "source": "business_data",
                "call_attempts": 0,
                "email_attempts": 0,
                "notes": f"Address: {address}" if address else "",
                "tags": ["business_data", "imported"],
            })
            imported += 1
        except Exception:
            pass  # Skip duplicates

    await session.commit()
    return {"imported": imported, "message": f"Successfully imported {imported} businesses as leads"}
