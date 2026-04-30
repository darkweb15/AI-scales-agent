"""TaskQueue — Celery + Redis wrapper for dispatching agent tasks.

Each AgentType maps to its own Celery queue so agents can be scaled
independently (Requirement 9.3).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from celery import Celery
from celery.result import AsyncResult

from ..models.enums import AgentType

# Queue name mapping — one queue per agent type.
AGENT_QUEUE_MAP: Dict[AgentType, str] = {
    AgentType.cold_calling: "queue.cold_calling",
    AgentType.follow_up: "queue.follow_up",
    AgentType.demo_scheduling: "queue.demo_scheduling",
    AgentType.auto_mail: "queue.auto_mail",
    AgentType.auto_reply: "queue.auto_reply",
    AgentType.call_answering: "queue.call_answering",
}

# Celery task name used for all agent dispatches.
_AGENT_TASK_NAME = "ai_sales.run_agent_action"


class TaskQueue:
    """Thin wrapper around Celery that provides a typed interface for
    enqueueing, cancelling, and inspecting agent tasks.

    Parameters
    ----------
    celery_app:
        A configured :class:`celery.Celery` instance.  Pass the module-level
        ``celery_app`` from ``backend.app.celery_app`` in production; inject a
        test double in unit tests.
    """

    def __init__(self, celery_app: Celery) -> None:
        self._app = celery_app
        self._register_task()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _register_task(self) -> None:
        """Ensure the generic agent-action task is registered on the app."""
        if _AGENT_TASK_NAME not in self._app.tasks:
            @self._app.task(name=_AGENT_TASK_NAME, bind=True, max_retries=None)
            def run_agent_action(self_task, agent_type: str, action: str,
                                 lead_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
                """Generic Celery task that agents consume from their queue."""
                # Actual agent execution is wired in by each agent module.
                # This stub records the parameters and returns them so the
                # result backend stores the call metadata.
                return {
                    "agent_type": agent_type,
                    "action": action,
                    "lead_id": lead_id,
                    "payload": payload,
                }

    def _queue_for(self, agent_type: AgentType) -> str:
        return AGENT_QUEUE_MAP[agent_type]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enqueue(
        self,
        agent_type: AgentType,
        action: str,
        lead_id: uuid.UUID,
        payload: Dict[str, Any],
        priority: int = 5,
        eta: Optional[datetime] = None,
    ) -> str:
        """Dispatch a task to the agent's dedicated queue.

        Parameters
        ----------
        agent_type:
            Which agent should process this task.
        action:
            The action string (e.g. ``"call"``, ``"send_intro_email"``).
        lead_id:
            UUID of the lead this task concerns.
        payload:
            Arbitrary JSON-serialisable data for the agent.
        priority:
            Celery task priority (0 = highest, 9 = lowest).  Default 5.
        eta:
            Optional earliest execution time (UTC).

        Returns
        -------
        str
            The Celery task ID (UUID string).
        """
        queue_name = self._queue_for(agent_type)
        kwargs: Dict[str, Any] = dict(
            args=[agent_type.value, action, str(lead_id), payload],
            queue=queue_name,
            priority=priority,
        )
        if eta is not None:
            kwargs["eta"] = eta

        result: AsyncResult = self._app.send_task(
            _AGENT_TASK_NAME,
            **kwargs,
        )
        return result.id

    def cancel(self, task_id: str) -> bool:
        """Revoke a queued or running task.

        Returns ``True`` if the revoke command was sent (does not guarantee
        the task was not already executing).
        """
        try:
            self._app.control.revoke(task_id, terminate=True, signal="SIGTERM")
            return True
        except Exception:
            return False

    def get_queue_depth(self, agent_type: AgentType) -> int:
        """Return the approximate number of tasks waiting in the agent's queue.

        Uses the Redis ``LLEN`` command on the queue's key.  Returns 0 if the
        broker is unreachable or the queue does not exist.
        """
        queue_name = self._queue_for(agent_type)
        try:
            with self._app.connection_for_read() as conn:
                with conn.channel() as channel:
                    # Kombu stores tasks in a list named after the queue.
                    return channel.client.llen(queue_name)
        except Exception:
            return 0
