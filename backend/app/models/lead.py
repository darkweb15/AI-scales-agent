import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database.base import Base
from .enums import AgentType, LeadStatus

# ---------------------------------------------------------------------------
# PII Encryption Placeholder (Requirement 8.5)
# ---------------------------------------------------------------------------
# In production, replace the standard String columns for PII fields (first_name,
# last_name, email, phone) with column-level encryption using Fernet symmetric
# encryption via SQLAlchemy TypeDecorator.
#
# Example implementation:
#
#   from cryptography.fernet import Fernet
#   from sqlalchemy import TypeDecorator
#
#   class EncryptedString(TypeDecorator):
#       impl = Text
#       cache_ok = True
#
#       def __init__(self, key: bytes, *args, **kwargs):
#           self._fernet = Fernet(key)
#           super().__init__(*args, **kwargs)
#
#       def process_bind_param(self, value, dialect):
#           if value is None:
#               return None
#           return self._fernet.encrypt(value.encode()).decode()
#
#       def process_result_value(self, value, dialect):
#           if value is None:
#               return None
#           return self._fernet.decrypt(value.encode()).decode()
#
# Then replace `String(255)` with `EncryptedString(key=FERNET_KEY)` for
# first_name, last_name, email, and phone columns.
# The FERNET_KEY must be stored in a secrets manager (AWS Secrets Manager,
# HashiCorp Vault) — never in environment variables or source code.
# ---------------------------------------------------------------------------


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)
    last_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[LeadStatus] = mapped_column(
        String(50), nullable=False, default=LeadStatus.new, index=True
    )
    source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    assigned_agent: Mapped[Optional[AgentType]] = mapped_column(String(50), nullable=True)
    call_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    email_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_contacted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_action_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    demo_scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True, default=list)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<Lead id={self.id} email={self.email} status={self.status}>"
