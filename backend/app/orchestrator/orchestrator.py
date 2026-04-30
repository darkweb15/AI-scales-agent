"""Orchestrator — central routing engine for the AI Sales Automation System.

Responsibilities (Requirements 1.1 – 1.10):
- Poll the database for leads pending action (Req 1.10)
- Skip leads on cooldown (Req 1.7, 1.8)
- Route each lead to the correct agent via evaluate_lead (Req 1.1 – 1.6)
- Dispatch tasks through the TaskQueue (Req 9.1)
- Persist task outcomes back to the database (Req 1.9)
- Emit lead.status_changed events via NotificationService
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..core.config import Config
from ..core.notification import NotificationService
from ..core.task_queue import TaskQueue
from ..database.service import DatabaseService
from ..models.enums import AgentType, LeadStatus
from .routing import RoutingConfig, RoutingTask, evaluate_lead, is_on_cooldown

logger = logging.getLogger(__name__)


@dataclass
class TaskOutcome:
    """Result of an agent task, used to update lead state."""

    lead_id: uuid.UUID
    new_status: Optional[LeadStatus] = None
    last_contacted_at: Optional[datetime] = None
    next_action_at: Optional[datetime] = None
    # Optional extra context (e.g. intent, channel) — not persisted directly
    metadata: Optional[Any] = None


class Orchestrator:
    """Central routing engine.

    Parameters
    ----------
    session_factory:
        SQLAlchemy async session factory (``async_sessionmaker``).
    task_queue:
        ``TaskQueue`` instance for dispatching agent tasks.
    notification_service:
        ``NotificationService`` for emitting events.
    config:
        Application ``Config`` instance.
    db_service:
        Optional ``DatabaseService`` override (useful for testing).
    """

    def __init__(
        self,
        session_factory: async_sessionmaker,
        task_queue: TaskQueue,
        notification_service: NotificationService,
        config: Config,
        db_service: Optional[DatabaseService] = None,
    ) -> None:
        self._session_factory = session_factory
        self._task_queue = task_queue
        self._notification = notification_service
        self._config = config
        self._db = db_service or DatabaseService()
        self._routing_config = RoutingConfig(
            max_cold_call_attempts=config.max_cold_call_attempts,
            follow_up_delay_hours=config.follow_up_delay_hours,
            cooldown_minutes=config.cooldown_minutes,
        )
        self._running = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Start the polling loop.

        Polls the database at ``config.orchestrator_poll_interval_seconds``
        intervals, evaluates each pending lead, and dispatches tasks.
        Runs until :meth:`stop` is called.

        Requirement 1.10.
        """
        self._running = True
        logger.info(
            "Orchestrator started (poll interval: %ds)",
            self._config.orchestrator_poll_interval_seconds,
        )
        while self._running:
            try:
                await self._tick()
            except Exception as exc:
                logger.exception("Orchestrator tick failed: %s", exc)
            await asyncio.sleep(self._config.orchestrator_poll_interval_seconds)

    def stop(self) -> None:
        """Signal the polling loop to stop after the current tick."""
        self._running = False

    async def evaluate_lead(self, lead: Any) -> Optional[RoutingTask]:
        """Apply routing rules and return the next task for *lead*, or None.

        Delegates to the pure ``routing.evaluate_lead`` function.
        Requirements 1.1 – 1.6.
        """
        now = datetime.now(timezone.utc)
        return evaluate_lead(lead, self._routing_config, now=now)

    async def dispatch(self, task: RoutingTask) -> None:
        """Enqueue *task* via the TaskQueue and update lead's next_action_at.

        Pre-dispatch guard (Req 8.3): verifies the lead is not
        do_not_contact or unsubscribed before enqueueing.

        Requirements 1.9, 8.3, 9.1.
        """
        async with self._session_factory() as session:
            lead = await self._db.get_lead(session, task.lead_id)
            if lead is None:
                logger.warning("dispatch: lead %s not found, skipping", task.lead_id)
                return

            # Pre-dispatch guard — Req 8.3
            if lead.status in (LeadStatus.do_not_contact, LeadStatus.unsubscribed):
                logger.info(
                    "dispatch: lead %s has status %s — skipping dispatch",
                    task.lead_id,
                    lead.status,
                )
                return

            now = datetime.now(timezone.utc)

            # Enqueue via TaskQueue (Req 9.1)
            celery_task_id = self._task_queue.enqueue(
                agent_type=task.agent_type,
                action=task.action,
                lead_id=task.lead_id,
                payload=task.payload,
            )

            # Persist AgentTask record
            await self._db.create_agent_task(
                session,
                {
                    "lead_id": task.lead_id,
                    "agent_type": task.agent_type,
                    "action": task.action,
                    "payload": {**task.payload, "celery_task_id": celery_task_id},
                    "scheduled_at": now,
                },
            )

            # Update lead's next_action_at
            await self._db.update_lead(
                session, task.lead_id, next_action_at=now
            )

            await session.commit()
            logger.info(
                "dispatch: enqueued %s/%s for lead %s (celery_id=%s)",
                task.agent_type,
                task.action,
                task.lead_id,
                celery_task_id,
            )

    async def handle_outcome(self, outcome: TaskOutcome) -> None:
        """Persist a task outcome and emit a lead.status_changed event.

        Updates lead status, last_contacted_at, and next_action_at in the
        database, then emits a ``lead.status_changed`` event via the
        NotificationService.

        Requirement 1.9.
        """
        async with self._session_factory() as session:
            fields: dict = {}
            if outcome.new_status is not None:
                fields["status"] = outcome.new_status
            if outcome.last_contacted_at is not None:
                fields["last_contacted_at"] = outcome.last_contacted_at
            if outcome.next_action_at is not None:
                fields["next_action_at"] = outcome.next_action_at

            if fields:
                await self._db.update_lead(session, outcome.lead_id, **fields)

            await session.commit()

        # Emit event (outside transaction — fire-and-forget)
        self._notification.emit(
            "lead.status_changed",
            {
                "lead_id": str(outcome.lead_id),
                "new_status": outcome.new_status.value if outcome.new_status else None,
                "last_contacted_at": (
                    outcome.last_contacted_at.isoformat()
                    if outcome.last_contacted_at
                    else None
                ),
            },
        )
        logger.info(
            "handle_outcome: lead %s updated (status=%s)",
            outcome.lead_id,
            outcome.new_status,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _tick(self) -> None:
        """Single poll iteration: query pending leads and dispatch tasks."""
        now = datetime.now(timezone.utc)
        async with self._session_factory() as session:
            leads = await self._db.query_leads_pending_action(session, now)

        logger.debug("_tick: %d leads pending action", len(leads))

        for lead in leads:
            try:
                # Req 1.7 / 1.8 — skip leads on cooldown
                if is_on_cooldown(lead, self._routing_config, now=now):
                    logger.debug("_tick: lead %s is on cooldown, skipping", lead.id)
                    continue

                task = await self.evaluate_lead(lead)
                if task is not None:
                    await self.dispatch(task)
            except Exception as exc:
                logger.exception(
                    "_tick: error processing lead %s: %s", lead.id, exc
                )
