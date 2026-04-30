"""WebSocket server — real-time dashboard updates without Redis.

Uses the in-process broadcaster (websocket_broadcaster.py).
Clients receive live events the moment they happen — no polling.
"""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.websocket_broadcaster import (
    add_client,
    remove_client,
    get_recent_events,
    broadcast,
    client_count,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    """Main dashboard WebSocket connection.

    On connect:
    - Sends last 50 buffered events so client catches up immediately
    - Registers client for all future broadcasts

    Stays alive via ping/pong keepalive.
    """
    await websocket.accept()
    add_client(websocket)

    # Send connection confirmation
    await websocket.send_text(json.dumps({
        "event_type": "connected",
        "payload": {
            "message": "Connected to SalesAI real-time feed",
            "clients": client_count(),
        },
    }))

    # Replay recent events so client doesn't miss anything
    recent = get_recent_events(50)
    if recent:
        for event in recent:
            try:
                await websocket.send_text(event)
            except Exception:
                break

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                if data == "ping":
                    await websocket.send_text(json.dumps({
                        "event_type": "pong",
                        "payload": {"clients": client_count()},
                    }))
            except asyncio.TimeoutError:
                # Send keepalive ping to detect dead connections
                try:
                    await websocket.send_text(json.dumps({
                        "event_type": "heartbeat",
                        "payload": {"clients": client_count()},
                    }))
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug("WebSocket error: %s", e)
    finally:
        remove_client(websocket)
