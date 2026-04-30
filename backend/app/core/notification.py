"""NotificationService — in-app event emission and Slack webhook delivery.

In-app events are published to a Redis pub/sub channel so the WebSocket
server (Task 13) can subscribe and forward them to connected dashboard
clients (Requirement 17).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import httpx
import redis as redis_lib

logger = logging.getLogger(__name__)

# Redis pub/sub channel name for in-app events.
IN_APP_CHANNEL = "ai_sales:events"

# Valid event types (Requirement 17.1).
EVENT_TYPES = frozenset(
    [
        "agent.status_changed",
        "task.completed",
        "task.failed",
        "lead.status_changed",
        "notification.new",
        "kpi.updated",
    ]
)


class NotificationService:
    """Broadcasts system events to in-app subscribers and Slack.

    Parameters
    ----------
    redis_url:
        Redis connection URL used for pub/sub.
    slack_webhook_url:
        Optional Slack incoming-webhook URL.  Slack delivery is silently
        skipped when this is ``None``.
    http_client:
        Optional :class:`httpx.Client` for Slack HTTP calls.  A new client
        is created if not provided.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        slack_webhook_url: Optional[str] = None,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self._redis_url = redis_url
        self._slack_webhook_url = slack_webhook_url
        self._http_client = http_client or httpx.Client(timeout=10.0)
        self._redis: Optional[redis_lib.Redis] = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_redis(self) -> redis_lib.Redis:
        if self._redis is None:
            self._redis = redis_lib.from_url(self._redis_url, decode_responses=True)
        return self._redis

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Publish an event to the Redis pub/sub channel.

        The WebSocket server subscribes to ``IN_APP_CHANNEL`` and forwards
        messages to connected dashboard clients.

        Parameters
        ----------
        event_type:
            One of the defined event type strings (e.g. ``"task.completed"``).
        payload:
            Arbitrary JSON-serialisable data describing the event.
        """
        message = json.dumps({"event_type": event_type, "payload": payload})
        try:
            self._get_redis().publish(IN_APP_CHANNEL, message)
        except Exception as exc:
            logger.warning("Failed to publish event '%s' to Redis: %s", event_type, exc)

    def send_slack(self, message: str) -> None:
        """Post a plain-text message to the configured Slack webhook.

        Silently skips if no webhook URL is configured.
        """
        if not self._slack_webhook_url:
            return
        try:
            response = self._http_client.post(
                self._slack_webhook_url,
                json={"text": message},
            )
            response.raise_for_status()
        except Exception as exc:
            logger.warning("Failed to send Slack notification: %s", exc)

    def notify_admin(self, message: str, event_type: str = "system") -> None:
        """Emit an in-app event and post to Slack.

        Combines :meth:`emit` and :meth:`send_slack` for admin-level alerts.

        Parameters
        ----------
        message:
            Human-readable alert text (used as the Slack message body and
            included in the event payload).
        event_type:
            Event type string for the in-app emission.  Defaults to
            ``"system"``.
        """
        self.emit(event_type, {"message": message})
        self.send_slack(message)
