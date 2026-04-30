import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base
from .enums import AgentType, Channel, Direction, Intent


class InteractionLog(Base):
    """Append-only record of every touchpoint between the system and a lead."""

    __tablename__ = "interaction_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_type: Mapped[AgentType] = mapped_column(String(50), nullable=False)
    channel: Mapped[Channel] = mapped_column(String(20), nullable=False)
    direction: Mapped[Direction] = mapped_column(String(20), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    intent_detected: Mapped[Optional[Intent]] = mapped_column(String(50), nullable=True)
    outcome: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raw_transcript: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<InteractionLog id={self.id} lead_id={self.lead_id} "
            f"channel={self.channel} direction={self.direction}>"
        )
