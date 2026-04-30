"""Bookings REST API endpoints."""
from __future__ import annotations

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import get_session
from app.database.service import DatabaseService
from app.models.enums import BookingStatus

router = APIRouter()
db = DatabaseService()


class BookingUpdate(BaseModel):
    status: Optional[str] = None
    meeting_link: Optional[str] = None


@router.get("")
async def list_bookings(session: AsyncSession = Depends(get_session)):
    from sqlalchemy import select
    from app.models.booking import Booking
    result = await session.execute(select(Booking).order_by(Booking.scheduled_at))
    bookings = result.scalars().all()
    return [_booking_dict(b) for b in bookings]


@router.get("/{booking_id}")
async def get_booking(booking_id: str, session: AsyncSession = Depends(get_session)):
    booking = await db.get_booking(session, uuid.UUID(booking_id))
    if not booking:
        raise HTTPException(404, "Booking not found")
    return _booking_dict(booking)


@router.patch("/{booking_id}")
async def update_booking(booking_id: str, body: BookingUpdate, session: AsyncSession = Depends(get_session)):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    booking = await db.update_booking(session, uuid.UUID(booking_id), **fields)
    await session.commit()
    return _booking_dict(booking)


@router.post("/{booking_id}/cancel")
async def cancel_booking(booking_id: str, session: AsyncSession = Depends(get_session)):
    booking = await db.update_booking(session, uuid.UUID(booking_id), status=BookingStatus.cancelled)
    await session.commit()
    return _booking_dict(booking)


def _booking_dict(b) -> dict:
    return {
        "id": str(b.id), "lead_id": str(b.lead_id),
        "calendar_event_id": b.calendar_event_id,
        "scheduled_at": b.scheduled_at.isoformat(),
        "duration_minutes": b.duration_minutes,
        "status": b.status, "reminder_sent": b.reminder_sent,
        "meeting_link": b.meeting_link,
    }
