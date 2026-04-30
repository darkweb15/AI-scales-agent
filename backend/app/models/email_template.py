import uuid
from typing import List, Optional

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base
from .enums import AgentType, LeadStatus


class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    subject_template: Mapped[str] = mapped_column(Text, nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    agent_type: Mapped[AgentType] = mapped_column(String(50), nullable=False, index=True)
    stage: Mapped[Optional[LeadStatus]] = mapped_column(String(50), nullable=True)
    variables: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String), nullable=True, default=list
    )

    def __repr__(self) -> str:
        return f"<EmailTemplate id={self.id} name={self.name} agent={self.agent_type}>"
