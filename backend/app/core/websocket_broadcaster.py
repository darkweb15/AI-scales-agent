"""In-process WebSocket broadcaster — no Redis required.

Replaces Redis pub/sub with a direct asyncio broadcast.
All agents and the orchestrator call broadcast() directly.
Works in dev and production without any external dependencies.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Global set of connected WebSocket clients
_clients: Set[WebSocket] = set()
# Event queue for buffering events when no clients connected
_event_buffer: list = []
MAX_BUFFER = 100


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def broadcast(event_type: str, payload: Dict[str, Any]) -> None:
    """Broadcast an event to ALL connected dashboard clients instantly.

    Called directly by agents, orchestrator, and webhooks.
    No Redis, no pub/sub — pure asyncio.
    """
    message = json.dumps({
        "event_type": event_type,
        "payload": payload,
        "timestamp": _now_iso(),
    })

    # Buffer for late-joining clients
    _event_buffer.append(message)
    if len(_event_buffer) > MAX_BUFFER:
        _event_buffer.pop(0)

    if not _clients:
        return

    disconnected: Set[WebSocket] = set()
    for ws in list(_clients):
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.add(ws)

    _clients.difference_update(disconnected)
    if disconnected:
        logger.debug("Removed %d disconnected WebSocket clients", len(disconnected))


def broadcast_sync(event_type: str, payload: Dict[str, Any]) -> None:
    """Fire-and-forget broadcast from sync context (e.g. notification service)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(broadcast(event_type, payload))
        else:
            loop.run_until_complete(broadcast(event_type, payload))
    except Exception as e:
        logger.debug("broadcast_sync failed: %s", e)


def add_client(ws: WebSocket) -> None:
    _clients.add(ws)
    logger.info("WS client connected. Total: %d", len(_clients))


def remove_client(ws: WebSocket) -> None:
    _clients.discard(ws)
    logger.info("WS client disconnected. Total: %d", len(_clients))


def get_recent_events(limit: int = 50) -> list:
    """Return recent buffered events for new clients to catch up."""
    return _event_buffer[-limit:]


def client_count() -> int:
    return len(_clients)
