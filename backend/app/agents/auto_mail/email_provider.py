"""EmailProvider interface and StubEmailProvider.

Abstracts the email delivery backend (SendGrid, AWS SES, Mailgun, etc.)
so the AutoMailAgent can be tested without real network calls.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class EmailSendResult:
    """Result returned by EmailProvider.send()."""

    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class EmailProvider:
    """Abstract interface for email delivery providers."""

    def send(
        self,
        to: str,
        subject: str,
        body: str,
        email_id: str,
    ) -> EmailSendResult:
        """Send an email immediately.

        Parameters
        ----------
        to:      Recipient email address.
        subject: Email subject line.
        body:    Email body (plain text or HTML).
        email_id: Unique identifier for tracking this send event.

        Returns
        -------
        EmailSendResult with success flag and provider message ID.
        """
        raise NotImplementedError

    def schedule(
        self,
        to: str,
        subject: str,
        body: str,
        email_id: str,
        send_at: datetime,
    ) -> str:
        """Schedule an email for deferred delivery.

        Returns the provider-assigned scheduled message ID.
        """
        raise NotImplementedError


class StubEmailProvider(EmailProvider):
    """In-memory stub that records sent/scheduled emails without real delivery.

    Useful for unit tests and local development.
    """

    def __init__(self, fail: bool = False) -> None:
        """
        Parameters
        ----------
        fail:
            When True, every send() call returns a failure result (simulates
            delivery failure for retry testing).
        """
        self.sent: list[dict] = []
        self.scheduled: list[dict] = []
        self._fail = fail

    def send(
        self,
        to: str,
        subject: str,
        body: str,
        email_id: str,
    ) -> EmailSendResult:
        if self._fail:
            logger.debug("StubEmailProvider: simulating delivery failure for %s", email_id)
            return EmailSendResult(success=False, error="Simulated delivery failure")

        record = {
            "to": to,
            "subject": subject,
            "body": body,
            "email_id": email_id,
            "sent_at": datetime.utcnow().isoformat(),
        }
        self.sent.append(record)
        message_id = f"stub-msg-{uuid.uuid4().hex[:8]}"
        logger.debug("StubEmailProvider: sent email %s to %s", message_id, to)
        return EmailSendResult(success=True, message_id=message_id)

    def schedule(
        self,
        to: str,
        subject: str,
        body: str,
        email_id: str,
        send_at: datetime,
    ) -> str:
        record = {
            "to": to,
            "subject": subject,
            "body": body,
            "email_id": email_id,
            "send_at": send_at.isoformat(),
        }
        self.scheduled.append(record)
        scheduled_id = f"stub-sched-{uuid.uuid4().hex[:8]}"
        logger.debug("StubEmailProvider: scheduled email %s to %s at %s", scheduled_id, to, send_at)
        return scheduled_id
