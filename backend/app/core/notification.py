"""NotificationService — in-process event emission + Slack delivery.

Uses the in-process WebSocket broadcaster instead of Redis pub/sub.
Works without any external dependencies in dev and production.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

EVENT_TYPES = frozenset([
    "agent.status_changed",
    "agent.action_completed",
    "task.completed",
    "task.failed",
    "lead.status_changed",
    "lead.escalated",
    "lead.scored",
    "notification.new",
    "kpi.updated",
    "call.completed",
    "email.sent",
    "demo.scheduled",
])


class NotificationService:
    """Broadcasts system events to dashboard clients and Slack.

    Uses in-process WebSocket broadcaster — no Redis required.
    """

    def __init__(
        self,
        slack_webhook_url: Optional[str] = None,
        http_client: Optional[httpx.Client] = None,
        redis_url: Optional[str] = None,  # kept for API compatibility, ignored
    ) -> None:
        self._slack_webhook_url = slack_webhook_url
        self._http_client = http_client or httpx.Client(timeout=10.0)

    def emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Broadcast an event to all connected dashboard clients instantly."""
        from app.core.websocket_broadcaster import broadcast_sync
        broadcast_sync(event_type, payload)

    async def emit_async(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Async version — use this from async contexts for better performance."""
        from app.core.websocket_broadcaster import broadcast
        await broadcast(event_type, payload)

    def send_slack(self, message: str) -> None:
        """Post a message to Slack webhook."""
        if not self._slack_webhook_url:
            return
        try:
            self._http_client.post(self._slack_webhook_url, json={"text": message})
        except Exception as e:
            logger.warning("Slack notification failed: %s", e)

    def notify_admin(self, message: str, event_type: str = "notification.new") -> None:
        """Emit in-app event and post to Slack."""
        self.emit(event_type, {"message": message, "level": "info"})
        self.send_slack(message)

    def notify_escalation(self, lead_id: str, reason: str, agent: str) -> None:
        """Emit escalation event — shows up in dashboard notification center."""
        self.emit("lead.escalated", {
            "lead_id": lead_id,
            "reason": reason,
            "agent": agent,
            "level": "warning",
        })
        self.send_slack(f"🚨 Lead {lead_id[:8]} escalated by {agent}: {reason}")

    def notify_call_completed(self, lead_id: str, outcome: str, score: int = 0) -> None:
        """Emit call completion event to dashboard."""
        self.emit("call.completed", {
            "lead_id": lead_id,
            "outcome": outcome,
            "score": score,
        })

    def notify_demo_scheduled(self, lead_id: str, lead_name: str, scheduled_at: str) -> None:
        """Emit demo scheduled event — updates KPI cards."""
        self.emit("demo.scheduled", {
            "lead_id": lead_id,
            "lead_name": lead_name,
            "scheduled_at": scheduled_at,
        })
        self.emit("kpi.updated", {"metric": "demos_scheduled", "delta": 1})
