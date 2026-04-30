"""SendGrid email provider — real email delivery with open tracking."""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
load_dotenv()  # Force reload .env

from .email_provider import EmailProvider, EmailSendResult

logger = logging.getLogger(__name__)


class SendGridProvider(EmailProvider):
    """Real SendGrid email delivery with open/click tracking."""

    def __init__(self) -> None:
        self._api_key  = os.environ.get("SENDGRID_API_KEY", "")
        self._from_email = os.environ.get("FROM_EMAIL", "priya@pebble.com")
        self._from_name  = os.environ.get("FROM_NAME", "Priya from Pebble")

    def send(self, to: str, subject: str, body: str, email_id: str) -> EmailSendResult:
        """Send email via SendGrid REST API."""
        if not self._api_key:
            return EmailSendResult(success=False, error="SENDGRID_API_KEY not set")

        import requests

        payload = {
            "personalizations": [{"to": [{"email": to}]}],
            "from": {"email": self._from_email, "name": self._from_name},
            "subject": subject,
            "content": [{"type": "text/html", "value": body}],
            "tracking_settings": {
                "click_tracking": {"enable": True},
                "open_tracking": {"enable": True},
            },
            "custom_args": {"email_id": email_id},
        }

        try:
            resp = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=15,
            )
            if resp.status_code in (200, 202):
                logger.info("SendGrid: sent to %s (email_id=%s)", to, email_id)
                return EmailSendResult(success=True, message_id=email_id)
            else:
                logger.error("SendGrid error %s: %s", resp.status_code, resp.text)
                return EmailSendResult(success=False, error=f"{resp.status_code}: {resp.text}")
        except Exception as exc:
            logger.error("SendGrid exception: %s", exc)
            return EmailSendResult(success=False, error=str(exc))

    def schedule(self, to: str, subject: str, body: str, email_id: str, send_at: datetime) -> str:
        """Schedule email for later delivery."""
        import requests
        import time

        send_at_unix = int(send_at.timestamp())
        payload = {
            "personalizations": [{"to": [{"email": to}]}],
            "from": {"email": self._from_email, "name": self._from_name},
            "subject": subject,
            "content": [{"type": "text/html", "value": body}],
            "send_at": send_at_unix,
            "custom_args": {"email_id": email_id},
        }

        try:
            resp = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=15,
            )
            return email_id if resp.status_code in (200, 202) else ""
        except Exception:
            return ""
