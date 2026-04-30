"""WebSocket server for real-time dashboard updates."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()

# Connected clients
_clients: Set[WebSocket] = set()


async def broadcast(event_type: str, payload: dict) -> None:
    """Broadcast an event to all connected WebSocket clients."""
    message = json.dumps({"event_type": event_type, "payload": payload})
    disconnected = set()
    for ws in _clients:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.add(ws)
    _clients.difference_update(disconnected)


@router.websocket("/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _clients.add(websocket)
    logger.info("WebSocket client connected. Total: %d", len(_clients))

    # Send initial connection confirmation
    await websocket.send_text(json.dumps({
        "event_type": "connected",
        "payload": {"message": "Connected to SalesAI real-time feed"}
    }))

    try:
        while True:
            # Keep connection alive, listen for client pings
            data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
            if data == "ping":
                await websocket.send_text(json.dumps({"event_type": "pong", "payload": {}}))
    except (WebSocketDisconnect, asyncio.TimeoutError):
        pass
    finally:
        _clients.discard(websocket)
        logger.info("WebSocket client disconnected. Total: %d", len(_clients))
