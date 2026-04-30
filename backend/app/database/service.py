"""DatabaseService — central CRUD layer used by all agents and the Orchestrator."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.agent_task import AgentTask
from ..models.booking import Booking
from ..models.email_template import EmailTemplate
from ..models.enums import LeadStatus, TaskStatus
from ..models.interaction_log import InteractionLog
from ..models.lead import Lead


class DatabaseService:
    """Provides all database operations for agents and the Orchestrator.

    Every method accepts an AsyncSession so callers control transaction scope.
    """

    # ------------------------------------------------------------------
    # Lead operations
    # ------------------------------------------------------------------

    async def get_lead(self, session: AsyncSession, lead_id: uuid.UUID) -> Optional[Lead]:
        """Return a Lead by primary key, or None if not found."""
        result = await session.get(Lead, lead_id)
        return result

    async def create_lead(self, session: AsyncSession, data: Dict[str, Any]) -> Lead:
        """Create and persist a new Lead record."""
        lead = Lead(**data)
        if lead.id is None:
            lead.id = uuid.uuid4()
        session.add(lead)
        await session.flush()
        await session.refresh(lead)
        return lead

    async def update_lead_status(
        self, session: AsyncSession, lead_id: uuid.UUID, status: LeadStatus
    ) -> Optional[Lead]:
        """Update only the status field of a lead."""
        await session.execute(
            update(Lead)
            .where(Lead.id == lead_id)
            .values(status=status, updated_at=datetime.utcnow())
        )
        return await self.get_lead(session, lead_id)

    async def update_lead(
        self, session: AsyncSession, lead_id: uuid.UUID, **fields: Any
    ) -> Optional[Lead]:
        """Update arbitrary fields on a lead."""
        fields["updated_at"] = datetime.utcnow()
        await session.execute(
            update(Lead).where(Lead.id == lead_id).values(**fields)
        )
        return await self.get_lead(session, lead_id)

    async def increment_call_attempts(
        self, session: AsyncSession, lead_id: uuid.UUID
    ) -> Optional[Lead]:
        """Atomically increment call_attempts by 1."""
        lead = await self.get_lead(session, lead_id)
        if lead is None:
            return None
        await session.execute(
            update(Lead)
            .where(Lead.id == lead_id)
            .values(
                call_attempts=Lead.call_attempts + 1,
                updated_at=datetime.utcnow(),
            )
        )
        await session.refresh(lead)
        return lead

    async def increment_email_attempts(
        self, session: AsyncSession, lead_id: uuid.UUID
    ) -> Optional[Lead]:
        """Atomically increment email_attempts by 1."""
        lead = await self.get_lead(session, lead_id)
        if lead is None:
            return None
        await session.execute(
            update(Lead)
            .where(Lead.id == lead_id)
            .values(
                email_attempts=Lead.email_attempts + 1,
                updated_at=datetime.utcnow(),
            )
        )
        await session.refresh(lead)
        return lead

    async def find_lead_by_email(
        self, session: AsyncSession, email: str
    ) -> Optional[Lead]:
        """Look up a lead by email address (case-insensitive)."""
        result = await session.execute(
            select(Lead).where(Lead.email.ilike(email))
        )
        return result.scalar_one_or_none()

    async def find_lead_by_phone(
        self, session: AsyncSession, phone: str
    ) -> Optional[Lead]:
        """Look up a lead by phone number."""
        result = await session.execute(
            select(Lead).where(Lead.phone == phone)
        )
        return result.scalar_one_or_none()

    async def query_leads_pending_action(
        self, session: AsyncSession, now: datetime
    ) -> List[Lead]:
        """Return leads that are due for action.

        A lead is pending action when:
          - next_action_at <= now, OR
          - next_action_at IS NULL AND status = 'new'

        Excludes do_not_contact and unsubscribed leads.
        """
        result = await session.execute(
            select(Lead).where(
                and_(
                    Lead.status.notin_([LeadStatus.do_not_contact, LeadStatus.unsubscribed]),
                    or_(
                        Lead.next_action_at <= now,
                        and_(
                            Lead.next_action_at.is_(None),
                            Lead.status == LeadStatus.new,
                        ),
                    ),
                )
            )
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # InteractionLog operations (append-only — no update/delete exposed)
    # Requirement 8.2: The InteractionLog is append-only. No update or delete
    # methods are provided. Once written, entries cannot be modified.
    # ------------------------------------------------------------------

    async def create_interaction_log(
        self, session: AsyncSession, data: Dict[str, Any]
    ) -> InteractionLog:
        """Append a new interaction log entry. No update or delete is provided."""
        log = InteractionLog(**data)
        if log.id is None:
            log.id = uuid.uuid4()
        session.add(log)
        await session.flush()
        await session.refresh(log)
        return log

    async def get_interactions_for_lead(
        self, session: AsyncSession, lead_id: uuid.UUID
    ) -> List[InteractionLog]:
        """Return all interaction logs for a lead, ordered by timestamp ascending."""
        result = await session.execute(
            select(InteractionLog)
            .where(InteractionLog.lead_id == lead_id)
            .order_by(InteractionLog.timestamp.asc())
        )
        return list(result.scalars().all())

    async def get_last_interaction(
        self, session: AsyncSession, lead_id: uuid.UUID
    ) -> Optional[InteractionLog]:
        """Return the most recent interaction log entry for a lead."""
        result = await session.execute(
            select(InteractionLog)
            .where(InteractionLog.lead_id == lead_id)
            .order_by(InteractionLog.timestamp.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # AgentTask operations
    # ------------------------------------------------------------------

    async def create_agent_task(
        self, session: AsyncSession, data: Dict[str, Any]
    ) -> AgentTask:
        """Create and persist a new AgentTask."""
        task = AgentTask(**data)
        if task.id is None:
            task.id = uuid.uuid4()
        session.add(task)
        await session.flush()
        await session.refresh(task)
        return task

    async def update_task_status(
        self, session: AsyncSession, task_id: uuid.UUID, status: TaskStatus
    ) -> Optional[AgentTask]:
        """Update the status of an AgentTask."""
        await session.execute(
            update(AgentTask)
            .where(AgentTask.id == task_id)
            .values(status=status)
        )
        return await self.get_task(session, task_id)

    async def get_task(
        self, session: AsyncSession, task_id: uuid.UUID
    ) -> Optional[AgentTask]:
        """Return an AgentTask by primary key."""
        return await session.get(AgentTask, task_id)

    # ------------------------------------------------------------------
    # Booking operations
    # ------------------------------------------------------------------

    async def save_booking(
        self, session: AsyncSession, data: Dict[str, Any]
    ) -> Booking:
        """Create and persist a new Booking record."""
        booking = Booking(**data)
        if booking.id is None:
            booking.id = uuid.uuid4()
        session.add(booking)
        await session.flush()
        await session.refresh(booking)
        return booking

    async def get_booking(
        self, session: AsyncSession, booking_id: uuid.UUID
    ) -> Optional[Booking]:
        """Return a Booking by primary key."""
        return await session.get(Booking, booking_id)

    async def update_booking(
        self, session: AsyncSession, booking_id: uuid.UUID, **fields: Any
    ) -> Optional[Booking]:
        """Update arbitrary fields on a Booking."""
        fields["updated_at"] = datetime.utcnow()
        await session.execute(
            update(Booking).where(Booking.id == booking_id).values(**fields)
        )
        return await self.get_booking(session, booking_id)

    # ------------------------------------------------------------------
    # EmailTemplate operations
    # ------------------------------------------------------------------

    async def get_email_template(
        self, session: AsyncSession, name: str
    ) -> Optional[EmailTemplate]:
        """Return an EmailTemplate by its unique name."""
        result = await session.execute(
            select(EmailTemplate).where(EmailTemplate.name == name)
        )
        return result.scalar_one_or_none()

    async def list_email_templates(
        self, session: AsyncSession
    ) -> List[EmailTemplate]:
        """Return all EmailTemplate records."""
        result = await session.execute(select(EmailTemplate))
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Escalation helpers (Requirement 8.4)
    # ------------------------------------------------------------------

    async def escalate_task_permanently_failed(
        self,
        session: AsyncSession,
        task_id: uuid.UUID,
        lead_id: uuid.UUID,
    ) -> None:
        """Mark a task as permanently_failed and set lead to requires_human_review.

        Called when an AgentTask exceeds config.maxTaskRetries (Req 8.4).

        Parameters
        ----------
        session:
            Database session for transaction control.
        task_id:
            AgentTask primary key.
        lead_id:
            Lead primary key to escalate.
        """
        await self.update_task_status(session, task_id, TaskStatus.permanently_failed)
        await self.update_lead_status(session, lead_id, LeadStatus.requires_human_review)
