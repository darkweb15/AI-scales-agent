"""Notifications REST API endpoints."""
from __future__ import annotations

from typing import List
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

# In-memory notification store (replace with DB in production)
_notifications = [
    {"id": "1", "type": "Escalation", "title": "Lead requires review", "message": "Sarah Johnson escalated after 5 attempts", "read": False, "created_at": "2026-04-24T18:00:00Z"},
    {"id": "2", "type": "Error",      "title": "Call Answering Agent error", "message": "Telephony API timeout", "read": False, "created_at": "2026-04-24T17:45:00Z"},
    {"id": "3", "type": "Success",    "title": "Demo confirmed", "message": "Acme Corp demo booked for Apr 26", "read": True,  "created_at": "2026-04-24T16:30:00Z"},
    {"id": "4", "type": "Reminder",   "title": "Demo in 24h", "message": "NexGen AI demo tomorrow at 2 PM", "read": False, "created_at": "2026-04-24T14:00:00Z"},
    {"id": "5", "type": "System",     "title": "Auto Mail paused", "message": "Operator paused Auto Mail agent", "read": True,  "created_at": "2026-04-24T12:00:00Z"},
]


@router.get("")
async def list_notifications(unread_only: bool = False):
    if unread_only:
        return [n for n in _notifications if not n["read"]]
    return _notifications


@router.post("/{notification_id}/read")
async def mark_read(notification_id: str):
    for n in _notifications:
        if n["id"] == notification_id:
            n["read"] = True
    return {"success": True}


@router.post("/read-all")
async def mark_all_read():
    for n in _notifications:
        n["read"] = True
    return {"success": True}


@router.get("/unread-count")
async def unread_count():
    return {"count": sum(1 for n in _notifications if not n["read"])}
